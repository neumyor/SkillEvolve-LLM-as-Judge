"""Local data/output translations; all judgment policy lives in JudgeGate."""
from __future__ import annotations

import json
from typing import Any

from skillopt.evaluation.evidence import bounded_text, public_value
from skillopt.evaluation.judge_gate import JudgeGate


def _render_candidate(candidate: Any) -> str:
    if isinstance(candidate, dict):
        return "\n\n".join(f"## {name}\n{candidate[name]}" for name in sorted(candidate))
    return str(candidate or "")


def _existing_card(item_id, task, output, trace, success, task_type="unspecified"):
    return {
        "id": str(item_id), "hard": success, "task_type": str(task_type),
        "judge_evidence": (
            f"id={item_id}; type={task_type}; observed_success={success}\n"
            + "task: " + bounded_text(public_value(task), 260)
            + "\nexisting_output: " + bounded_text(public_value(output), 260)
            + "\nexisting_trace: " + bounded_text(public_value(trace), 360)
        ),
    }


class GEPAJudgeAcceptanceCriterion:
    """Accept without child execution; optionally predict changes by task type."""

    skip_candidate_evaluation = True

    def reject_reason(self, proposal, state):
        record = proposal.metadata.get("judge_gate", {})
        return "Judge rejected without candidate execution: " + record.get("judge_reason", record.get("judge_error", ""))

    def __init__(self, judge=None, full_validation=None, prediction_axes=None):
        if full_validation is not None:
            raise ValueError("Judge mode forbids candidate full-validation audit")
        self.judge = judge or JudgeGate(prompt_variant="v3")
        self.prediction_axes = prediction_axes

    def should_accept(self, proposal, state):
        before = proposal.eval_before
        evidence = []
        if before is not None:
            for i, score in enumerate(before.scores):
                trace = before.trajectories[i] if before.trajectories else {}
                evidence.append(_existing_card(
                    proposal.subsample_indices[i],
                    trace.get("task_input", trace.get("question", trace.get("task", ""))) if isinstance(trace, dict) else "",
                    before.outputs[i], trace, score,
                    trace.get("task_type", "unspecified") if isinstance(trace, dict) else "unspecified",
                ))
        if not evidence:
            proposal.metadata["judge_gate"] = {"judge_accepted": False, "judge_error": "missing existing training evidence"}
            return False
        parent_ids = proposal.parent_program_ids
        parent = state.program_candidates[parent_ids[0]]
        result, record = self.judge(
            candidate_skill=_render_candidate(proposal.candidate),
            current_skill=_render_candidate(parent), current_score=0.0,
            best_skill=_render_candidate(parent), best_score=0.0,
            best_step=state.i, global_step=state.i + 1,
            ranked_patch={"rationale": proposal.metadata.get("rationale", "Reflective mutation of the parent")},
            batches=[{"results": evidence}], prediction_axes=self.prediction_axes,
        )
        record.update(adapter="gepa", parent_program_ids=parent_ids, candidate_executions=0)
        proposal.metadata["judge_gate"] = record
        return result.action == "accept_new_best"


class SkillGenJudgeAdapter:
    """Translate already-collected baseline trajectories, never verification cases."""

    def __init__(self, judge=None, full_validation=None):
        if full_validation is not None:
            raise ValueError("Judge mode forbids candidate full-validation audit")
        self.judge = judge or JudgeGate(prompt_variant="v3")

    def decide(self, *, candidate_skill, current_skill, trajectories,
               instances, rationale=None, previous_attempts=None):
        evidence = []
        for trajectory in trajectories:
            instance = instances.get(trajectory.instance_id)
            evidence.append(_existing_card(
                trajectory.instance_id, getattr(instance, "input", ""),
                trajectory.final_output, trajectory.messages, trajectory.success,
                (getattr(instance, "metadata", None) or {}).get("task_type", "unspecified"),
            ))
        if not evidence:
            return False, {"adapter": "skillgen", "judge_accepted": False,
                           "judge_error": "missing existing training evidence"}
        result, record = self.judge(
            candidate_skill=candidate_skill, current_skill=current_skill,
            current_score=0.0, best_skill=current_skill, best_score=0.0,
            best_step=0, global_step=len(previous_attempts or []),
            ranked_patch={"rationale": bounded_text(rationale or "", 2000)},
            batches=[{"results": evidence}], previous_attempts=previous_attempts,
        )
        record.update(adapter="skillgen", candidate_executions=0)
        return result.action == "accept_new_best", record


__all__ = ["GEPAJudgeAcceptanceCriterion", "SkillGenJudgeAdapter"]
