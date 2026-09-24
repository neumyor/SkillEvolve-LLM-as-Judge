"""Offline tests for the FUSE public-evidence export and workspaces."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from alfworld_eval.fuse import evidence  # noqa: E402


def _trajectory_payload(*, success: bool, task_type: str = "pick_heat_then_place_in_recep") -> dict:
    gamefile = f"json_2.1.1/train/{task_type}-Mug-None-Microwave-1/trial_T20190907_185649_000001/game.tw-pddl"
    return {
        "gamefile": gamefile,
        "task_type": task_type,
        "success": success,
        "steps": 2,
        "invalid_actions": 0,
        "invalid_requests": 0,
        "uncorrected_invalid_requests": 0,
        "correction_attempts": 0,
        "correction_successes": 0,
        "termination_reason": "success" if success else "step_limit",
        "initial_observation": "You are in the middle of a room. Your task is to: heat some mug.",
        "trajectory": [
            {
                "step": 1,
                "model_response": "```find the mug```<action>go to countertop 1</action>",
                "initial_model_response": "```find the mug```<action>go to countertop 1</action>",
                "correction_response": "",
                "correction_attempted": False,
                "correction_succeeded": False,
                "truncated": False,
                "diagnostic": {
                    "valid": True,
                    "format_valid": True,
                    "requested_action": "go to countertop 1",
                    "requested_admissible": True,
                    "truncated": False,
                    "issues": [],
                    "admissible_actions": ["go to countertop 1", "look"],
                },
                "correction_diagnostic": None,
                "action": "go to countertop 1",
                "valid": True,
                "format_valid": True,
                "admissible": True,
                "requested_action": "go to countertop 1",
                "requested_admissible": True,
                "initial_requested_action": "go to countertop 1",
                "initial_format_valid": True,
                "initial_requested_admissible": True,
                "env_feedback": "On the countertop 1, you see a mug 1.",
                "done": False,
                "won": False,
            },
            {
                "step": 2,
                "model_response": "```take it```<action>take mug 1</action>",
                "initial_model_response": "```take it```<action>take mug 1</action>",
                "correction_response": "",
                "correction_attempted": False,
                "correction_succeeded": False,
                "truncated": False,
                "diagnostic": {
                    "valid": True,
                    "format_valid": True,
                    "requested_action": "take mug 1",
                    "requested_admissible": True,
                    "truncated": False,
                    "issues": [],
                    "admissible_actions": ["take mug 1", "look"],
                },
                "correction_diagnostic": None,
                "action": "take mug 1",
                "valid": True,
                "format_valid": True,
                "admissible": True,
                "requested_action": "take mug 1",
                "requested_admissible": True,
                "initial_requested_action": "take mug 1",
                "initial_format_valid": True,
                "initial_requested_admissible": True,
                "env_feedback": "You pick up the mug 1." if success else "Nothing happens.",
                "done": success,
                "won": success,
            },
        ],
    }


class TestPublicStep(unittest.TestCase):
    def test_reward_signal_is_scrubbed(self):
        step = evidence.public_step(_trajectory_payload(success=True)["trajectory"][1])
        self.assertNotIn("won", step)
        self.assertNotIn("done", step)
        self.assertEqual(step["action"], "take mug 1")
        self.assertEqual(step["admissible_actions"], ["take mug 1", "look"])
        self.assertIn("env_feedback", step)


class TestExportRun(unittest.TestCase):
    def test_export_creates_source_and_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run" / "merged"
            traj_dir = run_dir / "trajectories"
            traj_dir.mkdir(parents=True)
            payload = _trajectory_payload(success=False)
            gamefile = payload["gamefile"]
            task_dir = Path(gamefile).parent.parent.name
            trial = Path(gamefile).parent.name
            incident_id = f"{task_dir}__{trial}"
            (traj_dir / f"{incident_id}.json").write_text(
                json.dumps(payload), encoding="utf-8"
            )
            with (run_dir / "results.jsonl").open("w", encoding="utf-8") as f:
                f.write(json.dumps({
                    "gamefile": gamefile,
                    "task_type": payload["task_type"],
                    "success": False,
                    "steps": 2,
                    "invalid_actions": 0,
                    "invalid_requests": 0,
                    "uncorrected_invalid_requests": 0,
                    "correction_attempts": 0,
                    "correction_successes": 0,
                    "truncated_responses": 0,
                    "termination_reason": "step_limit",
                    "usage": {},
                }) + "\n")

            out_dir = Path(tmp) / "out"
            incidents = evidence.export_run(run_dir, out_dir)

            self.assertEqual(len(incidents), 1)
            incident = incidents[0]
            self.assertEqual(incident.outcome, "failure")
            self.assertEqual(incident.task_type, payload["task_type"])
            self.assertTrue((out_dir / "manifest.jsonl").is_file())

            # The exported trajectory must not contain the reward channel.
            exported = (out_dir / "source" / f"{incident_id}.jsonl").read_text(
                encoding="utf-8"
            ).splitlines()
            steps = [json.loads(line) for line in exported]
            self.assertEqual(len(steps), 2)
            for step in steps:
                self.assertNotIn("won", step)
                self.assertNotIn("done", step)

            # Manifest roundtrip keeps the outcome at episode level only.
            reloaded = evidence.load_manifest(out_dir / "manifest.jsonl")
            self.assertEqual(reloaded[0].outcome, "failure")
            self.assertEqual(reloaded[0].initial_observation,
                             payload["initial_observation"])

    def test_export_rejects_trajectory_without_steps(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "merged"
            traj_dir = run_dir / "trajectories"
            traj_dir.mkdir(parents=True)
            (traj_dir / "empty.json").write_text(
                json.dumps({"gamefile": "g", "task_type": "t", "success": False,
                            "trajectory": []}),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                evidence.export_run(run_dir, Path(tmp) / "out")


class TestAttachDiagnoses(unittest.TestCase):
    def test_manifest_diagnosis_path_filled(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp) / "run" / "merged"
            traj_dir = run_dir / "trajectories"
            traj_dir.mkdir(parents=True)
            payload = _trajectory_payload(success=False)
            gamefile = payload["gamefile"]
            incident_id = f"{Path(gamefile).parent.parent.name}__{Path(gamefile).parent.name}"
            (traj_dir / f"{incident_id}.json").write_text(json.dumps(payload),
                                                          encoding="utf-8")
            out_dir = Path(tmp) / "out"
            evidence.export_run(run_dir, out_dir)

            diag = Path(tmp) / "diag" / incident_id / "diagnosis.md"
            diag.parent.mkdir(parents=True)
            diag.write_text("Decision: evolve\n# Summary\n", encoding="utf-8")
            updated = evidence.attach_diagnoses(
                out_dir / "manifest.jsonl", {incident_id: diag}
            )
            self.assertEqual(updated, 1)
            reloaded = evidence.load_manifest(out_dir / "manifest.jsonl")
            self.assertEqual(
                reloaded[0].diagnosis_path, diag
            )


class TestWorkspaces(unittest.TestCase):
    def _incident(self, tmp: Path) -> evidence.Incident:
        run_dir = tmp / "run" / "merged"
        traj_dir = run_dir / "trajectories"
        traj_dir.mkdir(parents=True, exist_ok=True)
        payload = _trajectory_payload(success=False)
        gamefile = payload["gamefile"]
        incident_id = f"{Path(gamefile).parent.parent.name}__{Path(gamefile).parent.name}"
        traj_file = traj_dir / f"{incident_id}.json"
        traj_file.write_text(json.dumps(payload), encoding="utf-8")
        return evidence.Incident(
            incident_id=incident_id,
            outcome="failure",
            task_type=payload["task_type"],
            gamefile=gamefile,
            trajectory_path=traj_file,
            initial_observation=payload["initial_observation"],
            steps=2,
        )

    def test_diagnosis_evidence_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            incident = self._incident(Path(tmp))
            parent = Path(tmp) / "parent.md"
            parent.write_text("# parent skill\n", encoding="utf-8")
            workspace = evidence.write_diagnosis_evidence(
                incident,
                Path(tmp) / "ws",
                meta_skill_text="# meta",
                parent_skill_path=parent,
            )
            for rel in ("README.md", "instruction.md", "protocol.json",
                        "meta_skill/SKILL.md", "current/trajectory.jsonl",
                        "current/skill.md"):
                self.assertTrue((workspace / rel).is_file(), rel)
            protocol = json.loads((workspace / "protocol.json").read_text())
            self.assertEqual(protocol["session_kind"], "diagnosis")
            self.assertEqual(protocol["result_file"], "result/diagnosis.md")

    def test_authoring_evidence_includes_members(self):
        with tempfile.TemporaryDirectory() as tmp:
            incident = self._incident(Path(tmp))
            parent = Path(tmp) / "parent.md"
            parent.write_text("# parent skill\n", encoding="utf-8")
            tags = [{
                "incident_id": incident.incident_id,
                "outcome": "failure",
                "capability_tags": ["heat an object"],
                "capability_summary": "Heat the target.",
            }]
            clusters = {"capability_clusters": []}
            workspace = evidence.write_authoring_evidence(
                incident.task_type,
                [incident],
                tags,
                clusters,
                Path(tmp) / "ws",
                meta_skill_text="# meta",
                parent_skill_path=parent,
            )
            members = [
                json.loads(line)
                for line in (workspace / "members.jsonl").read_text(
                    encoding="utf-8"
                ).splitlines()
            ]
            self.assertEqual(len(members), 1)
            self.assertEqual(members[0]["capability_tags"], ["heat an object"])
            self.assertTrue(
                (workspace / "incidents" / incident.incident_id / "trajectory.jsonl").is_file()
            )
            protocol = json.loads((workspace / "protocol.json").read_text())
            self.assertEqual(protocol["session_kind"], "authoring")
            self.assertEqual(protocol["n_failures"], 1)

    def test_tagging_evidence_copies_diagnosis_when_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            incident = self._incident(Path(tmp))
            diag = Path(tmp) / "d.md"
            diag.write_text("Decision: evolve\n", encoding="utf-8")
            incident.diagnosis_path = diag
            workspace = evidence.write_tagging_evidence(
                incident, Path(tmp) / "ws", meta_skill_text="# meta"
            )
            self.assertTrue((workspace / "diagnosis.md").is_file())


if __name__ == "__main__":
    unittest.main()
