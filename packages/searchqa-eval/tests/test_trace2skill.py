"""Offline tests for the Trace2Skill pipeline port (SearchQA).

No LLM, no network, no dataset download — the one subprocess test runs the
local verifier module only.
"""
from __future__ import annotations

import json
from pathlib import Path

from searchqa_eval.trace2skill import analyst
from searchqa_eval.trace2skill.analyst import run_error_analysis, run_success_analysis
from searchqa_eval.trace2skill.consolidate import consolidate_skill
from searchqa_eval.trace2skill.llm import ChatResponse
from searchqa_eval.trace2skill.parser import (
    parse_analysis_report,
    parse_success_report,
)

FAILURE_REPORT = """\
<think>
internal reasoning
</think>
# Failure Cause Item 1
## Title
Trusted a distractor passage
## Description
The agent answered from a passage that did not match the question's terms.
## Content
It fixated on the first entity mentioned instead of adjudicating passages.

# Failure Memory Item 1
## Title
Adjudicate conflicting passages
## Description
Prefer the passage whose wording matches the question's distinctive terms.
## Content
Cross-check names, dates, and titles before committing to an answer.
ACTION: TASK_COMPLETE
"""

SUCCESS_REPORT = """\
```markdown
# Success Memory Item 1
## Title
Ground the span in the evidence
## Description
Copy the exact surface form the strongest passage supports.
## Content
Return the distinctive entity, not a paraphrase of it.
```
"""


def test_trace2skill_report_parsers_accept_reasoning_and_fences():
    failure_items = parse_analysis_report(FAILURE_REPORT)
    assert [item["type"] for item in failure_items] == [
        "failure_cause",
        "failure_memory",
    ]
    assert failure_items[1]["title"] == "Adjudicate conflicting passages"

    success_items = parse_success_report(SUCCESS_REPORT)
    assert len(success_items) == 1
    assert success_items[0]["content"] == "Return the distinctive entity, not a paraphrase of it."


def test_fallback_consolidation_excludes_failure_causes():
    base = "# Base Skill\n\n- Ground answers in the context.\n"
    records = [
        {
            "instance_id": "item",
            "items": [
                {
                    "type": "failure_cause",
                    "title": "Specific cause",
                    "description": "Do not copy this diagnosis.",
                    "content": "Item-specific evidence.",
                },
                {
                    "type": "failure_memory",
                    "title": "General lesson",
                    "description": "Adjudicate conflicting passages.",
                    "content": "Cross-check distinctive terms before answering.",
                },
            ],
        }
    ]
    result = consolidate_skill(base, records)
    assert "Adjudicate conflicting passages." in result
    assert "Do not copy this diagnosis." not in result
    assert result.endswith("\n")


def make_workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "item"
    work = workspace / "agent_work"
    work.mkdir(parents=True)
    (workspace / "agent_log.md").write_text(
        "# SearchQA Episode\n\n## Outcome\n\nOutcome: FAILURE\n- EM: 0.0\n",
        encoding="utf-8",
    )
    (work / "input.json").write_text(
        json.dumps({"id": "item", "question": "q", "context": "[DOC] c"}), encoding="utf-8"
    )
    (work / "output.json").write_text(
        json.dumps({"id": "item", "answer": "wrong"}), encoding="utf-8"
    )
    (work / "gold.json").write_text(
        json.dumps({"id": "item", "question": "q", "answers": ["right"]}), encoding="utf-8"
    )
    return workspace


class FakeAnalystClient:
    def __init__(self):
        self.calls = 0

    def complete(self, messages, **kwargs):
        self.calls += 1
        if self.calls == 1:
            return ChatResponse(
                content="",
                tool_calls=[
                    {
                        "id": "write",
                        "function": {
                            "name": "write_json",
                            "arguments": json.dumps(
                                {
                                    "path": "agent_work/output_fixed.json",
                                    "data": {"id": "item", "answer": "right"},
                                }
                            ),
                        },
                    }
                ],
            )
        if self.calls == 2:
            return ChatResponse(
                content="",
                tool_calls=[
                    {
                        "id": "eval",
                        "function": {
                            "name": "evaluate_output",
                            "arguments": {"output_file": "agent_work/output_fixed.json"},
                        },
                    }
                ],
            )
        return ChatResponse(content=FAILURE_REPORT)


