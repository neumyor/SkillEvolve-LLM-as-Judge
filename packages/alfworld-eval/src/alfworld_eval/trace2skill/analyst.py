"""Verified Trace2Skill analysts for ALFWorld.

The error analyst is deliberately tool-driven.  It cannot mark an episode
fixed by assertion: a candidate must be replayed by ``verify_episode`` and
produce the verifier's exact PASS contract.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from alfworld_eval.analysis.verify_episode import DEFAULT_CONFIG

from .llm import ChatResponse, OpenAICompatibleClient
from .parser import parse_analysis_report, parse_success_report


@dataclass
class AnalysisResult:
    episode_id: str
    report: str
    items: list[dict[str, Any]]
    verified: bool
    turns: int
    usage: dict[str, int] = field(default_factory=dict)
    error: str = ""


def _inside(workspace: Path, requested: str) -> Path:
    requested_path = Path(requested)
    path = (
        (workspace / requested_path).resolve()
        if not requested_path.is_absolute()
        else requested_path.resolve()
    )
    try:
        path.relative_to(workspace.resolve())
    except ValueError as exc:
        raise ValueError(f"path is outside analysis workspace: {requested}") from exc
    return path


def _tool_schemas() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "list_files",
                "description": "List files inside the analysis workspace.",
                "parameters": {
                    "type": "object",
                    "properties": {"directory": {"type": "string"}},
                    "required": [],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read a UTF-8 text file inside the analysis workspace.",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "write_json",
                "description": "Write a JSON object to a file inside the analysis workspace.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "data": {"type": "object"},
                    },
                    "required": ["path", "data"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "evaluate_output",
                "description": "Replay a candidate action sequence in the real ALFWorld game.",
                "parameters": {
                    "type": "object",
                    "properties": {"output_file": {"type": "string"}},
                    "required": ["output_file"],
                },
            },
        },
    ]


def _call_tool(
    workspace: Path,
    name: str,
    arguments: dict[str, Any],
    config: str,
    *,
    verifier: str = "replay",
    verifier_env: dict[str, str] | None = None,
) -> str:
    if name == "list_files":
        directory = _inside(workspace, arguments.get("directory", "."))
        if not directory.is_dir():
            return f"[ERROR] Not a directory: {arguments.get('directory', '.')}"
        return "\n".join(
            str(p.relative_to(workspace)) for p in sorted(directory.rglob("*")) if p.is_file()
        ) or "(empty)"
    if name == "read_file":
        path = _inside(workspace, arguments["path"])
        if not path.is_file():
            return f"[ERROR] File does not exist: {arguments['path']}"
        return path.read_text(encoding="utf-8", errors="replace")[:120_000]
    if name == "write_json":
        path = _inside(workspace, arguments["path"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(arguments["data"], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return f"Wrote {path.relative_to(workspace)}"
    if name == "evaluate_output":
        path = _inside(workspace, arguments["output_file"])
        if not path.is_file():
            return f"[ERROR] Candidate file does not exist: {arguments['output_file']}"
        if verifier == "judge":
            # The judge reads the goal, the opening observation, the transcript
            # and the proposed actions. It is NOT given the game file, so it
            # cannot replay the sequence -- that removal is the experiment.
            command = [
                sys.executable,
                "-m",
                "alfworld_eval.analysis.judge_episode",
                "--output_file",
                str(path),
                "--config",
                config,
            ]
        else:
            command = [
                sys.executable,
                "-m",
                "alfworld_eval.analysis.verify_episode",
                "--output_file",
                str(path),
                "--config",
                config,
            ]
        # The judge needs the endpoint; the replay verifier drives TextWorld
        # locally and needs nothing. Credentials travel through the environment
        # so they never appear in a command line.
        child_env = dict(os.environ)
        child_env.update(verifier_env or {})
        result = subprocess.run(
            command,
            cwd=str(workspace),
            capture_output=True,
            text=True,
            timeout=180,
            env=child_env,
        )
        return (result.stdout + ("\n[STDERR]\n" + result.stderr if result.stderr else "")).strip()
    return f"[ERROR] Unknown tool: {name}"


def _error_system_prompt(workspace: Path, *, verifier: str = "replay") -> str:
    if verifier == "judge":
        verification_block = """Then write agent_work/output_fixed.json with a minimal corrected action sequence and
