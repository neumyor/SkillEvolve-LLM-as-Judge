"""Scoring and hashing utilities."""
from __future__ import annotations

import hashlib


def compute_score(results: list) -> tuple[float, float]:
    """Compute hard and soft accuracy from a list of episode results.

    Accepts both plain dicts and :class:    instances.  hard may be continuous (0.0-1.0) when using smoothed reward.
    """
    if not results:
        return 0.0, 0.0

    def _hard(r: object) -> float:
        return float(r.hard if hasattr(r, "hard") else r.get("hard", 0))

    def _soft(r: object) -> float:
        return float(r.soft if hasattr(r, "soft") else r.get("soft", 0.0))

    hard = sum(_hard(r) for r in results) / len(results)
    soft = sum(_soft(r) for r in results) / len(results)
    return hard, soft


def skill_hash(content: str) -> str:
    """Return a short deterministic hash of skill content (for caching)."""
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def evolution_skill_identity(content: str) -> str:
    """Hash of the *evolvable* part of a skill document.

    The slow-update block is protected: step-level reflect cannot edit it, and
    its content changes only at epoch boundaries. Two things follow.

    - Injecting the empty placeholder at the end of epoch 1 changes the skill
      document byte-for-byte while changing nothing the optimizer can act on.
      A full-text :func:`skill_hash` would read that as a new skill version
      and invalidate an evidence buffer that is still semantically
      homogeneous. Measured on the SearchQA run: 22 buffered observations
      (220 tasks) were discarded for exactly this reason.
    - A buffer only needs to be homogeneous in the part of the skill the
      optimizer *sees and edits*; the protected block is outside that scope.

    Use this wherever a skill identity decides buffer validity (evolution
    scheduling, resume, staleness checks), and keep plain :func:`skill_hash`
    where the whole document — protected block included — is the artifact
    (candidate/gate score caching, best-vs-current comparisons, reporting).
    """
    return skill_hash(strip_slow_update_fields(content))


def strip_slow_update_fields(content: str) -> str:
    """Return *content* without its ``SLOW_UPDATE_START/END`` region(s).

    Every existing pair and its contents are removed, as are stray markers, so
    that the result depends only on text a step-level edit can reach. The
    helper lives in :mod:`skillopt.optimizer.slow_update` next to the markers
    themselves; it is imported lazily to keep this module dependency-free.
    """
    from skillopt.optimizer.slow_update import _strip_all_slow_update_fields

    return _strip_all_slow_update_fields(content)
