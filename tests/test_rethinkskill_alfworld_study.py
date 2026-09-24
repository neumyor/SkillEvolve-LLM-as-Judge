"""Real installed ALFWorld, deterministic model replies, both complete study arms."""
import json
import os
import sys
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'packages'),str(ROOT/'packages/rethinkskill/src'),str(ROOT/'packages/skillopt'),
             str(ROOT/'packages/rethinkskill/integrations/alfworld/src')]

@pytest.mark.skipif(not os.environ.get('RETHINKSKILL_ALFWORLD_ASSET_ROOT'), reason='requires real ALFWorld corpus and its venv')
@pytest.mark.parametrize("http500", [False, True])
def test_real_alfworld_both_arms_keep_native_environment_and_final_test(tmp_path, http500):
    from rethinkskill_study import runner
    from rethinkskill_study.audit import audit_run
    from rethinkskill.runtime.types import ModelOutcome
    from skillopt.evaluation.judge_gate import JudgeGate

    class Executor:
        def __init__(self, optimizer=False):self.optimizer=optimizer;self.calls=0
        def public_manifest(self):return {'kind':'deterministic-test-only','optimizer':self.optimizer}
        def execute(self,rendered,**kw):
            self.calls+=1
            if http500 and not self.optimizer:
                return ModelOutcome(status='FAILED',response='',raw='',process={'returncode':1},
                    attempted_calls=1,completed_calls=0,failure_class='provider_http_error',failure='HTTP 500: failure')
            response=json.dumps({'operation':'replace','candidate_skill':'Always inspect admissible actions.',
                'rationale':'Avoid unsupported actions.'}) if self.optimizer else '<think>Inspect room.</think><action>look</action>'
            return ModelOutcome(status='COMPLETED',response=response,
                raw=json.dumps({'usage':{'prompt_tokens':10,'completion_tokens':2}}),
                process={'returncode':0},attempted_calls=1,completed_calls=1)
    data=tmp_path/'data';data.mkdir()
    for split in ('train','val','test'):
        rows=json.loads((ROOT/'packages/skillopt/data/alfworld_path_split'/split/'items.json').read_text())
        (data/f'{split}.json').write_text(json.dumps(rows[:2]))
    (data/'seed.md').write_text('Use admissible actions.\n')
    for mode in ('baseline','judge'):
        args=runner.parser().parse_args(['--benchmark','alfworld','--mode',mode,
            '--output-dir',str(tmp_path/mode),'--train-items',str(data/'train.json'),
            '--val-items',str(data/'val.json'),'--test-items',str(data/'test.json'),
            '--seed-skill',str(data/'seed.md'),'--model','test','--base-url','https://invalid.test/v1',
            '--rounds','1','--max-steps','1','--workers','2',
            '--asset-root',os.environ['RETHINKSKILL_ALFWORLD_ASSET_ROOT']])
        requests=[]
        def chat(**kw):
            requests.append(kw)
            return json.dumps({'verdict':'ACCEPT','confidence':'high','reason':'Grounded change.',
                               'predicted_changes':{'hard':1,'soft':0}}),{'prompt_tokens':5,'completion_tokens':2}
        target=Executor()
        code=runner.run(args,target_executor=target,optimizer_executor=Executor(True),
                        judge=JudgeGate(chat_fn=chat,prompt_variant='v3',retries=0))
        if http500:
            assert code==1
            assert target.calls==2
            assert not (tmp_path/mode/'test_summary.json').exists()
            assert requests==[]
            continue
        assert code==0
        assert target.calls==(8 if mode=='baseline' else 4)
        assert audit_run(tmp_path/mode)==[]
        assert len(requests)==int(mode=='judge')
        if requests:
            assert 'transcript' in requests[0]['user']
            assert 'look' in requests[0]['user']
        final=next((tmp_path/mode/'runs/final').rglob('results.jsonl'))
        row=json.loads(final.read_text().splitlines()[0])
        assert row['hard']==0
        assert row['execution']['interactive_runner']['transcript'][0]['action']=='look'
        if mode=='judge':
            proof=next((tmp_path/mode/'runs').rglob('verifier/benchmark_environment.json'))
            proof.unlink()
            assert 'Missing ALFWorld environment proof for a task' in audit_run(tmp_path/mode)


