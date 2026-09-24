"""Judge validation policy over the shared official training/proposal phase."""
from contextlib import nullcontext
from dataclasses import dataclass, field

from rethinkskill.evolution.loop import (
    EvolutionRound, _ComponentCallState, prepare_evolution_round, skill_hash,
    validate_evolution_plan_freeze,
)
from rethinkskill.utils.serde import atomic_write, atomic_write_json
from skillopt.evaluation.evidence import public_value


@dataclass
class JudgeState:
    current_skill: str
    best_skill: str
    rounds: list = field(default_factory=list)
    target_calls: _ComponentCallState = field(default_factory=_ComponentCallState)
    optimizer_calls: _ComponentCallState = field(default_factory=_ComponentCallState)
    failure_class: str | None = None
    failure: str = ''
    failure_stage: str | None = None
    failure_round: int | None = None
    terminal_optimizer_evidence: object = None

    @property
    def failed(self):
        return self.failure_class is not None

    def fail(self, *, failure_class, failure, stage, round_no):
        self.failure_class, self.failure = failure_class, failure
        self.failure_stage, self.failure_round = stage, round_no


def evidence_cards(training):
    """Explicitly adapt official feedback, never rely on GEPA/SkillOpt trace keys.

    Same optimizer-visible observed feedback, except answer keys/gold references
    are excluded from the Judge. No additional task execution or hidden data read.
    """
    cards = []
    for row in training.public()['feedback']:
        visible = public_value({k: v for k, v in row.items() if k != 'gold'})
        cards.append({'id': row.get('case_id'),
                      'hard': 1 if row.get('category') == 'success' else 0,
                      'judge_evidence': visible})
    return [{'results': cards}]


