"""Offline study audit; never interprets a parse failure as scientific rejection."""
import json
import hashlib
from pathlib import Path
from rethinkskill.evidence.run import validate_run_evidence
from rethinkskill.evidence.evolution import replay_evolution_proposal, replay_native_evaluation
from rethinkskill.evolution.loop import EvolutionRound
from rethinkskill.utils.serde import sha256_bytes


def audit_run(root):
    root = Path(root)
    def read(path):
        return json.loads(path.read_text())
    failures = []
    try:
        manifest = read(root/'study_manifest.json')
        if manifest.get('schema') != 'rethinkskill_study_v2':
            return ['Legacy RethinkSkill study output is invalid']
        mode = manifest['mode']
        if manifest.get('environment_provenance'):
            provenance = read(root/'benchmark_environment.json')
            if provenance != manifest['environment_provenance']:
                failures.append('ALFWorld environment provenance mismatch')
            if provenance.get('environment') != 'alfworld_eval.env.AlfworldTextEnv':
                failures.append('Unexpected ALFWorld environment')
            proofs = list((root/'runs').rglob('verifier/benchmark_environment.json'))
            results = list((root/'runs').rglob('tasks/*/RESULT.json'))
            if {p.parent.parent for p in proofs} != {p.parent for p in results}:
                failures.append('Missing ALFWorld environment proof for a task')
            from rethinkskill_alfworld.runtime import InstalledAlfWorldFactory
            import yaml
            for proof in proofs:
                observed = read(proof)
                expected_module = str(Path(provenance['root'])/'src/alfworld_eval/env.py')
                if observed['module'] != expected_module or observed['python'] != provenance['python'] or observed['config'] != provenance['config']:
                    failures.append('ALFWorld task used a different environment')
                effective = proof.parent/'benchmark_effective_config.yaml'
                if not effective.is_file() or hashlib.sha256(effective.read_bytes()).hexdigest() != observed['effective_config_sha256']:
                    failures.append('ALFWorld effective configuration is missing or changed')
                else:
                    official = InstalledAlfWorldFactory()._configuration(
                        gamefile=proof.parent/'environment/game.tw-pddl', verifier_workspace=proof.parent)
                    if yaml.safe_load(effective.read_text()) != official:
                        failures.append('ALFWorld effective configuration differs from official RethinkSkill')
        evolution = root/'runs/evolution'
        summary = read(root/'summary.json')
        if summary.get('status') != 'completed':
            failures.append('Study did not complete')
        selection = read(root/'selection.json')
        if selection['rule'] != 'best' or selection['sha256'] != sha256_bytes((evolution/'best_skill.md').read_bytes()):
            failures.append('Selected best skill hash mismatch')
        if summary.get('selected_sha256') != selection['sha256']:
            failures.append('Final summary selection mismatch')
        test = read(root/'test_summary.json')
        if not test['valid'] or test['full_validation_audit']:
            failures.append('Final test invalid')
        final_root = root/'runs/final/evaluations/test_round_0000'
        validate_run_evidence(final_root)
        final_manifest = read(final_root/'.rethinkskill/RUN_MANIFEST.json')
        if final_manifest['skill']['sha256'] != selection['sha256']:
            failures.append('Test executed a different skill')
        rows = [json.loads(line) for line in (final_root/'results.jsonl').read_text().splitlines()]
        if len(rows) != test['items'] or sum(r['hard'] for r in rows)/len(rows) != test['skill_success_rate']:
            failures.append('Final test totals differ from raw results')
        calls = read(root/'evolution_calls.json')
        rounds = [read(p) for p in sorted((evolution/'rounds').glob('round_*.json'))]
        if len(rounds) != manifest['rounds']:
            failures.append('Round coverage mismatch')
        if mode == 'baseline':
            validate_run_evidence(evolution)
        else:
            if any(c['split'] != 'train' for c in calls):
                failures.append('Judge executed validation/test during evolution')
            if any(p.name.startswith(('val_', 'test_')) for p in (evolution/'evaluations').iterdir()):
                failures.append('Forbidden Judge evolution artifacts')
            previous = manifest['seed_sha256']
            best = previous
            current_text = (evolution/'skills/initial.md').read_text()
            history = []
            judge_manifest = read(evolution/'judge_manifest.json')
            categories = {'normal':('failure','success'), 'fail_only':('failure',), 'success_only':('success',)}[manifest['arm']]
            for row in rounds:
                if row['parent_sha256'] != previous:
                    failures.append('Judge parent lineage mismatch')
                if row['candidate_hard'] is not None or row['validation'] is not None:
                    failures.append('Judge fabricated measured validation')
                decisions = row['judge_decisions']
                candidate = evolution/f"skills/round_{row['round_no']:04d}_candidate.md"
                if sha256_bytes(candidate.read_bytes()) != row['candidate_sha256']:
                    failures.append('Candidate artifact hash mismatch')
                evidence = read(evolution/f"optimizer/round_{row['round_no']:04d}/PROPOSAL_EVIDENCE.json")
                replay_evolution_proposal(run_root=evolution, round_no=row['round_no'],
                    row={**row, 'proposal':evidence['proposal']}, candidate_sha256=row['candidate_sha256'],
                    parent_digest=previous, current_skill_text=current_text, categories=categories,
                    training=row['training'], history=history, optimizer_kind='model-skill-optimizer',
                    optimizer_manifest=judge_manifest['optimizer'])
                replay_native_evaluation(run_root=evolution, evaluator_manifest=judge_manifest['evaluator'],
                    outcome=row['training'], role='train', round_no=row['round_no'],
                    expected_skill_sha256=previous, feedback_categories=categories)
                if row['operation'] == 'noop':
                    if decisions or row['action'] != 'flat' or row['candidate_sha256'] != previous:
                        failures.append('Invalid noop behavior')
                elif not decisions or any(d['judge_parse_failed'] or d['judge_error'] for d in decisions):
                    failures.append('Missing or invalid Judge decisions')
                else:
                    first = decisions[0]
                    expected = 'reject'
                    if first['reference_sha256'] != previous or first['comparison'] != 'current':
                        failures.append('Wrong current comparison')
                    hard = first['predicted_changes']['hard']
                    if first['judge_accepted'] and hard != -1:
                        if hard == 0:
                            expected = 'accept' if manifest['benchmark']=='searchqa' and first['predicted_changes']['soft']==1 else 'flat'
                        elif previous == best:
                            expected = 'accept_new_best'
                        else:
                            if len(decisions) != 2 or decisions[1]['reference_sha256'] != best or decisions[1]['comparison'] != 'best':
                                failures.append('Missing or wrong best comparison')
                            else:
                                second = decisions[1]
                                expected = 'accept_new_best' if second['judge_accepted'] and second['predicted_changes']['hard']==1 else 'accept'
                    if row['action'] != expected:
                        failures.append('Judge gate decision does not replay')
                if row['action'] in ('accept', 'accept_new_best'):
                    previous = row['candidate_sha256']
                    current_text = candidate.read_text()
                if row['action'] == 'accept_new_best':
                    best = row['candidate_sha256']
                if row['current_sha256'] != previous or row['best_sha256'] != best:
                    failures.append('Judge skill lineage mismatch')
                history.append(EvolutionRound(**{k:row[k] for k in EvolutionRound.__dataclass_fields__}))
            if selection['sha256'] != best:
                failures.append('Judge final best mismatch')
            for native_root in (evolution/'evaluations').iterdir():
                if native_root.is_dir():
                    validate_run_evidence(native_root)
        events = [json.loads(line) for line in (root/'usage_events.jsonl').read_text().splitlines()]
        labeled = [e for e in events if e.get('replacement_component')]
        allowed = {'llm_judge'} if mode=='judge' else {'seed_validation','candidate_validation'}
        if any(e['replacement_component'] not in allowed for e in labeled):
            failures.append('Wrong replacement cost component')
        cost = read(root/'replacement_cost.json')
        if sum(e['total_tokens'] for e in labeled) != cost['total_tokens']:
            failures.append('Replacement token total mismatch')
    except Exception as exc:
        failures.append(f'Incomplete or invalid study evidence: {type(exc).__name__}: {exc}')
    return failures