def test_error_analyst_requires_verified_pass(tmp_path: Path, monkeypatch):
    workspace = make_workspace(tmp_path)

    def fake_tool(root, name, arguments, **_kwargs):
        if name == "write_json":
            path = root / arguments["path"]
            path.write_text(json.dumps(arguments["data"]))
            return "Wrote output_fixed.json"
        if name == "evaluate_output":
            return "Result:          PASS\nSummary: fixed"
        raise AssertionError(name)

    monkeypatch.setattr(analyst, "_call_tool", fake_tool)
    result = run_error_analysis(workspace, FakeAnalystClient(), max_turns=5)
    assert result.verified is True
    assert result.items[1]["type"] == "failure_memory"
    assert (workspace / "evaluate_passed.flag").is_file()
    assert (workspace / "analyst_transcript.json").is_file()


def test_error_analyst_without_a_pass_contributes_nothing(tmp_path: Path, monkeypatch):
    workspace = make_workspace(tmp_path)

    def fake_tool(root, name, arguments, **_kwargs):
        if name == "evaluate_output":
            return "Result:          FAIL\nSummary: still wrong"
        raise AssertionError(name)

    monkeypatch.setattr(analyst, "_call_tool", fake_tool)

    class NeverFixedClient:
        def complete(self, messages, **kwargs):
            return ChatResponse(
                content="",
                tool_calls=[
                    {
                        "id": "eval",
                        "function": {
                            "name": "evaluate_output",
                            "arguments": {"output_file": "agent_work/output_fixed.json"},
                        },
                    }
                ],
            )

    result = run_error_analysis(workspace, NeverFixedClient(), max_turns=3)
    assert result.verified is False
    assert result.error  # max_turns exceeded without a PASS
    assert not (workspace / "evaluate_passed.flag").exists()


def test_evaluate_output_tool_runs_the_real_verifier(tmp_path: Path):
    """The tool must shell out to the harness's own scorer, not a private rule."""
    workspace = make_workspace(tmp_path)
    fixed = workspace / "agent_work" / "output_fixed.json"
    fixed.write_text(json.dumps({"id": "item", "answer": "right"}), encoding="utf-8")

    result = analyst._call_tool(
        workspace, "evaluate_output", {"output_file": "agent_work/output_fixed.json"}
    )
    assert "Result:          PASS" in result

    wrong = workspace / "agent_work" / "output_wrong.json"
    wrong.write_text(json.dumps({"id": "item", "answer": "wrong"}), encoding="utf-8")
    result = analyst._call_tool(
        workspace, "evaluate_output", {"output_file": "agent_work/output_wrong.json"}
    )
    assert "Result:          FAIL" in result


class FakeSuccessClient:
    def complete(self, messages, **kwargs):
        return ChatResponse(content=SUCCESS_REPORT)


def test_success_analyst_distills_memory_items(tmp_path: Path):
    workspace = make_workspace(tmp_path)
    result = run_success_analysis(workspace, FakeSuccessClient())
    assert result.verified is True
    assert result.items[0]["type"] == "success_memory"
    assert result.items[0]["title"] == "Ground the span in the evidence"


# --- pipeline wiring (scripts/run_trace2skill.py, no LLM) ------------------

import importlib.util  # noqa: E402

from searchqa_eval.trace2skill.analyst import AnalysisResult  # noqa: E402

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_trace2skill.py"
_spec = importlib.util.spec_from_file_location("run_trace2skill", _SCRIPT)
pipeline = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pipeline)


def _row(item_id: str, em: float, answer: str) -> dict:
    return {
        "id": item_id,
        "question": f"question {item_id}",
        "em": em,
        "f1": em,
        "sub_em": em,
        "hard": int(em),
        "soft": em,
        "predicted_answer": answer,
        "gold_answers": ["right"],
        "response": f"thinking... <answer>{answer}</answer>",
        "agent_ok": True,
    }


