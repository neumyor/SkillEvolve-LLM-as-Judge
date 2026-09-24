#!/usr/bin/env python3
"""Judge a proposed ALFWorld action sequence instead of replaying it.

This is the replacement for ``verify_episode`` when the point of the experiment
is to remove the regression test. ``verify_episode`` replays the candidate
sequence in the real TextWorld game, so its PASS is the environment's own goal
condition: the analyst cannot mark an episode repaired unless the sequence
actually solves it. This module makes no such claim. It shows an agent the task,
the opening observation, the failed transcript and the proposed actions, and
asks whether the repair is justified and whether the lesson generalizes.

The report keeps the same shape the analyst loop greps for
(``Result:          PASS``/``FAIL`` plus a summary), so ``analyst._call_tool``
can swap one verifier for the other without the loop knowing. It states
explicitly that the verdict is not a replay, so nothing downstream can mistake a
judge PASS for a solved episode.

Ground truth handling
---------------------
``team`` opens with the goal, which is public to the agent. The gold answer file
(``gold.txt``) and the game file are **not** read. That is the whole point: the
judge has no way to check the sequence works, so anything it accepts is a
judgement about plausibility, not a measurement.

Usage::

    python -m alfworld_eval.analysis.judge_episode \\
        --output_file agent_work/output_fixed.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

from alfworld_eval.analysis.report import RULE, THIN, header
from alfworld_eval.analysis.verify_episode import DEFAULT_CONFIG, extract_goal

#: Locates the judge's verdict line.
_VERDICT_RE = re.compile(r'"verdict"\s*:\s*"(PASS|FAIL|pass|fail)"')
#: Cap on the failed transcript shown to the judge.
MAX_LOG_CHARS = 24000


def load_actions(path: str) -> tuple[list[str], str, str]:
    """Read a candidate action sequence. Returns (actions, error).

    Accepts the same shapes as ``verify_episode.load_candidate`` so the analyst
    writes one file format for both verifiers.
    """
    p = Path(path)
    if not p.is_file():
        return [], f"Candidate file does not exist: {path}"
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [], f"Candidate file is not valid JSON: {exc}"
    if isinstance(data, list):
        actions = data
    elif isinstance(data, dict):
        actions = data.get("actions")
        if actions is None:
            return [], "Candidate JSON has no 'actions' key"
    else:
        return [], "Candidate JSON must be an object or a list"
    if not isinstance(actions, list) or not all(isinstance(a, str) for a in actions):
        return [], "'actions' must be a list of strings"
    return [a.strip() for a in actions], ""


JUDGE_SYSTEM_PROMPT_V1 = """You are judging a proposed repair to a failed agent episode.

You will see: the task the agent was given, the opening observation, the full
transcript of the failed attempt (each action and what the environment said
back), and a proposed replacement action sequence.

You CANNOT run the sequence. Your PASS means "this repair is justified and
follows from the evidence", not "this sequence reaches the goal". Judge only
what the transcript supports:

1. **Diagnosis supported?** The first thing that went wrong in the transcript
   should be visibly wrong from the environment's own feedback (a rejected
   action, a no-op, a repeated location, running out of steps while never
   covering the room). A diagnosis that names a failure the transcript does not
   show is speculation.
2. **Repair follows?** The proposed sequence must differ from the failed one in
   the place the diagnosis points at. Changing unrelated steps, or retrying the
   same action, is not a repair.
3. **Only admissible actions?** Every action must be one the environment offered
   or the transcript shows being accepted. The admissible list is printed in the
   transcript; an invented command would have been rejected in reality.
4. **No hindsight.** A repair that moves the agent to a hidden object's location
   without the agent discovering it is not a fair repair, even if it would work.
   The fix must be reachable from what the agent observed.

Be strict: a repair you would not bet on is a FAIL.

Answer with exactly one JSON object and nothing else:

