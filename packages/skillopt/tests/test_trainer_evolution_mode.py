"""Integration tests for evidence-triggered evolution in the trainer.

Runs the REAL ReflACTTrainer end-to-end with a deterministic fake
environment adapter (no LLM anywhere):

- rollout: succeeds iff the current skill contains the magic keyword — so
  accepted updates actually change rollout outcomes and exercise the gate;
- reflect: returns a canned patch (append the magic keyword) without any
  optimizer call;
- merge/rank: monkeypatched to identity so no LLM is contacted.

The controller-mode tests inject a scripted LLMEvidencePolicy through the
trainer's policy factory, so the observation stream, the evidence buffer,
the decision log, the attempt pipeline and the cycle reset are all exercised
exactly as in production — only the LLM call itself is replaced.

Fixed-schedule equivalence: immediate mode with m == batch_size must make
the same number of attempts over the same train coverage as the original
fixed schedule.
"""
from __future__ import annotations

import json
import os

import pytest

import skillopt.engine.trainer as trainer_module
from skillopt.datasets.base import BaseDataLoader, BatchSpec
from skillopt.engine.trainer import ReflACTTrainer
from skillopt.envs.base import EnvAdapter
from skillopt.evolution_controller import (
    UPDATE,
    WAIT,
    EvolutionDecision,
    LLMEvidencePolicy,
)

MAGIC = "keyword-that-makes-tasks-succeed"


# ── Fake environment ────────────────────────────────────────────────────────


class FakeDataLoader(BaseDataLoader):
    """In-memory 3-split loader over generated items."""

    def __init__(self, n_train: int, n_val: int, n_test: int) -> None:
        self._items = {
            "train": [
                {"id": f"train_{i}", "question": f"train question {i}", "answers": ["yes"]}
                for i in range(n_train)
            ],
            "val": [
                {"id": f"val_{i}", "question": f"val question {i}", "answers": ["yes"]}
                for i in range(n_val)
            ],
            "test": [
                {"id": f"test_{i}", "question": f"test question {i}", "answers": ["yes"]}
                for i in range(n_test)
            ],
        }

    def get_train_size(self) -> int:
        return len(self._items["train"])

    def get_split_items(self, split: str) -> list[dict]:
        return list(self._items.get(split, []))

    def build_train_batch(self, batch_size: int, seed: int, **kwargs) -> BatchSpec:
        items = self._items["train"]
        start = seed % len(items) if items else 0
        picked = [items[(start + i) % len(items)] for i in range(batch_size)]
        return BatchSpec(
            phase="train", split="train", seed=seed, batch_size=batch_size, payload=picked,
        )

    def build_eval_batch(self, env_num: int, split: str, seed: int, **kwargs) -> BatchSpec:
        items = self._items.get("val" if split == "valid_seen" else "test", [])
        if env_num:
            items = items[:env_num]
        return BatchSpec(
            phase="eval", split=split, seed=seed, batch_size=len(items), payload=items,
        )


class FakeAdapter(EnvAdapter):
    """Deterministic adapter: rollout succeeds iff the skill has MAGIC."""

    def __init__(self, n_train=12, n_val=4, n_test=4) -> None:
        self.dataloader = FakeDataLoader(n_train, n_val, n_test)
        self.rollout_calls: list[dict] = []

    def get_dataloader(self):
        return self.dataloader

    def build_env_from_batch(self, batch: BatchSpec, **kwargs):
        return list(batch.payload or [])

    def build_train_env(self, batch_size: int, seed: int, **kwargs):
        batch = self.dataloader.build_train_batch(batch_size=batch_size, seed=seed)
        return self.build_env_from_batch(batch)

    def build_eval_env(self, env_num: int, split: str, seed: int, **kwargs):
        batch = self.dataloader.build_eval_batch(env_num=env_num, split=split, seed=seed)
        return self.build_env_from_batch(batch)

    def rollout(self, env_manager, skill_content: str, out_dir: str, **kwargs) -> list[dict]:
        items: list[dict] = env_manager
        os.makedirs(os.path.join(out_dir, "predictions"), exist_ok=True)
        results = []
        for item in items:
            success = MAGIC in skill_content
            result = {
                "id": item["id"],
                "question": item["question"],
                "hard": 1 if success else 0,
                "soft": 1.0 if success else 0.0,
                "fail_reason": "" if success else "EM=0: predicted 'no' but expected ['yes']",
                "task_type": "fake",
                "task_description": item["question"],
                "n_turns": 1,
                "agent_ok": True,
            }
            pred_dir = os.path.join(out_dir, "predictions", item["id"])
            os.makedirs(pred_dir, exist_ok=True)
            with open(os.path.join(pred_dir, "conversation.json"), "w") as f:
                json.dump([{"role": "agent", "content": "fake trajectory"}], f)
            results.append(result)
        self.rollout_calls.append(
            {"n": len(items), "skill_has_magic": MAGIC in skill_content, "dir": out_dir}
        )
        return results

    def reflect(self, results, skill_content, out_dir, **kwargs):
        patches_dir = kwargs.get("patches_dir", os.path.join(out_dir, "patches"))
        os.makedirs(patches_dir, exist_ok=True)
        return [
            {
                "source_type": "failure",
                "patch": {
                    "reasoning": "fake",
                    "edits": [
                        {"op": "append", "content": f"\n- always apply {MAGIC}", "target": ""}
                    ],
                },
            }
        ]

    def get_task_types(self) -> list[str]:
        return ["fake"]


