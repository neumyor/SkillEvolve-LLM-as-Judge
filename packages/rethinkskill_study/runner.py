"""Unified study entry: official training/optimizer/harness, isolated gate policy."""
import argparse
import json
import os
import time
from pathlib import Path

from rethinkskill.benchmarks.capabilities import capability_catalog
from rethinkskill.evolution.loop import EvolutionOptions, execute_evolution, plan_evolution
from rethinkskill.evolution.native import NativeEvaluationSelection, NativeSkillEvaluator, freeze_native_evolution_inputs
from rethinkskill.evolution.optimizer import optimizer_catalog
from rethinkskill.evolution.protocol import GatePolicy
from rethinkskill.providers.catalog import prepare_executor
from rethinkskill.providers.transport import TransportConfig, TransportKind
from rethinkskill.utils.fs import Repository, OutputLock
from rethinkskill.utils.serde import atomic_write_json, sha256_bytes
from skillopt.evaluation.judge_gate import JudgeGate
from skillopt.evaluation.usage_ledger import UsageLedger
from .engine import execute_judge_evolution
from .runtime import MeteredExecutor, StudyEvaluator, judge_chat
from .journal import DurableLedger, RequestJournal
from .local_config import benchmark_root


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--benchmark', choices=['searchqa', 'alfworld'], required=True)
    p.add_argument('--mode', choices=['baseline', 'judge'], required=True)
    for name in ('output-dir', 'train-items', 'val-items', 'test-items', 'seed-skill'):
        p.add_argument('--' + name, required=True, type=Path)
    p.add_argument('--model', required=True)
    p.add_argument('--judge-model')
    p.add_argument('--base-url', required=True)
    p.add_argument('--api-key', default=os.environ.get('OPENAI_API_KEY', ''))
    p.add_argument('--judge-prompt-variant', default='v3')
    p.add_argument('--rounds', type=int, default=10)
    p.add_argument('--smoke', action='store_true')
    p.add_argument('--resume', action='store_true', help='Replay persisted calls without new API requests; continue unfinished work')
    p.add_argument('--workers', type=int, default=1, help='Maximum concurrent independent tasks per evaluation (1-64)')
    p.add_argument('--max-steps', type=int, default=50)
    p.add_argument('--alfworld-config')
    p.add_argument('--asset-root', type=Path)
    p.add_argument('--timeout-seconds', type=int, default=120)
    p.add_argument('--arm', choices=['normal','fail_only','success_only'], default='normal')
    return p


