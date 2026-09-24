#!/usr/bin/env python3
"""Small real paired smoke; no full campaign or performance claim."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'packages'), str(ROOT/'packages/rethinkskill/src'),
                str(ROOT/'packages/rethinkskill/integrations/alfworld/src'), str(ROOT/'packages/skillopt')]
from rethinkskill_study.audit import audit_run
from rethinkskill_study.local_config import load_local_config
from rethinkskill.utils.serde import atomic_write_json
from run_rethinkskill_full import classify_run, pending_tasks, pid_alive


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',required=True,type=Path)
    p.add_argument('--alfworld-max-steps',type=int,default=50)
    p.add_argument('--benchmark',choices=('both','alfworld','searchqa'),default='both')
    p.add_argument('--model',default='qwen3.6-flash-distill')
    p.add_argument('--workers',type=int,default=2)
    p.add_argument('--alfworld-workers',type=int,default=2)
    p.add_argument('--audit-only',action='store_true',help='Recheck completed outputs without model calls')
    p.add_argument('--resume',action='store_true')
    p.add_argument('--max-recovery-passes',type=int,choices=range(1,6),default=3)
    p.add_argument('--recovery-backoff-seconds',type=int,default=15)
    p.add_argument('--max-requests-per-minute',type=int,default=24)
    args=p.parse_args(); root=args.root.resolve()
    if args.recovery_backoff_seconds < 0:
        raise ValueError('Recovery backoff must be nonnegative')
    if not 1 <= args.max_requests_per_minute <= 600:
        raise ValueError('Request limit must be in [1, 600]')
    if args.audit_only:
        if not root.is_dir():
            raise ValueError('Audit root is missing')
        results={}
        for name in ('searchqa_baseline','searchqa_judge','alfworld_baseline','alfworld_judge'):
            out=root/name
            if not out.is_dir():
                continue
            errors=audit_run(out)
            rounds_dir=out/'runs/evolution/rounds'
            rounds=[json.loads(path.read_text()) for path in rounds_dir.glob('round_*.json')] if rounds_dir.is_dir() else []
            exercised=any(row['operation']!='noop' for row in rounds)
            result={'exit_code':0 if (out/'summary.json').is_file() and
                    json.loads((out/'summary.json').read_text()).get('status')=='completed' else 1,
                    'audit_errors':errors,'candidate_gate_exercised':exercised}
            result['status']='passed' if result['exit_code']==0 and not errors and exercised else 'failed'
            atomic_write_json(root/f'{name}.status.json',result)
            results[name]=result
        atomic_write_json(root/'verification.json',results)
        return int(not results or any(row['status']!='passed' for row in results.values()))
    root.mkdir(parents=True,exist_ok=args.resume)
    config=load_local_config()
    jobs=[]
    for bench,indices in [('searchqa',[94,312]),('alfworld',[35,38])]:
        if args.benchmark != 'both' and bench != args.benchmark:
            continue
        data=ROOT/'packages/skillopt/data'/('searchqa_split' if bench=='searchqa' else 'alfworld_path_split')
        for split in ('train','val','test'):
            rows=json.loads((data/split/'items.json').read_text())
            selected=[rows[i] for i in (indices if split=='train' else [0])]
            dest=root/'data'/bench/f'{split}.json'
            if dest.exists():
                if json.loads(dest.read_text())!=selected:
                    raise ValueError('Cannot resume preflight with changed selected tasks')
            else:
                atomic_write_json(dest,selected)
        section=config.get(f'{bench}-eval',config.get('default',{}))
        if not section.get('base_url') or not (section.get('api_key') or os.environ.get('OPENAI_API_KEY')):
            raise ValueError(f'Missing {bench} endpoint or API key in local configuration')
        for mode in ('baseline','judge'):
            name=f'{bench}_{mode}';out=root/name
            command=[str(ROOT/'packages/skillopt/.venv/bin/python'),str(ROOT/'scripts/run_method.py'),
                '--method','rethinkskill','--benchmark',bench,'--mode',mode,'--model',args.model,
                '--base-url',section['base_url'],'--output-dir',str(out),'--',
                '--rounds','1','--workers',str(args.alfworld_workers if bench == 'alfworld' else args.workers),
                '--timeout-seconds','300','--resume']
            if bench == 'alfworld':
                command += ['--max-steps',str(args.alfworld_max_steps)]
            for split in ('train','val','test'):
                command += [f'--{split}-items',str(root/'data'/bench/f'{split}.json')]
            jobs.append((bench,mode,name,out,command))
    plan={'purpose':'small paired official-chain smoke only','jobs':[j[4] for j in jobs],
        'performance_claim':False,'train_units':2,'val_units':1,'test_units':1,'rounds':1,
        'alfworld_max_steps':args.alfworld_max_steps,'benchmark':args.benchmark,
        'max_recovery_passes':args.max_recovery_passes,'recovery_backoff_seconds':args.recovery_backoff_seconds,
        'max_requests_per_minute':args.max_requests_per_minute}
    if (root/'plan.json').exists() and json.loads((root/'plan.json').read_text())!=plan:
        raise ValueError('Cannot resume preflight with changed plan')
    atomic_write_json(root/'plan.json',plan)
    def execute(job):
        bench,mode,name,out,command=job
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
            previous.update(status=state,reason=reason,audit_errors=errors)
            previous['history']=history
            atomic_write_json(status_path,previous)
        if previous.get('status')=='passed':
            state,_,errors=classify_run(out,0)
            if state=='completed':
                return name,previous
            previous.update(status='integrity_error',audit_errors=errors)
            atomic_write_json(status_path,previous)
            return name,previous
        if previous.get('status') in {'integrity_error','permanent_failure','failed'}:
            return name,previous
        result=previous
        while attempts<args.max_recovery_passes:
            attempts+=1
            attempt_command=list(command)
            worker_index=attempt_command.index('--workers')+1
            workers=max(1,int(command[worker_index])//(2**(attempts-1)))
            attempt_command[worker_index]=str(workers)
            with (root/f'{name}.log').open('a') as log:
                child=subprocess.Popen(attempt_command,stdout=log,stderr=subprocess.STDOUT,
                                       env=env,start_new_session=True)
                result={'pid':child.pid,'status':'running','attempts':attempts,'workers':workers,
                        'started_at':time.time(),'history':history}
                atomic_write_json(status_path,result)
                code=child.wait()
            state,reason,errors=classify_run(out,code)
            history.append({'attempt':attempts,'workers':workers,'exit_code':code,
                            'status':state,'reason':reason,'audit_errors':errors})
            rounds_dir=out/'runs/evolution/rounds'
            rounds=[json.loads(path.read_text()) for path in rounds_dir.glob('round_*.json')] if rounds_dir.is_dir() else []
            exercised=any(row['operation']!='noop' for row in rounds)
            status=('passed' if state=='completed' and exercised else
                    'failed' if state=='completed' else
                    'exhausted' if state=='retryable' and attempts==args.max_recovery_passes else state)
            result.update(exit_code=code,audit_errors=errors,candidate_gate_exercised=exercised,
                          reason='no_candidate_gate' if state=='completed' and not exercised else reason,
                          status=status,history=list(history),
                          pending_tasks=pending_tasks(out),finished_at=time.time())
            atomic_write_json(status_path,result)
            if state!='retryable' or attempts==args.max_recovery_passes:
                break
            delay=(args.recovery_backoff_seconds*(2**(attempts-1))+
                   int(hashlib.sha256(name.encode()).hexdigest(),16)%4)
            time.sleep(delay)
        return name,result
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=dict(pool.map(execute,jobs))
    atomic_write_json(root/'verification.json',results)
    return int(any(r['status']!='passed' for r in results.values()))

if __name__=='__main__':
    raise SystemExit(main())