call evaluate_output on it. Iterate until the judge accepts the sequence.

The judge reads the task, the opening observation, your transcript and your
proposed actions. It does NOT have the game file and does not replay your
sequence, so a judge PASS means the repair is justified by what the agent could
observe and follows from your diagnosis -- not that the sequence reaches the
goal. Do not adjust the sequence to guess at a grader; make it the repair your
diagnosis implies, and keep the lesson generalizable."""
    else:
        verification_block = """Then write agent_work/output_fixed.json with a minimal corrected action sequence and
call evaluate_output on it. Iterate until the verifier reports exactly PASS."""
    return f"""You are the verified error analyst for one failed ALFWorld episode.
Work only through the provided tools and only inside {workspace}.
Read agent_log.md, agent_work/input.json, agent_work/output.json, and gold.txt.
Diagnose the causal failure from the target agent's observations and actions.
{verification_block}

Constraints (mandatory) — these hold in both modes:
- Do not use hindsight unavailable to the target agent: do not call a path error
  merely because the correct location is revealed to you.
- Do not mention replay, ground truth, or expected answers in the final report.

After a verified PASS, answer using exactly the Markdown format below, with no fences:
# Failure Cause Item 1
## Title
...
## Description
...
## Content
...

# Failure Memory Item 1
## Title
...
## Description
...
## Content
...
Use at most three Failure Memory Items. End with ACTION: TASK_COMPLETE."""


def _error_user_prompt(workspace: Path, log_text: str, *, verifier: str = "replay") -> str:
    instruction = (
        "Use the tools to inspect the structured files, repair output_fixed.json, "
        "and submit it to the judge. The judge will not replay your sequence: it "
        "accepts only a repair that follows from the observations the agent had."
        if verifier == "judge"
        else "Use the tools to inspect the structured files, repair output_fixed.json, "
             "and verify it."
    )
    return f"""Analyze this failed episode. The complete transcript is below.

<agent_log>
{log_text}
</agent_log>

{instruction}
The final answer must contain only the requested Failure Cause and Failure Memory
sections followed by ACTION: TASK_COMPLETE."""


def _success_prompt(log_text: str) -> tuple[str, str]:
    system = """You analyze a successful ALFWorld trajectory. Distill only the lean,
generalizable strategy supported by the observed task, actions, and feedback. Do not
mention hidden answers, replay, or a solution key. Return no more than three items:
# Success Memory Item 1
## Title
...
## Description
...
## Content
...
"""
    user = f"""Here is the successful episode transcript:
<agent_log>
{log_text}
</agent_log>
Produce the required Success Memory Items only."""
    return system, user


def _assistant_message(response: ChatResponse) -> dict[str, Any]:
    message: dict[str, Any] = {"role": "assistant", "content": response.content}
    if response.tool_calls:
        message["tool_calls"] = response.tool_calls
    return message


def run_error_analysis(
    workspace: str | Path,
    client: OpenAICompatibleClient,
    *,
    config: str = "",
    max_turns: int = 20,
    verifier: str = "replay",
    verifier_env: dict[str, str] | None = None,
) -> AnalysisResult:
    root = Path(workspace).resolve()
    log_path = root / "agent_log.md"
    log_text = log_path.read_text(encoding="utf-8", errors="replace") if log_path.is_file() else ""
    config_path = config or str(DEFAULT_CONFIG)
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": _error_system_prompt(root, verifier=verifier)},
        {"role": "user", "content": _error_user_prompt(root, log_text, verifier=verifier)},
    ]
    final = ""
    usage: dict[str, int] = {}
    error = ""
    # Counted so an unverified episode is diagnosable: "never invoked the
    # verifier" and "invoked it 12 times and it never passed" are different
    # failures with different fixes.
    verifier_calls = 0
    turns_used = 0
    for _turn in range(1, max_turns + 1):
        turns_used = _turn
        response = client.complete(messages, tools=_tool_schemas())
        final = response.content or final
        usage = _sum_usage(usage, response.usage)
        if not response.tool_calls:
            break
        messages.append(_assistant_message(response))
        for call in response.tool_calls:
            function = call.get("function") or {}
            name = function.get("name", "")
            try:
                raw_arguments = function.get("arguments") or {}
                arguments = (
                    json.loads(raw_arguments)
                    if isinstance(raw_arguments, str)
                    else raw_arguments
                )
                result = _call_tool(
                    root, name, arguments, config_path,
                    verifier=verifier, verifier_env=verifier_env,
                )
            except (TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
                result = f"[ERROR] {exc}"
            if name == "evaluate_output":
                verifier_calls += 1
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.get("id", name),
                    "name": name,
                    "content": result,
                }
            )
            if "Result:          PASS" in result:
                (root / "evaluate_passed.flag").write_text("PASS\n", encoding="utf-8")
    else:
        error = f"max_turns exceeded ({max_turns})"

    items = parse_analysis_report(final)
    verified = (root / "evaluate_passed.flag").is_file()
    if not verified:
        error = error or "analyst did not produce a verified PASS"
    write_transcript(
        root,
        messages,
        outcome={
            "verified": verified,
            "verifier": verifier,
            "verifier_calls": verifier_calls,
            "turns_used": turns_used,
            "max_turns": max_turns,
            "items_parsed": len(items),
            "error": error,
            "final_answer_chars": len(final),
        },
    )
    return AnalysisResult(
        episode_id=root.name,
        report=final,
        items=items,
        verified=verified,
        turns=min(max_turns, len(messages)),
        usage=usage,
        error=error,
    )


def run_success_analysis(
    workspace: str | Path,
    client: OpenAICompatibleClient,
) -> AnalysisResult:
    root = Path(workspace).resolve()
    log_text = (root / "agent_log.md").read_text(encoding="utf-8", errors="replace")
    system, user = _success_prompt(log_text)
    response = client.complete(
        [{"role": "system", "content": system}, {"role": "user", "content": user}]
    )
    return AnalysisResult(
        episode_id=root.name,
        report=response.content,
        items=parse_success_report(response.content),
        verified=True,
        turns=1,
        usage=response.usage,
    )


def _sum_usage(old: dict[str, int], new: dict[str, Any]) -> dict[str, int]:
    result = dict(old)
    for key, value in new.items():
        if isinstance(value, int | float):
            result[key] = result.get(key, 0) + int(value)
    return result


#: Verifier output is what the analyst acts on, and the PASS/FAIL line is at the
#: end, so a large tool result is truncated from the front, not the back.
TRANSCRIPT_TOOL_CHARS = 8000


def write_transcript(root: Path, messages: list[dict[str, Any]], *, outcome: str) -> Path:
    """Persist the analyst's tool-calling conversation next to its workspace.

    Why this is not optional: when an analyst burns its turn budget without a
    verified PASS it contributes zero memory items, and the only trace of that
    was a one-line warning in the run log. Whether it failed because it could
    not repair the sequence, because it never called ``evaluate_output``, or
    because the verifier output was unreadable is not recoverable afterwards --
    so the conversation is written to disk.
    """
    rendered: list[dict[str, Any]] = []
    for message in messages:
        content = message.get("content")
        record = {key: value for key, value in message.items() if key != "content"}
        if isinstance(content, str):
            if len(content) > TRANSCRIPT_TOOL_CHARS:
                dropped = len(content) - TRANSCRIPT_TOOL_CHARS
                content = f"[truncated {dropped} earlier characters]\n" + content[
                    -TRANSCRIPT_TOOL_CHARS:
                ]
            record["content"] = content
        else:
            record["content"] = content
        rendered.append(record)

    path = root / "analyst_transcript.json"
    path.write_text(
        json.dumps(
            {"outcome": outcome, "messages": rendered}, indent=2, ensure_ascii=False
        )
        + "\n",
        encoding="utf-8",
    )
    return path