@pytest.mark.skipif(not os.environ.get('RETHINKSKILL_ALFWORLD_ASSET_ROOT'), reason='requires real ALFWorld corpus and its venv')
def test_real_alfworld_full_step_budget_with_parallel_training(tmp_path):
    from rethinkskill_study import runner
    from rethinkskill_study.audit import audit_run
    from rethinkskill.runtime.types import ModelOutcome
    from skillopt.evaluation.judge_gate import JudgeGate

    class Executor:
        def __init__(self, optimizer=False):
            self.optimizer = optimizer

        def public_manifest(self):
            return {'kind': 'deterministic-full-budget-test', 'optimizer': self.optimizer}

        def execute(self, rendered, **kwargs):
            response = (json.dumps({'operation': 'replace', 'candidate_skill': 'Inspect admissible actions.',
                                    'rationale': 'Use observed actions.'}) if self.optimizer else
                        '<think>Inspect room.</think><action>look</action>')
            return ModelOutcome(status='COMPLETED', response=response,
                raw=json.dumps({'usage': {'prompt_tokens': 10, 'completion_tokens': 2}}),
                process={'returncode': 0}, attempted_calls=1, completed_calls=1)

    data = tmp_path/'data'
    data.mkdir()
    source = ROOT/'packages/skillopt/data/alfworld_path_split'
    for split, count in (('train', 4), ('val', 1), ('test', 1)):
        rows = json.loads((source/split/'items.json').read_text())[:count]
        (data/f'{split}.json').write_text(json.dumps(rows))
    (data/'seed.md').write_text('Use admissible actions.\n')
    observed = {}
    for mode, workers in (('baseline', 1), ('judge', 1), ('baseline', 4), ('judge', 4)):
        output = tmp_path/f'{mode}_{workers}'
        args = runner.parser().parse_args([
            '--benchmark', 'alfworld', '--mode', mode, '--output-dir', str(output),
            '--train-items', str(data/'train.json'), '--val-items', str(data/'val.json'),
            '--test-items', str(data/'test.json'), '--seed-skill', str(data/'seed.md'),
            '--model', 'test', '--base-url', 'https://invalid.test/v1',
            '--rounds', '1', '--max-steps', '50', '--workers', str(workers),
            '--asset-root', os.environ['RETHINKSKILL_ALFWORLD_ASSET_ROOT']])
        judge = JudgeGate(chat_fn=lambda **kwargs: (
            json.dumps({'verdict': 'ACCEPT', 'confidence': 'high', 'reason': 'Grounded change.',
                        'predicted_changes': {'hard': 1, 'soft': 0}}),
            {'prompt_tokens': 5, 'completion_tokens': 2}), prompt_variant='v3', retries=0)
        assert runner.run(args, target_executor=Executor(), optimizer_executor=Executor(True), judge=judge) == 0
        assert audit_run(output) == []
        calls = json.loads((output/'evolution_calls.json').read_text())
        assert [call['split'] for call in calls] == (
            ['val', 'train', 'val'] if mode == 'baseline' else ['train'])
        training = output/'runs/evolution/evaluations/train_round_0001/results.jsonl'
        results = [json.loads(line) for line in training.read_text().splitlines()]
        expected = json.loads((data/'train.json').read_text())
        assert [row['case_id'] for row in results] == [row['id'] for row in expected]
        assert all(len(row['execution']['interactive_runner']['transcript']) == 50 for row in results)
        cost = json.loads((output/'replacement_cost.json').read_text())
        assert cost['usage_complete']
        assert cost['total_tokens'] == (1200 if mode == 'baseline' else 7)
        observed[(mode, workers)] = [
            (row['case_id'], row['hard'], row['soft'], row['execution']['interactive_runner']['transcript'])
            for row in results]
    for mode in ('baseline', 'judge'):
        assert observed[(mode, 1)] == observed[(mode, 4)]
    assert observed[('baseline', 1)] == observed[('judge', 1)]


