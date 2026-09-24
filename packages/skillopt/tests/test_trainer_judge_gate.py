"""Trainer integration for the judge gate, on the fake environment.

What these tests pin down, using the real trainer loop and no LLM:

* `gate_mode: judge` never runs a selection rollout per candidate — that
  rollout is the cost the judge gate is supposed to remove, so if it still
  happens the experiment measures nothing;
* the decision still drives the skill trajectory (accept replaces the skill,
  reject does not);
* `gate_mode: greedy` and `gate_mode: rollout` are unchanged, so the baseline
  numbers already on disk stay comparable.

The judge LLM is a scripted fake injected through
``trainer_module.judge_gate_for_config``; everything else is production code.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

import skillopt.engine.trainer as trainer_module
from skillopt.engine.trainer import ReflACTTrainer

from .test_trainer_evolution_mode import (  # noqa: F401 — fixture is imported for autouse
    MAGIC,
    FakeAdapter,
    _make_cfg,
    _no_llm_merge,
)


class _ScriptedJudge:
    """JudgeGate stand-in: replays a verdict script, records what it saw."""

    def __init__(self, verdicts: list[str]) -> None:
        self.verdicts = list(verdicts)
        self.calls: list[dict] = []

    def __call__(self, **kwargs):
        from skillopt.evaluation.gate import GateResult

        verdict = self.verdicts.pop(0) if self.verdicts else "REJECT"
        self.calls.append(kwargs)
        if verdict == "ACCEPT":
            result = GateResult(
                action="accept_new_best",
                current_skill=kwargs["candidate_skill"],
                current_score=kwargs["current_score"],
                best_skill=kwargs["candidate_skill"],
                best_score=kwargs["current_score"],
                best_step=kwargs["global_step"],
            )
        else:
            result = GateResult(
                action="reject",
                current_skill=kwargs["current_skill"],
                current_score=kwargs["current_score"],
                best_skill=kwargs["best_skill"],
                best_score=kwargs["best_score"],
                best_step=kwargs["best_step"],
            )
        return result, {
            "gate_kind": "judge",
            "judge_verdict": verdict,
            "judge_confidence": "high",
            "judge_reason": f"scripted {verdict}",
            "judge_parse_failed": False,
            "judge_calls": 1,
            "judge_error": "",
            "judge_usage": {},
            "judge_evidence_cards": len(kwargs.get("batches") or []),
            "judge_evidence_total": sum(
                len(b.get("results") or []) for b in (kwargs.get("batches") or [])
            ),
        }


def _install_judge(monkeypatch, judge):
    monkeypatch.setattr(
        trainer_module, "judge_gate_for_config", lambda cfg: judge
    )


def _selection_rollouts(adapter: FakeAdapter) -> list[dict]:
    """Rollout calls that evaluated a candidate on the selection split.

    Counts both the one-time baseline and per-candidate evaluations, so a
    mode that skips the per-candidate rollout shows a count of exactly 1.
    """
    return [c for c in adapter.rollout_calls if "selection_eval" in c["dir"]]


class TestJudgeGateMode:
    def test_package_relative_initial_skill_from_external_working_directory(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        judge = _ScriptedJudge(["REJECT"])
        _install_judge(monkeypatch, judge)
        cfg = _make_cfg(tmp_path, gate_mode="judge", evolution_mode="fixed", batch_size=12, train_size=12)
        cfg["skill_init"] = "skillopt/envs/searchqa/skills/initial.md"
        ReflACTTrainer(cfg, FakeAdapter()).train()
        expected = Path(trainer_module.__file__).resolve().parents[2] / cfg["skill_init"]
        assert (Path(cfg["out_root"]) / "skills/skill_v0000.md").read_text() == expected.read_text()

    @pytest.mark.parametrize("mode, expected", [("rollout", 36), ("judge", 9)])
    def test_only_replaced_rollouts_or_judge_tokens_are_counted(self, tmp_path, monkeypatch, mode, expected):
        from skillopt.model.common import TokenTracker
        from skillopt.evaluation.judge_gate import JudgeGate

        class MeteredAdapter(FakeAdapter):
            def rollout(self, *args, **kwargs):
                TokenTracker().record("rollout", 10, 2)
                return super().rollout(*args, **kwargs)

        judge = JudgeGate(prompt_variant="v3", chat_fn=lambda **kwargs: (
            json.dumps({"verdict": "ACCEPT", "confidence": "medium", "reason": "Repairs the failure"}),
            {"prompt_tokens": 2, "completion_tokens": 1},
        ))
        monkeypatch.setattr(trainer_module, "judge_gate_for_config", lambda cfg: judge if mode == "judge" else None)
        cfg = _make_cfg(tmp_path, gate_mode=mode, evolution_mode="fixed", batch_size=4, train_size=12)
        ReflACTTrainer(cfg, MeteredAdapter()).train()
        cost = json.loads((Path(cfg["out_root"]) / "replacement_cost.json").read_text())
        # Baseline: seed + two distinct candidates; the third attempt hits cache.
        assert cost["total_tokens"] == expected
        assert cost["usage_complete"]

    def test_no_selection_rollout_per_candidate(self, tmp_path, monkeypatch):
        """The whole point: the judge gate costs no selection rollout."""
        judge = _ScriptedJudge(["ACCEPT", "ACCEPT", "ACCEPT"])
        _install_judge(monkeypatch, judge)
        adapter = FakeAdapter()
        cfg = _make_cfg(
            tmp_path, gate_mode="judge", evolution_mode="fixed",
            batch_size=4, train_size=12,
        )
        ReflACTTrainer(cfg, adapter).train()

        # Exactly one final measurement, after the output has been frozen.
        assert [c["dir"].rsplit("/", 1)[-1] for c in _selection_rollouts(adapter)] == ["final_selection_eval"]
        assert len(judge.calls) == 3  # one per attempt, three attempts

    def test_rollout_mode_still_runs_selection_per_candidate(self, tmp_path):
        """Baseline protection: the paper path is untouched."""
        adapter = FakeAdapter()
        cfg = _make_cfg(
            tmp_path, gate_mode="rollout", evolution_mode="fixed",
            batch_size=12, train_size=12,
        )
        ReflACTTrainer(cfg, adapter).train()
        # baseline + the candidate (the remaining attempts are cache hits on
        # an identical candidate hash, so they cost no rollout)
        assert len(_selection_rollouts(adapter)) == 2

    def test_accept_replaces_the_skill(self, tmp_path, monkeypatch):
        judge = _ScriptedJudge(["ACCEPT"])
        _install_judge(monkeypatch, judge)
        adapter = FakeAdapter()
        cfg = _make_cfg(
            tmp_path, gate_mode="judge", evolution_mode="fixed",
            batch_size=12, train_size=12,
        )
        ReflACTTrainer(cfg, adapter).train()

        history = json.load(open(os.path.join(cfg["out_root"], "history.json")))
        assert len(history) == 1
        assert history[0]["action"] in {"accept", "accept_new_best"}
        assert history[0]["gate_kind"] == "judge"
        assert history[0]["judge_verdict"] == "ACCEPT"
        assert MAGIC in open(os.path.join(cfg["out_root"], "best_skill.md")).read()

    def test_reject_leaves_the_skill_alone(self, tmp_path, monkeypatch):
        judge = _ScriptedJudge(["REJECT"])
        _install_judge(monkeypatch, judge)
        adapter = FakeAdapter()
        cfg = _make_cfg(
            tmp_path, gate_mode="judge", evolution_mode="fixed",
            batch_size=12, train_size=12,
        )
        ReflACTTrainer(cfg, adapter).train()

        history = json.load(open(os.path.join(cfg["out_root"], "history.json")))
        assert history[0]["action"] == "reject"
        assert history[0]["judge_verdict"] == "REJECT"
        assert MAGIC not in open(os.path.join(cfg["out_root"], "best_skill.md")).read()

    def test_judge_sees_the_steps_evidence_window(self, tmp_path, monkeypatch):
        judge = _ScriptedJudge(["REJECT"])
        _install_judge(monkeypatch, judge)
        adapter = FakeAdapter()
        cfg = _make_cfg(
            tmp_path, gate_mode="judge", evolution_mode="fixed",
            batch_size=12, train_size=12,
        )
        ReflACTTrainer(cfg, adapter).train()

        call = judge.calls[0]
        batches = call["batches"]
        assert len(batches) == 1
        results = batches[0]["results"]
        assert len(results) == 12  # the whole 12-task window
        assert all("id" in r for r in results)
        assert call["ranked_patch"] is not None
        assert call["candidate_skill"] != call["current_skill"]

    def test_record_flags_which_gate_decided(self, tmp_path, monkeypatch):
        """The analysis stage reads gate_kind to separate the conditions."""
        judge = _ScriptedJudge(["ACCEPT"])
        _install_judge(monkeypatch, judge)
        adapter = FakeAdapter()
        cfg = _make_cfg(
            tmp_path, gate_mode="judge", evolution_mode="fixed",
            batch_size=12, train_size=12,
        )
        ReflACTTrainer(cfg, adapter).train()
        history = json.load(open(os.path.join(cfg["out_root"], "history.json")))
        assert history[0]["gate_kind"] == "judge"
        # No fabricated selection score is reported as if it were measured.
        assert history[0]["judge_evidence_total"] == 12

    def test_full_validation_audit_fails_before_execution(self, tmp_path):
        adapter = FakeAdapter()
        cfg = _make_cfg(tmp_path, gate_mode="judge", judge_full_validation_audit=True)
        with pytest.raises(ValueError, match="forbids"):
            ReflACTTrainer(cfg, adapter).train()
        assert adapter.rollout_calls == []

    def test_no_validation_at_all_when_final_measurement_disabled(self, tmp_path, monkeypatch):
        _install_judge(monkeypatch, _ScriptedJudge(["ACCEPT"]))
        adapter = FakeAdapter()
        cfg = _make_cfg(tmp_path, gate_mode="judge", eval_test=False,
                        evolution_mode="fixed", batch_size=12, train_size=12)
        summary = ReflACTTrainer(cfg, adapter).train()
        assert _selection_rollouts(adapter) == []
        assert summary["best_selection_hard"] is None

    def test_final_validation_is_fresh_and_cannot_change_judge_output(self, tmp_path, monkeypatch):
        _install_judge(monkeypatch, _ScriptedJudge(["ACCEPT"]))
        adapter = FakeAdapter()
        cfg = _make_cfg(tmp_path, gate_mode="judge", evolution_mode="fixed",
                        batch_size=12, train_size=12)
        summary = ReflACTTrainer(cfg, adapter).train()
        assert summary["best_selection_hard"] == 1.0
        assert summary["baseline_selection_hard"] is None
        assert all("step_" not in row["dir"] for row in _selection_rollouts(adapter))

    def test_greedy_mode_still_validates_but_accepts_everything(self, tmp_path):
        """`greedy` is the no-gate bound, and it still measures the split."""
        adapter = FakeAdapter()
        cfg = _make_cfg(
            tmp_path, gate_mode="greedy", evolution_mode="fixed",
            batch_size=12, train_size=12,
        )
        ReflACTTrainer(cfg, adapter).train()
        history = json.load(open(os.path.join(cfg["out_root"], "history.json")))
        assert all(h["action"] == "force_accept" for h in history)
        # validation ran for both the baseline and the candidate
        assert len(_selection_rollouts(adapter)) == 2

    def test_use_gate_false_is_equivalent_to_greedy(self, tmp_path, monkeypatch):
        """Backward compatibility: the old switch keeps its meaning."""
        judge = _ScriptedJudge(["ACCEPT"])
        _install_judge(monkeypatch, judge)
        adapter = FakeAdapter()
        cfg = _make_cfg(
            tmp_path, evolution_mode="fixed", batch_size=4, train_size=12,
        )
        cfg.pop("gate_mode", None)
        cfg["use_gate"] = False
        ReflACTTrainer(cfg, adapter).train()
        history = json.load(open(os.path.join(cfg["out_root"], "history.json")))
        assert all(h["action"] == "force_accept" for h in history)
        assert judge.calls == []


class TestJudgeModeConfigErrors:
    def test_unknown_gate_mode_fails_before_any_rollout(self, tmp_path):
        adapter = FakeAdapter()
        cfg = _make_cfg(tmp_path, gate_mode="ask-a-friend")
        with pytest.raises(ValueError, match="gate_mode"):
            ReflACTTrainer(cfg, adapter).train()
        assert adapter.rollout_calls == []
