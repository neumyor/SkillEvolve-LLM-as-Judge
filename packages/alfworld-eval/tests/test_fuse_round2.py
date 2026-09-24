"""Offline tests for FUSE round-2 semantics (per-type parent, extra
diagnoses, validation summary evidence, baseline override)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from alfworld_eval.fuse import evolution as fe  # noqa: E402
from tests.test_fuse_evolution import (  # noqa: E402
    GOOD_SKILL,
    FakeScriptedClient,
    _make_baseline_run,
    _make_config,
    _tool_call,
    _write_call,
)


def _make_round2_config(
    tmp: Path,
    baseline_run: Path,
    parent_skill: Path,
    staged_dir: Path,
    validation_summary: dict,
    baseline_override: dict,
    extra: tuple[str, ...] = (),
) -> fe.FuseEvolutionConfig:
    return fe.FuseEvolutionConfig(
        baseline_run_dir=baseline_run,
        parent_skill=parent_skill,
        out_dir=tmp / "round2",
        project_root=PROJECT_ROOT,
        base_url="http://invalid/v1",
        model="fake-model",
        parent_skills_dir=staged_dir,
        extra_diagnoses=extra,
        validation_summary=validation_summary,
        baseline_outcomes_override=baseline_override,
    )


class TestRound2(unittest.TestCase):
    def _setup(self, tmp: Path):
        baseline_run, parent = _make_baseline_run(tmp)
        # Round-1 published set: per-type documents that differ from parent.
        staged = tmp / "staged"
        staged.mkdir()
        from alfworld_eval.unified.skills import TASKS
        for task_type in TASKS:
            (staged / f"{task_type}.md").write_text(
                f"# round1 published {task_type}\n" + "carry forward.\n" * 20,
                encoding="utf-8",
            )
        return baseline_run, parent, staged

    def test_parent_for_uses_per_type_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            baseline_run, parent, staged = self._setup(Path(tmp))
            config = _make_round2_config(
                Path(tmp), baseline_run, parent, staged, {}, {}
            )
            evo = fe.FuseEvolution(config)
            for task_type in ("pick_and_place", "pick_heat_then_place_in_recep"):
                path = evo.parent_for(task_type)
                # macOS /var -> /private/var symlink: compare resolved paths.
                self.assertEqual(
                    path, (staged / f"{task_type}.md").resolve()
                )
            self.assertIn("round1 published", path.read_text(encoding="utf-8"))

    def test_parent_for_missing_type_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            baseline_run, parent, staged = self._setup(Path(tmp))
            (staged / "pick_and_place.md").unlink()
            config = _make_round2_config(
                Path(tmp), baseline_run, parent, staged, {}, {}
            )
            evo = fe.FuseEvolution(config)
            with self.assertRaises(FileNotFoundError):
                evo.parent_for("pick_and_place")

    def test_extra_diagnose_targets_regressions(self):
        """A baseline-success incident listed in extra_diagnoses gets a
        diagnosis session too (round-2 regression repair evidence)."""
        with tempfile.TemporaryDirectory() as tmp:
            baseline_run, parent, staged = self._setup(Path(tmp))
            config = _make_round2_config(
                Path(tmp), baseline_run, parent, staged, {}, {}, extra=(),
            )
            evo = fe.FuseEvolution(config)
            evo.stage_export()
            success_id = next(
                i.incident_id for i in evo.load_incidents()
                if i.outcome == "success"
            )
            # Rebuild with the success incident as an extra diagnosis target.
            config = _make_round2_config(
                Path(tmp), baseline_run, parent, staged, {}, {},
                extra=(success_id,),
            )
            evo = fe.FuseEvolution(config)
            client = FakeScriptedClient({
                success_id: [{"tool_calls": [_write_call(
                    "result/diagnosis.md", "Decision: evolve\n# R\n",
                )]}],
            })
            evo._session_client = lambda: client  # type: ignore[method-assign]
            diagnoses = evo.stage_diagnose()
            self.assertIn(success_id, diagnoses)

    def test_unknown_extra_diagnosis_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            baseline_run, parent, staged = self._setup(Path(tmp))
            config = _make_round2_config(
                Path(tmp), baseline_run, parent, staged, {}, {},
                extra=("no-such-incident",),
            )
            evo = fe.FuseEvolution(config)
            evo.stage_export()
            with self.assertRaises(ValueError):
                evo.stage_diagnose()

    def test_baseline_override_used_in_accept(self):
        """Acceptance compares against the override (round-1 published system),
        not the original baseline run."""
        with tempfile.TemporaryDirectory() as tmp:
            baseline_run, parent, staged = self._setup(Path(tmp))
            evo0 = fe.FuseEvolution(_make_config(Path(tmp), baseline_run, parent))
            evo0.stage_export()
            incidents = evo0.load_incidents()
            failure_id = next(
                i.incident_id for i in incidents if i.outcome == "failure"
            )
            success_id = next(
                i.incident_id for i in incidents if i.outcome == "success"
            )
            # Round-2 validation: the (originally failing) episode passes.
            validations = config_dir = Path(tmp) / "round2" / "validations"
            for index, rows in enumerate(
                [{failure_id: True, success_id: True}] * 3, start=1
            ):
                merged = (
                    validations / "pick_and_place" / f"attempt-{index}" / "merged"
                )
                merged.mkdir(parents=True, exist_ok=True)
                with (merged / "results.jsonl").open("w", encoding="utf-8") as f:
                    for incident_id, ok in rows.items():
                        task_dir, trial = incident_id.rsplit("__", 1)
                        f.write(json.dumps({
                            "gamefile": (
                                f"json_2.1.1/train/{task_dir}/{trial}/game.tw-pddl"
                            ),
                            "success": ok,
                            "usage": {},
                        }) + "\n")
            # Override says both episodes already passed in round 1.
            override = {
                failure_id: {"success": True, "source": "round1_candidate"},
                success_id: {"success": True, "source": "round1_candidate"},
            }
            config = _make_round2_config(
                Path(tmp), baseline_run, parent, staged, {}, override,
            )
            evo = fe.FuseEvolution(config)
            # Round-2 works on a manifest: export the baseline into round2.
            evo.stage_export()
            attempts = {
                "pick_and_place": {
                    "status": "validated",
                    "task_type": "pick_and_place",
                    "skill_sha256": "x",
                    "attempts": [evo._attempt_outcomes(
                        validations / "pick_and_place" / f"attempt-{i}" / "merged"
                    ) for i in (1, 2, 3)],
                }
            }
            (validations / "attempts.json").write_text(
                json.dumps(attempts), encoding="utf-8"
            )
            report = evo.stage_accept(only_types=("pick_and_place",))
            family = report["families"]["pick_and_place"]
            # Both members were round-1 passes and still pass: no regression.
            self.assertEqual(family["regressions"], [])
            # The family had no *override* failures, so all members must pass.
            self.assertEqual(family["status"], "accepted")

    def test_validation_summary_in_authoring_evidence(self):
        """The authoring workspace receives the previous-round verdicts."""
        with tempfile.TemporaryDirectory() as tmp:
            baseline_run, parent, staged = self._setup(Path(tmp))
            evo0 = fe.FuseEvolution(_make_config(Path(tmp), baseline_run, parent))
            evo0.stage_export()
            incidents = evo0.load_incidents()
            failure_id = next(
                i.incident_id for i in incidents if i.outcome == "failure"
            )
            summary = {
                failure_id: {
                    "task_type": "pick_and_place",
                    "attempt_successes": 0,
                    "attempts_present": 3,
                    "passed": False,
                },
            }
            # Authoring for pick_and_place: parent is the staged document and
            # the workspace must contain validation_summary.json.
            config = _make_round2_config(
                Path(tmp), baseline_run, parent, staged, summary, {},
            )
            evo = fe.FuseEvolution(config)
            evo.stage_export()
            incidents = evo.load_incidents()
            tags = [{
                "incident_id": i.incident_id, "outcome": i.outcome,
                "capability_tags": ["x"], "capability_summary": "x.",
            } for i in incidents]
            tagging = config.out_dir / "tagging"
            tagging.mkdir(parents=True, exist_ok=True)
            with (tagging / "tags.jsonl").open("w", encoding="utf-8") as f:
                for row in tags:
                    f.write(json.dumps(row) + "\n")
            (tagging / "clusters.json").write_text(
                json.dumps({"capability_clusters": []}), encoding="utf-8"
            )
            client = FakeScriptedClient({
                "pick_and_place": [{"tool_calls": [_write_call(
                    "result/skill.md", GOOD_SKILL,
                )]}],
                "pick_heat": [{"tool_calls": [_write_call(
                    "result/skill.md", GOOD_SKILL,
                )]}],
            })
            evo._session_client = lambda: client  # type: ignore[method-assign]
            published = evo.stage_author(only_types=("pick_and_place",))
            self.assertIn("pick_and_place", published)
            session_dir = config.skills_dir / "pick_and_place" / "session"
            workspaces = sorted(session_dir.glob("attempt-*/evidence"))
            self.assertTrue(workspaces)
            summary_file = workspaces[-1] / "validation_summary.json"
            self.assertTrue(summary_file.is_file())
            loaded = json.loads(summary_file.read_text(encoding="utf-8"))
            self.assertEqual(loaded["episodes"][failure_id]["passed"], False)
            parent_copy = workspaces[-1] / "parent" / "skill.md"
            self.assertIn("round1 published", parent_copy.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
