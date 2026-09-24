"""Tool-loop LLM sessions for the FUSE adaptation.

The original FUSE runs its diagnosis/evolution/tagging/clustering/authoring
sessions as native OpenClaw sessions inside Harbor Docker/E2B sandboxes. That
runtime does not exist in this repository; what does exist is the Trace2Skill
analyst pattern (``trace2skill/analyst.py``): an OpenAI-compatible client, a
small tool surface (list_files / read_file / write_file), and a workspace the
tools cannot escape. This module generalizes that pattern into the session
engine every FUSE stage shares.

Faithfulness notes (what is preserved from FUSE):

* the completion contract -- the session must *write* its result file with the
  write tool; a final assistant reply is not a delivery mechanism;
* the host parses only the minimal protocol surface (first line of the
  diagnosis, the tags JSON, ...), never the session transcript;
* every session leaves an audit record (turns, tool calls, token usage) and a
  full transcript, replacing FUSE's exported native openclaw-state sessions;
* evidence is read-only: write_file only accepts paths under the session's
  ``result/`` directory.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from alfworld_eval.trace2skill.llm import ChatResponse, OpenAICompatibleClient

SYSTEM_PROMPT = """You are a focused analysis agent working inside a read-only evidence workspace.
You operate only through the provided tools: list_files, read_file and write_file.
Read the evidence files carefully before drawing conclusions. You never invent
facts that are not in the workspace. When your analysis is complete, you must
deliver it by writing the required result file with the write_file tool."""

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files inside the evidence workspace, recursively.",
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
            "description": "Read a UTF-8 text file inside the evidence workspace.",
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
            "name": "write_file",
            "description": (
                "Write a UTF-8 text file inside the session result directory. "
                "This is the only way to deliver your result."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
]


def _inside(root: Path, requested: str) -> Path:
    """Resolve ``requested`` under ``root`` and refuse escapes."""
    path = Path(requested)
    resolved = (root / path).resolve() if not path.is_absolute() else path.resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(
            f"path is outside the workspace: {requested}"
        ) from exc
    return resolved


def _transcript_clip(text: str, head: int = 1000, tail: int = 500) -> str:
    """Keep a tool result readable in the transcript without dropping its end.

    File reads are clipped at ``max_read_bytes`` mid-session; clipping the
    transcript again from the front would hide exactly the marker that says
    the read was truncated, so long entries keep head *and* tail.
    """
    if len(text) <= head + tail + 50:
        return text
    return f"{text[:head]}\n... [transcript clipped {len(text) - head - tail} chars] ...\n{text[-tail:]}"


@dataclass
class SessionOutcome:
    completed: bool
    result_path: Path | None
    result_text: str = ""
    turns: int = 0
    tool_calls: int = 0
    usage: dict = field(default_factory=dict)
    error: str = ""
    transcript_path: Path | None = None
    seconds: float = 0.0

    def audit(self) -> dict:
        return {
            "completed": self.completed,
            "result_path": str(self.result_path) if self.result_path else "",
            "turns": self.turns,
            "tool_calls": self.tool_calls,
            "usage": self.usage,
            "error": self.error,
            "seconds": round(self.seconds, 1),
        }


class SessionRunner:
    """One tool-loop session against a read-only evidence workspace.

    ``result_relpath`` is the file (relative to the workspace) the session must
    write for its result, e.g. ``result/diagnosis.md``. Writes are only accepted
    inside the result directory, so evidence stays immutable.
    """

    def __init__(
        self,
        client: OpenAICompatibleClient,
        workspace: str | Path,
        result_relpath: str,
        *,
        session_dir: str | Path | None = None,
        max_read_bytes: int = 250_000,
    ):
        self.client = client
        self.workspace = Path(workspace).resolve()
        if not self.workspace.is_dir():
            raise FileNotFoundError(f"evidence workspace not found: {self.workspace}")
        self.result_relpath = str(result_relpath).lstrip("/")
        self.result_dir = (self.workspace / "result").resolve()
        self.result_path = self.workspace / self.result_relpath
        self.session_dir = (
            Path(session_dir).resolve() if session_dir
            else self.workspace.parent / "session"
        )
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.max_read_bytes = max_read_bytes

    # -- tool implementations ----------------------------------------------

    def _list_files(self, arguments: dict) -> str:
        directory = _inside(self.workspace, str(arguments.get("directory") or "."))
        if not directory.is_dir():
            return f"[ERROR] not a directory: {arguments.get('directory')}"
        entries = [
            str(p.relative_to(self.workspace))
            for p in sorted(directory.rglob("*"))
            if p.is_file()
        ]
        return "\n".join(entries) if entries else "(empty)"

    def _read_file(self, arguments: dict) -> str:
        path = _inside(self.workspace, str(arguments.get("path", "")))
        if not path.is_file():
            return f"[ERROR] no such file: {arguments.get('path')}"
        text = path.read_text(encoding="utf-8", errors="replace")
        if len(text) > self.max_read_bytes:
            text = text[: self.max_read_bytes] + f"\n... [truncated at {self.max_read_bytes} chars]"
        return text

    def _write_file(self, arguments: dict) -> str:
        path = _inside(self.workspace, str(arguments.get("path", "")))
        try:
            # Writes are restricted to the result directory: evidence is read-only.
            path.relative_to(self.result_dir)
        except ValueError:
            return (
                f"[ERROR] writes are only allowed under 'result/' "
                f"(requested {arguments.get('path')!r})"
            )
        content = str(arguments.get("content", ""))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"Wrote {len(content)} chars to {self.result_relpath_for(path)}"

    def result_relpath_for(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.workspace))
        except ValueError:
            return str(path)

    def _call_tool(self, name: str, arguments: dict) -> str:
        if name == "list_files":
            return self._list_files(arguments)
        if name == "read_file":
            return self._read_file(arguments)
        if name == "write_file":
            return self._write_file(arguments)
        return f"[ERROR] unknown tool: {name}"

    # -- session loop -------------------------------------------------------

    def run(
        self,
        user_prompt: str,
        *,
        max_turns: int = 30,
    ) -> SessionOutcome:
        """Run the tool loop until the model stops calling tools.

        The session is complete only if the required result file exists at the
        end *and* the loop terminated normally (the FUSE completion contract:
        the write tool is the delivery mechanism, and a session cut at
        ``max_turns`` is not a delivery).
        """
        started = time.time()
        transcript: list[dict[str, Any]] = []
        usage_total: dict[str, int] = {}
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        turns = 0
        tool_calls = 0
        error = ""
        try:
            while turns < max_turns:
                turns += 1
                response: ChatResponse = self.client.complete(
                    messages, tools=TOOL_SCHEMAS
                )
                for key in ("prompt_tokens", "completion_tokens"):
                    usage_total[key] = usage_total.get(key, 0) + int(
                        (response.usage or {}).get(key, 0) or 0
                    )
                usage_total["api_calls"] = usage_total.get("api_calls", 0) + 1
                if not response.tool_calls:
                    messages.append({
                        "role": "assistant",
                        "content": response.content or "(no content)",
                    })
                    transcript.append({"role": "assistant", "content": response.content})
                    break
                assistant_message: dict[str, Any] = {
                    "role": "assistant",
                    "content": response.content or "",
                }
                if response.tool_calls:
                    assistant_message["tool_calls"] = response.tool_calls
                messages.append(assistant_message)
                transcript.append({"role": "assistant", "tool_calls": response.tool_calls,
                                   "content": response.content})
                for call in response.tool_calls:
                    function = call.get("function") or {}
                    name = str(function.get("name", ""))
                    try:
                        arguments = json.loads(function.get("arguments") or "{}")
                        if not isinstance(arguments, dict):
                            raise ValueError("tool arguments must be a JSON object")
                    except (json.JSONDecodeError, ValueError) as exc:
                        arguments = {}
                        result_text = f"[ERROR] invalid tool arguments: {exc}"
                    else:
                        tool_calls += 1
                        # A tool error (bad path, escape attempt, missing file)
                        # is feedback for the model, not a reason to abort the
                        # session -- the analyst loop treats it the same way.
                        try:
                            result_text = self._call_tool(name, arguments)
                        except Exception as exc:  # noqa: BLE001
                            result_text = f"[ERROR] {type(exc).__name__}: {exc}"
                    messages.append({
                        "role": "tool",
                        "tool_call_id": str(call.get("id", name)),
                        "content": result_text,
                    })
                    transcript.append({
                        "role": "tool",
                        "tool_call_id": str(call.get("id", name)),
                        "name": name,
                        "content": _transcript_clip(result_text),
                    })
            else:
                error = f"session exceeded max_turns={max_turns}"
        except Exception as exc:  # noqa: BLE001 - audit everything, re-raise nothing
            error = f"{type(exc).__name__}: {exc}"

        completed = False
        result_text = ""
        if self.result_path.is_file():
            result_text = self.result_path.read_text(encoding="utf-8")
            # A session that exhausted max_turns may have written a partial or
            # unreviewed result; it is not a delivery. Retry semantics are the
            # caller's (one retry with error feedback, FUSE-style).
            completed = not error
        elif not error:
            error = "session ended without writing the result file"

        transcript_path = self.session_dir / "transcript.jsonl"
        with transcript_path.open("w", encoding="utf-8") as f:
            for entry in transcript:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        outcome = SessionOutcome(
            completed=completed,
            result_path=self.result_path if completed else None,
            result_text=result_text,
            turns=turns,
            tool_calls=tool_calls,
            usage=usage_total,
            error=error,
            transcript_path=transcript_path,
            seconds=time.time() - started,
        )
        (self.session_dir / "audit.json").write_text(
            json.dumps(outcome.audit(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return outcome


def build_client(
    *,
    base_url: str,
    model: str,
    api_key: str = "",
    max_tokens: int = 8192,
    temperature: float = 0.0,
    timeout: float = 600.0,
) -> OpenAICompatibleClient:
    """Session client with authoring-sized completion budgets."""
    return OpenAICompatibleClient(
        base_url=base_url,
        model=model,
        api_key=api_key,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
    )
