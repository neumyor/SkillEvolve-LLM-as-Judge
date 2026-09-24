"""Offline tests for the fuse additions to the unified evaluation stack."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from alfworld_eval.unified.prompts import SKILL_KNOWLEDGE_HEADER, build_user_prompt  # noqa: E402
from alfworld_eval.unified.skills import (  # noqa: E402
    TASKS,
    SkillProvider,
    load_skill_provider,
    skill_provenance,
)


def _make_skill_dir(tmp: Path, types=None) -> Path:
    directory = tmp / "routed"
    directory.mkdir()
    for task_type in (types or TASKS):
        (directory / f"{task_type}.md").write_text(
            f"# guide for {task_type}\nDo the right thing.\n" + "detail\n" * 20,
            encoding="utf-8",
        )
    return directory


class TestFuseSkillProvider(unittest.TestCase):
    def test_routes_by_gamefile(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = _make_skill_dir(Path(tmp))
            provider = load_skill_provider("fuse", skill_dir=skill_dir)
            gamefile = "json_2.1.1/valid_unseen/pick_heat_then_place_in_recep-Mug-None-Microwave-1/trial_T1/game.tw-pddl"
            view = provider.view_for(gamefile, "Your task is to: heat a mug.")
            self.assertTrue(view.prefix.startswith(SKILL_KNOWLEDGE_HEADER))
            self.assertIn("guide for pick_heat_then_place_in_recep", view.prefix)

    def test_missing_type_document_fails_fast(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = _make_skill_dir(Path(tmp), types=TASKS[:3])
            with self.assertRaises(ValueError) as ctx:
                load_skill_provider("fuse", skill_dir=skill_dir)
            self.assertIn("missing documents", str(ctx.exception))

    def test_missing_directory_fails_fast(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                load_skill_provider("fuse", skill_dir=Path(tmp) / "nope")

    def test_injected_into_prompt(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = _make_skill_dir(Path(tmp))
            provider = load_skill_provider("fuse", skill_dir=skill_dir)
            gamefile = "json_2.1.1/valid_unseen/pick_and_place-Spoon-None-Safe-1/trial_T1/game.tw-pddl"
            view = provider.view_for(gamefile, "observation")
            prompt = build_user_prompt(
                "You see a spoon.", ["take spoon 1"],
                skill=view, task_description="put the spoon somewhere",
            )
            self.assertIn("## Skill Knowledge", prompt)
            self.assertIn("guide for pick_and_place", prompt)
            self.assertIn("admissible actions", prompt)

    def test_provenance_records_per_type_digests(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = _make_skill_dir(Path(tmp))
            provenance = skill_provenance("fuse", skill_dir=skill_dir)
            self.assertEqual(provenance["kind"], "routed_skill_dir")
            self.assertEqual(len(provenance["per_type"]), len(TASKS))
            for task_type in TASKS:
                entry = provenance["per_type"][task_type]
                self.assertIn("sha256", entry)
                self.assertGreater(entry["chars"], 0)
            # Digest changes when one document changes.
            (skill_dir / f"{TASKS[0]}.md").write_text("changed\n", encoding="utf-8")
            changed = skill_provenance("fuse", skill_dir=skill_dir)
            self.assertNotEqual(provenance["sha256"], changed["sha256"])

    def test_unknown_task_type_gets_no_skill(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = _make_skill_dir(Path(tmp))
            provider = load_skill_provider("fuse", skill_dir=skill_dir)
            view = provider.view_for("some/other/game.tw-pddl", "obs")
            self.assertEqual(view.prefix, "")
            self.assertEqual(view.body, "")


class TestExistingMethodsUntouched(unittest.TestCase):
    def test_skillopt_provider_still_works(self):
        provider = load_skill_provider("skillopt")
        view = provider.view_for("any", "any")
        self.assertTrue(view.prefix.startswith(SKILL_KNOWLEDGE_HEADER))

    def test_vanilla_provider_still_works(self):
        provider = load_skill_provider("vanilla")
        view = provider.view_for("any", "any")
        self.assertEqual(view.prefix, "")
        self.assertEqual(view.body, "")


class TestInitialObservationRecording(unittest.TestCase):
    def test_mock_episode_records_initial_observation(self):
        """A mock-backend episode must carry the initial observation into the
        trajectory JSON so the FUSE export has the episode instruction."""
        from alfworld_eval.env import AlfworldTextEnv
        from alfworld_eval.unified.agent import build_agent
        from alfworld_eval.unified.runner import run_unified_episode

        env = AlfworldTextEnv(
            config_path=str(PROJECT_ROOT / "configs" / "textworld.yaml"),
            split="valid_seen",
            seed=42,
        )
        try:
            agent = build_agent("mock", seed=42)
            provider = SkillProvider("vanilla")
            result = run_unified_episode(
                env, agent, provider, record_trajectory=True
            )
            self.assertTrue(result.initial_observation)
            self.assertIn("task is to:", result.initial_observation)
        finally:
            env.close()


if __name__ == "__main__":
    unittest.main()
