"""Behavior tests execute upstream code; only model responses are deterministic."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'packages/rethinkskill'
sys.path.insert(0, str(PACKAGE / 'src'))
from rethinkskill.benchmarks.capabilities import capability_catalog
from rethinkskill.evolution.loop import EvolutionOptions, execute_evolution, plan_evolution
from rethinkskill.evolution.native import NativeEvaluationSelection, NativeSkillEvaluator, freeze_native_evolution_inputs
from rethinkskill.evolution.optimizer import optimizer_catalog
from rethinkskill.evolution.protocol import GatePolicy
from rethinkskill.runtime.types import ModelOutcome
from rethinkskill.utils.fs import Repository


class ScriptedExecutor:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.tasks = []

    def public_manifest(self):
        return {'kind': 'scripted-test-only', 'real_model_calls': False}

    def execute(self, rendered, *, workspace, timeout_seconds):
        self.tasks.append(rendered)
        response = next(self.responses)
        return ModelOutcome(status='COMPLETED', response=response, raw=response,
                            process={'returncode': 0, 'timed_out': False},
                            attempted_calls=1, completed_calls=1)


def run_chain(root, proposals, answers, *, arm='normal', rescue=None, dead_band=.01):
    root.mkdir(parents=True, exist_ok=True)
    (root / 'pyproject.toml').write_text('')
    skill = root / 'seed.md'
    skill.write_text('seed skill')
    dataset = root / 'dataset'
    for split in ('train', 'val'):
        folder = dataset / split
        folder.mkdir(parents=True)
        (folder / 'items.json').write_text(json.dumps([
            {'id': split + '-1', 'question': 'Which city?',
             'context': 'The city is New York.', 'answers': ['New York']}]))
    repository = Repository.discover(root)
    catalog = capability_catalog()
    out = root / 'runs/evolution'
    categories = ('failure',) if arm == 'fail_only' else ('failure', 'success')
    plan = plan_evolution(repository=repository, benchmark='searchqa', initial_skill=skill,
        output_root=out, gate=GatePolicy(hard_dead_band=dead_band, soft_rescue_delta=rescue),
        options=EvolutionOptions(rounds=len(proposals), arm=arm, feedback_categories=categories))
    frozen = freeze_native_evolution_inputs(repository=repository, catalog=catalog,
        benchmark='searchqa', dataset=dataset, initial_skill=skill, output_root=out,
        selections={s: NativeEvaluationSelection(split=s) for s in ('train', 'val')})
    target = ScriptedExecutor(answers)
    optimizer_executor = ScriptedExecutor(proposals)
    evaluator = NativeSkillEvaluator(repository=repository, catalog=catalog, frozen=frozen,
                                    output_root=out, executor=target)
    optimizer = optimizer_catalog().build('model-skill', executor=optimizer_executor,
                                         output_root=out, timeout_seconds=30)
    receipt = execute_evolution(plan, evaluator=evaluator, optimizer=optimizer, authorized=True)
    rounds = [json.loads(line) for line in (out / 'EVOLUTION_LEDGER.jsonl').read_text().splitlines()]
    from rethinkskill.evidence.run import validate_run_evidence
    validated = validate_run_evidence(out)
    assert validated["status"] == "RETHINKSKILL_RUN_EVIDENCE_VALIDATED", validated
    return receipt, rounds, target, optimizer_executor, out


def proposal(skill='changed skill', operation='replace'):
    return json.dumps({'operation': operation, 'candidate_skill': skill, 'rationale': 'Test policy'})


def test_vendored_files_are_hash_bound_to_upstream():
    manifest = json.loads((PACKAGE / 'UPSTREAM.json').read_text())
    assert manifest['commit'] == '8252445918ebebebce7adf9be843c90841e66810'
    for relative, digest in manifest['files'].items():
        expected = manifest.get('local_patches', {}).get(relative, {}).get('sha256', digest)
        assert hashlib.sha256((PACKAGE / relative).read_bytes()).hexdigest() == expected, relative


def test_native_noop_skips_validation_and_preserves_skill(tmp_path):
    receipt, rounds, target, opt, _ = run_chain(tmp_path,
        [proposal('seed skill', 'noop')], ['<answer>wrong</answer>', '<answer>New York</answer>'])
    assert receipt['status'] == 'RETHINKSKILL_EVOLUTION_VALIDATED'
    assert len(target.tasks) == 2  # seed validation, current-skill training only
    assert rounds[0]['action'] == 'flat'
    assert rounds[0]['candidate_hard'] is None
    assert receipt['final_current']['sha256'] == receipt['best']['sha256']
    assert '# Context' in target.tasks[0].task_markdown
    assert '<answer>' in target.tasks[0].task_markdown
    assert 'success' in opt.tasks[0].task_markdown


def test_invalid_optimizer_json_is_terminal_not_noop(tmp_path):
    receipt, rounds, target, _, _ = run_chain(tmp_path,
        ['not JSON', proposal()], ['<answer>wrong</answer>', '<answer>wrong</answer>'])
    assert receipt['status'] != 'RETHINKSKILL_EVOLUTION_VALIDATED'
    assert receipt['failure_stage'] == 'optimization'
    assert len(target.tasks) == 2
    assert len(rounds) == 1 and rounds[0]['action'] == 'infrastructure_invalid'


def test_accept_then_reject_trains_current_and_keeps_best(tmp_path):
    receipt, rounds, target, opt, _ = run_chain(tmp_path,
        [proposal('improved skill'), proposal('regressed skill')],
        ['<answer>wrong</answer>', '<answer>wrong</answer>', '<answer>New York</answer>',
         '<answer>New York</answer>', '<answer>wrong</answer>'])
    assert receipt['status'] == 'RETHINKSKILL_EVOLUTION_VALIDATED'
    assert [r['action'] for r in rounds] == ['accept_new_best', 'reject']
    assert len(target.tasks) == 5
    assert 'improved skill' in target.tasks[3].skill_markdown
    assert receipt['final_current']['sha256'] == hashlib.sha256(b'improved skill').hexdigest()
    assert receipt['best']['sha256'] == receipt['final_current']['sha256']
    assert 'accept_new_best' in opt.tasks[1].task_markdown  # actual round history


def test_soft_rescue_changes_current_but_not_best(tmp_path):
    receipt, rounds, _, _, _ = run_chain(tmp_path, [proposal()],
        ['<answer>wrong</answer>', '<answer>wrong</answer>', '<answer>New</answer>'], rescue=.02)
    assert receipt['status'] == 'RETHINKSKILL_EVOLUTION_VALIDATED'
    assert rounds[0]['action'] == 'accept'
    assert receipt['final_current']['sha256'] != receipt['best']['sha256']
    assert receipt['best']['sha256'] == hashlib.sha256(b'seed skill').hexdigest()


def test_fail_only_filters_success_before_official_optimizer(tmp_path):
    _, rounds, _, _, _ = run_chain(tmp_path, [proposal('seed skill', 'noop')],
        ['<answer>wrong</answer>', '<answer>New York</answer>'], arm='fail_only')
    assert rounds[0]['training']['feedback'] == []



def test_noop_must_preserve_trailing_newline_exactly(tmp_path):
    # Reproduce the real endpoint failure without another paid request.
    receipt, rounds, target, _, _ = run_chain(tmp_path,
        [proposal('seed skill\n', 'noop')], ['<answer>wrong</answer>', '<answer>wrong</answer>'])
    assert receipt['status'] == 'RETHINKSKILL_EVOLUTION_INVALID'
    assert receipt['failure_stage'] == 'optimization'
    assert receipt['optimizer_calls']['accounting_known'] is False
    assert rounds == []
    assert len(target.tasks) == 2


def test_gate_dead_band_and_soft_rescue_priority():
    from rethinkskill.evolution.protocol import GateState, gate_decision
    state = GateState(current_hard=.5, current_soft=.5, best_hard=.5, best_soft=.5, best_round=0)
    policy = GatePolicy(hard_dead_band=.02, soft_rescue_delta=.02)
    assert gate_decision(policy, state, hard=.51, soft=.5, round_no=1).action == 'flat'
    assert gate_decision(policy, state, hard=.51, soft=.6, round_no=1).action == 'accept'
    assert gate_decision(policy, state, hard=.4, soft=.9, round_no=1).action == 'reject'


def test_optimizer_rejects_json_fence_like_official_source(tmp_path):
    from rethinkskill.evolution.optimizer import ModelSkillOptimizer, render_model_optimizer_task
    from rethinkskill.runtime.types import ModelOutcome
    from rethinkskill.evolution.loop import OptimizationContext
    class E:
        def execute(self, rendered, **kwargs):
            return ModelOutcome(status='COMPLETED', response='```json\n{"operation":"replace","candidate_skill":"new","rationale":"r"}\n```', raw='', process={}, attempted_calls=1, completed_calls=1)
    # Exercise the official model optimizer parser through its public proposal path.
    optimizer=ModelSkillOptimizer(executor=E(), output_root=tmp_path, timeout_seconds=10)
    context=OptimizationContext(round_no=1,current_skill='old',current_sha256='x',training=type('T',(),{'public':lambda self:{'hard':0,'soft':0,'feedback':[]}})(),history=[],feedback_categories=('failure','success'))
    result=optimizer.propose(context)
    assert not result.valid and result.failure_class=='optimizer_response_schema_error'
