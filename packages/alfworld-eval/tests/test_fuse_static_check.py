"""Offline tests for the candidate skill static checks."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from alfworld_eval.fuse.static_check import check_candidate_skill  # noqa: E402

GOOD_SKILL = """# Operating Guide: Heating Tasks

## Understanding the task
Read the task line carefully: the object to heat and the destination are both
named there. Heat means the microwave, never the toaster or the oven.

## Locating the object
Check receptacles one at a time. Open closed containers (drawers, cabinets)
and look inside before moving on. The object may be in an unexpected place.

## Heating
Take the object, go to the microwave, heat it, then carry it to the destination
receptacle and place it.

## Verifying
Before finishing, confirm the object is in the destination and was heated.
""" + "Ensure the carried object is the target before placing.\n" * 10


class TestStaticCheck(unittest.TestCase):
    def test_good_document_passes(self):
        self.assertEqual(check_candidate_skill(GOOD_SKILL), [])

    def test_empty(self):
        self.assertEqual(len(check_candidate_skill("")), 1)

    def test_too_short(self):
        errors = check_candidate_skill("heat things")
        self.assertTrue(any("too short" in e for e in errors))

    def test_too_long(self):
        errors = check_candidate_skill("x" * 20_000)
        self.assertTrue(any("budget" in e for e in errors))

    def test_cjk_rejected(self):
        errors = check_candidate_skill(GOOD_SKILL + "\n加热物体时使用微波炉。\n")
        self.assertTrue(any("CJK" in e for e in errors))

    def test_trial_id_rejected(self):
        errors = check_candidate_skill(GOOD_SKILL + "\nSee trial_T20190907_185649.\n")
        self.assertTrue(any("trial" in e for e in errors))

    def test_gamefile_rejected(self):
        errors = check_candidate_skill(
            GOOD_SKILL + "\nLoad json_2.1.1/train first.\n"
        )
        self.assertTrue(any("gamefile" in e for e in errors))

    def test_benchmark_vocabulary_rejected(self):
        for word in ("reward", "verifier", "benchmark"):
            errors = check_candidate_skill(
                GOOD_SKILL + f"\nThis improves the {word}.\n"
            )
            self.assertTrue(
                any("benchmark meta vocabulary" in e for e in errors),
                msg=word,
            )

    def test_verify_is_legitimate_language(self):
        errors = check_candidate_skill(
            GOOD_SKILL + "\nAlways verify the object state before placing it.\n"
        )
        self.assertEqual(errors, [])

    def test_placeholder_rejected(self):
        errors = check_candidate_skill(GOOD_SKILL + "\nTODO: fill in\n")
        self.assertTrue(any("placeholder" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