def _make_cfg(tmp_path, **overrides) -> dict:
    skill_init = tmp_path / "skill_init.md"
    if not skill_init.exists():
        skill_init.write_text("base skill\n", encoding="utf-8")
    cfg = {
        "env": "fake",
        "out_root": str(tmp_path / "out"),
        "skill_init": str(skill_init),
        "optimizer_model": "fake-optimizer",
        "target_model": "fake-target",
        "num_epochs": 1,
        "train_size": 12,
        "batch_size": 4,
        "accumulation": 1,
        "seed": 42,
        "minibatch_size": 8,
        "merge_batch_size": 8,
        "analyst_workers": 2,
        "failure_only": False,
        "edit_budget": 8,
        "min_edit_budget": 2,
        "lr_scheduler": "constant",
        "lr_control_mode": "fixed",
        "skill_update_mode": "patch",
        "use_gate": True,
        "gate_metric": "hard",
        "sel_env_num": 0,
        "test_env_num": 0,
        "eval_test": True,
        "use_slow_update": False,
        "use_meta_skill": False,
        "use_skill_aware_reflection": False,
        # evolution defaults
        "evolution_mode": "fixed",
        "observation_batch_size": 4,
        "evolution_fixed_k": 1,
    }
    cfg.update(overrides)
    return cfg


@pytest.fixture(autouse=True)
def _no_llm_merge(monkeypatch):
    """Replace the LLM-based merge with a deterministic concatenation."""

    def fake_merge(skill, failure_patches, success_patches, **kwargs):
        # normalised patches are the INNER patch dicts ({"edits": [...]});
        # accept the raw wrapped shape too, just in case.
        edits = []
        for p in failure_patches + success_patches:
            inner = p.get("patch", p) if isinstance(p, dict) else {}
            edits.extend(inner.get("edits", []))
        return {"reasoning": "fake merge", "edits": edits}

    monkeypatch.setattr(trainer_module, "merge_patches", fake_merge)


class ScriptedPolicy(LLMEvidencePolicy):
    """LLM policy that replays a scripted decision sequence."""

    name = "controller"

    def __init__(self, script: list[str]) -> None:
        super().__init__()
        self.script = list(script)

    def observe(self, skill, new_results, evidence_state, **kwargs):
        if not self.script:
            action = WAIT
        else:
            action = self.script.pop(0)
        return EvolutionDecision(
            action=action,
            state=(
                {"hypotheses": [{"defect": "scripted", "supporting_cases": [], "counter_cases": [], "assessment": "test"}], "unresolved": ""}
                if action == WAIT
                else {"hypotheses": [{"defect": "scripted", "supporting_cases": ["t"], "counter_cases": [], "assessment": "actionable"}], "unresolved": ""}
            ),
            reason=f"scripted {action}",
            meta={"policy": self.name},
        )


def _install_policy(monkeypatch, policy):
    monkeypatch.setattr(
        trainer_module, "build_evolution_policy", lambda cfg: policy
    )


# ── Controller mode: the evidence-triggered loop ────────────────────────────


