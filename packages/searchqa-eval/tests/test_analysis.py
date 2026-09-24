"""Offline tests for the Trace2Skill-style analysis port (SearchQA).

No LLM, no network, no dataset download — every fixture is inline.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from searchqa_eval.analysis.dump_artifacts import render_log, setup_analysis_dir
from searchqa_eval.analysis.report import FAIL_LINE, PASS_LINE, header
from searchqa_eval.analysis.verify_answer import build_report, load_candidate, load_gold

GOLD = {"id": "q1", "question": "Who published it?", "answers": ["John Newbery"]}


def write(tmp_path: Path, name: str, payload) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(payload) if not isinstance(payload, str) else payload)
    return path


def run_verifier(candidate: Path, gold: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "searchqa_eval.analysis.verify_answer",
         "--output_file", str(candidate), "--ground_truth", str(gold)],
        capture_output=True, text=True,
    )


# --- report contract -------------------------------------------------------

def test_header_emits_the_exact_result_line_the_agent_greps_for():
    passed = "\n".join(header("T", {"a": "b"}, True, "ok"))
    failed = "\n".join(header("T", {"a": "b"}, False, "no"))
    assert re.search(r"^Result:\s+PASS\b", passed, re.MULTILINE)
    assert not re.search(r"^Result:\s+PASS\b", failed, re.MULTILINE)
    assert PASS_LINE in passed and FAIL_LINE in failed


# --- candidate / gold parsing ---------------------------------------------

def test_load_candidate_accepts_a_plain_answer(tmp_path):
    path = write(tmp_path, "c.json", {"answer": "John Newbery"})
    assert load_candidate(str(path)) == ("John Newbery", "")


def test_load_candidate_extracts_from_a_raw_response(tmp_path):
    """A raw response goes through the harness's own <answer> extraction."""
    path = write(tmp_path, "c.json",
                 {"response": "Let me think. <answer>John Newbery</answer>"})
    answer, error = load_candidate(str(path))
    assert answer == "John Newbery" and not error


@pytest.mark.parametrize("payload,fragment", [
    ("not json", "not valid JSON"),
    ({"id": "q1"}, "neither an 'answer' nor a 'response'"),
    ("[1, 2]", "must be an object"),
])
def test_load_candidate_reports_malformed_input(tmp_path, payload, fragment):
    path = write(tmp_path, "bad.json", payload)
    _, error = load_candidate(str(path))
    assert fragment in error


@pytest.mark.parametrize("payload,fragment", [
    ({"id": "q1"}, "no 'answers' key"),
    ({"answers": []}, "non-empty list"),
    ({"answers": "John"}, "non-empty list"),
])
def test_load_gold_rejects_unusable_ground_truth(tmp_path, payload, fragment):
    path = write(tmp_path, "g.json", payload)
    _, error = load_gold(str(path))
    assert fragment in error


# --- scoring delegation ----------------------------------------------------

def test_exact_match_passes():
    passed, summary, text = build_report("John Newbery", GOLD, "c", "g")
    assert passed and "EM = 1.0" in summary
    assert PASS_LINE in text


def test_scoring_uses_the_harness_normalization_not_a_private_rule():
    """Case and articles are normalized away by the benchmark's own scorer."""
    passed, _, _ = build_report("john newbery", GOLD, "c", "g")
    assert passed


def test_near_miss_is_distinguished_from_a_wrong_answer():
    """sub_EM=1 means right entity, wrong span — a different repair than a wrong entity."""
    _, near, _ = build_report("published by John Newbery", GOLD, "c", "g")
    assert "sub_EM = 1.0" in near

    _, wrong, _ = build_report("Thomas Boreman", GOLD, "c", "g")
    assert "no token overlap" in wrong


def test_partial_overlap_is_reported_as_such():
    _, summary, _ = build_report("John Smith", GOLD, "c", "g")
    assert "partial token overlap" in summary


def test_failure_report_shows_the_normalization_and_a_hint():
    _, _, text = build_report("Thomas Boreman", GOLD, "c", "g")
    assert "Predicted (normalized)" in text
    assert "[!=]" in text
    assert "Hint:" in text


# --- CLI exit codes --------------------------------------------------------

def test_cli_exit_codes_follow_the_verdict(tmp_path):
    gold = write(tmp_path, "gold.json", GOLD)

    good = run_verifier(write(tmp_path, "ok.json", {"answer": "John Newbery"}), gold)
    assert good.returncode == 0 and PASS_LINE in good.stdout

    bad = run_verifier(write(tmp_path, "no.json", {"answer": "nobody"}), gold)
    assert bad.returncode == 1 and FAIL_LINE in bad.stdout


def test_cli_fails_cleanly_on_a_missing_candidate(tmp_path):
    gold = write(tmp_path, "gold.json", GOLD)
    proc = run_verifier(tmp_path / "absent.json", gold)
    assert proc.returncode == 1 and FAIL_LINE in proc.stdout


# --- artifact dump ---------------------------------------------------------

ROW = {
    "id": "q1", "question": "Who published it?", "em": 0.0, "f1": 0.0, "sub_em": 0.0,
    "predicted_answer": "nobody", "gold_answers": ["John Newbery"],
    "response": "<answer>nobody</answer>", "agent_ok": True,
}
ITEM = {"id": "q1", "question": "Who published it?", "context": "[DOC] John Newbery ..."}


def test_dump_creates_the_workspace_layout_the_analyst_expects(tmp_path):
    setup_analysis_dir(tmp_path, ROW, ITEM)
    base = tmp_path / "q1"
    assert (base / "agent_log.md").is_file()
    for name in ("input.json", "output.json", "gold.json"):
        assert (base / "agent_work" / name).is_file()


def test_dump_separates_what_the_agent_saw_from_the_ground_truth(tmp_path):
    """input.json must not leak the answer; gold.json holds it alone."""
    setup_analysis_dir(tmp_path, ROW, ITEM)
    work = tmp_path / "q1" / "agent_work"
    agent_input = json.loads((work / "input.json").read_text())
    assert "answers" not in agent_input
    assert set(agent_input) == {"id", "question", "context"}
    assert json.loads((work / "gold.json").read_text())["answers"] == ["John Newbery"]


def test_dumped_output_round_trips_through_the_verifier(tmp_path):
    """The dump writes output.json in exactly the shape the verifier reads."""
    setup_analysis_dir(tmp_path, ROW, ITEM)
    work = tmp_path / "q1" / "agent_work"

    failing = run_verifier(work / "output.json", work / "gold.json")
    assert failing.returncode == 1

    (work / "output_fixed.json").write_text(json.dumps({"id": "q1", "answer": "John Newbery"}))
    fixed = run_verifier(work / "output_fixed.json", work / "gold.json")
    assert fixed.returncode == 0 and PASS_LINE in fixed.stdout


def test_log_flags_a_missing_response_instead_of_silently_omitting_it():
    without = render_log({k: v for k, v in ROW.items() if k != "response"}, ITEM)
    assert "--record-response" in without
    assert "Extracted answer" in without

    with_response = render_log(ROW, ITEM)
    assert "<answer>nobody</answer>" in with_response
