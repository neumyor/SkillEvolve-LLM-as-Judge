"""Unified ALFWorld episode runner.

One interaction loop shared by every method. The action protocol is the
SkillRL/SkillOpt projection: lowercase the response, extract
``<action>...</action>`` and mark the response invalid when the protocol tags
are absent or the action is not admissible. Invalid responses are recorded as
invalid, but a harmless admissible fallback action is sent to the environment
instead of arbitrary truncated text. Success is the environment's ``won``
flag; episodes are cut off at ``max_steps`` (50, matching all three papers).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from alfworld_eval.env import AlfworldTextEnv

from .agent import FINISH_LENGTH, Agent
from .prompts import build_user_prompt, extract_task_description
from .skills import SkillProvider, task_type_from_gamefile

ACTION_RE = re.compile(r"<action>(.*?)</action>", re.DOTALL)
THINK_RE = re.compile(r"<think>(.*?)</think>", re.DOTALL)
CJK_RE = re.compile(r"[一-鿿]")


@dataclass
class EpisodeResult:
    gamefile: str
    task_type: str
    success: bool
    steps: int
    invalid_actions: int
    termination_reason: str
    invalid_requests: int = 0
    uncorrected_invalid_requests: int = 0
    correction_attempts: int = 0
    correction_successes: int = 0
    truncated_responses: int = 0
    usage: dict = field(default_factory=dict)
    trajectory: list[dict] = field(default_factory=list)
    # Not part of RESULT_ROW_KEYS: results.jsonl stays byte-compatible. It is
    # only persisted inside the trajectory JSON, where downstream stages (the
    # FUSE evidence export) need the episode's instruction (initial observation
    # with the task description) without re-opening the environment.
    initial_observation: str = ""


def project_action(model_response: str) -> tuple[str, bool]:
    """Parse the shared protocol, retaining the historical text fallback.

    The runner sanitizes this fallback before sending it to ALFWorld. Keeping
    it here preserves the standalone projection contract used by older tests
    and callers.
    """
    lowered = model_response.lower()
    start = lowered.find("<action>")
    end = lowered.find("</action>")
    if start == -1 or end == -1:
        action = lowered[-30:] if lowered else "look"
        valid = False
    else:
        action = lowered[start + len("<action>"):end].strip()
        valid = True

    if not (model_response.find("<think>") != -1 and model_response.find("</think>") != -1):
        valid = False
    if CJK_RE.search(model_response):
        valid = False
    return action, valid


def safe_admissible_fallback(admissible_commands: tuple[str, ...] | list[str]) -> str:
    """Return a state-preserving fallback without inventing progress.

    Always ``look``, including when the environment does not currently list it:
    ALFWorld treats an unlisted command as a no-op, whereas picking an arbitrary
    *admissible* command could change state and let malformed model output steer
    the trajectory being measured. The argument is kept so callers can pass the
    list they validated against.
    """
    return "look"


def project_and_validate_action(
    model_response: str,
    admissible_commands: tuple[str, ...] | list[str],
) -> tuple[str, bool, bool]:
    """Return ``(action_to_execute, format_valid, requested_admissible)``.

    A correctly formatted but inadmissible action is replaced by a harmless
    fallback, while ``format_valid`` retains the historical protocol metric.
    """
    action, format_valid = project_action(model_response)
    admissible = action in admissible_commands
    if not format_valid or not admissible:
        return safe_admissible_fallback(admissible_commands), format_valid, admissible
    return action, format_valid, True


def diagnose_action(
    model_response: str,
    admissible_commands: tuple[str, ...] | list[str],
    *,
    truncated: bool = False,
) -> dict[str, object]:
    """Explain why a model response cannot be executed.

    The diagnostic is deliberately generated from deterministic checks rather
    than from another model call, so the correction prompt is stable and
    actionable. ``truncated`` reports that the endpoint stopped the completion at
    ``max_tokens``: the response then ends inside its reasoning with no
    ``<action>``, which looks identical to a protocol violation but needs a
    different repair (be brief, not "add the tags").
    """
    action, format_valid = project_action(model_response)
    commands = list(admissible_commands)
    issues: list[str] = []
    lowered = model_response.lower()

    if truncated:
        issues.append(
            "the response was cut off at the completion token limit before any "
            "<action> was emitted"
        )
    if "<think>" not in lowered:
        issues.append("missing opening <think> tag")
    if "</think>" not in lowered:
        issues.append("missing closing </think> tag")
    if "<action>" not in lowered:
        issues.append("missing opening <action> tag")
    if "</action>" not in lowered:
        issues.append("missing closing </action> tag")
    if CJK_RE.search(model_response):
        issues.append("response contains non-English characters")
    if action not in commands:
        issues.append(f"extracted action {action!r} is not in the admissible action list")
    if not issues and not format_valid:
        issues.append("response does not satisfy the action protocol")

    return {
        "valid": bool(format_valid and action in commands),
        "format_valid": format_valid,
        "requested_action": action,
        "requested_admissible": action in commands,
        "truncated": truncated,
        "issues": issues,
        "admissible_actions": commands,
    }


def build_correction_prompt(
    original_prompt: str,
    model_response: str,
    diagnostic: dict[str, object],
) -> str:
    """Append one deterministic repair request to the original context."""
    issues = diagnostic["issues"] or ["response failed validation"]
    admissible = diagnostic["admissible_actions"]
    brevity = (
        "Your previous response ran out of output tokens, so it was cut off "
        "mid-reasoning. Reason in at most one short sentence this time.\n"
        if diagnostic.get("truncated")
        else ""
    )
    return (
        f"{original_prompt}\n\n"
        "VALIDATION FAILED. Correct your previous response once.\n"
        f"Diagnostics: {'; '.join(str(issue) for issue in issues)}.\n"
        f"{brevity}"
        f"Your extracted action was: {diagnostic['requested_action']!r}.\n"
        f"Choose exactly one action from this admissible list: {admissible!r}.\n"
        "Do not explain the correction. Output exactly one line and nothing else:\n"
        "<think>brief reason</think><action>one admissible action</action>\n"
        "Do not output anything before <think> or after </action>."
    )


ZERO_USAGE = {"prompt_tokens": 0, "completion_tokens": 0, "api_calls": 0, "api_errors": 0}

# Columns of results.jsonl, in order. Kept next to result_row()/result_from_row().
RESULT_ROW_KEYS = (
    "gamefile",
    "task_type",
    "success",
    "steps",
    "invalid_actions",
    "invalid_requests",
    "uncorrected_invalid_requests",
    "correction_attempts",
    "correction_successes",
    "truncated_responses",
    "termination_reason",
)


def _usage_snapshot(agent: Agent) -> dict | None:
    usage = getattr(agent, "usage", None)
    return usage.to_dict() if usage is not None else None


def episode_usage(agent: Agent, before: dict | None) -> dict:
    """Usage charged to one episode, not the run total so far.

    The agent outlives the episode, so its accumulator is cumulative. Storing
    ``to_dict()`` per episode made ``summarize()`` sum cumulative totals, which
    grows quadratically with episode count -- a 3-episode 50-step run reported
    300 api calls for 150 real requests, and a full 134-episode run would
    overstate calls by ~67x. Charge each episode its own delta instead.
    """
    if before is None:
        return dict(ZERO_USAGE)
    usage = getattr(agent, "usage", None)
    if usage is None:
        return dict(ZERO_USAGE)
    return usage.delta_since(before)


def run_unified_episode(
    env: AlfworldTextEnv,
    agent: Agent,
    skill_provider: SkillProvider,
    *,
    max_steps: int | None = None,
    history_length: int = 2,
    record_trajectory: bool = False,
) -> EpisodeResult:
    # The episode cut-off is part of the evaluation protocol, so it must have a
    # single source of truth. ALFWorld registers ``max_nb_steps_per_episode``
    # from configs/textworld.yaml; a separately supplied cap silently forks the
    # protocol and the artifacts cannot tell the two runs apart. Default to the
    # environment's budget and refuse an explicit disagreement.
    budget = int(getattr(env, "step_budget", 0) or 0)
    if max_steps is None:
        if budget <= 0:
            raise ValueError(
                "env does not expose step_budget and no max_steps was given; "
                "cannot determine the episode cut-off"
            )
        max_steps = budget
    elif budget > 0 and max_steps != budget:
        raise ValueError(
            f"max_steps={max_steps} disagrees with the environment's "
            f"max_nb_steps_per_episode={budget} (configs/textworld.yaml). The "
            "episode cut-off must come from a single source; align the config "
            "and --max-steps, or omit --max-steps to follow the config."
        )
    usage_before = _usage_snapshot(agent)
    observation = env.reset()
    gamefile = observation.game_file or ""
    task_description = extract_task_description(observation.text)
    skill = skill_provider.view_for(gamefile, observation.text)
    initial_observation = observation.text

    history: list[tuple[str, str]] = []
    invalid_actions = 0
    invalid_requests = 0
    uncorrected_invalid_requests = 0
    correction_attempts = 0
    correction_successes = 0
    truncated_responses = 0
    trajectory: list[dict] = []

    for step in range(1, max_steps + 1):
        prompt = build_user_prompt(
            observation.text,
            observation.admissible_commands,
            skill=skill if skill.prefix or skill.body else None,
            task_description=task_description,
            history=history,
            history_length=history_length,
        )
        response, _usage = agent.respond(prompt)
        initial_truncated = getattr(agent, "last_finish_reason", None) == FINISH_LENGTH
        truncated_responses += int(initial_truncated)

        admissible_before_step = observation.admissible_commands
        first_diagnostic = diagnose_action(
            response, admissible_before_step, truncated=initial_truncated
        )
        first_action = str(first_diagnostic["requested_action"])
        first_format_valid = bool(first_diagnostic["format_valid"])
        first_requested_admissible = bool(first_diagnostic["requested_admissible"])
        first_valid = bool(first_diagnostic["valid"])
        correction_response = ""
        correction_diagnostic: dict[str, object] | None = None
        correction_attempted = False
        # Bound before the branch below: the trajectory record is built on every
        # step, including steps that needed no correction.
        correction_truncated = False

        if not first_valid:
            invalid_requests += 1
            # Preserve the historical metric as a count of invalid model
            # requests, even when the one-shot correction repairs them.
            invalid_actions += 1
            correction_attempted = True
            correction_attempts += 1
            correction_prompt = build_correction_prompt(
                prompt, response, first_diagnostic
            )
            correction_response, _usage = agent.respond(correction_prompt)
            correction_truncated = (
                getattr(agent, "last_finish_reason", None) == FINISH_LENGTH
            )
            truncated_responses += int(correction_truncated)
            correction_diagnostic = diagnose_action(
                correction_response, admissible_before_step, truncated=correction_truncated
            )
            if bool(correction_diagnostic["valid"]):
                correction_successes += 1
                action = str(correction_diagnostic["requested_action"])
                format_valid = bool(correction_diagnostic["format_valid"])
                requested_admissible = bool(correction_diagnostic["requested_admissible"])
            else:
                uncorrected_invalid_requests += 1
                action = safe_admissible_fallback(admissible_before_step)
                format_valid = bool(correction_diagnostic["format_valid"])
                requested_admissible = bool(correction_diagnostic["requested_admissible"])
        else:
            action = first_action
            format_valid = first_format_valid
            requested_admissible = first_requested_admissible

        obs_before_step = observation.text
        result = env.step(action)
        observation = result.observation
        history.append((obs_before_step, action))

        if record_trajectory:
            trajectory.append({
                "step": step,
                "model_response": correction_response or response,
                "initial_model_response": response,
                "correction_response": correction_response,
                "correction_attempted": correction_attempted,
                "correction_succeeded": bool(
                    correction_diagnostic and correction_diagnostic["valid"]
                ),
                "truncated": initial_truncated or correction_truncated,
                "diagnostic": first_diagnostic,
                "correction_diagnostic": correction_diagnostic,
                "action": action,
                "valid": bool(
                    correction_diagnostic["valid"]
                    if correction_diagnostic is not None
                    else first_valid
                ),
                "format_valid": format_valid,
                "admissible": action in admissible_before_step,
                "requested_action": project_action(
                    correction_response or response
                )[0],
                "requested_admissible": requested_admissible,
                "initial_requested_action": first_action,
                "initial_format_valid": first_format_valid,
                "initial_requested_admissible": first_requested_admissible,
                "env_feedback": observation.text,
                "done": result.done,
                "won": result.won,
            })

        if result.done:
            return EpisodeResult(
                gamefile=gamefile,
                task_type=task_type_from_gamefile(gamefile),
                success=bool(result.won),
                steps=step,
                invalid_actions=invalid_actions,
                termination_reason="success" if result.won else "environment_done",
                invalid_requests=invalid_requests,
                uncorrected_invalid_requests=uncorrected_invalid_requests,
                correction_attempts=correction_attempts,
                correction_successes=correction_successes,
                truncated_responses=truncated_responses,
                usage=episode_usage(agent, usage_before),
                trajectory=trajectory,
                initial_observation=initial_observation,
            )

    return EpisodeResult(
        gamefile=gamefile,
        task_type=task_type_from_gamefile(gamefile),
        success=False,
        steps=max_steps,
        invalid_actions=invalid_actions,
        termination_reason="step_limit",
        invalid_requests=invalid_requests,
        uncorrected_invalid_requests=uncorrected_invalid_requests,
        correction_attempts=correction_attempts,
        correction_successes=correction_successes,
        truncated_responses=truncated_responses,
        usage=episode_usage(agent, usage_before),
        trajectory=trajectory,
        initial_observation=initial_observation,
    )


def summarize(results: list[EpisodeResult]) -> dict:
    n = len(results)
    by_type: dict[str, dict] = {}
    for r in results:
        bucket = by_type.setdefault(
            r.task_type,
            {"count": 0, "successes": 0, "steps_sum": 0},
        )
        bucket["count"] += 1
        bucket["successes"] += int(r.success)
        bucket["steps_sum"] += r.steps

    task_breakdown = {
        task: {
            "count": b["count"],
            "success_rate": round(b["successes"] / b["count"], 4) if b["count"] else 0.0,
            "avg_steps": round(b["steps_sum"] / b["count"], 2) if b["count"] else 0.0,
        }
        for task, b in sorted(by_type.items())
    }
    total_usage = {
        key: sum(r.usage.get(key, 0) for r in results)
        for key in ("prompt_tokens", "completion_tokens", "api_calls", "api_errors")
    }
    total_corrections = {
        "invalid_requests": sum(r.invalid_requests for r in results),
        "uncorrected_invalid_requests": sum(
            r.uncorrected_invalid_requests for r in results
        ),
        "correction_attempts": sum(r.correction_attempts for r in results),
        "correction_successes": sum(r.correction_successes for r in results),
        "truncated_responses": sum(r.truncated_responses for r in results),
    }
    return {
        "n_episodes": n,
        "success_rate": round(sum(r.success for r in results) / n, 4) if n else 0.0,
        "avg_steps": round(sum(r.steps for r in results) / n, 2) if n else 0.0,
        "invalid_action_rate": round(
            sum(r.invalid_actions for r in results)
            / max(sum(r.steps for r in results), 1),
            4,
        ),
        "invalid_request_rate": round(
            sum(r.invalid_requests for r in results)
            / max(sum(r.steps for r in results), 1),
            4,
        ),
        "uncorrected_invalid_request_rate": round(
            sum(r.uncorrected_invalid_requests for r in results)
            / max(sum(r.steps for r in results), 1),
            4,
        ),
        "corrections": total_corrections,
        "termination": {
            reason: sum(1 for r in results if r.termination_reason == reason)
            for reason in ("success", "environment_done", "step_limit")
        },
        "per_task_type": task_breakdown,
        "usage": total_usage,
    }


def episode_id(gamefile: str, index: int = 0) -> str:
    """Stable, collision-free identifier for an episode.

    ALFWorld game files live at ``<task_dir>/<trial_dir>/game.tw-pddl``. The
    trial directory is timestamped but not guaranteed unique across task
    directories, so both components are used.
    """
    path = Path(gamefile)
    trial = path.parent.name
    task = path.parent.parent.name
    if not trial:
        return f"episode_{index:04d}"
    return f"{task}__{trial}" if task else trial


def result_row(result: EpisodeResult) -> dict:
    """Serialize one episode to its ``results.jsonl`` row.

    Single source of truth for the row schema: the per-episode checkpoint, the
    final save, and merge_shards all write it, while resume and merge read it
    back. Three hand-copied dict literals previously duplicated this schema, so
    any field added to only one of them would silently disappear from the
    workflow that used another.
    """
    row = {key: getattr(result, key) for key in RESULT_ROW_KEYS}
    row["usage"] = dict(result.usage)
    return row


def result_from_row(row: dict) -> EpisodeResult:
    """Rebuild an EpisodeResult from a ``results.jsonl`` row.

    Shared by the resume path and merge_shards so a resumed or merged run
    reports the same totals as an uninterrupted one. Rows written before
    ``usage`` was persisted simply contribute zero usage.
    """
    return EpisodeResult(
        gamefile=str(row.get("gamefile", "")),
        task_type=str(row.get("task_type", "other")),
        success=bool(row.get("success", False)),
        steps=int(row.get("steps", 0)),
        invalid_actions=int(row.get("invalid_actions", 0)),
        invalid_requests=int(row.get("invalid_requests", 0)),
        uncorrected_invalid_requests=int(row.get("uncorrected_invalid_requests", 0)),
        correction_attempts=int(row.get("correction_attempts", 0)),
        correction_successes=int(row.get("correction_successes", 0)),
        truncated_responses=int(row.get("truncated_responses", 0)),
        termination_reason=str(row.get("termination_reason", "")),
        usage=dict(row.get("usage") or {}),
    )


def save_results(
    out_dir: str | Path,
    results: list[EpisodeResult],
    summary: dict,
    meta: dict,
) -> None:
    out = Path(out_dir)
    (out / "predictions").mkdir(parents=True, exist_ok=True)
    with (out / "results.jsonl").open("w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(result_row(r), ensure_ascii=False) + "\n")
    with (out / "summary.json").open("w", encoding="utf-8") as f:
        json.dump({**meta, "summary": summary}, f, indent=2, ensure_ascii=False)
    if any(r.trajectory for r in results):
        traj_dir = out / "trajectories"
        traj_dir.mkdir(exist_ok=True)
        for i, r in enumerate(results):
            if not r.trajectory:
                continue
            with (traj_dir / f"{episode_id(r.gamefile, i)}.json").open("w", encoding="utf-8") as f:
                # Carry the episode metadata inside the file. A bare step list
                # can only be joined back to results.jsonl by filename, and the
                # trial directory alone is not guaranteed unique across task
                # directories.
                json.dump({
                    "gamefile": r.gamefile,
                    "task_type": r.task_type,
                    "success": r.success,
                    "steps": r.steps,
                    "invalid_actions": r.invalid_actions,
                    "invalid_requests": r.invalid_requests,
                    "uncorrected_invalid_requests": r.uncorrected_invalid_requests,
                    "correction_attempts": r.correction_attempts,
                    "correction_successes": r.correction_successes,
                    "termination_reason": r.termination_reason,
                    # The episode's instruction for downstream evidence export;
                    # absent in files written before this field existed.
                    "initial_observation": r.initial_observation,
                    "trajectory": r.trajectory,
                }, f, ensure_ascii=False, indent=2)