class TestControllerMode:
    def test_wait_then_update_runs_attempt_and_resets_cycle(self, tmp_path, monkeypatch):
        # 12 train tasks, m=4 → 3 observations per epoch.
        # Script: WAIT, WAIT, UPDATE → attempt after the 3rd observation
        # with all 3 observations (12 tasks) in the window.
        _install_policy(
            monkeypatch,
            ScriptedPolicy([WAIT, WAIT, UPDATE]),
        )
        cfg = _make_cfg(tmp_path, evolution_mode="controller", observation_batch_size=4)
        trainer = ReflACTTrainer(cfg, FakeAdapter())
        summary = trainer.train()

        # exactly one attempt consumed all three observations
        assert summary["evolution"]["total_attempts"] == 1
        assert summary["evolution"]["total_observations"] == 3
        intervals = summary["evolution"]["trigger_intervals"]
        assert len(intervals) == 1
        assert intervals[0]["observations"] == 3
        assert intervals[0]["tasks"] == 12

        # the attempt record carries the evolution window metadata
        history = json.load(open(os.path.join(cfg["out_root"], "history.json")))
        assert len(history) == 1
        rec = history[0]
        assert rec["step"] == 1
        assert rec["evolution"]["n_observations"] == 3
        assert rec["evolution"]["window_tasks"] == 12
        assert rec["evolution"]["obs_indices"] == [1, 2, 3]
        assert rec["rollout_n"] == 12

        # the candidate contains the magic edit → gate must accept it
        assert rec["action"] in {"accept", "accept_new_best"}
        assert MAGIC in open(os.path.join(cfg["out_root"], "best_skill.md")).read()

        # every decision is logged with its buffer state
        decisions = [
            json.loads(line)
            for line in open(os.path.join(cfg["out_root"], "evolution_decisions.jsonl"))
        ]
        assert [d["action"] for d in decisions] == [WAIT, WAIT, UPDATE]
        assert [d["buffer_observations"] for d in decisions] == [1, 2, 3]
        assert [d["buffer_tasks"] for d in decisions] == [4, 8, 12]

        # observation artifacts exist and are referenced by the state file
        for obs_idx in (1, 2, 3):
            obs_dir = os.path.join(cfg["out_root"], "observations", f"obs_{obs_idx:05d}")
            assert os.path.exists(os.path.join(obs_dir, "rollout"))
            assert os.path.exists(os.path.join(obs_dir, "obs_results.json"))
        state = json.load(open(os.path.join(cfg["out_root"], "evolution_state.json")))
        assert state["global_obs_index"] == 3
        assert state["buffer"] == []  # cycle reset after the attempt
        assert state["pending_decision"] is None

    def test_update_on_first_observation_short_window(self, tmp_path, monkeypatch):
        _install_policy(monkeypatch, ScriptedPolicy([UPDATE, UPDATE, UPDATE]))
        cfg = _make_cfg(tmp_path, evolution_mode="controller", observation_batch_size=4)
        summary = ReflACTTrainer(cfg, FakeAdapter()).train()
        # every observation triggered → 3 attempts, each with a 4-task window
        assert summary["evolution"]["total_attempts"] == 3
        assert [t["tasks"] for t in summary["evolution"]["trigger_intervals"]] == [4, 4, 4]
        history = json.load(open(os.path.join(cfg["out_root"], "history.json")))
        assert len(history) == 3

    def test_all_wait_never_invokes_optimizer(self, tmp_path, monkeypatch):
        _install_policy(monkeypatch, ScriptedPolicy([WAIT, WAIT, WAIT]))
        cfg = _make_cfg(tmp_path, evolution_mode="controller", observation_batch_size=4)
        summary = ReflACTTrainer(cfg, FakeAdapter()).train()
        # observations still ran; zero attempts; skill never changed
        assert summary["evolution"]["total_observations"] == 3
        assert summary["evolution"]["total_attempts"] == 0
        assert summary["evolution"]["leftover_buffer_observations"] == 3
        assert not os.path.exists(os.path.join(cfg["out_root"], "history.json"))
        best = open(os.path.join(cfg["out_root"], "best_skill.md")).read()
        assert MAGIC not in best

    def test_rejected_candidate_still_resets_cycle(self, tmp_path, monkeypatch):
        # Gate rejects: candidate evaluated with the SAME skill (magic
        # already there? no — skill starts empty and rollout always fails
        # until an edit lands). Force rejection by pre-filling the skill
        # with the magic keyword: then current already scores 1.0 and the
        # candidate cannot beat it.
        _install_policy(monkeypatch, ScriptedPolicy([UPDATE, UPDATE, UPDATE]))
        skill_init = tmp_path / "init.md"
        skill_init.write_text(f"base skill with {MAGIC}\n")
        cfg = _make_cfg(
            tmp_path,
            evolution_mode="controller",
            observation_batch_size=4,
            skill_init=str(skill_init),
        )
        summary = ReflACTTrainer(cfg, FakeAdapter()).train()
        history = json.load(open(os.path.join(cfg["out_root"], "history.json")))
        # attempts still happened and still consumed their windows —
        # the cycle resets regardless of the gate outcome
        assert summary["evolution"]["total_attempts"] == 3
        assert all(rec["action"] == "reject" for rec in history)
        state = json.load(open(os.path.join(cfg["out_root"], "evolution_state.json")))
        assert state["buffer"] == []

    def test_epoch_end_consult_triggers_end_policy(self, tmp_path):
        # EndPolicy: WAIT during the epoch, UPDATE at the boundary.
        # (Real policy — no stub, no LLM: EndPolicy is pure counting.)
        cfg = _make_cfg(tmp_path, evolution_mode="end", observation_batch_size=4)
        summary = ReflACTTrainer(cfg, FakeAdapter()).train()
        assert summary["evolution"]["total_attempts"] == 1
        interval = summary["evolution"]["trigger_intervals"][0]
        assert interval["trigger"] == "end:epoch_end"
        assert interval["tasks"] == 12

    def test_epoch_end_controller_consult_uses_buffer(self, tmp_path, monkeypatch):
        # Script WAITs the 3 observations and UPDATEs at the epoch boundary.
        policy = ScriptedPolicy([WAIT, WAIT, WAIT, UPDATE])
        _install_policy(monkeypatch, policy)
        cfg = _make_cfg(tmp_path, evolution_mode="controller", observation_batch_size=4)
        summary = ReflACTTrainer(cfg, FakeAdapter()).train()
        assert summary["evolution"]["total_attempts"] == 1
        decisions = [
            json.loads(line)
            for line in open(os.path.join(cfg["out_root"], "evolution_decisions.jsonl"))
        ]
        assert len(decisions) == 4  # 3 observations + 1 epoch boundary
        assert decisions[-1]["epoch_end"] is True
        assert decisions[-1]["action"] == UPDATE
        assert summary["evolution"]["trigger_intervals"][0]["trigger"].endswith(":epoch_end")

    def test_stale_buffer_dropped_on_skill_change_between_epochs(
        self, tmp_path, monkeypatch
    ):
        # WAIT everything in epoch 1; epoch-1 boundary consult UPDATEs
        # (attempt 1 consumes the whole epoch); epoch 2's first observation
        # UPDATEs immediately (attempt 2, mid-epoch trigger), the rest WAIT.
        # Script order: obs1..3, epoch-1 boundary, obs4..6, epoch-2 boundary.
        policy = ScriptedPolicy(
            [WAIT, WAIT, WAIT, UPDATE, UPDATE, WAIT, WAIT, WAIT]
        )
        _install_policy(monkeypatch, policy)
        cfg = _make_cfg(
            tmp_path,
            evolution_mode="controller",
            observation_batch_size=4,
            num_epochs=2,
        )
        summary = ReflACTTrainer(cfg, FakeAdapter()).train()
        assert summary["evolution"]["total_observations"] == 6
        assert summary["evolution"]["total_attempts"] == 2
        intervals = summary["evolution"]["trigger_intervals"]
        assert intervals[0]["trigger"].endswith(":epoch_end")
        assert intervals[1]["trigger"] == "controller"