@pytest.mark.skipif(not os.environ.get('RETHINKSKILL_ALFWORLD_ASSET_ROOT'), reason='requires real ALFWorld corpus and its venv')
def test_real_alfworld_resume_retries_only_failed_model_task(tmp_path):
    from threading import Lock
    from rethinkskill_study import runner
    from rethinkskill_study.audit import audit_run
    from rethinkskill.runtime.types import ModelOutcome

    class Executor:
        def __init__(self, optimizer=False, fail_once=False):
            self.optimizer, self.fail_once = optimizer, fail_once
            self.calls = []
            self.lock = Lock()

        def public_manifest(self):
            return {'kind': 'deterministic-recovery-test', 'optimizer': self.optimizer}

        def execute(self, rendered, *, workspace, timeout_seconds):
            with self.lock:
                self.calls.append(str(workspace))
                fail = self.fail_once and 'val_round_0000' in str(workspace)
                if fail:
                    self.fail_once = False
            if fail:
                return ModelOutcome(status='FAILED', response='', raw='',
                    process={'http_status': 500}, attempted_calls=1, completed_calls=0,
                    failure_class='provider_http_error', failure='HTTP 500')
            response = (json.dumps({'operation': 'replace', 'candidate_skill': 'Inspect actions.',
                                    'rationale': 'Use admissible actions.'}) if self.optimizer else
                        '<think>Inspect room.</think><action>look</action>')
            return ModelOutcome(status='COMPLETED', response=response,
                raw=json.dumps({'usage': {'prompt_tokens': 10, 'completion_tokens': 2}}),
                process={}, attempted_calls=1, completed_calls=1)

    data=tmp_path/'data'
    data.mkdir()
    source=ROOT/'packages/skillopt/data/alfworld_path_split'
    for split in ('train','val','test'):
        (data/f'{split}.json').write_text(json.dumps(json.loads((source/split/'items.json').read_text())[:2]))
    (data/'seed.md').write_text('Use admissible actions.\n')
    args=runner.parser().parse_args(['--benchmark','alfworld','--mode','baseline',
        '--output-dir',str(tmp_path/'baseline'),'--train-items',str(data/'train.json'),
        '--val-items',str(data/'val.json'),'--test-items',str(data/'test.json'),
        '--seed-skill',str(data/'seed.md'),'--model','test','--base-url','https://invalid.test/v1',
        '--rounds','1','--max-steps','1','--workers','2',
        '--asset-root',os.environ['RETHINKSKILL_ALFWORLD_ASSET_ROOT']])
    first=Executor(fail_once=True)
    assert runner.run(args,target_executor=first,optimizer_executor=Executor(optimizer=True))==1
    assert len(first.calls)==2
    assert not (tmp_path/'baseline/test_summary.json').exists()
    args.resume=True
    args.workers=1
    second=Executor()
    assert runner.run(args,target_executor=second,optimizer_executor=Executor(optimizer=True))==0
    assert len(second.calls)==7
    assert audit_run(tmp_path/'baseline')==[]
    assert json.loads((tmp_path/'baseline/replacement_cost.json').read_text())['usage_complete'] is False


