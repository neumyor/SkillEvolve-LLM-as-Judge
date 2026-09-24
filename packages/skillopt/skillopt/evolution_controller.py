"""Evidence-triggered skill evolution — the Evolution Controller Agent.

SkillOpt's trainer drives skill updates on a fixed schedule: every
``train.batch_size * train.accumulation`` rollouts, the reflect → aggregate →
select → update → gate pipeline runs unconditionally. This module replaces
*when that pipeline is invoked* with an explicit, swappable decision layer
while leaving *how the skill is evolved* untouched.

The trainer streams training tasks in small **observation batches** of
``evolution.observation_batch_size`` (m) tasks. After every observation, the
active :class:`EvolutionPolicy` sees the current skill, the newly observed
rollout results, and its own persistent evidence state, and answers exactly
one question:

    Is there sufficient accumulated evidence to justify invoking the skill
    optimizer now?

The answer is a single action::

    a_t ∈ { WAIT, UPDATE }

On WAIT, the evidence buffer keeps growing and nothing else happens — no
reflect, no candidate, no validation. On UPDATE, the original SkillOpt
optimizer runs over *everything accumulated since the previous attempt*
(B_t = all experiences in the window), and the buffer plus the controller
state are reset afterwards regardless of whether the validation gate accepts
or rejects the candidate. One cycle is therefore::

    evidence accumulation → evolution attempt → reset

Policies
--------
``ImmediatePolicy``
    UPDATE after every observation batch (per-observation-batch schedule).
``FixedKPolicy``
    UPDATE after every K observation batches (fixed-K schedule; the window
    is K*m tasks). This generalises the original fixed ``batch_size``
    schedule, which is the special case m = batch_size, K = 1.
``EndPolicy``
    WAIT after every observation; UPDATE at the epoch boundary (per-epoch
    schedule).
``LLMEvidencePolicy``
    **Ours** — the Evolution Controller Agent. An LLM judge that maintains a
    short semantic *evidence state* M_t (suspected deficiencies, supporting
    and counter evidence, unresolved uncertainty) and decides WAIT/UPDATE by
    reasoning over the *content* of the evidence, not merely its quantity.

All policies implement the same :class:`EvolutionPolicy` interface and run
inside the same trainer loop, so every scheduling baseline and our method
differ *only* in this decision. The skill optimizer (reflect prompts,
patch aggregation, edit selection, update, validation gate, rollback) is
byte-for-byte the original SkillOpt implementation.

The LLM policy deliberately contains no numeric thresholds (no "update if
failure rate > x", no "update after N failures"). Its decision is a semantic
judgement guided by the four principles in its system prompt.
"""
from __future__ import annotations

import json
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

__all__ = [
    "WAIT",
    "UPDATE",
    "EvolutionDecision",
    "EvolutionPolicy",
    "ImmediatePolicy",
    "FixedKPolicy",
    "EndPolicy",
    "LLMEvidencePolicy",
    "normalize_evolution_mode",
    "EVOLUTION_MODES",
    "build_evolution_policy",
    "format_observation_card",
    "load_trajectory_excerpt",
    "failure_direction",
    "summarize_window",
]


# ── Actions ──────────────────────────────────────────────────────────────────

WAIT = "WAIT"
UPDATE = "UPDATE"

_ACTION_ALIASES = {
    "wait": WAIT,
    "update": UPDATE,
}


def _normalize_action(value: object) -> str:
    raw = str(value or "").strip().strip('`"\'').upper()
    return _ACTION_ALIASES.get(raw.lower(), raw)


# ── Decision ─────────────────────────────────────────────────────────────────


@dataclass
class EvolutionDecision:
    """The controller's answer for one observation: WAIT or UPDATE.

    Parameters
    ----------
    action : str
        ``"WAIT"`` or ``"UPDATE"``.
    state : dict
        The updated evidence state M_t (JSON-serializable). Owned by the
        policy; the trainer persists it verbatim and hands it back on the
        next observation.
    reason : str
        Short human-readable justification (logged, never parsed).
    raw : dict | None
        The full unparsed controller output (LLM policies), for auditing.
    meta : dict
        Extra bookkeeping (policy name, parse retries, fallback flags).
    """

    action: str
    state: dict
    reason: str = ""
    raw: dict | None = None
    meta: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.action = _normalize_action(self.action)
        if self.action not in (WAIT, UPDATE):
            raise ValueError(
                f"EvolutionDecision.action must be 'WAIT' or 'UPDATE', got {self.action!r}"
            )

    @property
    def is_update(self) -> bool:
        return self.action == UPDATE


# ── Policy interface ─────────────────────────────────────────────────────────


class EvolutionPolicy(ABC):
    """Decides *when* to invoke the skill optimizer — never *how*.

    Contract
    --------
    - ``observe`` is called once after every observation batch, and once at
      an epoch boundary (``epoch_end=True``, ``new_results=[]``) when the
      evidence buffer is non-empty.
    - The policy itself is stateless between calls: its mutable belief lives
      in the ``evidence_state`` dict that the trainer persists and passes
      back. Everything must therefore stay JSON-serializable.
    - The policy must not modify the skill, select training examples, or
      otherwise influence the optimizer. It only returns WAIT or UPDATE.
    """

    #: short name used in logs / artifacts
    name: str = "policy"

    @abstractmethod
    def initial_state(self) -> dict:
        """Return the fresh evidence state M_0 for a new accumulation cycle."""

    def reset_state(
        self,
        outcome: str = "accepted",
        trigger_state: dict | None = None,
    ) -> dict:
        """Return the evidence state to use after an evolution attempt.

        Default: a fresh :meth:`initial_state`, whatever the outcome.
        Called after every attempt (accepted, rejected, or skipped).
        ``trigger_state`` is the controller's own state at the moment the
        attempt was triggered, for policies that keep magnitude memory
        across a failed attempt on an unchanged skill.
        """
        return self.initial_state()

    @abstractmethod
    def observe(
        self,
        skill: str,
        new_results: list[dict],
        evidence_state: dict,
        *,
        epoch_end: bool = False,
        rollout_dir: str | None = None,
        context: dict | None = None,
    ) -> EvolutionDecision:
        """Judge whether the accumulated evidence justifies an UPDATE.

        Parameters
        ----------
        skill : str
            The current skill document (unchanged since the buffer was
            started — the trainer guarantees a homogeneous-skill window).
        new_results : list[dict]
            Rollout result dicts (:class:`~skillopt.types.RolloutResult`
            layout) from the observation batch that just completed. Empty
            at an epoch-boundary consult.
        evidence_state : dict
            The policy's own state from the previous observation (M_{t-1}).
        epoch_end : bool
            True when this consult happens at an epoch boundary (the
            observation stream for the current epoch is exhausted).
        rollout_dir : str | None
            Directory holding ``predictions/<id>/conversation.json`` for
            ``new_results`` — used to surface trajectory excerpts.
        context : dict | None
            Optional bookkeeping from the trainer (epoch, observation
            index, buffer sizes, train_size). Never load-bearing for the
            decision; useful for logging.
        """