def run(args, *, target_executor=None, optimizer_executor=None, judge=None):
    out = args.output_dir.resolve()
    if not 1 <= args.max_steps <= 50:
        raise ValueError('max_steps must be between 1 and 50')
    if not 1 <= args.workers <= 64:
        raise ValueError('workers must be between 1 and 64')
    environment_provenance = None
    if args.benchmark == 'alfworld':
        from .benchmark_environment import benchmark_provenance
        alfworld_benchmark = benchmark_root()
        args.alfworld_config = args.alfworld_config or str(alfworld_benchmark/'configs/rethinkskill_official.yaml')
        args.asset_root = args.asset_root or alfworld_benchmark/'.data/alfworld'
        environment_provenance = benchmark_provenance(args.alfworld_config)
        if args.asset_root.resolve() != (alfworld_benchmark/'.data/alfworld').resolve():
            raise ValueError('Use the workspace benchmark/alfworld-eval data root')
        if Path(args.alfworld_config).resolve() != (alfworld_benchmark/'configs/rethinkskill_official.yaml').resolve():
            raise ValueError('Use the official-equivalent RethinkSkill ALFWorld configuration')
    with OutputLock(out):
        initialized = (out/'study_manifest.json').exists()
        if out.exists() and any(out.iterdir()) and not args.resume:
            raise ValueError('Fresh output directory required; existing work is never overwritten')
        out.mkdir(parents=True, exist_ok=True)
        packages = Path(__file__).resolve().parents[1]
        sources = list((packages/'rethinkskill/src').rglob('*.py')) + list((packages/'rethinkskill_study').glob('*.py'))
        sources += list((packages/'rethinkskill/integrations/alfworld/src').rglob('*.py'))
        sources += [packages/'skillopt/skillopt/evaluation'/name for name in ('judge_gate.py','evidence.py','usage_ledger.py')]
        implementation = {str(p.relative_to(packages)):sha256_bytes(p.read_bytes()) for p in sources}
        controls = {k:str(v) if isinstance(v,Path) else v for k,v in vars(args).items() if k not in {'api_key','resume'}}
        concurrency_ceiling = args.workers
        if initialized:
            previous_manifest = json.loads((out/'study_manifest.json').read_text())
            concurrency_ceiling = previous_manifest['concurrency_ceiling']
            if args.workers > concurrency_ceiling:
                raise ValueError('Cannot exceed the frozen task concurrency ceiling on resume')
            if args.benchmark == 'alfworld' and (
                not (out/'benchmark_environment.json').exists()
                or json.loads((out/'benchmark_environment.json').read_text()) != environment_provenance
            ):
                raise ValueError('Cannot resume an ALFWorld run with different environment provenance')
            previous_controls = json.loads((out/'controls.json').read_text())
            if (json.loads((out/'implementation.json').read_text()) != implementation or
                {k:v for k,v in previous_controls.items() if k != 'workers'} !=
                {k:v for k,v in controls.items() if k != 'workers'}):
                raise ValueError('Cannot resume with changed implementation or controls')
            if (out/'initial.md').read_text() != args.seed_skill.read_text().rstrip():
                raise ValueError('Cannot resume with changed seed')
            for split in ('train','val','test'):
                if json.loads((out/'dataset'/split/'items.json').read_text()) != json.loads(getattr(args,split+'_items').read_text()):
                    raise ValueError('Cannot resume with changed split')
            if (out/'summary.json').exists() and json.loads((out/'summary.json').read_text()).get('status') == 'completed':
                from .audit import audit_run
                errors = audit_run(out)
                if errors:
                    raise ValueError(f'Completed run failed audit: {errors}')
                return 0
            archive = out/'recovery'/str(time.time_ns())
            archive.mkdir(parents=True)
            atomic_write_json(archive/'controls.json', previous_controls)
            for name in ('runs','judge_requests','summary.json','test_summary.json','selection.json','evolution_receipt.json','evolution_calls.json'):
                if (out/name).exists():
                    (out/name).rename(archive/name)
        atomic_write_json(out/'controls.json',controls)
        atomic_write_json(out/'implementation.json',implementation)
        if environment_provenance:
            atomic_write_json(out/'benchmark_environment.json', environment_provenance)
        (out / 'pyproject.toml').write_text('# RethinkSkill study workspace\n')
        # Input normalization is identical in both modes and recorded explicitly.
        initial = args.seed_skill.read_text().rstrip()
        (out / 'initial.md').write_text(initial)
        seen = set()
        for split in ('train', 'val', 'test'):
            source = getattr(args, split + '_items')
            rows = json.loads(source.read_text())
            ids = [str(row.get('id', row.get('case_id'))) for row in rows]
            if not rows or len(set(ids)) != len(ids) or seen.intersection(ids):
                raise ValueError('Each split must be nonempty with unique, disjoint task IDs')
            seen.update(ids)
            dest = out / 'dataset' / split
            dest.mkdir(parents=True, exist_ok=True)
            atomic_write_json(dest / 'items.json', rows)
        atomic_write_json(out / 'study_manifest.json', {
            'schema':'rethinkskill_study_v2', 'method':'rethinkskill', 'mode':args.mode,
            'benchmark':args.benchmark, 'model':args.model, 'base_url':args.base_url,
            'judge_model':args.judge_model or args.model, 'judge_prompt_variant':args.judge_prompt_variant,
            'rounds':1 if args.smoke else args.rounds, 'arm':args.arm,
            'seed_transform':'rstrip trailing whitespace before freezing, identical in both arms',
            'seed_sha256':sha256_bytes(initial.encode()), 'final_selection':'best',
            'full_validation_audit':False, 'actual_concurrency':args.workers,
            'concurrency_ceiling':concurrency_ceiling,
            'environment_provenance':environment_provenance,
            'environment_concurrency':'isolated process per episode' if args.benchmark == 'alfworld' else None,
            'max_steps':args.max_steps, 'timeout_seconds':args.timeout_seconds,
            'metrics':{'performance':'frozen best skill final test hard',
                       'tokens':'replacement validation requests versus all Judge requests only'},
            'replacement_components': ['llm_judge'] if args.mode == 'judge' else ['seed_validation','candidate_validation']})
        ledger = DurableLedger(out / 'usage_events.jsonl')
        ledger.configure_replacement_cost('rethinkskill', args.mode)
        journal = RequestJournal(out,ledger)
        if target_executor is None or optimizer_executor is None:
            os.environ['RETHINKSKILL_STUDY_API_KEY'] = args.api_key
            config = TransportConfig(kind=TransportKind.OPENAI_COMPATIBLE, model=args.model,
                reasoning_effort='', api_base_url=args.base_url, api_key_env='RETHINKSKILL_STUDY_API_KEY')
            target_executor = target_executor or prepare_executor(config, authorized=True, role='target')
            optimizer_executor = optimizer_executor or prepare_executor(config, authorized=True, role='optimizer')
        target = MeteredExecutor(target_executor, ledger, stage='target', model=args.model, journal=journal)
        opt = MeteredExecutor(optimizer_executor, ledger, stage='optimizer', model=args.model, journal=journal)
        repository = Repository.discover(out)
        catalog = capability_catalog(load_harness_plugins=False)
        if args.benchmark == 'alfworld':
            from rethinkskill.benchmarks.capabilities import CapabilityCatalog
            from rethinkskill.benchmarks.core import benchmark_catalog
            from rethinkskill.benchmarks.harness_catalog import HarnessCatalog, NativeHarnessSpec, EvaluationAuthority
            from rethinkskill.integrations.catalog import integration_catalog
            from rethinkskill_alfworld.harness import AlfWorldHarness
            from .benchmark_environment import BenchmarkAlfWorldFactory
            harness = AlfWorldHarness(max_steps=args.max_steps,
                environment_factory=BenchmarkAlfWorldFactory(Path(args.alfworld_config).resolve()))
            catalog = CapabilityCatalog(benchmark_catalog(), HarnessCatalog((NativeHarnessSpec(
                name='alfworld', harness=harness,
                execution_scope=f'RethinkSkill episode protocol; workspace benchmark environment; max_steps={args.max_steps}',
                source='benchmark/alfworld-eval process-isolated environment',
                evaluation_authority=EvaluationAuthority.HARNESS),)), integration_catalog())
        evolution_root = out / 'runs/evolution'
        categories = {'normal':('failure','success'), 'fail_only':('failure',), 'success_only':('success',)}[args.arm]
        plan = plan_evolution(repository=repository, benchmark=args.benchmark,
            initial_skill=out/'initial.md', output_root=evolution_root,
            gate=GatePolicy(.01 if args.benchmark == 'searchqa' else .02, .02 if args.benchmark == 'searchqa' else None),
            options=EvolutionOptions(rounds=1 if args.smoke else args.rounds, arm=args.arm, feedback_categories=categories))
        frozen = freeze_native_evolution_inputs(repository=repository, catalog=catalog,
            benchmark=args.benchmark, dataset=out/'dataset', initial_skill=out/'initial.md',
            output_root=evolution_root,
            selections={s:NativeEvaluationSelection(split=s) for s in ('train','val','test')},
            asset_root=args.asset_root if args.benchmark == 'alfworld' else None, timeout_seconds=args.timeout_seconds,
            task_workers=args.workers)
        native = NativeSkillEvaluator(repository=repository, catalog=catalog, frozen=frozen,
            output_root=evolution_root, executor=target, timeout_seconds=args.timeout_seconds,
            task_workers=args.workers)
        evaluator = StudyEvaluator(native, ledger, mode=args.mode)
        optimizer = optimizer_catalog().build('model-skill', executor=opt, output_root=evolution_root,
                                              timeout_seconds=args.timeout_seconds)
        if args.mode == 'baseline':
            receipt = execute_evolution(plan, evaluator=evaluator, optimizer=optimizer, authorized=True)
            valid = receipt['status'] == 'RETHINKSKILL_EVOLUTION_VALIDATED'
        else:
            judge = judge or JudgeGate(chat_fn=judge_chat(model=args.judge_model or args.model,
                base_url=args.base_url, api_key=args.api_key, output_root=out, journal=journal,
                prompt_variant=args.judge_prompt_variant),
                prompt_variant=args.judge_prompt_variant, retries=1)
            judge.replacement_ledger = ledger
            receipt = execute_judge_evolution(plan, evaluator=evaluator, optimizer=optimizer, judge=judge)
            valid = receipt['status'] == 'JUDGE_EVOLUTION_COMPLETED'
        atomic_write_json(out / 'evolution_receipt.json', receipt)
        atomic_write_json(out / 'evolution_calls.json', evaluator.calls)
        ledger.write_replacement_summary()
        if not valid:
            atomic_write_json(out/'summary.json', {'method':'rethinkskill','mode':args.mode,
                'status':'invalid','failure_class':receipt.get('failure_class'),
                'failure':receipt.get('failure',''),'full_validation_audit':False})
            return 1
        # The output selection is frozen BEFORE any test execution.
        best = (evolution_root/'best_skill.md').read_text()
        atomic_write_json(out/'selection.json', {'rule':'best','sha256':sha256_bytes(best.encode()),
            'source':'official_validation' if args.mode == 'baseline' else 'judge_prediction'})
        final_native = NativeSkillEvaluator(repository=repository, catalog=catalog, frozen=frozen,
            output_root=out/'runs/final', executor=target, timeout_seconds=args.timeout_seconds,
            task_workers=args.workers)
        final = StudyEvaluator(final_native, ledger, mode=args.mode, final=True)
        result = final.evaluate(best, split='test', round_no=0)
        atomic_write_json(out/'test_summary.json', {'items':len(frozen.selections['test'].task_ids),
            'skill_success_rate':result.hard, 'soft':result.soft, 'valid':result.valid,
            'reference':result.reference, 'full_validation_audit':False})
        atomic_write_json(out/'summary.json', {'schema':'rethinkskill_study_v2','method':'rethinkskill',
            'benchmark':args.benchmark,'mode':args.mode,'status':'completed' if result.valid else 'invalid',
            'rounds':receipt['rounds_recorded'],'test_hard':result.hard,'test_soft':result.soft,
            'failure_class':result.failure_class,'failure':result.failure,
            'full_validation_audit':False, 'selected_sha256':sha256_bytes(best.encode())})
        ledger.write_replacement_summary()
        return 0 if result.valid else 1


def main():
    return run(parser().parse_args())