@pytest.mark.skipif(not os.environ.get('RETHINKSKILL_ALFWORLD_ASSET_ROOT'), reason='requires real ALFWorld')
def test_workspace_environment_serial_parallel_invariants(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from rethinkskill_study.benchmark_environment import BenchmarkEpisode, BENCHMARK_ROOT
    rows=json.loads((ROOT/'packages/skillopt/data/alfworld_path_split/train/items.json').read_text())[:2]
    def episode(index, label):
        game=Path(rows[index]['gamefile'])
        if game.is_absolute():
            game=Path(*game.parts[game.parts.index('json_2.1.1'):])
        worker=BenchmarkEpisode(gamefile=BENCHMARK_ROOT/'.data/alfworld'/game,
            workspace=tmp_path/label/str(index),seed=42,split='train',
            config=BENCHMARK_ROOT/'configs/rethinkskill_official.yaml')
        try:
            states=[worker.reset()]
            states.extend(worker.step('look') for _ in range(2))
            return states,worker.pid
        finally:
            worker.close()
    serial=[episode(i,'serial') for i in range(2)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        parallel=list(pool.map(lambda i:episode(i,'parallel'),range(2)))
    assert [v[0] for v in serial]==[v[0] for v in parallel]
    assert all('help' not in state.admissible_actions for states, _ in serial for state in states)
    assert len({v[1] for v in parallel})==2
    for _, pid in parallel:
        with pytest.raises(ProcessLookupError):
            os.kill(pid, 0)
    for i in range(2):
        proof=json.loads((tmp_path/'parallel'/str(i)/'benchmark_environment.json').read_text())
        assert proof['module']==str(BENCHMARK_ROOT/'src/alfworld_eval/env.py')
        assert proof['step_budget']==50


def test_workspace_configuration_matches_official_environment_settings():
    import yaml
    from rethinkskill_study.benchmark_environment import BENCHMARK_ROOT
    from rethinkskill_alfworld.runtime import InstalledAlfWorldFactory
    config=yaml.safe_load((BENCHMARK_ROOT/'configs/rethinkskill_official.yaml').read_text())
    official=InstalledAlfWorldFactory()._configuration(
        gamefile=Path('/tmp/game.tw-pddl'),verifier_workspace=Path('/tmp/verifier'))
    for section in ('env','general','rl','dagger'):
        assert config[section]==official[section]
    assert config['dataset']['num_train_games']==official['dataset']['num_train_games']
    assert config['dataset']['num_eval_games']==official['dataset']['num_eval_games']


@pytest.mark.skipif(not os.environ.get('RETHINKSKILL_ALFWORLD_ASSET_ROOT'), reason='requires real ALFWorld')
def test_workspace_bridge_matches_official_episode_states(tmp_path):
    from rethinkskill_alfworld.runtime import InstalledAlfWorldFactory
    from rethinkskill_study.benchmark_environment import BenchmarkEpisode, BENCHMARK_ROOT
    row=json.loads((ROOT/'packages/skillopt/data/alfworld_path_split/train/items.json').read_text())[0]
    game=BENCHMARK_ROOT/'.data/alfworld'/row['gamefile']
    official_workspace=tmp_path/'official'
    logic=official_workspace/'logic'
    logic.mkdir(parents=True)
    for name in ('alfred.pddl','alfred.twl2'):
        (logic/name).symlink_to(BENCHMARK_ROOT/'.data/alfworld/logic'/name)

    def states(episode):
        try:
            return [episode.reset(), episode.step('look'), episode.step('inventory')]
        finally:
            episode.close()

    official=states(InstalledAlfWorldFactory().open(
        gamefile=game,data_root=BENCHMARK_ROOT/'.data/alfworld',
        verifier_workspace=official_workspace,seed=42,split='train'))
    bridged=states(BenchmarkEpisode(gamefile=game,workspace=tmp_path/'bridge',
        seed=42,split='train',config=BENCHMARK_ROOT/'configs/rethinkskill_official.yaml'))
    def visible(state):
        return state.observation,state.admissible_actions,state.done,state.won
    assert [visible(state) for state in official]==[visible(state) for state in bridged]


def test_partial_environment_response_obeys_timeout():
    import subprocess
    from rethinkskill_study.benchmark_environment import BenchmarkEpisode
    episode=BenchmarkEpisode.__new__(BenchmarkEpisode)
    episode.timeout=.1
    episode._stdout_buffer=bytearray()
    episode.process=subprocess.Popen(
        [sys.executable,'-u','-c',"import sys,time;sys.stdout.write('{');sys.stdout.flush();time.sleep(2)"],
        stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True)
    try:
        with pytest.raises(TimeoutError,match='timed out'):
            episode.request('reset')
    finally:
        episode.process.terminate()
        episode.process.wait(timeout=5)
        episode.process.stdin.close()
        episode.process.stdout.close()