{"verdict": "PASS" | "FAIL", "reason": "<two or three sentences naming the first wrong step and what the repair changes>"}
"""

JUDGE_SYSTEM_PROMPT_V2 = JUDGE_SYSTEM_PROMPT_V1.replace(
    "Be strict: a repair you would not bet on is a FAIL.",
    "Be strict: a repair you would not bet on is a FAIL. Name the defect "
    "mechanism and one concrete falsifier; unsupported or flat repairs FAIL.",
)
JUDGE_PROMPT_VARIANTS = {"v1": JUDGE_SYSTEM_PROMPT_V1, "v2": JUDGE_SYSTEM_PROMPT_V2}


def register_judge_prompt_variant(name: str, prompt: str, *, replace: bool = False) -> None:
    """Register a named Trace2Skill judge prompt without changing the runner."""
    key = str(name or "").strip().lower()
    if not key or not str(prompt or "").strip():
        raise ValueError("judge prompt variant requires a non-empty name and prompt")
    if key in JUDGE_PROMPT_VARIANTS and not replace:
        raise ValueError(f"judge prompt variant already exists: {key}")
    JUDGE_PROMPT_VARIANTS[key] = str(prompt)


def available_judge_prompt_variants() -> tuple[str, ...]:
    return tuple(sorted(JUDGE_PROMPT_VARIANTS))


def judge_prompt_variant() -> tuple[str, str]:
    variant = os.environ.get("TRACE2SKILL_JUDGE_PROMPT_VARIANT", "v1").strip().lower()
    return variant, JUDGE_PROMPT_VARIANTS.get(variant, JUDGE_SYSTEM_PROMPT_V1)


def _build_prompt(
    *,
    task: str,
    initial_observation: str,
    log_text: str,
    actions: list[str],
) -> str:
    numbered = "\n".join(f"{i + 1:>3}. {a}" for i, a in enumerate(actions))
    return (
        f"## Task\n{task or '(task statement unavailable)'}\n\n"
        f"## Opening Observation\n{initial_observation or '(unavailable)'}\n\n"
        f"## Failed Attempt Transcript\n{log_text[:MAX_LOG_CHARS] or '(unavailable)'}\n\n"
        f"## Proposed Replacement Sequence ({len(actions)} actions)\n{numbered}\n\n"
        "Decide whether this repair should be accepted. Answer with the JSON object "
        "described in your instructions and nothing else."
    )


def _call_judge(prompt: str, *, max_tokens: int, timeout: float) -> tuple[str, str]:
    """One judge call against the configured endpoint. Returns (text, error)."""
    base_url = os.environ.get("TRACE2SKILL_BASE_URL", "").strip()
    model = os.environ.get("TRACE2SKILL_MODEL", "").strip()
    api_key = os.environ.get("TRACE2SKILL_API_KEY", "").strip()
    if not base_url or not model:
        return "", "TRACE2SKILL_BASE_URL / TRACE2SKILL_MODEL are not set"
    _variant, system_prompt = judge_prompt_variant()
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
        "max_tokens": max_tokens,
    }
    request = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.load(response)
    except Exception as exc:  # noqa: BLE001 — the caller degrades, never crashes
        return "", f"{type(exc).__name__}: {exc}"
    try:
        return body["choices"][0]["message"]["content"] or "", ""
    except (KeyError, IndexError, TypeError) as exc:
        return "", f"unexpected response shape: {exc}"


def parse_verdict(text: str) -> tuple[str, str, str]:
    """Return (verdict, reason, error). Verdict is "" when unparseable."""
    text = (text or "").strip()
    if not text:
        return "", "", "empty judge response"
    candidates = re.findall(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL) + [text]
    for candidate in candidates:
        start, end = candidate.find("{"), candidate.rfind("}")
        if start == -1 or end <= start:
            continue
        try:
            payload = json.loads(candidate[start:end + 1])
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        verdict = str(payload.get("verdict", "") or "").strip().upper()
        if verdict in ("PASS", "FAIL"):
            return verdict, str(payload.get("reason", "") or "").strip(), ""
    match = _VERDICT_RE.search(text)
    if match:
        return match.group(1).upper(), "", ""
    return "", "", "judge response carries no verdict"


def build_report(
    verdict: str,
    reason: str,
    error: str,
    *,
    n_actions: int,
    task: str,
    output_file: str,
) -> tuple[bool, str, str]:
    """Render the judge report. Returns (passed, summary, text)."""
    passed = verdict == "PASS"
    if error:
        summary = f"FAIL — judge unavailable ({error}); treated as FAIL."
    elif passed:
        summary = f"PASS — judge accepted the repair: {reason or '(no reason given)'}"
    else:
        summary = f"FAIL — judge rejected the repair: {reason or '(no reason given)'}"

    fields = {
        "Candidate file": output_file,
        "Task": task or "(unavailable)",
        "Verifier": "judge (sequence not replayed)",
    }
    lines = header("ALFWORLD EPISODE JUDGE REPORT", fields, passed, summary)
    lines.append("This verdict comes from a judging agent reading the transcript.")
    lines.append("The game file was not opened and the sequence was not executed,")
    lines.append(f"so nothing here establishes that the {n_actions} proposed action(s)")
    lines.append("actually reach the goal.")
    lines.append("")
    if reason:
        lines.append(f"  Judge reason : {reason}")
    if error:
        lines.append(f"  Judge error  : {error}")
    lines.append(THIN)
    lines.append(RULE)
    return passed, summary, "\n".join(lines)


def _load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output_file", required=True,
                        help="Candidate JSON with an 'actions' list")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG),
                        help="Accepted for CLI parity with verify_episode; unused "
                             "(the judge never builds the game)")
    parser.add_argument("--max_tokens", type=int, default=1024)
    parser.add_argument("--timeout", type=float, default=120.0)
    args = parser.parse_args()

    candidate_path = Path(args.output_file)
    workspace = candidate_path.resolve().parent.parent
    agent_work = workspace / "agent_work"

    def fail(reason: str) -> int:
        passed, _, text = build_report(
            "", "", reason, n_actions=0, task="", output_file=args.output_file,
        )
        print(text)
        return 0 if passed else 1

    actions, actions_error = load_actions(args.output_file)
    if actions_error:
        return fail(actions_error)
    if not actions:
        return fail("Candidate contains an empty action sequence.")

    input_record = _load_json(agent_work / "input.json")
    output_record = _load_json(agent_work / "output.json")
    log_path = workspace / "agent_log.md"
    log_text = log_path.read_text(encoding="utf-8", errors="replace") if log_path.is_file() else ""

    # The task statement is public (it is in the agent's own opening
    # observation); derive it the same way verify_episode does rather than
    # reading anything the agent could not see.
    initial_obs = str(input_record.get("initial_observation") or "")
    task = str(input_record.get("task") or "") or (
        extract_goal(initial_obs) if initial_obs else ""
    )
    if not task and output_record.get("task"):
        task = str(output_record["task"])

    prompt = _build_prompt(
        task=task,
        initial_observation=initial_obs,
        log_text=log_text,
        actions=actions,
    )
    text, call_error = _call_judge(prompt, max_tokens=args.max_tokens, timeout=args.timeout)
    verdict, reason, verdict_error = parse_verdict(text)

    passed, _, report = build_report(
        verdict, reason, call_error or verdict_error,
        n_actions=len(actions), task=task, output_file=args.output_file,
    )
    print(report)
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
