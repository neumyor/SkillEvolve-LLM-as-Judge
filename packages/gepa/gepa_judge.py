"""GEPA runner helpers for JudgeGate and full-validation auditing."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from skillopt.evaluation import GEPAJudgeAcceptanceCriterion


class GEPAFullValidationAudit:
    """Evaluate every proposal on the complete GEPA validation set.

    Judge-mode runs do not otherwise score this held-out set during candidate
    selection. This callback intentionally evaluates rejected proposals too,
    so an explicitly requested audit can classify both false accepts and false
    rejects. Its result is consumed only by ``GEPAJudgeAcceptanceCriterion``
    and never feeds acceptance.
    """

    def __init__(self, adapter: Any, valset: list[Any], *, audit_path: str | Path | None = None):
        self.adapter = adapter
        self.valset = valset
        self.audit_path = Path(audit_path) if audit_path else None

    def __call__(self, *, candidate, parent, proposal, state) -> dict[str, Any]:
        parent_ids = list(getattr(proposal, "parent_program_ids", None) or [])
        parent_idx = int(parent_ids[0]) if parent_ids else 0
        parent_scores = list(getattr(state, "program_full_scores_val_set", None) or [])
        before = float(parent_scores[parent_idx]) if 0 <= parent_idx < len(parent_scores) else 0.0
        evaluated = self.adapter.evaluate(self.valset, candidate, capture_traces=False)
        scores = list(getattr(evaluated, "scores", None) or [])
        after = sum(float(score) for score in scores) / max(len(scores), 1)
        return {
            "candidate_id": getattr(state, "i", "unknown"),
            "before_score": before,
            "after_score": after,
            "items": len(scores),
            "full_validation_scores": scores,
            "audit_path": str(self.audit_path) if self.audit_path else "",
        }


def make_judge_acceptance_criterion(
    *,
    prompt_variant: str = "v3",
    full_validation=None,
    prediction_axes=None,
    **judge_kwargs,
) -> GEPAJudgeAcceptanceCriterion:
    """Build the configured GEPA criterion from the shared JudgeGate."""
    from skillopt.evaluation import JudgeGate

    judge = JudgeGate(prompt_variant=prompt_variant, **judge_kwargs)
    return GEPAJudgeAcceptanceCriterion(judge, full_validation=full_validation,
                                       prediction_axes=prediction_axes)


__all__ = ["GEPAFullValidationAudit", "make_judge_acceptance_criterion"]
