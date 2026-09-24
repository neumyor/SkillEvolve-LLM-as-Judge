"""Offline tests for the Trace2Skill-style analysis port (ALFWorld).

No LLM and no network. The ALFWorld tests need the local game data; they skip
cleanly when ALFWORLD_DATA is unset or the fixture game is not present.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from alfworld_eval.analysis.report import FAIL_LINE, PASS_LINE, header
from alfworld_eval.analysis.verify_episode import extract_goal, load_candidate
from alfworld_eval.unified.runner import episode_id

# A look_at_obj_in_light episode from valid_unseen, and a sequence verified to
# reach its goal. Serves as the ground-truth-positive case for the verifier.
FIXTURE_GAME_REL = (
    "json_2.1.1/valid_unseen/"
    "look_at_obj_in_light-AlarmClock-None-DeskLamp-308/"
    "trial_T20190908_222917_366542/game.tw-pddl"
)
WINNING_ACTIONS = [
    "go to desk 2",
    "take alarmclock 1 from desk 2",
    "go to desk 1",
    "use desklamp 1",
]
LOSING_ACTIONS = ["go to bed 1", "examine bed 1", "examine bed 1"]


def fixture_game() -> str:
    data = os.environ.get("ALFWORLD_DATA")
    if not data:
        pytest.skip("ALFWORLD_DATA not set")
    path = Path(data) / FIXTURE_GAME_REL
    if not path.is_file():
        pytest.skip(f"fixture game not present: {path}")
    return str(path)


def run_verifier(candidate: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "alfworld_eval.analysis.verify_episode",
         "--output_file", str(candidate)],
        capture_output=True, text=True,
    )


def write_candidate(tmp_path: Path, actions: list[str], gamefile: str) -> Path:
    path = tmp_path / "candidate.json"
    path.write_text(json.dumps({"gamefile": gamefile, "actions": actions}))
    return path


# --- report contract -------------------------------------------------------

def test_header_emits_the_exact_result_line_the_agent_greps_for():
    """The analyst tool wrapper detects success with ^Result:\\s+PASS\\b."""
    import re
    passed = "\n".join(header("T", {"a": "b"}, True, "ok"))
    failed = "\n".join(header("T", {"a": "b"}, False, "no"))
    assert re.search(r"^Result:\s+PASS\b", passed, re.MULTILINE)
    assert not re.search(r"^Result:\s+PASS\b", failed, re.MULTILINE)
    assert PASS_LINE in passed and FAIL_LINE in failed


# --- candidate parsing -----------------------------------------------------

def test_load_candidate_accepts_dict_and_bare_list(tmp_path):
    as_dict = tmp_path / "d.json"
    as_dict.write_text('{"gamefile": "/g", "actions": ["look"]}')
    assert load_candidate(str(as_dict)) == (["look"], "/g", "")

    as_list = tmp_path / "l.json"
    as_list.write_text('["look", "go to bed 1"]')
    actions, gamefile, error = load_candidate(str(as_list))
    assert actions == ["look", "go to bed 1"] and gamefile is None and not error


@pytest.mark.parametrize("content,fragment", [
    ("not json", "not valid JSON"),
    ('{"gamefile": "/g"}', "no 'actions' key"),
    ('{"actions": [1, 2]}', "list of strings"),
    ('"a string"', "object or a list"),
])
def test_load_candidate_reports_malformed_input(tmp_path, content, fragment):
    path = tmp_path / "bad.json"
    path.write_text(content)
    _, _, error = load_candidate(str(path))
    assert fragment in error


def test_load_candidate_missing_file():
    _, _, error = load_candidate("/nonexistent/candidate.json")
    assert "does not exist" in error


# --- goal extraction -------------------------------------------------------

def test_extract_goal_reads_the_task_out_of_the_opening_observation():
    obs = (
        "-= Welcome to TextWorld, ALFRED! =-\n\nYou are in the middle of a room. "
        "Looking quickly around you, you see a bed 1.\n\n"
        "Your task is to: examine the alarmclock with the desklamp.\n"
    )
    assert extract_goal(obs) == "examine the alarmclock with the desklamp."


def test_extract_goal_degrades_gracefully():
    assert "not found" in extract_goal("no task statement here")


# --- episode ids -----------------------------------------------------------

def test_episode_id_disambiguates_trials_sharing_a_task_directory():
    """Three trials of one task must not collide onto one filename."""
    base = "/data/valid_unseen/look_at_obj_in_light-AlarmClock-None-DeskLamp-308"
    ids = {episode_id(f"{base}/trial_{n}/game.tw-pddl") for n in ("a", "b", "c")}
    assert len(ids) == 3
    assert all(i.startswith("look_at_obj_in_light-AlarmClock") for i in ids)


def test_episode_id_falls_back_when_the_path_is_empty():
    assert episode_id("", 7) == "episode_0007"


# --- the verifier, end to end ---------------------------------------------

def test_winning_sequence_passes_with_exit_code_zero(tmp_path):
    game = fixture_game()
    proc = run_verifier(write_candidate(tmp_path, WINNING_ACTIONS, game))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert PASS_LINE in proc.stdout
    assert "examine the alarmclock with the desklamp" in proc.stdout


def test_losing_sequence_fails_with_exit_code_one(tmp_path):
    game = fixture_game()
    proc = run_verifier(write_candidate(tmp_path, LOSING_ACTIONS, game))
    assert proc.returncode == 1
    assert FAIL_LINE in proc.stdout
    assert "actions proposed : 3" in proc.stdout


def test_inadmissible_action_is_reported_with_the_alternatives(tmp_path):
    """The analyst's main repair signal: what it could have done instead."""
    game = fixture_game()
    proc = run_verifier(write_candidate(tmp_path, ["fly to the moon"], game))
    assert proc.returncode == 1
    assert "inadmissible     : 1" in proc.stdout
    assert "Admissible commands at that step:" in proc.stdout
    assert "- go to desk 2" in proc.stdout


def test_empty_and_missing_candidates_fail_without_crashing(tmp_path):
    game = fixture_game()
    empty = write_candidate(tmp_path, [], game)
    proc = run_verifier(empty)
    assert proc.returncode == 1 and "empty action sequence" in proc.stdout

    proc = run_verifier(tmp_path / "absent.json")
    assert proc.returncode == 1 and FAIL_LINE in proc.stdout