# ── Fixed-schedule baselines ────────────────────────────────────────────────


class ImmediatePolicy(EvolutionPolicy):
    """UPDATE after every observation batch (per-batch fixed schedule).

    With ``observation_batch_size=m`` this updates every m tasks; with m=1
    it degenerates to the per-sample schedule.
    """

    name = "immediate"

    def initial_state(self) -> dict:
        return {"observations_since_attempt": 0}

    def observe(
        self,
        skill: str,
        new_results: list[dict],
        evidence_state: dict,
        *,
        epoch_end: bool = False,
        rollout_dir: str | None = None,
        context: dict | None = None,
    ) -> EvolutionDecision:
        state = dict(evidence_state or {})
        n_new = 1 if new_results else 0
        state["observations_since_attempt"] = (
            int(state.get("observations_since_attempt", 0) or 0) + n_new
        )
        if state["observations_since_attempt"] >= 1:
            return EvolutionDecision(
                action=UPDATE,
                state=state,
                reason="immediate schedule: update after every observation batch",
                meta={"policy": self.name},
            )
        return EvolutionDecision(
            action=WAIT,
            state=state,
            reason="no new observations",
            meta={"policy": self.name},
        )


class FixedKPolicy(EvolutionPolicy):
    """UPDATE after every K observation batches (fixed-K schedule).

    The evidence window of one attempt is ``K * observation_batch_size``
    tasks. Counting is global across epochs: a partial window at an epoch
    boundary carries over, so update events stay uniformly spaced over the
    whole stream. With m = batch_size and K = 1 this reproduces the
    original SkillOpt per-step schedule.
    """

    name = "fixed_k"

    def __init__(self, k: int = 1) -> None:
        k = int(k)
        if k < 1:
            raise ValueError(f"fixed_k must be >= 1, got {k}")
        self.k = k

    def initial_state(self) -> dict:
        return {"observations_since_attempt": 0}

    def observe(
        self,
        skill: str,
        new_results: list[dict],
        evidence_state: dict,
        *,
        epoch_end: bool = False,
        rollout_dir: str | None = None,
        context: dict | None = None,
    ) -> EvolutionDecision:
        state = dict(evidence_state or {})
        n_new = 1 if new_results else 0
        state["observations_since_attempt"] = (
            int(state.get("observations_since_attempt", 0) or 0) + n_new
        )
        count = state["observations_since_attempt"]
        if count >= self.k:
            reason = (
                f"fixed-K schedule: {count} observation batch(es) accumulated "
                f"(K={self.k})"
            )
            return EvolutionDecision(
                action=UPDATE, state=state, reason=reason,
                meta={"policy": self.name, "k": self.k},
            )
        return EvolutionDecision(
            action=WAIT,
            state=state,
            reason=f"fixed-K schedule: {count}/{self.k} observation batch(es) accumulated",
            meta={"policy": self.name, "k": self.k},
        )


class EndPolicy(EvolutionPolicy):
    """WAIT after every observation; UPDATE at the epoch boundary.

    One attempt per epoch, using the whole epoch's accumulated evidence —
    the per-epoch fixed schedule.
    """

    name = "end"

    def initial_state(self) -> dict:
        return {"observations_since_attempt": 0}

    def observe(
        self,
        skill: str,
        new_results: list[dict],
        evidence_state: dict,
        *,
        epoch_end: bool = False,
        rollout_dir: str | None = None,
        context: dict | None = None,
    ) -> EvolutionDecision:
        state = dict(evidence_state or {})
        n_new = 1 if new_results else 0
        state["observations_since_attempt"] = (
            int(state.get("observations_since_attempt", 0) or 0) + n_new
        )
        count = state["observations_since_attempt"]
        if epoch_end:
            if count >= 1:
                return EvolutionDecision(
                    action=UPDATE,
                    state=state,
                    reason=f"end-of-epoch schedule: {count} observation batch(es) accumulated",
                    meta={"policy": self.name, "epoch_end": True},
                )
            return EvolutionDecision(
                action=WAIT,
                state=state,
                reason="end-of-epoch schedule: no evidence accumulated",
                meta={"policy": self.name, "epoch_end": True},
            )
        return EvolutionDecision(
            action=WAIT,
            state=state,
            reason="end-of-epoch schedule: waiting for the epoch boundary",
            meta={"policy": self.name},
        )


# ── Evidence cards ───────────────────────────────────────────────────────────


def _clip(text: object, limit: int) -> str:
    value = "" if text is None else str(text)
    value = value.strip()
    if limit <= 0 or len(value) <= limit:
        return value
    return value[:limit] + " …[truncated]"


def _to_int(value: object, default: int) -> int:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    return max(0, n)


def _hard_of(result: object) -> float:
    if isinstance(result, dict):
        value = result.get("hard")
    else:
        value = getattr(result, "hard", None)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def failure_direction(result: object) -> str | None:
    """Classify one failure as over-specified, under-specified, or other.

    "over" means the predicted answer carries more words than the shortest
    gold span (the classic SearchQA over-extraction failure); "under" means
    it carries fewer (over-stripping). ``None`` marks a success.

    The split matters because the two directions call for *opposite* fixes.
    A window whose failures straddle both directions cannot be repaired by
    adding another rule — the skill itself is inconsistent — so the
    controller must see the split rather than a bare failure count.
    """
    if _hard_of(result) >= 1.0:
        return None

    def _norm(text: object) -> str:
        value = str(text or "").lower()
        value = re.sub(r"[^a-z0-9 ]", " ", value)
        return " ".join(value.split())

    pred = _norm(
        result.get("predicted_answer") if isinstance(result, dict)
        else getattr(result, "predicted_answer", "")
    )
    golds = (
        result.get("gold_answers") if isinstance(result, dict)
        else getattr(result, "gold_answers", None)
    ) or []
    gold_lengths = [len(_norm(g).split()) for g in golds if _norm(g)]
    if not pred or not gold_lengths:
        return "other"
    pred_len = len(pred.split())
    gold_len = min(gold_lengths)
    if pred_len > gold_len:
        return "over"
    if pred_len < gold_len:
        return "under"
    return "other"


def summarize_window(batches: list) -> dict:
    """Aggregate failure evidence across the whole buffered window.

    The controller only ever sees evidence cards for the *latest* batch, so
    a decision to spend an optimizer attempt on a 50-task window was being
    made from 10 tasks of evidence. This summary gives it the real window:
    how many tasks, how many failures, and — the part that never reached the
    prompt before — how the failures split across directions.
    """
    n_tasks = n_failures = over = under = other = 0
    for batch in batches or []:
        for result in batch or []:
            n_tasks += 1
            direction = failure_direction(result)
            if direction is None:
                continue
            n_failures += 1
            if direction == "over":
                over += 1
            elif direction == "under":
                under += 1
            else:
                other += 1
    return {
        "n_batches": len(batches or []),
        "n_tasks": n_tasks,
        "n_failures": n_failures,
        "fail_rate": (n_failures / n_tasks) if n_tasks else 0.0,
        "over": over,
        "under": under,
        "other": other,
    }


