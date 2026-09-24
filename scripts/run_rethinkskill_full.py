#!/usr/bin/env python3
"""Detached four-setting supervisor. Resume with the same root and frozen inputs."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'packages'),str(ROOT/'packages/rethinkskill/src'),
              str(ROOT/'packages/rethinkskill/integrations/alfworld/src'),str(ROOT/'packages/skillopt')]
from rethinkskill.utils.serde import atomic_write_json
from rethinkskill_study.audit import audit_run
from rethinkskill_study.benchmark_environment import benchmark_provenance
from rethinkskill_study.local_config import benchmark_root, load_local_config
from rethinkskill_study.runtime import retryable_model_failure


def classify_run(out, exit_code):
    """Only a complete, audited run is usable; transient failures may resume."""
    summary_path=out/'summary.json'
    if summary_path.is_file():
        try:
            summary=json.loads(summary_path.read_text())
        except (ValueError, OSError):
            return 'integrity_error', 'unreadable_summary', ['Summary is unreadable']
        if summary.get('status')=='completed':
            errors=audit_run(out)
            return ('completed' if exit_code in (0,None) and not errors else 'integrity_error',
                    'audit_failed' if errors else 'exit_code_mismatch' if exit_code else '', errors)
        failure_class=summary.get('failure_class') or 'unknown_failure'
        if failure_class in {'judge_invalid','optimizer_response_schema_error'}:
            return 'retryable', failure_class, []
        if retryable_model_failure({'status':'FAILED','failure_class':failure_class,
                                    'failure':summary.get('failure','')}):
            return 'retryable', failure_class, []
        if failure_class in {'environment_initialization_error','environment_error','parallel_task_error'}:
            return 'retryable', failure_class, []
        return 'permanent_failure', failure_class, []
    if exit_code < 0:
        return 'interrupted', f'signal_{-exit_code}', []
    return 'retryable', 'missing_summary', []


def pid_alive(pid):
    if type(pid) is not int or pid < 1:
        return False
    try:
        os.kill(pid,0)
    except ProcessLookupError:
        return False
    return True


def pending_tasks(out):
    """Report unfinished task boundaries without changing the frozen selection."""
    pending=[]
    for manifest_path in sorted((out/'runs').glob('*/evaluations/*/.rethinkskill/RUN_MANIFEST.json')):
        evaluation=manifest_path.parent.parent
        try:
            selection=json.loads(manifest_path.read_text())['selection']
            for task_id,workspace in selection['task_workspaces'].items():
                result_path=evaluation/'tasks'/workspace/'RESULT.json'
                row=json.loads(result_path.read_text()) if result_path.is_file() else None
                if row is None or row.get('failure_class'):
                    pending.append({'evaluation':str(evaluation.relative_to(out)),
                        'case_id':task_id,'failure_class':row.get('failure_class') if row else 'missing_result'})
        except (OSError, ValueError, KeyError) as exc:
            pending.append({'evaluation':str(evaluation.relative_to(out)),
                            'case_id':'<manifest>','failure_class':type(exc).__name__})
    return pending


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--preflight',type=Path,required=True)
    p.add_argument('--model',default='qwen3.6-flash-distill')
    p.add_argument('--alfworld-workers',type=int,choices=range(1,65),default=8)
    p.add_argument('--max-recovery-passes',type=int,choices=range(1,6),default=3)
    p.add_argument('--recovery-backoff-seconds',type=int,default=15)
    p.add_argument('--max-requests-per-minute',type=int,default=24)
    args=p.parse_args();root=args.root.resolve();pre=args.preflight.resolve()
    if args.recovery_backoff_seconds < 0:
        raise ValueError('Recovery backoff must be nonnegative')
    if not 1 <= args.max_requests_per_minute <= 600:
        raise ValueError('Request limit must be in [1, 600]')
    verification=json.loads((pre/'verification.json').read_text())
    preflight_plan=json.loads((pre/'plan.json').read_text())
    if preflight_plan.get('max_requests_per_minute')!=args.max_requests_per_minute:
        raise ValueError('Full campaign must use the same model-channel pacing as preflight')
    expected={f'{b}_{m}' for b in ('searchqa','alfworld') for m in ('baseline','judge')}
    if set(verification)!=expected or any(v['status']!='passed' for v in verification.values()):
        raise ValueError('Four real paired smoke settings must pass before launch')
    implementation=json.loads((pre/'searchqa_baseline/implementation.json').read_text())
    for name in expected:
        if audit_run(pre/name) or json.loads((pre/name/'implementation.json').read_text())!=implementation:
            raise ValueError('Preflight source mismatch or audit failure')
        manifest=json.loads((pre/name/'study_manifest.json').read_text())
        if manifest['model'] != args.model or manifest['judge_model'] != args.model or manifest['judge_prompt_variant'] != 'v3':
            raise ValueError('Preflight must use the campaign model and Judge prompt version')
    for name,digest in implementation.items():
        if hashlib.sha256((ROOT/'packages'/name).read_bytes()).hexdigest()!=digest:
            raise ValueError('Implementation changed after real smoke')
    for mode in ('baseline','judge'):
        manifest=json.loads((pre/f'alfworld_{mode}/study_manifest.json').read_text())
        if manifest['max_steps'] != 50 or manifest['environment_provenance'] != benchmark_provenance(
            benchmark_root()/'configs/rethinkskill_official.yaml'):
            raise ValueError('ALFWorld preflight must exercise 50 steps with the current benchmark environment')
    # Control/data invariants: compare actual frozen content, not condition names.
    for bench in ('searchqa','alfworld'):
        b=pre/f'{bench}_baseline';j=pre/f'{bench}_judge'
        for rel in ('initial.md','dataset/train/items.json','dataset/val/items.json','dataset/test/items.json'):
            if (b/rel).read_bytes()!=(j/rel).read_bytes():raise ValueError('Unmatched paired inputs')
        bc=json.loads((b/'controls.json').read_text());jc=json.loads((j/'controls.json').read_text())
        for key in bc:
            if key not in {'mode','output_dir'} and bc[key]!=jc[key]:raise ValueError(f'Unmatched control {key}')
    root.mkdir(parents=True,exist_ok=True)
    lock=(root/'supervisor.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    config=load_local_config()
    jobs=[];inputs={}
    for bench in ('searchqa','alfworld'):
        section=config.get(f'{bench}-eval',config.get('default',{}))
        if not section.get('base_url') or not (section.get('api_key') or os.environ.get('OPENAI_API_KEY')):
            raise ValueError(f'Missing {bench} endpoint or API key in local configuration')
        data=ROOT/'packages/skillopt/data'/('searchqa_split' if bench=='searchqa' else 'alfworld_path_split')
        for split in ('train','val','test'):
            dest=root/'inputs'/bench/f'{split}.json'
            if not dest.exists():atomic_write_json(dest,json.loads((data/split/'items.json').read_text()))
            inputs[str(dest.relative_to(root))]={'sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'count':len(json.loads(dest.read_text()))}
        seed=root/'inputs'/bench/'seed.md'
        if not seed.exists():seed.write_bytes((ROOT/'packages/skillopt/skillopt/envs'/bench/'skills/initial.md').read_bytes())
        inputs[str(seed.relative_to(root))]={'sha256':hashlib.sha256(seed.read_bytes()).hexdigest()}
        for mode in ('baseline','judge'):
            name=f'{bench}_{mode}';out=root/name
            command=[str(ROOT/'packages/skillopt/.venv/bin/python'),str(ROOT/'scripts/run_method.py'),
                '--method','rethinkskill','--benchmark',bench,'--mode',mode,'--model',args.model,
                '--base-url',section['base_url'],'--output-dir',str(out),'--',
                '--rounds','10','--workers',str(args.alfworld_workers if bench == 'alfworld' else 64),'--timeout-seconds','300','--max-steps','50',
                '--seed-skill',str(seed),'--resume']
            for split in ('train','val','test'):command += [f'--{split}-items',str(root/'inputs'/bench/f'{split}.json')]
            jobs.append((bench,name,out,command))
    plan={'schema':'rethinkskill_full_v3','model':args.model,'preflight':str(pre),'implementation':implementation,'inputs':inputs,
        'rounds':10,'alfworld_max_steps':50,'maximum_allowed_workers_per_setting':64,
        'initial_workers':{'searchqa':64,'alfworld':args.alfworld_workers},
        'parallel_settings':4,'judge_validation_rollouts':0,'full_validation_audit':False,'final_selection':'best',
        'primary_performance':'per-dataset paired final-test hard scores; report judge minus baseline and discordant pairs',
        'primary_cost':'baseline seed_validation+candidate_validation versus all llm_judge calls; exclude training, optimizer, final test',
        'missing_usage':'unknown; known totals are lower bounds, never claim exact savings from incomplete usage',
        'shared_model_rate_limit_per_minute':args.max_requests_per_minute,
        'http500':'official invalid evaluation; do not score or select a skill after an incomplete model call',
        'recovery':{'max_passes_per_setting':args.max_recovery_passes,
                    'backoff_seconds':args.recovery_backoff_seconds,
                    'worker_schedule':'initial workers, then floor-half per recovery pass with minimum 1',
                    'retryable':['HTTP 408/409/425/429/5xx','timeout','transport','response schema',
                                 'Judge invalid response','optimizer output schema','environment interruption','missing summary'],
                    'permanent':['HTTP 4xx other than retryable','optimizer contract error','completed run audit failure'],
                    'resume':'rebuild official artifacts from cached successful requests; retry failed request only; never score omitted tasks'},
        'claim_limit':'single run each; descriptive comparison, not proof of general non-inferiority',
        'commands':{j[1]:j[3] for j in jobs}}
    if (root/'plan.json').exists() and json.loads((root/'plan.json').read_text())!=plan:
        raise ValueError('Cannot resume campaign with changed preregistered inputs or implementation')
    atomic_write_json(root/'plan.json',plan)
    atomic_write_json(root/'supervisor.json',{'pid':os.getpid(),'status':'running','started_at':time.time()})
    def execute(job):
        bench,name,out,command=job
        section=config.get(f'{bench}-eval',config.get('default',{}))
        env=dict(os.environ,OPENAI_API_KEY=section.get('api_key') or os.environ['OPENAI_API_KEY'],OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',
                 TOKENIZERS_PARALLELISM='false',
                 RETHINKSKILL_RATE_LIMIT_FILE=str(root/'request_rate.json'),
                 RETHINKSKILL_MAX_REQUESTS_PER_MINUTE=str(args.max_requests_per_minute))
        status_path=root/f'{name}.status.json'
        previous=json.loads(status_path.read_text()) if status_path.exists() else {}
        attempts=previous.get('attempts',0)
        history=list(previous.get('history',[]))
        if previous.get('status')=='running' and pid_alive(previous.get('pid')):
            while pid_alive(previous['pid']):
                time.sleep(10)
            state,reason,errors=classify_run(out,None)
            history.append({'attempt':attempts,'workers':previous.get('workers'),
                            'exit_code':None,'status':state,'reason':reason,'audit_errors':errors})
            previous.update(status=state,reason=reason,audit_errors=errors,finished_at=time.time())
            previous['pending_tasks']=pending_tasks(out)
            previous['history']=history
            atomic_write_json(status_path,previous)
        if previous.get('status')=='completed':
            state,reason,errors=classify_run(out,0)
            if state=='completed':
                return name,previous
            previous.update(status=state,reason=reason,audit_errors=errors,
                            pending_tasks=pending_tasks(out),finished_at=time.time())
            atomic_write_json(status_path,previous)
            return name,previous
        if previous.get('status') in {'integrity_error','permanent_failure'}:
            return name,previous
        status=previous
        while attempts < args.max_recovery_passes:
            attempts+=1
            attempt_command=list(command)
            worker_index=attempt_command.index('--workers')+1
            initial_workers=int(command[worker_index])
            workers=max(1,initial_workers//(2**(attempts-1)))
            attempt_command[worker_index]=str(workers)
            with (root/f'{name}.log').open('a') as log:
                child=subprocess.Popen(attempt_command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,env=env,start_new_session=True)
                status={'pid':child.pid,'status':'running','started_at':time.time(),
                        'attempts':attempts,'workers':workers,
                        'max_recovery_passes':args.max_recovery_passes,'history':history}
                atomic_write_json(status_path,status)
                code=child.wait()
            state,reason,errors=classify_run(out,code)
            history.append({'attempt':attempts,'workers':workers,'exit_code':code,
                            'status':state,'reason':reason,'audit_errors':errors})
            status.update(exit_code=code,audit_errors=errors,reason=reason,
                          finished_at=time.time(),status=('exhausted' if state=='retryable' and
                          attempts==args.max_recovery_passes else state))
            status['history']=list(history)
            status['pending_tasks']=pending_tasks(out)
            atomic_write_json(status_path,status)
            if state!='retryable' or attempts==args.max_recovery_passes:
                break
            delay=args.recovery_backoff_seconds*(2**(attempts-1))+(int(hashlib.sha256(name.encode()).hexdigest(),16)%4)
            time.sleep(delay)
        return name,status
    with ThreadPoolExecutor(max_workers=4) as pool:results=dict(pool.map(execute,jobs))
    atomic_write_json(root/'completion.json',results)
    atomic_write_json(root/'supervisor.json',{'pid':os.getpid(),'status':'finished','finished_at':time.time()})
    return int(any(r['status']!='completed' for r in results.values()))

if __name__=='__main__':raise SystemExit(main())