def _fake_train_run(tmp_path: Path) -> tuple[Path, Path]:
    """Two failures (one repairable) and one success, as a mini train run."""
    items = [
        {"id": "fail1", "question": "q1", "context": "[DOC] c1", "answers": ["right"]},
        {"id": "fail2", "question": "q2", "context": "[DOC] c2", "answers": ["right"]},
        {"id": "good1", "question": "q3", "context": "[DOC] c3", "answers": ["right"]},
    ]
    items_path = tmp_path / "train_items.json"
    items_path.write_text(json.dumps(items), encoding="utf-8")

    run_dir = tmp_path / "train_run"
    run_dir.mkdir()
    rows = [
        _row("fail1", 0.0, "wrong"),
        _row("fail2", 0.0, "wrong"),
        _row("good1", 1.0, "right"),
    ]
    (run_dir / "results.jsonl").write_text(
        "\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8"
    )
    return items_path, run_dir


def test_pipeline_wiring_routes_verifies_and_consolidates(
    tmp_path: Path, monkeypatch, capsys
):
    items_path, train_run = _fake_train_run(tmp_path)
    work_dir = tmp_path / "work"

    def fake_error_analysis(workspace, client, *, max_turns=20, **_kwargs):
        verified = workspace.name == "fail1"  # only fail1 gets a verified PASS
        if verified:
            (workspace / "evaluate_passed.flag").write_text("PASS\n", encoding="utf-8")
        return AnalysisResult(
            item_id=workspace.name,
            report=FAILURE_REPORT,
            items=parse_analysis_report(FAILURE_REPORT),
            verified=verified,
            turns=3,
            error="" if verified else "analyst did not produce a verified PASS",
        )

    def fake_success_analysis(workspace, client):
        return AnalysisResult(
            item_id=workspace.name,
            report=SUCCESS_REPORT,
            items=parse_success_report(SUCCESS_REPORT),
            verified=True,
            turns=1,
        )

    monkeypatch.setattr(pipeline, "run_error_analysis", fake_error_analysis)
    monkeypatch.setattr(pipeline, "run_success_analysis", fake_success_analysis)
    monkeypatch.setattr(pipeline, "client_from_env", lambda **kwargs: None)

    argv = [
        "run_trace2skill.py",
        "--skip-train",
        "--skip-eval",
        "--base-url", "http://stub",  # client_from_env is monkeypatched; no HTTP
        "--model", "stub",
        "--train-items", str(items_path),
        "--train-run-dir", str(train_run),
        "--base-skill", str(items_path.with_name("seed.md")),
        "--work-dir", str(work_dir),
    ]
    seed = tmp_path / "seed.md"
    seed.write_text("# Seed Skill\n\n- Read the context.\n", encoding="utf-8")
    argv[argv.index("--base-skill") + 1] = str(seed)
    monkeypatch.setattr("sys.argv", argv)

    assert pipeline.main() == 0

    # Routing: failures got error reports, the success got a success report.
    assert (work_dir / "analysis_workspaces/fail1/analysis_report.md").is_file()
    assert (work_dir / "analysis_workspaces/fail2/analysis_report.md").is_file()
    assert (work_dir / "analysis_workspaces/good1/success_analysis.md").is_file()

    # The verification gate: fail2 (no PASS flag) is dropped from the records.
    summary = json.loads((work_dir / "analysis_summary.json").read_text(encoding="utf-8"))
    assert summary["workspaces_analysed"] == 3
    assert summary["workspaces_verified"] == 2
    assert summary["discarded_episodes"] == ["fail2"]
    assert summary["episodes_contributing_memory"] == 2

    # Consolidation (fallback, no LLM): both memories land in the skill.
    skill = (work_dir / "trace2skill_searchqa.md").read_text(encoding="utf-8")
    assert skill.startswith("# Seed Skill")
    assert "Prefer the passage whose wording matches" in skill  # fail1's failure memory
    assert "Copy the exact surface form" in skill  # from good1's success memory