def window_lean(window: dict, margin: float = 0.25) -> str:
    """Classify a window's failure directions as leaned, straddling, or noisy.

    Returns ``"over"``, ``"under"``, ``"straddle"``, or ``"none"``.

    ``other`` participates: a failure whose predicted and gold answers have
    the same word count is neither over- nor under-specified, and a window
    where ``other`` dominates is the *most* fragmented kind — every failure
    is a different mechanism. Ignoring ``other`` mislabels exactly those
    windows as shared-direction ones. Measured on the V5 run: the 200-task
    window was ``over=16 under=9 other=18`` and was rendered as "leans
    OVER-specified (the failures share a direction)" because the ratio only
    looked at 16/(16+9); the controller believed the line and spent a
    200-task window on an attempt the gate rejected at val 0.7500.
    """
    over = int(window.get("over") or 0)
    under = int(window.get("under") or 0)
    other = int(window.get("other") or 0)
    total = over + under + other
    if total == 0:
        return "none"
    leaning = over + under
    # No directional failure at all: every failure was an undirected miss.
    if leaning == 0:
        return "none"
    # `other` dominating the directional ones means no shared direction
    # exists to act on — the window is fragmented across mechanisms.
    if other > max(over, under):
        return "straddle"
    # Both directions present with no clear lean.
    if over > 0 and under > 0 and abs(over - under) / leaning < margin:
        return "straddle"
    # The lean must also be a real share of ALL failures, not just of the
    # directional subset.
    if abs(over - under) / total < margin * 0.5:
        return "straddle"
    return "over" if over > under else "under"


def load_trajectory_excerpt(
    rollout_dir: str | None,
    task_id: str,
    max_chars: int = 1200,
) -> str:
    """Load a compact trajectory excerpt for one task from its rollout dir.

    Reads ``predictions/<task_id>/conversation.json`` — the exact artifact
    the SkillOpt reflect stage consumes — and renders it with the shared
    trajectory formatter, clipped to ``max_chars``. Any missing/corrupt
    file yields an empty string (the card degrades gracefully).
    """
    if not rollout_dir:
        return ""
    path = os.path.join(rollout_dir, "predictions", str(task_id), "conversation.json")
    try:
        with open(path, encoding="utf-8") as f:
            conversation = json.load(f)
    except (OSError, ValueError):
        return ""
    if not isinstance(conversation, list) or not conversation:
        return ""
    from skillopt.gradient.reflect import fmt_trajectory

    return _clip(fmt_trajectory(conversation), max_chars)


def format_observation_card(
    result: dict,
    rollout_dir: str | None = None,
    *,
    max_chars: int = 1200,
    view: str = "semantic",
) -> str:
    """Render one rollout result as a compact evidence card.

    ``view="semantic"`` (ours): task, outcome, score, evaluator feedback and
    a trajectory excerpt — the same artifacts the reflect stage uses.
    ``view="score"`` (ablation): only the task id, outcome and score; no
    task content, no feedback, no trajectory, and the caller also omits the
    skill and the semantic evidence state. This isolates *content-based*
    timing from *quantity/aggregate-statistics-based* timing.
    """
    view = str(view or "semantic").strip().lower()
    if view not in ("semantic", "score"):
        raise ValueError(
            f"evidence card view must be 'semantic' or 'score', got {view!r}"
        )
    task_id = str(result.get("id", "?"))
    hard = result.get("hard", 0)
    outcome = "success" if (hard is not None and float(hard) >= 1.0) else "failure"
    soft = result.get("soft", 0.0)
    try:
        soft_text = f"{float(soft):.3f}"
    except (TypeError, ValueError):
        soft_text = str(soft)

    if view == "score":
        return f"- {task_id}: {outcome} (score {soft_text})"

    lines = [f"### Task {task_id}"]
    task_type = str(result.get("task_type", "") or "").strip()
    if task_type:
        lines.append(f"- Task type: {_clip(task_type, 120)}")
    task_desc = result.get("task_description") or result.get("question") or result.get("instruction") or ""
    if task_desc:
        lines.append(f"- Task: {_clip(task_desc, 400)}")
    lines.append(f"- Outcome: {outcome}")
    lines.append(f"- Score: {soft_text}")
    fail_reason = str(result.get("fail_reason", "") or "").strip()
    if fail_reason:
        lines.append(f"- Evaluator feedback: {_clip(fail_reason, 400)}")
    excerpt = load_trajectory_excerpt(rollout_dir, task_id, max_chars=max_chars)
    if excerpt:
        lines.append("- Trajectory excerpt:")
        lines.append(excerpt)
    return "\n".join(lines)


# ── The Evolution Controller Agent (ours) ────────────────────────────────────

