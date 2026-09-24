"""Offline tests for the FUSE session engine (tool loop, no network)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from alfworld_eval.fuse.sessions import SessionRunner  # noqa: E402


class FakeClient:
    """Scripted client: pops one response per complete() call."""

    def __init__(self, responses: list[Any]):
        self.responses = list(responses)

    def complete(self, messages, tools=None, **kwargs):  # noqa: ANN001
        from alfworld_eval.trace2skill.llm import ChatResponse
        if not self.responses:
            raise AssertionError("FakeClient ran out of scripted responses")
        item = self.responses.pop(0)
        if isinstance(item, ChatResponse):
            return item
        return ChatResponse(content=item.get("content", ""),
                            tool_calls=item.get("tool_calls", []),
                            usage={"prompt_tokens": 10, "completion_tokens": 5})


def _tool_call(name: str, arguments: dict, call_id: str = "c1") -> dict:
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(arguments)},
    }


class TestSessionRunner(unittest.TestCase):
    def _workspace(self, tmp: Path) -> Path:
        ws = tmp / "evidence"
        (ws / "current").mkdir(parents=True)
        (ws / "instruction.md").write_text("Your task is to: heat a mug.", encoding="utf-8")
        (ws / "current" / "trajectory.jsonl").write_text(
            json.dumps({"kind": "step", "step": 1, "action": "look"}) + "\n",
            encoding="utf-8",
        )
        return ws

    def test_successful_delivery(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._workspace(Path(tmp))
            client = FakeClient([
                {"tool_calls": [_tool_call("read_file", {"path": "instruction.md"})]},
                {"tool_calls": [_tool_call(
                    "write_file",
                    {"path": "result/diagnosis.md",
                     "content": "Decision: evolve\n# Summary\n"},
                )]},
                {"content": "done"},
            ])
            runner = SessionRunner(client, ws, "result/diagnosis.md",
                                   session_dir=Path(tmp) / "session")
            outcome = runner.run("diagnose this")
            self.assertTrue(outcome.completed)
            self.assertEqual(outcome.result_text, "Decision: evolve\n# Summary\n")
            self.assertEqual(outcome.tool_calls, 2)
            self.assertTrue((Path(tmp) / "session" / "transcript.jsonl").is_file())
            audit = json.loads((Path(tmp) / "session" / "audit.json").read_text())
            self.assertTrue(audit["completed"])

    def test_missing_result_file_is_incomplete(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._workspace(Path(tmp))
            client = FakeClient([
                {"content": "I decided not to write anything."},
            ])
            runner = SessionRunner(client, ws, "result/diagnosis.md",
                                   session_dir=Path(tmp) / "session")
            outcome = runner.run("diagnose this")
            self.assertFalse(outcome.completed)
            self.assertIn("without writing the result file", outcome.error)

    def test_write_outside_result_dir_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._workspace(Path(tmp))
            client = FakeClient([
                {"tool_calls": [_tool_call(
                    "write_file",
                    {"path": "instruction.md", "content": "tampered"},
                )]},
                {"content": "done"},
            ])
            runner = SessionRunner(client, ws, "result/diagnosis.md",
                                   session_dir=Path(tmp) / "session")
            outcome = runner.run("diagnose this")
            # The write was refused, the required file never appeared.
            self.assertFalse(outcome.completed)
            self.assertEqual(
                (ws / "instruction.md").read_text(encoding="utf-8"),
                "Your task is to: heat a mug.",
            )

    def test_read_outside_workspace_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._workspace(Path(tmp))
            secret = Path(tmp) / "secret.txt"
            secret.write_text("private", encoding="utf-8")
            client = FakeClient([
                {"tool_calls": [_tool_call("read_file", {"path": "../secret.txt"})]},
                {"content": "done"},
            ])
            runner = SessionRunner(client, ws, "result/diagnosis.md",
                                   session_dir=Path(tmp) / "session")
            runner.run("diagnose this")
            transcript = (Path(tmp) / "session" / "transcript.jsonl").read_text(
                encoding="utf-8"
            )
            self.assertIn("outside the workspace", transcript)
            self.assertNotIn("private", transcript)

    def test_max_turns_is_incomplete_even_with_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._workspace(Path(tmp))
            responses = [
                {"tool_calls": [_tool_call("list_files", {})]},
                {"tool_calls": [_tool_call(
                    "write_file",
                    {"path": "result/diagnosis.md", "content": "Decision: evolve\n"},
                )]},
            ]
            # Then keep calling tools until max_turns.
            responses += [
                {"tool_calls": [_tool_call("list_files", {}, call_id=f"c{i}")]}
                for i in range(10)
            ]
            client = FakeClient(responses)
            runner = SessionRunner(client, ws, "result/diagnosis.md",
                                   session_dir=Path(tmp) / "session")
            outcome = runner.run("diagnose this", max_turns=5)
            self.assertFalse(outcome.completed)
            self.assertIn("max_turns", outcome.error)

    def test_invalid_tool_arguments_do_not_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._workspace(Path(tmp))
            bad_call = {
                "id": "c1",
                "type": "function",
                "function": {"name": "read_file", "arguments": "{not json"},
            }
            client = FakeClient([
                {"tool_calls": [bad_call]},
                {"tool_calls": [_tool_call(
                    "write_file",
                    {"path": "result/diagnosis.md", "content": "Decision: no_change\n"},
                )]},
                {"content": "done"},
            ])
            runner = SessionRunner(client, ws, "result/diagnosis.md",
                                   session_dir=Path(tmp) / "session")
            outcome = runner.run("diagnose this")
            self.assertTrue(outcome.completed)

    def test_read_truncation(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._workspace(Path(tmp))
            (ws / "big.txt").write_text("x" * 300_000, encoding="utf-8")
            client = FakeClient([
                {"tool_calls": [_tool_call("read_file", {"path": "big.txt"})]},
                {"tool_calls": [_tool_call(
                    "write_file",
                    {"path": "result/diagnosis.md", "content": "Decision: evolve\n"},
                )]},
                {"content": "done"},
            ])
            runner = SessionRunner(client, ws, "result/diagnosis.md",
                                   session_dir=Path(tmp) / "session")
            outcome = runner.run("diagnose this")
            self.assertTrue(outcome.completed)
            transcript = (Path(tmp) / "session" / "transcript.jsonl").read_text(
                encoding="utf-8"
            )
            self.assertIn("[truncated at", transcript)


if __name__ == "__main__":
    unittest.main()