# ── Window de-dilution + enriched attempt memory ────────────────────────────


class ObsScriptedAdapter(FakeAdapter):
    """FakeAdapter whose rollout outcome is scripted per observation.

    Observation 1 succeeds for every task (a zero-failure batch); all
    other observations fail unless the skill contains MAGIC. Eval
    rollouts (selection/val) never match the obs pattern and follow the
    MAGIC rule alone.
    """

    def __init__(self) -> None:
        super().__init__()
        self.reflect_calls: list[str] = []

    def rollout(self, env_manager, skill_content, out_dir, **kwargs) -> list[dict]:
        import re

        items: list[dict] = env_manager
        os.makedirs(os.path.join(out_dir, "predictions"), exist_ok=True)
        m = re.search(r"obs_(\d+)", out_dir)
        obs_success = bool(m) and int(m.group(1)) == 1
        results = []
        for item in items:
            success = MAGIC in skill_content or obs_success
            result = {
                "id": item["id"],
                "question": item["question"],
                "hard": 1 if success else 0,
                "soft": 1.0 if success else 0.0,
                "fail_reason": "" if success else "EM=0: predicted 'no' but expected ['yes']",
                "task_type": "fake",
                "task_description": item["question"],
                "n_turns": 1,
                "agent_ok": True,
            }
            pred_dir = os.path.join(out_dir, "predictions", item["id"])
            os.makedirs(pred_dir, exist_ok=True)
            with open(os.path.join(pred_dir, "conversation.json"), "w") as f:
                json.dump([{"role": "agent", "content": "fake trajectory"}], f)
            results.append(result)
        self.rollout_calls.append(
            {"n": len(items), "skill_has_magic": MAGIC in skill_content, "dir": out_dir}
        )
        return results

    def reflect(self, results, skill_content, out_dir, **kwargs):
        self.reflect_calls.append(str(kwargs.get("patches_dir") or out_dir))
        return super().reflect(results, skill_content, out_dir, **kwargs)


