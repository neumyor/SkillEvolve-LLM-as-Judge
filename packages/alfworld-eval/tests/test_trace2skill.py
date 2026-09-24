from __future__ import annotations

import json
from pathlib import Path

from alfworld_eval.trace2skill import analyst
from alfworld_eval.trace2skill.analyst import run_error_analysis
from alfworld_eval.trace2skill.consolidate import consolidate_skill
from alfworld_eval.trace2skill.llm import ChatResponse
from alfworld_eval.trace2skill.parser import (
    parse_analysis_report,
    parse_success_report,
)

FAILURE_REPORT = """\
<think>internal reasoning</think>
# Failure Cause Item 1
## Title
Repeated no-op
## Description
The agent repeated an action after feedback showed no effect.
## Content
It did not update its search state after the no-op.

# Failure Memory Item 1
## Title
Recover from no-op
## Description
Change the search target after an action has no effect.
## Content
Record searched locations and do not retry the same ineffective action.
ACTION: TASK_COMPLETE
"""

SUCCESS_REPORT = """\
```markdown
# Success Memory Item 1
## Title
Track sub-goals
## Description
Maintain an explicit ordered task state.
## Content
Finish transformation before delivery.
```
"""


def test_trace2skill_report_parsers_accept_reasoning_and_fences():
    failure_items = parse_analysis_report(FAILURE_REPORT)
    assert [item["type"] for item in failure_items] == [
        "failure_cause",
        "failure_memory",
    ]
    assert failure_items[1]["title"] == "Recover from no-op"

    success_items = parse_success_report(SUCCESS_REPORT)
    assert len(success_items) == 1
    assert success_items[0]["content"] == "Finish transformation before delivery."


def test_fallback_consolidation_excludes_failure_causes(tmp_path: Path):
    base = "# Base Skill\n\n- Use admissible actions.\n"
    records = [
        {
            "instance_id": "ep",
            "items": [
                {
                    "type": "failure_cause",
                    "title": "Specific cause",
                    "description": "Do not copy this diagnosis.",
                    "content": "Episode-specific evidence.",
                },
                {
                    "type": "failure_memory",
                    "title": "General lesson",
                    "description": "Track searched locations.",
                    "content": "Avoid repeating ineffective actions.",
                },
            ],
        }
    ]
    result = consolidate_skill(base, records)
    assert "Track searched locations." in result
    assert "Do not copy this diagnosis." not in result
    assert result.endswith("\n")


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
                                    "data": {
                                        "gamefile": "/tmp/game.tw-pddl",
                                        "actions": ["look"],
                                    },
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
    workspace = tmp_path / "episode"
    (workspace / "agent_work").mkdir(parents=True)
    (workspace / "agent_log.md").write_text("# episode\n")
    (workspace / "agent_work/input.json").write_text("{}")
    (workspace / "agent_work/output.json").write_text("{}")
    (workspace / "agent_work/gold.txt").write_text("/tmp/game.tw-pddl\n")

    def fake_tool(root, name, arguments, config, **_kwargs):
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
