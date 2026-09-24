import json
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'packages'),str(ROOT/'packages/rethinkskill/src'),str(ROOT/'packages/skillopt')]
from rethinkskill_study.runner import parser, run
from rethinkskill_study.runtime import StudyEvaluator
from rethinkskill.runtime.types import ModelOutcome
from skillopt.evaluation.judge_gate import JudgeGate


class Executor:
    def __init__(self, replies):
        self.replies = iter(replies)
        self.tasks = []
    def public_manifest(self):
        return {'kind':'deterministic-study-test'}
    def execute(self, rendered, **kwargs):
        self.tasks.append(rendered)
        response = next(self.replies)
        return ModelOutcome(status='COMPLETED',response=response,
            raw=json.dumps({'usage':{'prompt_tokens':10,'completion_tokens':2}}),
            process={'returncode':0},attempted_calls=1,completed_calls=1)


def args_for(tmp, mode, rounds=1):
    data = tmp/'data';data.mkdir(exist_ok=True)
    for split in ('train','val','test'):
        (data/f'{split}.json').write_text(json.dumps([{'id':split+'1','question':'Which city?',
            'context':'The city is New York.', 'answers':['New York']}]))
    (data/'seed.md').write_text('seed skill\n')
    return parser().parse_args(['--benchmark','searchqa','--mode',mode,'--output-dir',str(tmp/mode),
        '--train-items',str(data/'train.json'),'--val-items',str(data/'val.json'),
        '--test-items',str(data/'test.json'),'--seed-skill',str(data/'seed.md'),
        '--model','test','--base-url','https://invalid.test/v1','--rounds',str(rounds)])


def proposal(skill='changed skill', operation='replace'):
    return json.dumps({'operation':operation,'candidate_skill':skill,'rationale':'fix observed failures'})


def judge_for(replies, requests):
    replies = iter(replies)
    def chat(**kw):
        requests.append(kw)
        return next(replies), {'prompt_tokens':5,'completion_tokens':2}
    return JudgeGate(chat_fn=chat,prompt_variant='v3', retries=0)


def decision(verdict='ACCEPT',hard=1,soft=0):
    return json.dumps({'verdict':verdict,'confidence':'high','reason':'observed evidence',
                       'predicted_changes':{'hard':hard,'soft':soft}})


def test_paired_complete_pipeline_only_gate_differs(tmp_path, monkeypatch):
    baseline = args_for(tmp_path,'baseline')
    btarget=Executor(['<answer>wrong</answer>','<answer>wrong</answer>',
                      '<answer>New York</answer>','<answer>New York</answer>'])
    bopt=Executor([proposal()])
    assert run(baseline,target_executor=btarget,optimizer_executor=bopt)==0
    judge=args_for(tmp_path,'judge');requests=[]
    jtarget=Executor(['<answer>wrong</answer>','<answer>New York</answer>'])
    jopt=Executor([proposal()])
    original = StudyEvaluator.evaluate
    def guarded(self,skill,*,split,round_no):
        if self.mode=='judge' and not self.final:
            assert split=='train'
        return original(self,skill,split=split,round_no=round_no)
    monkeypatch.setattr(StudyEvaluator,'evaluate',guarded)
    assert run(judge,target_executor=jtarget,optimizer_executor=jopt,
               judge=judge_for([decision()],requests))==0
    assert btarget.tasks[1] == jtarget.tasks[0]  # identical training prompt/skill
    assert bopt.tasks == jopt.tasks  # exact official optimizer input, including feedback
    assert btarget.tasks[-1] == jtarget.tasks[-1]  # identical selected skill and final test
    assert 'existing training evidence' in requests[0]['system']
    assert 'CURRENT' in requests[0]['user'] and 'CANDIDATE' in requests[0]['user']
    assert 'Which city?' in requests[0]['user']
    assert 'The city is New York.' in requests[0]['user']  # public original context
    assert 'gold_aliases' not in requests[0]['user']  # no hidden answer key
    for mode, expected, components in [('baseline',24,{'seed_validation','candidate_validation'}),
                                       ('judge',7,{'llm_judge'})]:
        root=tmp_path/mode
        cost=json.loads((root/'replacement_cost.json').read_text())
        assert cost['total_tokens']==expected
        assert cost['usage_complete']
        assert set(cost['components'])==components
        assert json.loads((root/'test_summary.json').read_text())['valid']
    assert not list((tmp_path/'judge/runs/evolution/evaluations').glob('val_*'))
    assert not list((tmp_path/'judge/runs/evolution/evaluations').glob('test_*'))


def test_noop_skips_both_validation_and_judge(tmp_path):
    requests=[]
    args=args_for(tmp_path,'judge')
    assert run(args,target_executor=Executor(['<answer>wrong</answer>','<answer>New York</answer>']),
               optimizer_executor=Executor([proposal('seed skill','noop')]),
               judge=judge_for([],requests))==0
    assert requests==[]
    assert json.loads((tmp_path/'judge/replacement_cost.json').read_text())['total_tokens']==0