class TestWindowDeDilution:
    """Fix 3a: zero-failure observation batches are dropped from attempt
    windows (they only contribute success patches that dilute failure
    evidence); a fully failure-free buffer falls back to unchanged
    behaviour, and dropped batches still count as consumed from the stream."""

    def test_zero_failure_batches_dropped_from_window(self, tmp_path, monkeypatch):
        # obs 1: all four tasks succeed (zero-failure batch) → dropped;
        # obs 2, 3: all tasks fail → kept. UPDATE on obs 3 with the whole
        # buffer → the attempt window must be obs 2+3 only (8 tasks).
        _install_policy(monkeypatch, ScriptedPolicy([WAIT, WAIT, UPDATE]))
        adapter = ObsScriptedAdapter()
        cfg = _make_cfg(tmp_path, evolution_mode="controller", observation_batch_size=4)
        summary = ReflACTTrainer(cfg, adapter).train()

        assert summary["evolution"]["total_attempts"] == 1
        history = json.load(open(os.path.join(cfg["out_root"], "history.json")))
        rec = history[0]
        ev = rec["evolution"]
        assert ev["n_observations"] == 2
        assert ev["window_tasks"] == 8
        assert ev["obs_indices"] == [2, 3]
        assert ev["dropped_zero_failure_observations"] == 1
        assert ev["dropped_zero_failure_tasks"] == 4
        assert rec["rollout_n"] == 8

        # the dropped batch was never reflected (no analyst spend on it)
        reflected_obs = sorted(
            int(p.split("obs_")[-1].split("/")[0])
            for p in adapter.reflect_calls
            if "obs_" in p
        )
        assert reflected_obs == [2, 3]

        # stream accounting: all 12 buffered tasks were consumed, even
        # though only 8 entered the attempt window
        interval = summary["evolution"]["trigger_intervals"][0]
        assert interval["tasks"] == 12
        assert interval["observations"] == 3
        assert interval["attempt_tasks"] == 8
        assert interval["attempt_observations"] == 2

        # the attempt log entry carries the enriched facts (fixes 1B/2B):
        # candidate score + the optimizer's actual edits. Accepted: the
        # proposed edits are also the applied ones.
        entry = summary["evolution"]["attempt_log"][0]
        assert entry["validation"] == "accepted"
        assert entry["candidate_score"] == 1.0
        assert isinstance(entry["edits_proposed"], list) and entry["edits_proposed"]
        assert entry["edits_applied"] == entry["edits_proposed"]
        assert isinstance(entry["base_skill"], str) and entry["base_skill"]
        assert isinstance(entry["trigger_state"], dict)
        # stream position counts all consumed tasks
        assert entry["tasks_consumed"] == 12

    def test_all_failure_free_buffer_falls_back_to_whole_window(
        self, tmp_path, monkeypatch
    ):
        # Skill pre-filled with MAGIC: every observation is failure-free;
        # the fallback must keep the whole buffer (upstream behaviour),
        # and the attempt still runs (and is rejected — current already
        # scores perfectly).
        _install_policy(monkeypatch, ScriptedPolicy([WAIT, WAIT, UPDATE]))
        skill_init = tmp_path / "init.md"
        skill_init.write_text(f"base skill with {MAGIC}\n")
        cfg = _make_cfg(
            tmp_path,
            evolution_mode="controller",
            observation_batch_size=4,
            skill_init=str(skill_init),
        )
        summary = ReflACTTrainer(cfg, FakeAdapter()).train()
        history = json.load(open(os.path.join(cfg["out_root"], "history.json")))
        rec = history[0]
        assert rec["evolution"]["n_observations"] == 3
        assert rec["evolution"]["window_tasks"] == 12
        assert rec["evolution"]["dropped_zero_failure_observations"] == 0
        assert rec["rollout_n"] == 12
        assert rec["action"] == "reject"

        # rejected attempts also carry the enriched facts — and are honest
        # about the edits: proposed, but rolled back (never applied)
        entry = summary["evolution"]["attempt_log"][0]
        assert entry["validation"] == "rejected"
        assert entry["candidate_score"] == 1.0  # candidate ties current → reject
        assert isinstance(entry["edits_proposed"], list)
        assert entry["edits_applied"] == []

    def test_attempt_log_enrichment_persisted_for_resume(self, tmp_path, monkeypatch):
        # The enriched attempt log survives in evolution_state.json, so a
        # resumed run feeds the same facts back to the controller.
        _install_policy(monkeypatch, ScriptedPolicy([WAIT, WAIT, UPDATE]))
        adapter = ObsScriptedAdapter()
        cfg = _make_cfg(tmp_path, evolution_mode="controller", observation_batch_size=4)
        ReflACTTrainer(cfg, adapter).train()
        state = json.load(open(os.path.join(cfg["out_root"], "evolution_state.json")))
        log = state["attempt_log"]
        assert len(log) == 1
        assert "candidate_score" in log[0]
        assert "edits_proposed" in log[0]
        assert log[0]["edits_proposed"]
        assert "base_skill" in log[0]
        assert "trigger_state" in log[0]

    def test_rejected_attempt_keeps_weakened_hypotheses(self, tmp_path, monkeypatch):
        # Outcome-aware reset: after a REJECT the skill is unchanged, so the
        # controller's hypotheses carry over as weakened (magnitude memory
        # in prior_* fields) instead of being wiped.
        _install_policy(monkeypatch, ScriptedPolicy([WAIT, WAIT, UPDATE]))
        skill_init = tmp_path / "init.md"
        skill_init.write_text(f"base skill with {MAGIC}\n")
        cfg = _make_cfg(
            tmp_path,
            evolution_mode="controller",
            observation_batch_size=4,
            skill_init=str(skill_init),
        )
        ReflACTTrainer(cfg, FakeAdapter()).train()
        state = json.load(open(os.path.join(cfg["out_root"], "evolution_state.json")))
        assert state["attempt_log"][0]["validation"] == "rejected"
        hyps = state["evidence_state"]["hypotheses"]
        assert hyps, "rejected attempt must carry hypotheses forward"
        assert hyps[0]["defect"] == "scripted"
        assert hyps[0]["status"] == "weakened"
        assert hyps[0]["support_count"] == 0
        # the attempt log also froze the trigger-time state
        assert state["attempt_log"][0]["trigger_state"]["hypotheses"]




