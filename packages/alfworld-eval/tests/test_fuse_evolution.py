"""Offline tests for the FUSE evolution orchestrator (no network, no evals)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from alfworld_eval.fuse import evolution as fe  # noqa: E402


class FakeScriptedClient:
    def __init__(self, script: dict[str, list[dict]]):
        self.script = {k: list(v) for k, v in script.items()}
        self.calls: list[str] = []

    def complete(self, messages, tools=None, **kwargs):  # noqa: ANN001
        from alfworld_eval.trace2skill.llm import ChatResponse
        # Identify the session by the first user message.
        first_user = next(m["content"] for m in messages if m["role"] == "user")
        for key, responses in self.script.items():
            if key in first_user and responses:
                self.calls.append(key)
                item = responses.pop(0)
                return ChatResponse(
                    content=item.get("content", ""),
                    tool_calls=item.get("tool_calls", []),
                    usage={"prompt_tokens": 10, "completion_tokens": 5},
                )
        # Default: end the session (no result file).
        return ChatResponse(content="(end)", tool_calls=[], usage={})


def _tool_call(name: str, arguments: dict, call_id: str = "c1") -> dict:
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(arguments)},
    }


def _write_call(path: str, content: str) -> dict:
    return _tool_call("write_file", {"path": path, "content": content})


GOOD_SKILL = "# Guide\n" + "Useful transferable instructions.\n" * 40


def _make_baseline_run(tmp: Path) -> tuple[Path, Path]:
    """Two episodes (one success, one failure) with recorded trajectories."""
    run_dir = tmp / "baseline" / "merged"
    traj_dir = run_dir / "trajectories"
    traj_dir.mkdir(parents=True)
    parent_skill = tmp / "parent.md"
    parent_skill.write_text(GOOD_SKILL, encoding="utf-8")

    episodes = [
        ("pick_heat_then_place_in_recep-Mug-None-Microwave-1",
         "trial_T20190907_1", True),
        ("pick_and_place-Spoon-None-Safe-1", "trial_T20190908_2", False),
    ]
    with (run_dir / "results.jsonl").open("w", encoding="utf-8") as f:
        for task_dir, trial, success in episodes:
            gamefile = (
                f"json_2.1.1/train/{task_dir}/{trial}/game.tw-pddl"
            )
            incident_id = f"{task_dir}__{trial}"
            payload = {
                "gamefile": gamefile,
                "task_type": task_dir.split("-")[0] if False else _task_type(task_dir),
                "success": success,
                "steps": 2,
                "invalid_actions": 0,
                "invalid_requests": 0,
                "uncorrected_invalid_requests": 0,
                "correction_attempts": 0,
                "correction_successes": 0,
                "termination_reason": "success" if success else "step_limit",
                "initial_observation": f"Your task is to: do {task_dir}.",
                "trajectory": [
                    {
                        "step": 1,
                        "model_response": "```go```<action>look</action>",
                        "action": "look",
                        "requested_action": "look",
                        "format_valid": True,
                        "admissible": True,
                        "diagnostic": {"admissible_actions": ["look"]},
                        "correction_attempted": False,
                        "correction_response": "",
                        "env_feedback": "You see nothing.",
                        "done": False,
                        "won": False,
                    },
                    {
                        "step": 2,
                        "model_response": "```go```<action>look</action>",
                        "action": "look",
                        "requested_action": "look",
                        "format_valid": True,
                        "admissible": True,
                        "diagnostic": {"admissible_actions": ["look"]},
                        "correction_attempted": False,
                        "correction_response": "",
                        "env_feedback": "Nothing happens.",
                        "done": success,
                        "won": success,
                    },
                ],
            }
            (traj_dir / f"{incident_id}.json").write_text(
                json.dumps(payload), encoding="utf-8"
            )
            f.write(json.dumps({
                "gamefile": gamefile,
                "task_type": payload["task_type"],
                "success": success,
                "steps": 2,
                "invalid_actions": 0,
                "invalid_requests": 0,
                "uncorrected_invalid_requests": 0,
                "correction_attempts": 0,
                "correction_successes": 0,
                "truncated_responses": 0,
                "termination_reason": payload["termination_reason"],
                "usage": {},
            }) + "\n")
    return run_dir, parent_skill


def _task_type(task_dir: str) -> str:
    from alfworld_eval.unified.skills import TASKS
    for task in TASKS:
        if task in task_dir:
            return task
    return "other"


class _NoEvalEvolution(fe.FuseEvolution):
    """Evolution with the eval driver stubbed out (no subprocess)."""

    def __init__(self, config, attempt_results: dict[str, list[dict[str, bool]]]):
        super().__init__(config)
        self.attempt_results = attempt_results  # {task_type: [attempt rows]}
        self.eval_calls: list[dict] = []

    def _run_eval(self, *, out_base, method, items, skill_path, skill_dir,
                 skip_warmup=False):
        self.eval_calls.append({
            "out_base": str(out_base), "method": method,
            "items": str(items), "skill_path": str(skill_path),
        })
        merged = Path(out_base) / "merged"
        merged.mkdir(parents=True, exist_ok=True)
        task_type = Path(out_base).parent.name
        attempt_index = int(Path(out_base).name.split("-")[1])
        rows = self.attempt_results[task_type][attempt_index - 1]
        with (merged / "results.jsonl").open("w", encoding="utf-8") as f:
            for incident_id, success in rows.items():
                task_dir, trial = incident_id.rsplit("__", 1)
                f.write(json.dumps({
                    "gamefile": f"json_2.1.1/train/{task_dir}/{trial}/game.tw-pddl",
                    "success": success,
                    "usage": {},
                }) + "\n")
        return merged


def _make_config(tmp: Path, baseline_run: Path, parent_skill: Path) -> fe.FuseEvolutionConfig:
    return fe.FuseEvolutionConfig(
        baseline_run_dir=baseline_run,
        parent_skill=parent_skill,
        out_dir=tmp / "out",
        project_root=PROJECT_ROOT,
        base_url="http://invalid/v1",
        model="fake-model",
        api_key="",
        attempts=3,
        shards=2,
    )


class TestStageExport(unittest.TestCase):
    def test_export_and_families(self):
        with tempfile.TemporaryDirectory() as tmp:
            baseline_run, parent = _make_baseline_run(Path(tmp))
            evo = fe.FuseEvolution(_make_config(Path(tmp), baseline_run, parent))
            incidents = evo.stage_export()
            self.assertEqual(len(incidents), 2)
            failures = [i for i in incidents if i.outcome == "failure"]
            self.assertEqual(len(failures), 1)
            families = evo._authoring_families()
            self.assertIn("pick_heat_then_place_in_recep", families)
            self.assertIn("pick_and_place", families)


class TestStageDiagnoseAndTag(unittest.TestCase):
    def test_diagnose_writes_and_tags_all(self):
        with tempfile.TemporaryDirectory() as tmp:
            baseline_run, parent = _make_baseline_run(Path(tmp))
            evo = fe.FuseEvolution(_make_config(Path(tmp), baseline_run, parent))
            evo.stage_export()
            failure_id = next(
                i.incident_id for i in evo.load_incidents()
                if i.outcome == "failure"
            )
            client = FakeScriptedClient({
                failure_id: [
                    {"tool_calls": [_write_call(
                        "result/diagnosis.md", "Decision: evolve\n# S\n",
                    )]},
                ],
            })
            evo.client = client
            evo._session_client = lambda: client  # type: ignore[method-assign]
            diagnoses = evo.stage_diagnose()
            self.assertEqual(list(diagnoses), [failure_id])

            # Tagging: both incidents need tags.json.
            incident_ids = [i.incident_id for i in evo.load_incidents()]
            tag_script: dict[str, list[dict]] = {}
            for incident_id in incident_ids:
                tag_script[incident_id] = [{"tool_calls": [_write_call(
                    "result/tags.json",
                    json.dumps({
                        "schema_version": 1,
                        "incident_id": incident_id,
                        "outcome": "failure" if incident_id == failure_id else "success",
                        "capability_tags": ["locate an object"],
                        "capability_summary": "Find the object.",
                    }),
                )]}]
            tag_client = FakeScriptedClient(tag_script)
            evo.client = tag_client
            evo._session_client = lambda: tag_client  # type: ignore[method-assign]
            tags = evo.stage_tag()
            self.assertEqual(len(tags), 2)

            # Manifest now references the diagnosis.
            reloaded = evo.load_incidents()
            by_id = {i.incident_id: i for i in reloaded}
            self.assertIsNotNone(by_id[failure_id].diagnosis_path)

    def test_diagnose_incomplete_leaves_no_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            baseline_run, parent = _make_baseline_run(Path(tmp))
            evo = fe.FuseEvolution(_make_config(Path(tmp), baseline_run, parent))
            evo.stage_export()
            failure_id = next(
                i.incident_id for i in evo.load_incidents()
                if i.outcome == "failure"
            )
            client = FakeScriptedClient({failure_id: []})
            evo._session_client = lambda: client  # type: ignore[method-assign]
            diagnoses = evo.stage_diagnose()
            self.assertEqual(diagnoses, {})


class TestStageCluster(unittest.TestCase):
    def test_cluster_validates_membership(self):
        with tempfile.TemporaryDirectory() as tmp:
            baseline_run, parent = _make_baseline_run(Path(tmp))
            evo = fe.FuseEvolution(_make_config(Path(tmp), baseline_run, parent))
            evo.stage_export()
            incidents = evo.load_incidents()
            ids = [i.incident_id for i in incidents]
            tag_rows = [
                {"incident_id": i.incident_id, "outcome": i.outcome,
                 "capability_tags": ["locate an object"],
                 "capability_summary": "Find the object."}
                for i in incidents
            ]
            (evo.config.tagging_dir).mkdir(parents=True, exist_ok=True)
            with (evo.config.tagging_dir / "tags.jsonl").open("w", encoding="utf-8") as f:
                for row in tag_rows:
                    f.write(json.dumps(row) + "\n")
            clusters_payload = {
                "capability_clusters": [{
                    "cluster_id": "c1",
                    "label": "Locating objects",
                    "definition": "Find target objects.",
                    "decision": "merge",
                    "member_ids": ids,
                }]
            }
            client = FakeScriptedClient({
                "Cluster": [{"tool_calls": [_write_call(
                    "result/clusters.json", json.dumps(clusters_payload),
                )]}],
            })
            evo._session_client = lambda: client  # type: ignore[method-assign]
            result = evo.stage_cluster()
            self.assertEqual(len(result["capability_clusters"]), 1)


class TestStageAuthor(unittest.TestCase):
    def test_author_ok_and_static_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            baseline_run, parent = _make_baseline_run(Path(tmp))
            evo = fe.FuseEvolution(_make_config(Path(tmp), baseline_run, parent))
            evo.stage_export()
            incidents = evo.load_incidents()
            tag_rows = [
                {"incident_id": i.incident_id, "outcome": i.outcome,
                 "capability_tags": ["locate an object"],
                 "capability_summary": "Find the object."}
                for i in incidents
            ]
            tagging = evo.config.tagging_dir
            tagging.mkdir(parents=True, exist_ok=True)
            with (tagging / "tags.jsonl").open("w", encoding="utf-8") as f:
                for row in tag_rows:
                    f.write(json.dumps(row) + "\n")
            (tagging / "clusters.json").write_text(
                json.dumps({"capability_clusters": []}), encoding="utf-8"
            )
            # First authoring attempt violates static checks (too short);
            # second attempt succeeds for one type, first try for the other.
            script: dict[str, list[dict]] = {
                "pick_heat": [
                    {"tool_calls": [_write_call("result/skill.md", "too short")]},
                    {"tool_calls": [_write_call("result/skill.md", GOOD_SKILL)]},
                ],
                "pick_and_place": [
                    {"tool_calls": [_write_call("result/skill.md", GOOD_SKILL)]},
                ],
            }
            client = FakeScriptedClient(script)
            evo._session_client = lambda: client  # type: ignore[method-assign]
            published = evo.stage_author()
            self.assertEqual(sorted(published), [
                "pick_and_place", "pick_heat_then_place_in_recep",
            ])
            heat = (published["pick_heat_then_place_in_recep"]).read_text()
            self.assertEqual(heat, GOOD_SKILL)

    def test_author_two_failures_raise(self):
        with tempfile.TemporaryDirectory() as tmp:
            baseline_run, parent = _make_baseline_run(Path(tmp))
            evo = fe.FuseEvolution(_make_config(Path(tmp), baseline_run, parent))
            evo.stage_export()
            incidents = evo.load_incidents()
            tag_rows = [
                {"incident_id": i.incident_id, "outcome": i.outcome,
                 "capability_tags": ["x"],
                 "capability_summary": "x."}
                for i in incidents
            ]
            tagging = evo.config.tagging_dir
            tagging.mkdir(parents=True, exist_ok=True)
            with (tagging / "tags.jsonl").open("w", encoding="utf-8") as f:
                for row in tag_rows:
                    f.write(json.dumps(row) + "\n")
            (tagging / "clusters.json").write_text(
                json.dumps({"capability_clusters": []}), encoding="utf-8"
            )
            script: dict[str, list[dict]] = {
                "pick_heat": [
                    {"tool_calls": [_write_call("result/skill.md", "bad")]},
                    {"tool_calls": [_write_call("result/skill.md", "still bad")]},
                ],
                "pick_and_place": [
                    {"tool_calls": [_write_call("result/skill.md", GOOD_SKILL)]},
                ],
            }
            client = FakeScriptedClient(script)
            evo._session_client = lambda: client  # type: ignore[method-assign]
            with self.assertRaises(RuntimeError):
                evo.stage_author()


class TestAcceptanceRules(unittest.TestCase):
    def _setup(self, tmp: Path):
        baseline_run, parent = _make_baseline_run(Path(tmp))
        config = _make_config(Path(tmp), baseline_run, parent)
        return baseline_run, parent, config

    def _write_attempts(self, config, task_type: str, attempts: list[dict[str, bool]]):
        validations = config.validations_dir / task_type
        for index, rows in enumerate(attempts, start=1):
            merged = validations / f"attempt-{index}" / "merged"
            merged.mkdir(parents=True, exist_ok=True)
            with (merged / "results.jsonl").open("w", encoding="utf-8") as f:
                for incident_id, success in rows.items():
                    # Reconstruct the real gamefile shape so episode_id()
                    # reproduces the manifest's incident_id (<task>__<trial>).
                    task_dir, trial = incident_id.rsplit("__", 1)
                    f.write(json.dumps({
                        "gamefile": (
                            f"json_2.1.1/train/{task_dir}/{trial}/game.tw-pddl"
                        ),
                        "success": success,
                        "usage": {},
                    }) + "\n")

    def test_gain_accepted(self):
        """Baseline failure flips to pass -> gain, accepted."""
        with tempfile.TemporaryDirectory() as tmp:
            baseline_run, parent, config = self._setup(Path(tmp))
            evo = fe.FuseEvolution(config)
            evo.stage_export()
            failure_id = next(
                i.incident_id for i in evo.load_incidents()
                if i.outcome == "failure"
            )
            success_id = next(
                i.incident_id for i in evo.load_incidents()
                if i.outcome == "success"
            )
            # The failing family's candidate passes 2/3 on the failed episode.
            self._write_attempts(config, "pick_and_place", [
                {failure_id: True, success_id: True},
                {failure_id: False, success_id: True},
                {failure_id: True, success_id: True},
            ])
            attempts = {
                "pick_and_place": {
                    "status": "validated",
                    "task_type": "pick_and_place",
                    "skill_sha256": "x",
                    "attempts": [evo._attempt_outcomes(
                        config.validations_dir / "pick_and_place" / f"attempt-{i}" / "merged"
                    ) for i in (1, 2, 3)],
                }
            }
            (config.validations_dir / "attempts.json").write_text(
                json.dumps(attempts), encoding="utf-8"
            )
            report = evo.stage_accept(only_types=("pick_and_place",))
            family = report["families"]["pick_and_place"]
            self.assertEqual(family["status"], "accepted")
            self.assertEqual(family["gains"], [failure_id])
            self.assertEqual(family["regressions"], [])

    def test_regression_rejected(self):
        """Baseline success flips to fail -> regression, rejected."""
        with tempfile.TemporaryDirectory() as tmp:
            baseline_run, parent, config = self._setup(Path(tmp))
            evo = fe.FuseEvolution(config)
            evo.stage_export()
            # The baseline-success episode belongs to the heat family.
            success_id = next(
                i.incident_id for i in evo.load_incidents()
                if i.outcome == "success"
            )
            self._write_attempts(config, "pick_heat_then_place_in_recep", [
                {success_id: False},
                {success_id: False},
                {success_id: True},
            ])
            attempts = {
                "pick_heat_then_place_in_recep": {
                    "status": "validated",
                    "task_type": "pick_heat_then_place_in_recep",
                    "skill_sha256": "x",
                    "attempts": [evo._attempt_outcomes(
                        config.validations_dir
                        / "pick_heat_then_place_in_recep" / f"attempt-{i}" / "merged"
                    ) for i in (1, 2, 3)],
                }
            }
            (config.validations_dir / "attempts.json").write_text(
                json.dumps(attempts), encoding="utf-8"
            )
            report = evo.stage_accept(
                only_types=("pick_heat_then_place_in_recep",)
            )
            family = report["families"]["pick_heat_then_place_in_recep"]
            self.assertEqual(family["status"], "validation_failed")
            self.assertEqual(family["regressions"], [success_id])

    def test_missing_attempt_is_infra_not_regression(self):
        """A baseline-success episode with a missing attempt is infra, not a
        regression (FUSE infrastructure separation)."""
        with tempfile.TemporaryDirectory() as tmp:
            baseline_run, parent, config = self._setup(Path(tmp))
            evo = fe.FuseEvolution(config)
            evo.stage_export()
            success_id = next(
                i.incident_id for i in evo.load_incidents()
                if i.outcome == "success"
            )
            # Attempt 2 lost the episode entirely (shard died); 1 and 3 split,
            # so no majority exists -- exactly the untrustworthy verdict case.
            self._write_attempts(config, "pick_heat_then_place_in_recep", [
                {success_id: True},
                {},
                {success_id: False},
            ])
            attempts = {
                "pick_heat_then_place_in_recep": {
                    "status": "validated",
                    "task_type": "pick_heat_then_place_in_recep",
                    "skill_sha256": "x",
                    "attempts": [evo._attempt_outcomes(
                        config.validations_dir
                        / "pick_heat_then_place_in_recep" / f"attempt-{i}" / "merged"
                    ) for i in (1, 2, 3)],
                }
            }
            (config.validations_dir / "attempts.json").write_text(
                json.dumps(attempts), encoding="utf-8"
            )
            report = evo.stage_accept(
                only_types=("pick_heat_then_place_in_recep",)
            )
            family = report["families"]["pick_heat_then_place_in_recep"]
            # Not a regression; infra slots never count against a candidate.
            self.assertEqual(family["regressions"], [])
            members = {m["incident_id"]: m for m in family["members"]}
            self.assertEqual(
                members[success_id]["verdict"], "infrastructure_unresolved"
            )
            # And with nothing judgeable left, the family is not accepted.
            self.assertEqual(family["status"], "validation_failed")
            self.assertIn("infrastructure-unresolved", family["reason"])

    def test_all_success_family_requires_all_pass(self):
        """A family whose members all succeeded in the baseline is accepted
        only when every member still passes."""
        with tempfile.TemporaryDirectory() as tmp:
            baseline_run, parent, config = self._setup(Path(tmp))
            evo = fe.FuseEvolution(config)
            evo.stage_export()
            success_id = next(
                i.incident_id for i in evo.load_incidents()
                if i.outcome == "success"
            )
            self._write_attempts(config, "pick_heat_then_place_in_recep", [
                {success_id: True},
                {success_id: True},
                {success_id: False},
            ])
            attempts = {
                "pick_heat_then_place_in_recep": {
                    "status": "validated",
                    "task_type": "pick_heat_then_place_in_recep",
                    "skill_sha256": "x",
                    "attempts": [evo._attempt_outcomes(
                        config.validations_dir
                        / "pick_heat_then_place_in_recep" / f"attempt-{i}" / "merged"
                    ) for i in (1, 2, 3)],
                }
            }
            (config.validations_dir / "attempts.json").write_text(
                json.dumps(attempts), encoding="utf-8"
            )
            report = evo.stage_accept(only_types=("pick_heat_then_place_in_recep",))
            family = report["families"]["pick_heat_then_place_in_recep"]
            # 2/3 majority on a baseline-success member: passes -> accepted.
            self.assertEqual(family["status"], "accepted")


class TestStaging(unittest.TestCase):
    def test_staging_falls_back_to_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            baseline_run, parent = _make_baseline_run(Path(tmp))
            config = _make_config(Path(tmp), baseline_run, parent)
            evo = fe.FuseEvolution(config)
            evo.stage_export()
            report = {"families": {
                "pick_and_place": {"status": "accepted"},
                "pick_heat_then_place_in_recep": {"status": "validation_failed"},
            }}
            (config.out_dir / "report.json").write_text(
                json.dumps(report), encoding="utf-8"
            )
            # The accepted family needs an authored skill.
            accepted_skill = config.skills_dir / "pick_and_place" / "skill.md"
            accepted_skill.parent.mkdir(parents=True, exist_ok=True)
            accepted_skill.write_text(GOOD_SKILL, encoding="utf-8")

            staged = evo.stage_stage()
            from alfworld_eval.unified.skills import TASKS
            for task_type in TASKS:
                self.assertTrue((staged / f"{task_type}.md").is_file())
            self.assertEqual(
                (staged / "pick_and_place.md").read_text(encoding="utf-8"),
                GOOD_SKILL,
            )
            self.assertEqual(
                (staged / "pick_heat_then_place_in_recep.md").read_text(
                    encoding="utf-8"
                ),
                parent.read_text(encoding="utf-8"),
            )
            staging = json.loads((staged / "staging.json").read_text())
            self.assertEqual(
                staging["report"]["pick_and_place"], "accepted"
            )


class TestValidateStage(unittest.TestCase):
    def test_validate_invokes_driver_per_attempt(self):
        with tempfile.TemporaryDirectory() as tmp:
            baseline_run, parent = _make_baseline_run(Path(tmp))
            config = _make_config(Path(tmp), baseline_run, parent)
            evo = _NoEvalEvolution(config, attempt_results={
                "pick_and_place": [
                    {"pick_and_place-Spoon-None-Safe-1__trial_T20190908_2": True},
                ] * 3,
                "pick_heat_then_place_in_recep": [
                    {"pick_heat_then_place_in_recep-Mug-None-Microwave-1__trial_T20190907_1": True},
                ] * 3,
            })
            evo.stage_export()
            failure_id = next(
                i.incident_id for i in evo.load_incidents()
                if i.outcome == "failure"
            )
            # Author minimal skills so validation has something to inject.
            for task_type in ("pick_and_place", "pick_heat_then_place_in_recep"):
                skill = config.skills_dir / task_type / "skill.md"
                skill.parent.mkdir(parents=True, exist_ok=True)
                skill.write_text(GOOD_SKILL, encoding="utf-8")
            reports = evo.stage_validate()
            self.assertEqual(len(evo.eval_calls), 6)  # 2 families x 3 attempts
            self.assertEqual(
                reports["pick_and_place"]["status"], "validated"
            )
            # The manifest used for pick_and_place contains only its members.
            pp_call = next(
                c for c in evo.eval_calls if c["skill_path"].endswith(
                    "pick_and_place/skill.md"
                )
            )
            items = json.loads(Path(pp_call["items"]).read_text())
            gamefiles = [item["gamefile"] for item in items]
            self.assertTrue(all("pick_and_place" in g for g in gamefiles))
            self.assertEqual(len(gamefiles), 1)


if __name__ == "__main__":
    unittest.main()
