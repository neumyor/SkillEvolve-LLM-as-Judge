"""Full-validation audit records for LLM-gated candidate decisions.

The judge is allowed to decide acceptance without seeing held-out scores.  A
separate full-validation pass can still be run afterwards and recorded as an
oracle audit.  The audit never changes the judge decision.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def validation_decision(*, before_score: float, after_score: float, strict: bool = True) -> bool:
    """Return the deterministic acceptance decision used by the old gate."""
    if strict:
        return float(after_score) > float(before_score)
    return float(after_score) >= float(before_score)


def make_validation_audit(
    *,
    method: str,
    candidate_id: str,
    judge_accepted: bool,
    before_score: float,
    after_score: float,
    split: str = "full_validation",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a JSON-serializable judge-vs-validation comparison."""
    validation_accepted = validation_decision(
        before_score=before_score,
        after_score=after_score,
    )
    if judge_accepted and validation_accepted:
        error_type = "correct_accept"
    elif not judge_accepted and not validation_accepted:
        error_type = "correct_reject"
    elif judge_accepted:
        error_type = "false_accept"
    else:
        error_type = "false_reject"
    record: dict[str, Any] = {
        "method": method,
        "candidate_id": str(candidate_id),
        "split": split,
        "judge_accepted": bool(judge_accepted),
        "validation_accepted": bool(validation_accepted),
        "before_score": float(before_score),
        "after_score": float(after_score),
        "delta": float(after_score) - float(before_score),
        "error_type": error_type,
    }
    if metadata:
        record.update(metadata)
    return record


def append_validation_audit(path: str | Path, record: dict[str, Any]) -> None:
    """Append one audit record, creating parent directories as needed."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


__all__ = [
    "append_validation_audit",
    "make_validation_audit",
    "validation_decision",
]