class TestFixedScheduleBaselines:
    def test_immediate_matches_original_schedule(self, tmp_path):
        # immediate with m=4: 12 train tasks / 4 = 3 attempts per epoch —
        # the same cadence as the original fixed schedule with batch_size=4.
        cfg = _make_cfg(tmp_path, evolution_mode="immediate", observation_batch_size=4)
        summary = ReflACTTrainer(cfg, FakeAdapter()).train()
        assert summary["evolution"]["policy"] == "immediate"
        assert summary["evolution"]["total_attempts"] == 3
        assert [t["tasks"] for t in summary["evolution"]["trigger_intervals"]] == [4, 4, 4]

    def test_fixed_k_accumulates_k_observations(self, tmp_path):
        cfg = _make_cfg(tmp_path, evolution_mode="fixed_k", observation_batch_size=4, evolution_fixed_k=2)
        summary = ReflACTTrainer(cfg, FakeAdapter()).train()
        # 3 observations / K=2 → 1 attempt with a 2-observation window;
        # the 3rd observation remains buffered (carries over).
        assert summary["evolution"]["total_attempts"] == 1
        assert summary["evolution"]["trigger_intervals"][0]["tasks"] == 8
        assert summary["evolution"]["leftover_buffer_observations"] == 1

    def test_end_policy_updates_once_per_epoch(self, tmp_path):
        cfg = _make_cfg(tmp_path, evolution_mode="end", observation_batch_size=4, num_epochs=2)
        summary = ReflACTTrainer(cfg, FakeAdapter()).train()
        assert summary["evolution"]["total_attempts"] == 2
        assert all(
            t["tasks"] == 12 for t in summary["evolution"]["trigger_intervals"]
        )


# ── Fixed mode (original) still works and co-exists ─────────────────────────