def test_parse_failure_is_not_successful_rejection_and_no_final_test(tmp_path):
    args=args_for(tmp_path,'judge'); requests=[]
    target=Executor(['<answer>wrong</answer>'])
    assert run(args,target_executor=target,optimizer_executor=Executor([proposal()]),
               judge=judge_for(['bad json'],requests))==1
    assert not (tmp_path/'judge/test_summary.json').exists()
    assert json.loads((tmp_path/'judge/summary.json').read_text())['status']=='invalid'
    assert len(target.tasks)==1
    assert json.loads((tmp_path/'judge/replacement_cost.json').read_text())['total_tokens']==7


def test_soft_rescue_keeps_best_and_separate_best_comparison_is_charged(tmp_path):
    args=args_for(tmp_path,'judge',rounds=2);requests=[]
    target=Executor(['<answer>wrong</answer>','<answer>wrong</answer>','<answer>New York</answer>'])
    opt=Executor([proposal('soft improvement'),proposal('second candidate')])
    judge=judge_for([decision(hard=0,soft=1),decision(hard=1),decision('REJECT',hard=0)],requests)
    assert run(args,target_executor=target,optimizer_executor=opt,judge=judge)==0
    root=tmp_path/'judge'
    rows=[json.loads(p.read_text()) for p in sorted((root/'runs/evolution/rounds').glob('*.json'))]
    assert [r['action'] for r in rows]==['accept','accept']
    assert (root/'runs/evolution/best_skill.md').read_text()=='seed skill'
    assert (root/'runs/evolution/final_current_skill.md').read_text()=='second candidate'
    assert 'soft improvement' in target.tasks[1].skill_markdown
    assert 'seed skill' in target.tasks[-1].skill_markdown
    assert len(requests)==3
    assert json.loads((root/'replacement_cost.json').read_text())['total_tokens']==21
    assert all(r['candidate_hard'] is None and r['validation'] is None for r in rows)


def test_invalid_proposal_never_calls_judge(tmp_path):
    args=args_for(tmp_path,'judge'); requests=[]
    assert run(args,target_executor=Executor(['<answer>wrong</answer>']),
               optimizer_executor=Executor(['not json']),judge=judge_for([],requests))==1
    assert requests==[]


def test_offline_audit_accepts_valid_pair_and_detects_tampering(tmp_path):
    from rethinkskill_study.audit import audit_run
    for mode in ('baseline','judge'):
        args=args_for(tmp_path,mode)
        target=Executor(['<answer>wrong</answer>']*(3 if mode=='baseline' else 1)+['<answer>New York</answer>'])
        assert run(args,target_executor=target,optimizer_executor=Executor([proposal()]),
                   judge=judge_for([decision('REJECT',hard=-1)],[]))==0
        assert audit_run(tmp_path/mode)==[]
    selection=tmp_path/'judge/selection.json'
    data=json.loads(selection.read_text());data['sha256']='0'*64;selection.write_text(json.dumps(data))
    assert audit_run(tmp_path/'judge')


def test_shared_training_proposal_body_matches_unmodified_official_source():
    import ast
    original=ast.parse((ROOT.parent/'pulled/rethinkskill/src/rethinkskill/evolution/loop.py').read_text())
    current=ast.parse((ROOT/'packages/rethinkskill/src/rethinkskill/evolution/loop.py').read_text())
    old=next(n for n in original.body if isinstance(n,ast.FunctionDef) and n.name=='execute_evolution_round')
    new=next(n for n in current.body if isinstance(n,ast.FunctionDef) and n.name=='prepare_evolution_round')
    assert [ast.dump(n) for n in old.body[1:3]] == [ast.dump(n) for n in new.body[1:3]]


def test_judge_retries_are_counted_and_missing_usage_stays_unknown(tmp_path):
    args=args_for(tmp_path,'judge'); requests=[]
    gate=judge_for(['bad json',decision()],requests);gate.retries=1
    assert run(args,target_executor=Executor(['<answer>wrong</answer>','<answer>New York</answer>']),
               optimizer_executor=Executor([proposal()]),judge=gate)==0
    assert len(requests)==2
    assert json.loads((tmp_path/'judge/replacement_cost.json').read_text())['total_tokens']==14
    other=tmp_path/'missing';other.mkdir()
    args=args_for(other,'judge')
    gate=JudgeGate(chat_fn=lambda **kw:(decision(),{}),prompt_variant='v3',retries=0)
    assert run(args,target_executor=Executor(['<answer>wrong</answer>','<answer>New York</answer>']),
               optimizer_executor=Executor([proposal()]),judge=gate)==0
    assert not json.loads((other/'judge/replacement_cost.json').read_text())['usage_complete']