_CONTROLLER_SYSTEM_PROMPT = """You are an evolution timing controller for a self-evolving agent skill.

Your job is NOT to improve or rewrite the skill.
Your only job is to decide whether the accumulated execution evidence is
sufficient to justify invoking the skill optimizer now.

UPDATE when the current evidence supports a coherent, recurring, actionable
deficiency in the current skill.

WAIT when the evidence is isolated, noisy, contradictory, task-specific,
or can plausibly be explained by execution randomness rather than the skill.

Two memory layers, strictly separated:

- The EVIDENCE STATE is your current belief about the current skill: which
  defects are supported, how strongly, and whether support is still growing.
  It is not optimizer history. A rejected candidate is NOT evidence against
  a hypothesis — rejection only means that particular edit set failed
  validation.
- The PREVIOUS EVOLUTION ATTEMPTS record real interventions: why the
  controller triggered, what the optimizer actually changed, and how the
  verifier judged the whole candidate. The optimizer never sees your
  hypotheses (it edits from the raw failure buffer), so never assume an
  attempt targeted your hypothesis — compare its edits to the mechanism you
  now see and judge whether they materially overlap.

When deciding, consider:
- whether multiple independent cases support the same underlying problem;
- whether successes inside a hypothesis's scope contradict it;
- whether the problem is attributable to the skill rather than the task;
- whether a generalizable skill-level correction appears possible.

Evidence state rules:
- support_count / contradiction_count carry magnitude; keep only a few
  representative case ids, not every one.
- A success is a contradiction ONLY if the hypothesis applied (the task
  fell inside its scope) and the failure it predicts could have occurred
  but did not. A success outside the hypothesis's scope is not
  counter-evidence.
- Hypotheses may weaken or die: set status to "active", "weakened", or
  "rejected". "rejected" means your own current evidence disproves the
  hypothesis — never use it merely because an attempt was rejected.
- A hypothesis with status "weakened" and prior_support / prior_window_tasks
  fields is carried over from a previous cycle on this same skill: its
  evidence was consumed by an attempt, prior_support is the peak it reached
  over prior_window_tasks tasks, and current counts measure regrowth since.
- assessment discusses the current evidence only; do not cite attempt
  history inside it.

Fragmented windows:
- The window summary reports how failures split across OVER-specified
  (the answer carried more words than the gold span) and UNDER-specified
  (fewer). These two directions call for opposite corrections.
- A window whose failures straddle both directions with no clear lean is
  usually evidence that the skill itself is internally inconsistent, not
  that a rule is missing. Adding another rule to such a skill makes it
  worse: each new rule feeds one direction and starves the other. Prefer
  WAIT, or state the contradiction explicitly in the hypothesis `defect`
  field ("RULES X AND Y CONFLICT: X drops modifiers while Y requires them")
  so the optimizer is asked to reconcile them rather than append a third
  opinion.
- Repeated attempts that all target the same contradiction and are all
  rejected are evidence the *diagnosis* is wrong, not the threshold. Do not
  keep re-triggering with a new count on the same wording.

Using history: a previous attempt justifies WAIT only when ALL of these
hold —
1. the current defect is materially similar to what that attempt addressed;
2. that attempt's edits were materially similar to what would be needed now;
3. support has not grown since that attempt (no new failure mechanism, and
   the failure rate has not risen beyond the window's sampling noise).
Any single escape breaks the block: the optimizer never actually addressed
this mechanism; this is a different specific mechanism within the same
family; support has clearly grown; the past attempt was a near-miss (a tie
or small decline rejected by the gate) rather than a clear refutation; or
the defect reappeared on a new skill after an ACCEPTED change.
"Clearly grown" means a rate increase larger than sampling noise, not a
count increase — three failures in ten tasks is noise, not growth.

The window summary reports how many attempts in a row have now been
rejected on this unchanged skill. Each one means the optimizer tried, from
roughly this much evidence, and the validation set disagreed. A streak of
two or more is a strong reason to WAIT until the window is materially
larger than the windows those attempts consumed — unless the new evidence
shows a *different* mechanism, in which case say so explicitly in the
hypothesis and trigger.

In short: Evidence State tells you what is currently supported. Previous
Attempts tell you what was actually tried. Use history only to avoid
redundant interventions when current evidence has not materially changed.

Return WAIT or UPDATE and the updated evidence state.
Do not propose the actual skill modification.

Return exactly one JSON object with this shape:
{
  "decision": "WAIT" or "UPDATE",
  "evidence_state": {
    "hypotheses": [
      {
        "defect": "<suspected skill deficiency>",
        "support_count": <integer>,
        "contradiction_count": <integer>,
        "supporting_cases": ["<task id>"],
        "contradicting_cases": ["<task id>"],
        "status": "active" | "weakened" | "rejected",
        "assessment": "<why this is or is not yet actionable>"
      }
    ],
    "unresolved": "<what further evidence would help>"
  },
  "reason": "<one short paragraph>"
}

tasks_since_last_attempt and failures_since_last_attempt are maintained
automatically — carry their current values through unchanged.
"""

_REMINDER = (
    'Return exactly one JSON object: {"decision": "WAIT"|"UPDATE", '
    '"evidence_state": {...}, "reason": "..."}'
)