class TestOriginalFixedMode:
    def test_fixed_mode_runs_original_loop(self, tmp_path):
        cfg = _make_cfg(tmp_path, evolution_mode="fixed", batch_size=4)
        summary = ReflACTTrainer(cfg, FakeAdapter()).train()
        assert summary["evolution"] is None
        history = json.load(open(os.path.join(cfg["out_root"], "history.json")))
        assert len(history) == 3  # 12 tasks / batch_size 4
        # original layout: rollouts live under steps/step_XXXX/rollout
        assert os.path.exists(os.path.join(cfg["out_root"], "steps", "step_0001", "rollout"))
        # no evolution artifacts in fixed mode
        assert not os.path.exists(os.path.join(cfg["out_root"], "evolution_decisions.jsonl"))
        assert not os.path.exists(os.path.join(cfg["out_root"], "observations"))

    def test_fixed_mode_with_accumulation(self, tmp_path):
        cfg = _make_cfg(
            tmp_path, evolution_mode="fixed", batch_size=2, accumulation=2,
        )
        summary = ReflACTTrainer(cfg, FakeAdapter()).train()
        history = json.load(open(os.path.join(cfg["out_root"], "history.json")))
        assert len(history) == 3
        # accumulation=2 → each attempt consumed 2 batches of 2 tasks
        assert all(rec["rollout_n"] == 4 for rec in history)
        assert all(len(rec["accumulation_batches"]) == 2 for rec in history)


# ── Resume ───────────────────────────────────────────────────────────────────