def execute_judge_evolution(plan, *, evaluator, optimizer, judge):
    initial = validate_evolution_plan_freeze(plan)
    if plan.output_root.exists():
        raise ValueError('Judge evolution requires fresh output')
    plan.output_root.mkdir(parents=True)
    atomic_write(plan.output_root / 'skills/initial.md', initial.encode())
    state = JudgeState(initial, initial)
    history = []
    atomic_write_json(plan.output_root / 'judge_manifest.json', {
        'schema': 'rethinkskill_judge_v1', 'score_source': 'judge_prediction',
        'initial_validation': False, 'candidate_validation': False,
        'final_selection': 'best', 'prompt_variant': judge.prompt_variant,
        'evaluator': evaluator.public_manifest(), 'optimizer': optimizer.public_manifest(),
    })
    for round_no in range(1, plan.options.rounds + 1):
        prepared = prepare_evolution_round(plan, state=state, evaluator=evaluator,
            optimizer=optimizer, round_no=round_no, failure_stage=lambda _: nullcontext())
        if prepared is None:
            break
        training, proposal, optimizer_evidence, parent_hash, candidate_hash = prepared
        decisions = []
        if not proposal.valid:
            state.fail(failure_class=proposal.failure_class, failure=proposal.failure,
                       stage='optimization', round_no=round_no)
            action = 'infrastructure_invalid'
        elif proposal.operation == 'noop':
            action = 'flat'  # upstream: no validation, no Judge, no skill changes
        else:
            def decide(reference, comparison):
                # Shared gate's synthetic score outputs are deliberately ignored.
                _, record = judge(candidate_skill=proposal.candidate_skill,
                    current_skill=reference, current_score=0, best_skill=reference,
                    best_score=0, best_step=0, global_step=round_no,
                    ranked_patch={'rationale': proposal.rationale},
                    batches=evaluator.judge_batches(training) if hasattr(evaluator, 'judge_batches') else evidence_cards(training),
                    previous_attempts=history,
                    prediction_axes=['hard', 'soft'],
                    local_instructions=(
                        f'RethinkSkill local gate: hard=1 means predicted hard gain >= {plan.gate.hard_dead_band}; '
                        f'hard=-1 means predicted hard loss >= {plan.gate.hard_dead_band}; hard=0 means inside that band. '
                        f'soft=1 means predicted soft gain >= {plan.gate.soft_rescue_delta}.'
                        if plan.gate.soft_rescue_delta is not None else
                        f'RethinkSkill local gate: hard=1 means predicted hard gain >= {plan.gate.hard_dead_band}; '
                        f'hard=-1 means predicted hard loss >= {plan.gate.hard_dead_band}; hard=0 means inside that band. '
                        'Soft rescue is disabled; return soft=0.'
                    ) + (' This comparison selects the best checkpoint: hard=1 means any predicted hard improvement; '
                         'soft improvement alone must not update best.' if comparison == 'best' else ''))
                record = {**record, 'comparison': comparison,
                          'reference_sha256': skill_hash(reference),
                          'candidate_sha256': candidate_hash}
                decisions.append(record)
                return record

            record = decide(state.current_skill, 'current')
            if record['judge_parse_failed'] or record['judge_error']:
                action = 'judge_invalid'
            elif not record['judge_accepted'] or record['predicted_changes']['hard'] == -1:
                action = 'reject'
            elif record['predicted_changes']['hard'] == 0:
                if plan.gate.soft_rescue_delta is not None and record['predicted_changes']['soft'] == 1:
                    state.current_skill = proposal.candidate_skill
                    action = 'accept'  # official soft rescue never updates best
                else:
                    action = 'flat'
            else:
                best_record = record if state.current_skill == state.best_skill else decide(state.best_skill, 'best')
                if best_record['judge_parse_failed'] or best_record['judge_error']:
                    action = 'judge_invalid'
                else:
                    state.current_skill = proposal.candidate_skill
                    action = 'accept_new_best' if best_record['judge_accepted'] and best_record['predicted_changes']['hard'] == 1 else 'accept'
                    if action == 'accept_new_best':
                        state.best_skill = proposal.candidate_skill
            if action == 'judge_invalid':
                state.fail(failure_class='judge_invalid', failure='Judge response failed validation',
                           stage='candidate_validation', round_no=round_no)
        record = EvolutionRound(round_no=round_no, action=action, operation=proposal.operation,
            parent_sha256=parent_hash, candidate_sha256=candidate_hash,
            current_sha256=skill_hash(state.current_skill), best_sha256=skill_hash(state.best_skill),
            candidate_hard=None, candidate_soft=None)
        state.rounds.append(record)
        payload = {**record.public(), 'training': training.public(),
                   'optimizer_evidence': optimizer_evidence, 'judge_decisions': decisions,
                   'validation': None, 'score_source': 'judge_prediction'}
        atomic_write_json(plan.output_root / f'rounds/round_{round_no:04d}.json', payload)
        atomic_write_json(plan.output_root / 'checkpoint.json', {
            'round': round_no, 'current_skill': state.current_skill, 'best_skill': state.best_skill,
            'history': [r.public() for r in state.rounds], 'failure_class': state.failure_class})
        history.extend(decisions)
        if state.failed:
            break
    atomic_write(plan.output_root / 'final_current_skill.md', state.current_skill.encode())
    atomic_write(plan.output_root / 'best_skill.md', state.best_skill.encode())
    receipt = {'schema': 'rethinkskill_judge_v1',
        'status': 'JUDGE_EVOLUTION_INVALID' if state.failed else 'JUDGE_EVOLUTION_COMPLETED',
        'failure_class': state.failure_class, 'failure': state.failure,
        'failure_stage': state.failure_stage, 'rounds_recorded': len(state.rounds),
        'final_current': {'sha256': skill_hash(state.current_skill)},
        'best': {'sha256': skill_hash(state.best_skill)},
        'score_source': 'judge_prediction', 'initial_validation': None}
    atomic_write_json(plan.output_root / 'judge_receipt.json', receipt)
    return receipt