class LLMEvidencePolicy(EvolutionPolicy):
    """The Evolution Controller Agent — an LLM-based sequential evidence judge.

    After every observation batch the controller sees:

    1. the current skill,
    2. its own previous evidence state M_{t-1} (suspected deficiencies,
       supporting and counter evidence, unresolved uncertainty), and
    3. compact evidence cards for the newly observed task executions
       (task, outcome, score, evaluator feedback, trajectory excerpt),

    and returns ``(M_t, a_t)`` with ``a_t in {WAIT, UPDATE}``.

    Design notes
    ------------
    - Reuses the optimizer backend (same underlying LLM as the skill
      optimizer, via :func:`skillopt.model.chat_optimizer` with a distinct
      token-tracking stage) but with its own system prompt, state and
      responsibility — it is a different agent, not a different model.
    - No numeric thresholds in the decision: it is a semantic judgement.
      (Cycle-level bookkeeping — tasks/failures since the last attempt — is
      maintained deterministically by the policy code, not by the LLM.)
    - Memory is two strictly separated layers: the evidence state holds the
      *current* belief about the current skill (hypotheses with magnitude
      and status), while previous evolution attempts record real
      interventions (trigger evidence → optimizer edits → verifier
      verdict). A rejected candidate is never evidence against a
      hypothesis; history justifies WAIT only when the defect, the edits,
      and the evidence level all match a prior attempt.
    - A malformed response is retried a bounded number of times and then
      falls back to WAIT with the previous state unchanged — a controller
      failure must never crash training or silently trigger updates.
    - ``view="score"`` strips the skill, the task content, the evaluator
      feedback, the trajectory and the semantic state, leaving only
      per-task outcome/score rows: the "Score Controller" ablation that
      tests whether adaptive timing needs the *content* of evidence.
    """

    name = "controller"

    def __init__(
        self,
        *,
        view: str = "semantic",
        max_observation_chars: int = 1200,
        max_state_chars: int = 4000,
        max_parse_retries: int = 2,
        max_completion_tokens: int = 4096,
        attempt_memory: bool = True,
        min_window_tasks: int = 10,
        floor_step: int = 30,
        window_lean_margin: float = 0.25,
        chat_fn=None,
    ) -> None:
        view = str(view or "semantic").strip().lower()
        if view not in ("semantic", "score"):
            raise ValueError(
                f"evolution.controller_view must be 'semantic' or 'score', got {view!r}"
            )
        self.view = view
        self.max_observation_chars = int(max_observation_chars)
        self.max_state_chars = int(max_state_chars)
        self.max_parse_retries = max(0, int(max_parse_retries))
        self.max_completion_tokens = int(max_completion_tokens)
        #: Base evidence floor in tasks. A static floor is wrong in both
        #: directions: V3's decisive accept came from a 50-task window while
        #: its wasteful attempts came from 10-task re-triggers, and a floor
        #: high enough to block the latter also blocked the former. The floor
        #: therefore escalates with ``floor_step`` per consecutive rejection
        #: on the *current* skill (see :attr:`reject_streak`): early triggers
        #: stay agile, and a streak of rejected attempts on an unchanged
        #: skill must earn a proportionally larger window before it may spend
        #: another optimizer attempt.
        self.min_window_tasks = max(0, int(min_window_tasks))
        self.floor_step = max(0, int(floor_step))
        #: Failure rate a below-floor window must clear to still be consulted.
        self.window_floor_fail_rate = 0.4
        #: Over/under lean a fragmented window must show before its
        #: contradiction is treated as actionable rather than noisy.
        self.window_lean_margin = float(window_lean_margin)
        #: Skip the consult entirely when the buffer shows no failures at
        #: all: no hypothesis can gain support from a failure-free window.
        self.skip_zero_failure = True
        #: Feed previous attempts + their validation outcomes to the
        #: controller. History justifies WAIT only under the
        #: three-condition rule in the system prompt (materially similar
        #: defect + materially similar edits + no grown support); without
        #: any attempt memory the controller cannot see that an
        #: intervention was already tried and re-triggers redundantly
        #: (measured: 7 attempts vs 5 for a fixed-K baseline on the same
        #: 60-task stream).
        self.attempt_memory = bool(attempt_memory)
        self._chat_fn = chat_fn

    # -- LLM access ---------------------------------------------------------

    @property
    def chat_fn(self):
        if self._chat_fn is None:
            from skillopt.model import chat_optimizer

            self._chat_fn = chat_optimizer
        return self._chat_fn

    # -- State --------------------------------------------------------------

    def initial_state(self) -> dict:
        return {
            "hypotheses": [],
            "tasks_since_last_attempt": 0,
            "failures_since_last_attempt": 0,
            "consecutive_rejects": 0,
            "unresolved": "",
        }

    def reset_state(
        self,
        outcome: str = "accepted",
        trigger_state: dict | None = None,
    ) -> dict:
        """Return the evidence state to use after an evolution attempt.

        On ``accepted`` the skill changed, so beliefs about it may no longer
        hold: hard reset. On ``rejected`` / ``skipped`` the skill is
        unchanged but the supporting observations were consumed: hypotheses
        carry over as ``weakened`` — counts move to ``prior_*`` magnitude
        memory (for growth-rate comparison), current counts restart at
        zero, consumed case ids are dropped, and ``unresolved`` is kept.
        """
        outcome = str(outcome or "accepted").strip().lower()
        if outcome.startswith("accept") or not isinstance(trigger_state, dict):
            return self.initial_state()
        window = _to_int(trigger_state.get("tasks_since_last_attempt"), 0)
        streak = _to_int(trigger_state.get("consecutive_rejects"), 0) + 1
        carried = []
        for h in trigger_state.get("hypotheses") or []:
            if not isinstance(h, dict) or not str(h.get("defect", "") or "").strip():
                continue
            carried.append({
                "defect": _clip(h.get("defect", ""), 400),
                "support_count": 0,
                "contradiction_count": 0,
                "supporting_cases": [],
                "contradicting_cases": [],
                "status": "weakened",
                "assessment": _clip(h.get("assessment", ""), 400),
                "prior_support": _to_int(h.get("support_count"), 0),
                "prior_window_tasks": window,
            })
        state = {
            "hypotheses": carried,
            "tasks_since_last_attempt": 0,
            "failures_since_last_attempt": 0,
            "consecutive_rejects": streak,
            "unresolved": _clip(trigger_state.get("unresolved", ""), 600),
        }
        if self.max_state_chars > 0:
            while state["hypotheses"]:
                try:
                    text = json.dumps(state, ensure_ascii=False)
                except (TypeError, ValueError):
                    break
                if len(text) <= self.max_state_chars:
                    break
                state["hypotheses"].pop()
        return state

    # -- Prompt construction --------------------------------------------------

    def _render_state(self, evidence_state: dict) -> str:
        state = evidence_state if isinstance(evidence_state, dict) else {}
        has_content = bool(
            state.get("hypotheses")
            or state.get("unresolved")
            or _to_int(state.get("tasks_since_last_attempt"), 0)
        )
        if not state or not has_content:
            return "(none yet — this is the first observation of this cycle)"
        try:
            text = json.dumps(state, ensure_ascii=False, indent=2)
        except (TypeError, ValueError):
            return "(evidence state could not be rendered)"
        if self.max_state_chars > 0 and len(text) > self.max_state_chars:
            hypotheses = state.get("hypotheses")
            if isinstance(hypotheses, list):
                kept = list(hypotheses)
                while kept and len(text) > self.max_state_chars:
                    kept.pop()
                    reduced = dict(state, hypotheses=kept)
                    try:
                        text = json.dumps(reduced, ensure_ascii=False, indent=2)
                    except (TypeError, ValueError):
                        break
            if len(text) > self.max_state_chars:
                text = text[: self.max_state_chars] + "\n…[truncated]"
        return text

    def _build_user_message(
        self,
        *,
        skill: str,
        new_results: list[dict],
        evidence_state: dict,
        epoch_end: bool,
        rollout_dir: str | None,
        context: dict | None,
        window: dict | None = None,
        same_skill_as_last: bool = False,
    ) -> str:
        parts: list[str] = []

        if self.view == "semantic":
            ident = str((context or {}).get("skill_identity") or "").strip()
            if same_skill_as_last:
                parts.append(
                    f"## Current Skill (identity {ident[:8]}) — unchanged since "
                    f"your previous consult; the full text you were shown then "
                    f"is still current."
                )
            else:
                head = "## Current Skill"
                if ident:
                    head += f" (identity {ident[:8]})"
                parts.append(head + "\n" + (skill.strip() or "(empty skill)"))
            parts.append(
                "## Evidence State (from previous observations)\n"
                + self._render_state(evidence_state)
            )
        if window:
            parts.append(
                self._render_window(
                    window, streak=_to_int(evidence_state.get("consecutive_rejects"), 0)
                )
            )

        cards = [
            format_observation_card(
                r,
                rollout_dir,
                max_chars=self.max_observation_chars,
                view=self.view,
            )
            for r in new_results
        ]
        cards = [c for c in cards if c.strip()]
        if cards:
            parts.append(
                f"## New Observations ({len(new_results)} task executions)\n"
                + "\n\n".join(cards)
            )
        else:
            parts.append(
                "## New Observations\n(no new task executions in this consult — "
                "this is an epoch-boundary consult over the evidence accumulated "
                "so far)"
            )

        if self.view == "score" and context:
            buffered = int(context.get("buffer_observations", 0) or 0)
            buffered_tasks = int(context.get("buffer_tasks", 0) or 0)
            parts.append(
                "## Cumulative Window So Far\n"
                f"- observation batches since the last evolution attempt: {buffered}\n"
                f"- task executions since the last evolution attempt: {buffered_tasks}"
            )

        attempts = list((context or {}).get("attempt_history") or [])
        if self.attempt_memory and attempts:
            if self.view == "semantic":
                parts.append(self._render_attempts_semantic(attempts, context))
            else:
                parts.append(self._render_attempts_score(attempts))

        if epoch_end:
            parts.append(
                "Note: the current training epoch's observation stream is now "
                "exhausted (epoch boundary)."
            )

        parts.append(
            "Decide whether the accumulated evidence is now sufficient to "
            "justify invoking the skill optimizer, and maintain the evidence "
            "state. " + _REMINDER
        )
        return "\n\n".join(parts)

    # -- Attempt history rendering -------------------------------------------

    def _render_window(self, window: dict, streak: int = 0) -> str:
        """The whole buffered window, not just the batch that just landed.

        An UPDATE spends a full optimizer attempt on the window, but the
        controller used to judge from the newest batch alone. The lean line
        is the load-bearing part: failures that straddle both directions
        mean the skill contradicts itself, which no additional rule fixes.
        """
        n_tasks = int(window.get("n_tasks") or 0)
        n_fail = int(window.get("n_failures") or 0)
        over = int(window.get("over") or 0)
        under = int(window.get("under") or 0)
        other = int(window.get("other") or 0)
        if not n_tasks:
            return "## Window Summary\n(no buffered evidence yet)"
        rate = float(window.get("fail_rate") or 0.0)
        lean_kind = window_lean(window, self.window_lean_margin)
        if lean_kind == "none":
            lean = "no directional failure evidence"
        elif lean_kind == "straddle":
            lean = (
                f"STRADDLES both directions / {other} undirected — the failures "
                f"call for opposite or unrelated corrections, which usually means "
                f"the skill's own rules contradict each other rather than a rule "
                f"being missing"
            )
        else:
            word = "OVER-specified" if lean_kind == "over" else "UNDER-specified"
            lean = f"leans {word} (the failures share a direction)"
        streak_line = (
            f"- consecutive rejected attempts on this unchanged skill: {streak}"
            f" (an accepted attempt clears this to 0)\n"
            if streak
            else ""
        )
        return (
            "## Window Summary (the window an UPDATE would consume)\n"
            f"- buffered batches: {int(window.get('n_batches') or 0)}\n"
            f"- tasks: {n_tasks} (failures {n_fail}, rate {rate:.2f})\n"
            f"- failure directions: over-specified {over}, "
            f"under-specified {under}, other {other}\n"
            f"{streak_line}"
            f"- {lean}"
        )

    @staticmethod
    def _format_score(value: object) -> str:
        try:
            return f"{float(value):.4f}"
        except (TypeError, ValueError):
            return "?"

    @classmethod
    def _format_attempt_semantic(cls, a: dict, current_identity: str) -> list[str]:
        """Render one attempt as three independent sections.

        Trigger evidence / Optimizer changes / Verifier must stay separate:
        the optimizer never sees the controller's hypotheses, so its edits
        are never "targeted at" the trigger defect, and a rejected candidate
        means the edits never entered the skill.
        """
        validation = str(a.get("validation") or "?")
        base = str(a.get("base_skill") or "").strip()
        if base and current_identity and base == current_identity:
            base_txt = "base skill = current skill"
        elif base:
            base_txt = f"base skill {base[:8]} (superseded)"
        else:
            base_txt = "base skill unknown"
        lines = [
            f"- Attempt {a.get('attempt')} "
            f"(after {a.get('tasks_consumed')} tasks, {base_txt}):"
        ]
        snap = a.get("trigger_state")
        hyps = (
            [h for h in snap.get("hypotheses") or [] if isinstance(h, dict)]
            if isinstance(snap, dict)
            else []
        )
        if hyps:
            window = snap.get("tasks_since_last_attempt")
            over = f" over {window} tasks" if window else ""
            rendered = []
            for h in hyps[:2]:
                defect = " ".join(str(h.get("defect", "")).split())[:160]
                rendered.append(
                    f'"{defect}" '
                    f"(support {h.get('support_count', '?')}, "
                    f"contradiction {h.get('contradiction_count', '?')})"
                )
            lines.append(
                f"  Trigger evidence ({len(hyps)} hypothesis(es){over}): "
                + "; ".join(rendered)
            )
        else:
            legacy = str(a.get("targeted_defect") or "").strip()
            lines.append(
                f"  Trigger evidence: {json.dumps(legacy[:160]) if legacy else 'trigger hypotheses not recorded'}"
            )
        proposed = list(a.get("edits_proposed") or a.get("edits_applied") or [])
        if validation == "accepted":
            tail = "applied — now part of the current skill"
        elif validation == "skipped":
            tail = "no candidate was produced"
        else:
            tail = "candidate rolled back — the edits never entered the skill"
        if proposed:
            edit_str = "; ".join(
                " ".join(str(e).split())[:90] for e in proposed[:4]
            )
            lines.append(f"  Optimizer changes ({tail}): {edit_str}")
        else:
            lines.append(f"  Optimizer changes: {tail}")
        val_b, val_a = a.get("val_before"), a.get("val_after")
        cand = a.get("candidate_score")
        verdict = f"  Verifier: {validation.upper()}"
        if isinstance(cand, (int, float)) and not isinstance(cand, bool):
            try:
                delta = float(cand) - float(val_b or 0.0)
                verdict += (
                    f" — candidate {float(cand):.4f} vs current "
                    f"{float(val_b or 0.0):.4f} (delta {delta:+.4f})"
                )
            except (TypeError, ValueError):
                pass
        verdict += (
            f"; skill score {cls._format_score(val_b)} -> {cls._format_score(val_a)}"
        )
        lines.append(verdict)
        return lines

    def _render_attempts_semantic(
        self, attempts: list[dict], context: dict | None
    ) -> str:
        ident = str((context or {}).get("skill_identity") or "").strip()
        lines = ["## Previous Evolution Attempts (this run)"]
        for a in attempts[-5:]:
            lines.extend(self._format_attempt_semantic(a, ident))
        lines.append(
            "The optimizer never saw the trigger hypotheses above — it edited "
            "from the raw failure buffer — so judge overlap by comparing its "
            "edits to the mechanism you now see. A previous attempt justifies "
            "WAIT only when the defect and the edits are both materially "
            "similar AND support has not grown since (no new failure "
            "mechanism, and a failure rate that has not risen beyond the "
            "window's sampling noise — three failures in ten tasks is noise, "
            "not growth). A rejected candidate does not invalidate the "
            "trigger hypothesis, but a *series* of rejected attempts against "
            "the same wording does mean the diagnosis is wrong: reformulate "
            "the defect or WAIT, do not re-trigger with a fresh count."
        )
        return "\n".join(lines)

    @staticmethod
    def _render_attempts_score(attempts: list[dict]) -> str:
        """Numeric-only attempt lines — keeps the score-view ablation free of
        semantic content (no defect wording, no edit targets)."""
        lines = ["## Previous Evolution Attempts (this run)"]
        for a in attempts[-5:]:
            n_edits = len(a.get("edits_proposed") or a.get("edits_applied") or [])
            lines.append(
                f"- attempt {a.get('attempt')} after {a.get('tasks_consumed')} tasks: "
                f"validation {a.get('validation')} "
                f"(val {a.get('val_before')} -> {a.get('val_after')}, "
                f"candidate {a.get('candidate_score')}, {n_edits} proposed edits)"
            )
        lines.append(
            "Do not re-invoke the optimizer when a prior attempt covered a "
            "similar window with a similar outcome and the current window "
            "has not grown."
        )
        return "\n".join(lines)

    # -- Response parsing -----------------------------------------------------

    @staticmethod
    def _clip_hypothesis(hyp: dict) -> dict:
        if not isinstance(hyp, dict):
            return {}
        # Old-format states used "counter_cases"; accept both spellings.
        contra_src = hyp.get("contradicting_cases")
        if contra_src is None:
            contra_src = hyp.get("counter_cases")
        support_cases = [_clip(c, 80) for c in (hyp.get("supporting_cases") or [])[:8]]
        contra_cases = [_clip(c, 80) for c in (contra_src or [])[:8]]
        support_count = _to_int(hyp.get("support_count"), len(support_cases))
        contra_count = _to_int(hyp.get("contradiction_count"), len(contra_cases))
        status = str(hyp.get("status") or "active").strip().lower()
        if status not in ("active", "weakened", "rejected"):
            status = "active"
        clean = {
            "defect": _clip(hyp.get("defect", ""), 400),
            "support_count": min(support_count, 999),
            "contradiction_count": min(contra_count, 999),
            "supporting_cases": support_cases,
            "contradicting_cases": contra_cases,
            "status": status,
            "assessment": _clip(hyp.get("assessment", ""), 400),
        }
        prior_support = _to_int(hyp.get("prior_support"), -1)
        if prior_support >= 0:
            clean["prior_support"] = min(prior_support, 999)
        prior_window = _to_int(hyp.get("prior_window_tasks"), -1)
        if prior_window >= 0:
            clean["prior_window_tasks"] = min(prior_window, 99999)
        return clean

    def _normalize_state(self, state: object, counters: dict | None = None) -> dict:
        """Sanitize the LLM-returned evidence state into a bounded dict.

        ``counters`` carries the deterministically maintained cycle counts
        (tasks/failures since the last attempt); they override whatever the
        LLM reported, which keeps arithmetic exact across observations.
        """
        counters = counters if isinstance(counters, dict) else {}
        clean = {
            "hypotheses": [],
            "tasks_since_last_attempt": _to_int(
                counters.get("tasks_since_last_attempt"), 0
            ),
            "failures_since_last_attempt": _to_int(
                counters.get("failures_since_last_attempt"), 0
            ),
            # Maintained by reset_state / _advance_counters, never by the
            # LLM: the streak is the escalation input for the window floor,
            # and the seen-identity decides whether the skill text is
            # re-sent.
            "consecutive_rejects": _to_int(
                counters.get("consecutive_rejects"), 0
            ),
            "unresolved": "",
        }
        seen = str(counters.get("skill_seen_identity") or "")
        if seen:
            clean["skill_seen_identity"] = seen
        if not isinstance(state, dict):
            return clean
        hypotheses = state.get("hypotheses")
        if isinstance(hypotheses, list):
            clean["hypotheses"] = [
                h for h in (self._clip_hypothesis(h) for h in hypotheses[:10]) if h
            ]
        clean["unresolved"] = _clip(state.get("unresolved", ""), 600)
        # Hard bound the serialized size by dropping hypotheses from the end.
        if self.max_state_chars > 0:
            while clean["hypotheses"]:
                try:
                    text = json.dumps(clean, ensure_ascii=False)
                except (TypeError, ValueError):
                    break
                if len(text) <= self.max_state_chars:
                    break
                clean["hypotheses"].pop()
        return clean

    def _parse_response(
        self, response: str, counters: dict | None = None
    ) -> tuple[str, dict, str] | None:
        """Parse the controller JSON. Returns (action, state, reason) or None."""
        from skillopt.utils import extract_json

        result = extract_json(response)
        if not isinstance(result, dict):
            return None
        action = _normalize_action(result.get("decision", result.get("action", "")))
        if action not in (WAIT, UPDATE):
            return None
        reason = _clip(result.get("reason", ""), 800)
        return (
            action,
            self._normalize_state(result.get("evidence_state"), counters),
            reason,
        )

    # -- Deterministic gates -------------------------------------------------

    def _window_gate(
        self, streak: int, window: dict
    ) -> str | None:
        """Return a WAIT reason when the window cannot justify a consult.

        Two structural facts decide a consult without any semantic judgement:
        a window with no failures cannot support any hypothesis, and a window
        too small to carry a failure-rate signal produces triggers that are
        indistinguishable from sampling noise. Skipping the LLM for those
        cases is free correctness, not a heuristic.

        The floor escalates with the streak of consecutive rejections on the
        current skill: the first triggers may fire on a small window (V3's
        best candidate came from a 50-task window, and a static 40-task floor
        is what cost V4 that attempt), but a skill that has already rejected
        N candidates must show a proportionally larger window before it may
        spend another attempt. That is the difference between "the optimizer
        has not seen this yet" and "the optimizer has seen this three times
        and disagreed each time".
        """
        if self.skip_zero_failure and window["n_tasks"] and not window["n_failures"]:
            return (
                f"window holds {window['n_tasks']} tasks with no failures — "
                f"no hypothesis can gain support; mechanical WAIT"
            )
        streak = max(0, int(streak or 0))
        floor = self.min_window_tasks + self.floor_step * streak
        if (
            floor > 0
            and 0 < window["n_tasks"] < floor
            and window["fail_rate"] < self.window_floor_fail_rate
        ):
            why = (
                f"after {streak} rejected attempt(s) on this skill"
                if streak
                else "under the base evidence floor"
            )
            return (
                f"window holds only {window['n_tasks']} tasks "
                f"({window['n_failures']} failures, rate "
                f"{window['fail_rate']:.2f}) — below the {floor}-task floor "
                f"({why}) and under the "
                f"{self.window_floor_fail_rate:.0%} failure-rate exception; "
                f"wait for a larger window"
            )
        return None

    # -- The decision -----------------------------------------------------------

    @staticmethod
    def _is_success(result: dict) -> bool:
        return _hard_of(result) >= 1.0

    def _advance_counters(
        self,
        evidence_state: object,
        new_results: list[dict],
        context: dict | None = None,
    ) -> dict:
        """Deterministically advance the cycle-level counters.

        Cross-observation arithmetic is not left to the LLM: it echoes,
        drifts, or invents counts. The returned state is what gets rendered
        into the prompt and what a fallback WAIT returns, so counters move
        forward even when the controller response is unparseable.
        """
        state = (
            dict(evidence_state)
            if isinstance(evidence_state, dict)
            else self.initial_state()
        )
        state["tasks_since_last_attempt"] = _to_int(
            state.get("tasks_since_last_attempt"), 0
        ) + len(new_results or [])
        state["failures_since_last_attempt"] = _to_int(
            state.get("failures_since_last_attempt"), 0
        ) + sum(1 for r in (new_results or []) if not self._is_success(r))
        # Remember which skill text this consult saw, so the next one can
        # confirm "unchanged" instead of re-sending it. Also recorded here
        # (not in the LLM's reply) so it moves forward on a fallback WAIT.
        ident = str((context or {}).get("skill_identity") or "").strip()
        if ident:
            state["skill_seen_identity"] = ident
        return state

    def observe(
        self,
        skill: str,
        new_results: list[dict],
        evidence_state: dict,
        *,
        epoch_end: bool = False,
        rollout_dir: str | None = None,
        context: dict | None = None,
    ) -> EvolutionDecision:
        working = self._advance_counters(evidence_state, new_results, context)
        window = summarize_window(
            (context or {}).get("buffered_batches") or ([new_results] if new_results else [])
        )
        streak = _to_int(working.get("consecutive_rejects"), 0)
        skip_reason = self._window_gate(streak, window)
        if skip_reason is not None:
            return EvolutionDecision(
                action=WAIT,
                state=working,
                reason=skip_reason,
                meta={
                    "policy": self.name,
                    "view": self.view,
                    "deterministic_skip": True,
                    "window": window,
                    "consecutive_rejects": streak,
                    "epoch_end": epoch_end,
                },
            )
        # The skill is unchanged between 95% of consecutive consults
        # (measured on V5: 38 of 41 pairs). Re-sending the full text every
        # time buys nothing — the controller only needs to know it is the
        # same document it already judged — so send it once and confirm
        # thereafter. The identity lives in the persisted state, so a resume
        # re-sends the text rather than assuming.
        ident = str((context or {}).get("skill_identity") or "").strip()
        same_skill_as_last = bool(ident) and ident == str(
            evidence_state.get("skill_seen_identity") or ""
        )
        user = self._build_user_message(
            skill=skill,
            new_results=new_results,
            evidence_state=working,
            epoch_end=epoch_end,
            rollout_dir=rollout_dir,
            context=context,
            window=window,
            same_skill_as_last=same_skill_as_last,
        )
        last_error = ""
        for attempt in range(1 + self.max_parse_retries):
            try:
                response, _usage = self.chat_fn(
                    system=_CONTROLLER_SYSTEM_PROMPT,
                    user=user,
                    max_completion_tokens=self.max_completion_tokens,
                    retries=3,
                    stage="evolution_controller",
                )
            except Exception as exc:  # noqa: BLE001 — never crash training
                last_error = f"{type(exc).__name__}: {exc}"
                continue
            parsed = self._parse_response(response, counters=working)
            if parsed is not None:
                action, state, reason = parsed
                return EvolutionDecision(
                    action=action,
                    state=state,
                    reason=reason,
                    raw={"response": response},
                    meta={
                        "policy": self.name,
                        "view": self.view,
                        "parse_attempts": attempt + 1,
                        "epoch_end": epoch_end,
                    },
                )
            last_error = "unparseable controller response"
        print(
            f"    [evolution-controller] WARNING: {last_error} after "
            f"{1 + self.max_parse_retries} attempt(s) — falling back to WAIT "
            f"with the previous evidence state"
        )
        return EvolutionDecision(
            action=WAIT,
            state=working,
            reason=f"controller fallback ({last_error})",
            meta={
                "policy": self.name,
                "view": self.view,
                "fallback": True,
                "epoch_end": epoch_end,
            },
        )