class TestEvolutionResume:
    def test_resume_replays_stream_without_repetition(self, tmp_path, monkeypatch):
        # Run 1: WAIT once, then UPDATE on obs 2, then WAIT on obs 3 and
        # stop the run mid-stream by faking num_epochs... instead: run a
        # full run, then rerun the trainer on the same out_root and assert
        # it skips every completed observation and attempt (idempotence).
        _install_policy(monkeypatch, ScriptedPolicy([WAIT, UPDATE, WAIT]))
        cfg = _make_cfg(tmp_path, evolution_mode="controller", observation_batch_size=4)
        out_root = cfg["out_root"]
        s1 = ReflACTTrainer(cfg, FakeAdapter()).train()
        assert s1["evolution"]["total_attempts"] == 1
        assert s1["evolution"]["total_observations"] == 3

        # Rerun: policy is fresh (all WAIT) but the stream is complete —
        # no new observations may run and no new decisions may be logged.
        n_decisions_before = sum(
            1 for _ in open(os.path.join(out_root, "evolution_decisions.jsonl"))
        )
        _install_policy(monkeypatch, ScriptedPolicy([]))
        cfg2 = _make_cfg(
            tmp_path, evolution_mode="controller", observation_batch_size=4,
        )
        cfg2["out_root"] = out_root
        s2 = ReflACTTrainer(cfg2, FakeAdapter()).train()
        assert s2["evolution"]["total_observations"] == 3  # unchanged
        n_decisions_after = sum(
            1 for _ in open(os.path.join(out_root, "evolution_decisions.jsonl"))
        )
        assert n_decisions_after == n_decisions_before
        # the rerun must not add attempts
        assert s2["evolution"]["total_attempts"] == 1

    def test_pending_update_decision_executed_on_resume(self, tmp_path, monkeypatch):
        # Simulate a crash after an UPDATE decision but before the attempt:
        # run with a policy that UPDATEs on obs 3 (epoch end not reached),
        # then hand-craft the crash by truncating history after the run.
        _install_policy(monkeypatch, ScriptedPolicy([WAIT, WAIT, UPDATE]))
        cfg = _make_cfg(tmp_path, evolution_mode="controller", observation_batch_size=4)
        out_root = cfg["out_root"]
        ReflACTTrainer(cfg, FakeAdapter()).train()

        # Reconstruct the "crashed" state: attempt 1 never completed.
        state = json.load(open(os.path.join(out_root, "evolution_state.json")))
        history = json.load(open(os.path.join(out_root, "history.json")))
        assert state["buffer"] == []  # completed attempt reset the buffer

        # Simulate: attempt not completed → buffer still held 3 observations
        # and pending_decision was UPDATE. We rebuild that state from the
        # persisted observation artifacts and assert resume executes it.
        crash_state = dict(state)
        crash_state["buffer"] = [
            {
                "obs_index": i,
                "epoch": 1,
                "obs_in_epoch": i,
                "batch_seed": 42 + i,
                "n_envs": 4,
                "dir": os.path.relpath(
                    os.path.join(out_root, "observations", f"obs_{i:05d}"), out_root
                ),
                "hard": 0.0,
                "soft": 0.0,
                "ids": [f"train_{j}" for j in range(4)],
            }
            for i in (1, 2, 3)
        ]
        crash_state["evidence_state"] = {"hypotheses": [], "unresolved": "crash"}
        crash_state["pending_decision"] = {
            "action": "UPDATE",
            "trigger": "controller",
            "reason": "crashed before attempt",
            "epoch": 1,
            "epoch_end": False,
            "attempt_step": 1,
        }
        crash_state["global_obs_index"] = 3
        # The attempt never completed, so the crash-time counters must
        # reflect that (a real crash would have persisted this state at the
        # UPDATE decision, before the attempt ran).
        crash_state["total_attempts"] = 0
        crash_state["total_decisions"] = 3
        crash_state["trigger_intervals"] = []
        with open(os.path.join(out_root, "evolution_state.json"), "w") as f:
            json.dump(crash_state, f)
        # Roll back attempt bookkeeping to "nothing completed".
        with open(os.path.join(out_root, "history.json"), "w") as f:
            json.dump([], f)
        import shutil
        shutil.rmtree(os.path.join(out_root, "steps"))
        os.remove(os.path.join(out_root, "runtime_state.json"))
        shutil.rmtree(os.path.join(out_root, "skills"), ignore_errors=True)
        for name in ("best_skill.md", "summary.json"):
            p = os.path.join(out_root, name)
            if os.path.exists(p):
                os.remove(p)

        # Resume: the pending UPDATE must execute with the rebuilt buffer.
        _install_policy(monkeypatch, ScriptedPolicy([]))
        cfg2 = _make_cfg(
            tmp_path, evolution_mode="controller", observation_batch_size=4,
        )
        cfg2["out_root"] = out_root
        s2 = ReflACTTrainer(cfg2, FakeAdapter()).train()
        # stream was already exhausted (obs 3 of 3) → only the pending
        # attempt ran; it consumed the 3 rebuilt observations
        history2 = json.load(open(os.path.join(out_root, "history.json")))
        assert len(history2) == 1
        assert history2[0]["evolution"]["n_observations"] == 3
        assert history2[0]["step"] == 1
        assert s2["evolution"]["total_attempts"] == 1

    def test_resume_pending_attempt_already_completed(self, tmp_path, monkeypatch):
        # Crash AFTER the attempt completed but BEFORE the state reset:
        # pending_decision still says UPDATE. Resume must discard it
        # instead of re-running the attempt.
        _install_policy(monkeypatch, ScriptedPolicy([WAIT, WAIT, UPDATE]))
        cfg = _make_cfg(tmp_path, evolution_mode="controller", observation_batch_size=4)
        out_root = cfg["out_root"]
        ReflACTTrainer(cfg, FakeAdapter()).train()

        state = json.load(open(os.path.join(out_root, "evolution_state.json")))
        state["pending_decision"] = {
            "action": "UPDATE", "trigger": "controller", "reason": "x",
            "epoch": 1, "epoch_end": False, "attempt_step": 1,
        }
        with open(os.path.join(out_root, "evolution_state.json"), "w") as f:
            json.dump(state, f)

        _install_policy(monkeypatch, ScriptedPolicy([]))
        cfg2 = _make_cfg(
            tmp_path, evolution_mode="controller", observation_batch_size=4,
        )
        cfg2["out_root"] = out_root
        s2 = ReflACTTrainer(cfg2, FakeAdapter()).train()
        # still exactly one attempt in history; no duplicate attempt ran
        history = json.load(open(os.path.join(out_root, "history.json")))
        assert len(history) == 1
        assert s2["evolution"]["total_attempts"] == 1


# ── Config plumbing inside the trainer ───────────────────────────────────────


class TestTrainerConfigPlumbing:
    def test_invalid_observation_batch_size_rejected(self, tmp_path):
        cfg = _make_cfg(tmp_path, evolution_mode="controller", observation_batch_size=0)
        with pytest.raises(ValueError, match="observation_batch_size"):
            ReflACTTrainer(cfg, FakeAdapter()).train()

    def test_unknown_mode_rejected(self, tmp_path):
        cfg = _make_cfg(tmp_path, evolution_mode="sometimes")
        with pytest.raises(ValueError, match="evolution.mode"):
            ReflACTTrainer(cfg, FakeAdapter()).train()

    def test_controller_attempts_numbered_like_steps(self, tmp_path, monkeypatch):
        _install_policy(monkeypatch, ScriptedPolicy([UPDATE, UPDATE, UPDATE]))
        cfg = _make_cfg(tmp_path, evolution_mode="controller", observation_batch_size=4)
        ReflACTTrainer(cfg, FakeAdapter()).train()
        for step in (1, 2, 3):
            assert os.path.exists(
                os.path.join(cfg["out_root"], "steps", f"step_{step:04d}", "step_record.json")
            )