# ── Mode normalization + factory ─────────────────────────────────────────────

EVOLUTION_MODES = ("fixed", "immediate", "fixed_k", "end", "controller")

_MODE_ALIASES: dict[str, str] = {
    "fixed": "fixed",
    "default": "fixed",
    "none": "fixed",
    "off": "fixed",
    "batch": "fixed",
    "original": "fixed",
    "immediate": "immediate",
    "always": "immediate",
    "every": "immediate",
    "per_observation": "immediate",
    "per_batch": "immediate",
    "sample": "immediate",
    "per_sample": "immediate",
    "fixed_k": "fixed_k",
    "fixedk": "fixed_k",
    "k": "fixed_k",
    "window": "fixed_k",
    "end": "end",
    "epoch": "end",
    "per_epoch": "end",
    "epoch_end": "end",
    "controller": "controller",
    "llm": "controller",
    "llm_evidence": "controller",
    "evidence": "controller",
    "semantic": "controller",
    "evidence_triggered": "controller",
    "ete": "controller",
}


def normalize_evolution_mode(mode: object) -> str:
    raw = str(mode or "fixed").strip().lower()
    normalized = _MODE_ALIASES.get(raw)
    if normalized is None:
        raise ValueError(
            f"evolution.mode must be one of {EVOLUTION_MODES} (or an alias), "
            f"got {mode!r}"
        )
    return normalized


def build_evolution_policy(cfg: dict) -> EvolutionPolicy:
    """Build the :class:`EvolutionPolicy` named by ``evolution.mode``.

    ``evolution.mode=fixed`` keeps the original SkillOpt schedule and runs
    the untouched legacy loop, so no policy is built for it — calling this
    factory with ``fixed`` is a configuration error.
    """
    mode = normalize_evolution_mode(cfg.get("evolution_mode", "controller"))
    if mode == "fixed":
        raise ValueError(
            "evolution.mode=fixed uses the original SkillOpt schedule and "
            "builds no evolution policy; pass a non-fixed mode"
        )
    if mode == "immediate":
        return ImmediatePolicy()
    if mode == "fixed_k":
        return FixedKPolicy(k=int(cfg.get("evolution_fixed_k", 1)))
    if mode == "end":
        return EndPolicy()
    # controller (ours)
    return LLMEvidencePolicy(
        view=str(cfg.get("evolution_controller_view", "semantic") or "semantic"),
        attempt_memory=cfg.get("evolution_controller_attempt_memory", True) is not False,
        min_window_tasks=int(
            cfg.get("evolution_controller_min_window_tasks", 10) or 0
        ),
        floor_step=int(cfg.get("evolution_controller_floor_step", 30) or 0),
        max_observation_chars=int(
            cfg.get("evolution_controller_max_observation_chars", 1200) or 1200
        ),
        max_state_chars=int(
            cfg.get("evolution_controller_max_state_chars", 4000) or 4000
        ),
        max_parse_retries=int(
            cfg.get("evolution_controller_max_parse_retries", 2) or 2
        ),
        max_completion_tokens=int(
            cfg.get("evolution_controller_max_completion_tokens", 4096) or 4096
        ),
    )


# ── Small shared helpers used by the trainer ─────────────────────────────────

_TASK_ID_SAFE = re.compile(r"[^A-Za-z0-9_.-]+")


def safe_task_id(value: object) -> str:
    return _TASK_ID_SAFE.sub("_", str(value)).strip("_")[:80] or "task"
