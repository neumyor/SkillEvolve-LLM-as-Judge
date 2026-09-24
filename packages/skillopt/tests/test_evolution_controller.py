"""Tests for skillopt.evolution_controller — the Evolution Controller Agent.

Zero LLM dependencies for the fixed-schedule policies (Immediate / FixedK /
End): all behaviour is deterministic counting. The LLM policy is exercised
through an injected ``chat_fn`` stub, covering the WAIT/UPDATE parsing, the
semantic vs score evidence views, state sanitisation/clipping, and the
fallback-to-WAIT behaviour on unparseable responses.

Controller contract
-------------------
- observe() is called once per observation batch and once per epoch boundary
  (epoch_end=True, new_results=[]); the decision is WAIT or UPDATE.
- The evidence state is JSON-serializable and passed back on the next call.
- No numeric thresholds: the fixed policies count observation batches; the
  LLM policy is a pure semantic judge over the rendered evidence.
"""
from __future__ import annotations

import json
import os

import pytest

from skillopt.evolution_controller import (
    WAIT,
    UPDATE,
    EndPolicy,
    EvolutionDecision,
    FixedKPolicy,
    ImmediatePolicy,
    LLMEvidencePolicy,
    build_evolution_policy,
    format_observation_card,
    load_trajectory_excerpt,
    normalize_evolution_mode,
)


def _results(outcomes: list[int]) -> list[dict]:
    """Rollout results with hard=1 (success) / 0 (failure) per outcome."""
    return [
        {
            "id": f"task_{i}",
            "hard": outcome,
            "soft": float(outcome),
            "task_type": "qa",
            "task_description": f"question {i}",
            "fail_reason": "" if outcome else "EM=0: predicted 'x' but expected ['y']",
        }
        for i, outcome in enumerate(outcomes)
    ]


# ── EvolutionDecision ────────────────────────────────────────────────────────


class TestEvolutionDecision:
    def test_normalizes_action_case(self) -> None:
        d = EvolutionDecision(action="update", state={})
        assert d.action == UPDATE
        assert d.is_update

    def test_rejects_unknown_action(self) -> None:
        with pytest.raises(ValueError, match="WAIT.*UPDATE"):
            EvolutionDecision(action="maybe", state={})


# ── ImmediatePolicy ──────────────────────────────────────────────────────────


class TestImmediatePolicy:
    def test_updates_after_every_observation(self) -> None:
        p = ImmediatePolicy()
        state = p.initial_state()
        d = p.observe("skill", _results([0, 1]), state)
        assert d.action == UPDATE
        assert d.state["observations_since_attempt"] == 1

    def test_waits_with_no_new_results(self) -> None:
        p = ImmediatePolicy()
        d = p.observe("skill", [], p.initial_state(), epoch_end=True)
        assert d.action == WAIT


# ── FixedKPolicy ─────────────────────────────────────────────────────────────


class TestFixedKPolicy:
    def test_waits_until_k_observations(self) -> None:
        p = FixedKPolicy(k=3)
        state = p.initial_state()
        d1 = p.observe("skill", _results([0]), state)
        assert d1.action == WAIT
        d2 = p.observe("skill", _results([0]), d1.state)
        assert d2.action == WAIT
        assert d2.state["observations_since_attempt"] == 2
        d3 = p.observe("skill", _results([0]), d2.state)
        assert d3.action == UPDATE
        assert d3.state["observations_since_attempt"] == 3

    def test_epoch_end_partial_window_carries_over(self) -> None:
        p = FixedKPolicy(k=3)
        state = p.initial_state()
        state = p.observe("skill", _results([0]), state).state
        state = p.observe("skill", _results([0]), state).state
        # epoch boundary with a 2/3 window: no trigger, window carries over
        d = p.observe("skill", [], state, epoch_end=True)
        assert d.action == WAIT
        assert d.state["observations_since_attempt"] == 2

    def test_epoch_end_full_window_triggers(self) -> None:
        p = FixedKPolicy(k=2)
        state = p.initial_state()
        state = p.observe("skill", _results([0]), state).state
        state = p.observe("skill", _results([0]), state).state
        d = p.observe("skill", [], state, epoch_end=True)
        assert d.action == UPDATE

    def test_rejects_invalid_k(self) -> None:
        with pytest.raises(ValueError, match="fixed_k"):
            FixedKPolicy(k=0)


# ── EndPolicy ────────────────────────────────────────────────────────────────


class TestEndPolicy:
    def test_waits_during_epoch(self) -> None:
        p = EndPolicy()
        state = p.initial_state()
        state = p.observe("skill", _results([0]), state).state
        d = p.observe("skill", _results([0]), state)
        assert d.action == WAIT

    def test_updates_at_epoch_end_with_evidence(self) -> None:
        p = EndPolicy()
        state = p.initial_state()
        state = p.observe("skill", _results([0, 0]), state).state
        d = p.observe("skill", [], state, epoch_end=True)
        assert d.action == UPDATE
        assert d.state["observations_since_attempt"] == 1

    def test_waits_at_epoch_end_without_evidence(self) -> None:
        p = EndPolicy()
        d = p.observe("skill", [], p.initial_state(), epoch_end=True)
        assert d.action == WAIT


# ── mode normalization + factory ─────────────────────────────────────────────


class TestModeNormalization:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("fixed", "fixed"),
            ("default", "fixed"),
            ("", "fixed"),
            (None, "fixed"),
            ("immediate", "immediate"),
            ("per_observation", "immediate"),
            ("fixed_k", "fixed_k"),
            ("k", "fixed_k"),
            ("end", "end"),
            ("per_epoch", "end"),
            ("controller", "controller"),
            ("llm", "controller"),
            ("ete", "controller"),
        ],
    )
    def test_aliases(self, raw, expected) -> None:
        assert normalize_evolution_mode(raw) == expected

    def test_unknown_mode_raises(self) -> None:
        with pytest.raises(ValueError, match="evolution.mode"):
            normalize_evolution_mode("sometimes")

    def test_factory_fixed_raises(self) -> None:
        with pytest.raises(ValueError, match="fixed"):
            build_evolution_policy({"evolution_mode": "fixed"})

    def test_factory_builds_each_policy(self) -> None:
        assert isinstance(
            build_evolution_policy({"evolution_mode": "immediate"}), ImmediatePolicy
        )
        assert isinstance(
            build_evolution_policy({"evolution_mode": "fixed_k", "evolution_fixed_k": 4}),
            FixedKPolicy,
        )
        assert isinstance(build_evolution_policy({"evolution_mode": "end"}), EndPolicy)
        assert isinstance(
            build_evolution_policy({"evolution_mode": "controller"}),
            LLMEvidencePolicy,
        )

    def test_factory_passes_controller_options(self) -> None:
        p = build_evolution_policy(
            {
                "evolution_mode": "controller",
                "evolution_controller_view": "score",
                "evolution_controller_max_state_chars": 1000,
            }
        )
        assert p.view == "score"
        assert p.max_state_chars == 1000


# ── evidence cards ───────────────────────────────────────────────────────────


class TestObservationCards:
    def test_semantic_card_contains_evidence(self, tmp_path) -> None:
        # trajectory artifact exactly where the reflect stage reads it
        pred_dir = tmp_path / "rollout" / "predictions" / "task_0"
        pred_dir.mkdir(parents=True)
        (pred_dir / "conversation.json").write_text(
            json.dumps([{"role": "agent", "content": "I answered x"}]),
            encoding="utf-8",
        )
        result = _results([0])[0]
        card = format_observation_card(
            result, str(tmp_path / "rollout"), max_chars=500, view="semantic",
        )
        assert "### Task task_0" in card
        assert "Outcome: failure" in card
        assert "Evaluator feedback:" in card
        assert "I answered x" in card  # trajectory excerpt surfaced
        assert "EM=0" in card

    def test_score_card_strips_content(self, tmp_path) -> None:
        pred_dir = tmp_path / "rollout" / "predictions" / "task_0"
        pred_dir.mkdir(parents=True)
        (pred_dir / "conversation.json").write_text(
            json.dumps([{"role": "agent", "content": "secret reasoning"}]),
            encoding="utf-8",
        )
        result = _results([0])[0]
        card = format_observation_card(
            result, str(tmp_path / "rollout"), max_chars=500, view="score",
        )
        assert card == "- task_0: failure (score 0.000)"
        assert "secret reasoning" not in card
        assert "question 0" not in card
        assert "EM=0" not in card

    def test_missing_trajectory_degrades_gracefully(self, tmp_path) -> None:
        card = format_observation_card(
            _results([1])[0], str(tmp_path), max_chars=100, view="semantic",
        )
        assert "Outcome: success" in card
        assert "Trajectory excerpt" not in card

    def test_load_trajectory_excerpt_clips(self, tmp_path) -> None:
        pred_dir = tmp_path / "predictions" / "t1"
        pred_dir.mkdir(parents=True)
        (pred_dir / "conversation.json").write_text(
            json.dumps([{"role": "agent", "content": "x" * 5000}]),
            encoding="utf-8",
        )
        excerpt = load_trajectory_excerpt(str(tmp_path), "t1", max_chars=100)
        assert len(excerpt) <= 120
        assert excerpt.endswith("…[truncated]")

    def test_invalid_view_raises(self, tmp_path) -> None:
        with pytest.raises(ValueError, match="evidence card view"):
            format_observation_card(
                _results([1])[0], str(tmp_path), view="everything",
            )


# ── LLMEvidencePolicy ────────────────────────────────────────────────────────


def _controller_json(decision: str, defect: str = "", unresolved: str = "") -> str:
    return json.dumps(
        {
            "decision": decision,
            "evidence_state": {
                "hypotheses": [
                    {
                        "defect": defect or "skill lacks X",
                        "support_count": 2,
                        "contradiction_count": 0,
                        "supporting_cases": ["task_0"],
                        "contradicting_cases": [],
                        "status": "active",
                        "assessment": "recurring",
                    }
                ],
                "unresolved": unresolved,
            },
            "reason": "because of Y",
        }
    )


class StubChat:
    """chat_optimizer-compatible stub returning queued responses."""

    def __init__(self, responses: list[str]) -> None:
        self.responses = list(responses)
        self.calls: list[dict] = []

    def __call__(self, *, system, user, **kwargs):
        self.calls.append({"system": system, "user": user, **kwargs})
        if not self.responses:
            raise AssertionError("stub chat exhausted")
        return self.responses.pop(0), {"total_tokens": 1}


class TestLLMEvidencePolicy:
    def _policy(self, stub: StubChat, **kwargs) -> LLMEvidencePolicy:
        # min_window_tasks=0: these tests exercise the prompt/parse contract,
        # not the deterministic window gate (see test_evolution_controller_v4).
        kwargs.setdefault("min_window_tasks", 0)
        return LLMEvidencePolicy(chat_fn=stub, **kwargs)

    def test_parses_update_decision(self) -> None:
        stub = StubChat([_controller_json("UPDATE", defect="no recovery step")])
        p = self._policy(stub)
        d = p.observe("the skill", _results([0, 0, 0]), p.initial_state())
        assert d.action == UPDATE
        assert d.state["hypotheses"][0]["defect"] == "no recovery step"
        assert d.reason == "because of Y"
        assert d.meta["policy"] == "controller"

    def test_parses_wait_decision_and_updates_state(self) -> None:
        stub = StubChat([_controller_json("WAIT", unresolved="need more cases")])
        p = self._policy(stub)
        d = p.observe("the skill", _results([0]), p.initial_state())
        assert d.action == WAIT
        assert d.state["unresolved"] == "need more cases"

    def test_prompt_contains_skill_state_and_evidence(self, tmp_path) -> None:
        pred_dir = tmp_path / "rollout" / "predictions" / "task_0"
        pred_dir.mkdir(parents=True)
        (pred_dir / "conversation.json").write_text(
            json.dumps([{"role": "agent", "content": "agent reasoning here"}]),
            encoding="utf-8",
        )
        stub = StubChat([_controller_json("WAIT")])
        p = self._policy(stub)
        state = p.initial_state()
        state["hypotheses"].append(
            {"defect": "prior hypothesis", "supporting_cases": ["a"], "counter_cases": [], "assessment": "s"}
        )
        p.observe(
            "MY CURRENT SKILL", _results([0])[0:1], state,
            rollout_dir=str(tmp_path / "rollout"),
        )
        user = stub.calls[0]["user"]
        system = stub.calls[0]["system"]
        assert "MY CURRENT SKILL" in user
        assert "prior hypothesis" in user  # previous evidence state rendered
        assert "agent reasoning here" in user  # trajectory excerpt
        assert "EM=0" in user  # evaluator feedback
        # core principles
        for principle in (
            "NOT to improve or rewrite",
            "UPDATE when the current evidence supports",
            "WAIT when the evidence is isolated",
            "Do not propose the actual skill modification",
        ):
            assert principle in system

    def test_score_view_omits_semantic_content(self, tmp_path) -> None:
        pred_dir = tmp_path / "rollout" / "predictions" / "task_0"
        pred_dir.mkdir(parents=True)
        (pred_dir / "conversation.json").write_text(
            json.dumps([{"role": "agent", "content": "agent reasoning here"}]),
            encoding="utf-8",
        )
        stub = StubChat([_controller_json("WAIT")])
        p = self._policy(stub, view="score")
        state = {"hypotheses": [{"defect": "prior hypothesis"}], "unresolved": ""}
        p.observe(
            "MY CURRENT SKILL", _results([0])[0:1], state,
            rollout_dir=str(tmp_path / "rollout"),
            context={"buffer_observations": 3, "buffer_tasks": 12},
        )
        user = stub.calls[0]["user"]
        assert "MY CURRENT SKILL" not in user
        assert "agent reasoning here" not in user
        assert "EM=0" not in user
        assert "question 0" not in user
        assert "prior hypothesis" not in user
        assert "failure" in user  # outcome rows remain
        assert "12" in user  # cumulative window stats remain

    def test_epoch_end_consult_renders_boundary_note(self) -> None:
        stub = StubChat([_controller_json("WAIT")])
        p = self._policy(stub)
        p.observe("skill", [], p.initial_state(), epoch_end=True)
        assert "epoch boundary" in stub.calls[0]["user"] or "exhausted" in stub.calls[0]["user"]

    def test_unparseable_response_retries_then_falls_back_to_wait(self) -> None:
        stub = StubChat(["garbage not json", "still not json", "irrelevant"])
        p = self._policy(stub, max_parse_retries=2)
        state = p.initial_state()
        state["unresolved"] = "keep me"
        d = p.observe("skill", _results([0]), state)
        assert d.action == WAIT
        assert len(stub.calls) == 3  # 1 + 2 retries
        assert d.state["unresolved"] == "keep me"  # state unchanged on fallback
        assert d.meta.get("fallback") is True

    def test_chat_exception_falls_back_to_wait(self) -> None:
        def boom(**kwargs):
            raise RuntimeError("backend down")

        p = LLMEvidencePolicy(chat_fn=boom, max_parse_retries=1, min_window_tasks=0)
        d = p.observe("skill", _results([0]), p.initial_state())
        assert d.action == WAIT
        assert d.meta.get("fallback") is True

    def test_invalid_action_treated_as_parse_failure(self) -> None:
        stub = StubChat(
            [
                json.dumps({"decision": "MAYBE", "evidence_state": {}, "reason": "x"}),
                _controller_json("WAIT"),
            ]
        )
        p = self._policy(stub, max_parse_retries=1)
        d = p.observe("skill", _results([0]), p.initial_state())
        assert d.action == WAIT
        assert len(stub.calls) == 2

    def test_state_normalization_clips_and_bounds(self) -> None:
        huge_state = {
            "hypotheses": [
                {"defect": "d" * 5000, "supporting_cases": ["c"] * 50, "counter_cases": [], "assessment": "a" * 5000}
                for _ in range(20)
            ],
            "unresolved": "u" * 5000,
        }
        stub = StubChat(
            [json.dumps({"decision": "WAIT", "evidence_state": huge_state, "reason": "r"})]
        )
        p = self._policy(stub, max_state_chars=800)
        d = p.observe("skill", _results([0]), p.initial_state())
        serialized = json.dumps(d.state)
        assert len(serialized) <= 800 + 200  # bounded (small slop for the dropper)
        assert len(d.state["hypotheses"]) <= 10
        for hyp in d.state["hypotheses"]:
            assert len(hyp["defect"]) <= 410
            assert len(hyp["assessment"]) <= 410

    def test_non_dict_state_normalizes_to_initial(self) -> None:
        stub = StubChat(
            [json.dumps({"decision": "WAIT", "evidence_state": "garbage", "reason": "r"})]
        )
        p = self._policy(stub)
        d = p.observe("skill", _results([0]), p.initial_state())
        # hypotheses/unresolved clean; counters advanced deterministically
        assert d.state["hypotheses"] == []
        assert d.state["unresolved"] == ""
        assert d.state["tasks_since_last_attempt"] == 1
        assert d.state["failures_since_last_attempt"] == 1

    def test_initial_state_shape(self) -> None:
        p = LLMEvidencePolicy(chat_fn=StubChat([]))
        assert p.initial_state() == {
            "hypotheses": [],
            "tasks_since_last_attempt": 0,
            "failures_since_last_attempt": 0,
            "consecutive_rejects": 0,
            "unresolved": "",
        }
        # JSON-serializable (must round-trip through evolution_state.json)
        json.dumps(p.initial_state())

    def test_counters_advance_deterministically(self) -> None:
        # The LLM reports nonsense counts; the policy's arithmetic wins.
        stub = StubChat(
            [json.dumps({
                "decision": "WAIT",
                "evidence_state": {
                    "hypotheses": [],
                    "tasks_since_last_attempt": 9999,
                    "failures_since_last_attempt": -5,
                    "unresolved": "",
                },
                "reason": "r",
            })]
        )
        p = self._policy(stub)
        state = p.initial_state()
        state["tasks_since_last_attempt"] = 7
        state["failures_since_last_attempt"] = 3
        d = p.observe("skill", _results([0, 1, 0]), state)
        assert d.action == WAIT
        assert d.state["tasks_since_last_attempt"] == 10
        assert d.state["failures_since_last_attempt"] == 5

    def test_counters_advance_even_on_fallback(self) -> None:
        def boom(**kwargs):
            raise RuntimeError("backend down")

        p = LLMEvidencePolicy(chat_fn=boom, max_parse_retries=0)
        state = p.initial_state()
        state["tasks_since_last_attempt"] = 4
        state["failures_since_last_attempt"] = 1
        d = p.observe("skill", _results([0, 0]), state)
        assert d.action == WAIT
        assert d.meta.get("fallback") is True
        # hypotheses untouched, counters still moved
        assert d.state["tasks_since_last_attempt"] == 6
        assert d.state["failures_since_last_attempt"] == 3

    def test_epoch_end_consult_advances_no_counters(self) -> None:
        stub = StubChat([_controller_json("WAIT")])
        p = self._policy(stub)
        state = p.initial_state()
        state["tasks_since_last_attempt"] = 12
        state["failures_since_last_attempt"] = 5
        d = p.observe("skill", [], state, epoch_end=True)
        assert d.state["tasks_since_last_attempt"] == 12
        assert d.state["failures_since_last_attempt"] == 5

    def test_stage_is_tracked_for_token_accounting(self) -> None:
        stub = StubChat([_controller_json("WAIT")])
        p = self._policy(stub)
        p.observe("skill", _results([0]), p.initial_state())
        assert stub.calls[0].get("stage") == "evolution_controller"


class TestAttemptMemory:
    """The controller must remember what it actually tried (trigger evidence
    → optimizer edits → verifier verdict); without that it re-triggers on
    the same rejected deficiency."""

    def test_attempt_history_is_rendered(self) -> None:
        stub = StubChat([_controller_json("WAIT")])
        p = LLMEvidencePolicy(chat_fn=stub, min_window_tasks=0)
        p.observe(
            "skill", _results([0]), p.initial_state(),
            context={
                "buffer_observations": 2,
                "buffer_tasks": 8,
                "attempt_history": [
                    {
                        "attempt": 1,
                        "tasks_consumed": 28,
                        "trigger": "controller",
                        "targeted_defect": "answers are over-specified",
                        "validation": "rejected",
                        "val_before": 0.475,
                        "val_after": 0.475,
                    }
                ],
            },
        )
        user = stub.calls[0]["user"]
        assert "Previous Evolution Attempts" in user
        assert "over-specified" in user
        assert "Verifier: REJECTED" in user
        assert "does not invalidate the trigger hypothesis" in user

    def test_attempt_memory_off_omits_history(self) -> None:
        stub = StubChat([_controller_json("WAIT")])
        p = LLMEvidencePolicy(chat_fn=stub, attempt_memory=False, min_window_tasks=0)
        p.observe(
            "skill", _results([0]), p.initial_state(),
            context={"attempt_history": [{"attempt": 1, "targeted_defect": "x",
                                          "validation": "rejected", "tasks_consumed": 4,
                                          "trigger": "controller", "val_before": 0.5,
                                          "val_after": 0.5}]},
        )
        user = stub.calls[0]["user"]
        assert "Previous Evolution Attempts" not in user

    def test_no_history_block_when_empty(self) -> None:
        stub = StubChat([_controller_json("WAIT")])
        p = LLMEvidencePolicy(chat_fn=stub, min_window_tasks=0)
        p.observe("skill", _results([0]), p.initial_state(), context={"attempt_history": []})
        assert "Previous Evolution Attempts" not in stub.calls[0]["user"]

    def test_prompt_principle_present(self) -> None:
        stub = StubChat([_controller_json("WAIT")])
        p = LLMEvidencePolicy(chat_fn=stub, min_window_tasks=0)
        p.observe("skill", _results([0]), p.initial_state())
        system = stub.calls[0]["system"]
        assert "A rejected candidate is NOT evidence against" in system
        assert "Evidence State tells you what is currently supported" in system

    def test_attempt_facts_gate_delta_and_edits_rendered(self) -> None:
        # Enriched attempt entries: the controller sees how far each
        # rejected candidate was from the current skill and what the
        # optimizer actually edited, not only its own defect wording.
        stub = StubChat([_controller_json("WAIT")])
        p = LLMEvidencePolicy(chat_fn=stub, min_window_tasks=0)
        p.observe(
            "skill", _results([0]), p.initial_state(),
            context={
                "attempt_history": [
                    {
                        "attempt": 2,
                        "tasks_consumed": 36,
                        "trigger": "controller",
                        "targeted_defect": "over-specification",
                        "validation": "rejected",
                        "val_before": 0.62,
                        "val_after": 0.62,
                        "candidate_score": 0.56,
                        "edits_proposed": [
                            "replace: **Implicit Query Handling**",
                            "append: prefer the surname only",
                        ],
                        "edits_applied": [],
                    },
                    {
                        "attempt": 3,
                        "tasks_consumed": 40,
                        "trigger": "controller",
                        "targeted_defect": "name granularity",
                        "validation": "accepted",
                        "val_before": 0.62,
                        "val_after": 0.69,
                        "candidate_score": 0.69,
                        "edits_proposed": ["append: prefer the surname only"],
                        "edits_applied": ["append: prefer the surname only"],
                    },
                ],
            },
        )
        user = stub.calls[0]["user"]
        # rejected attempt: negative delta, edits never entered the skill
        assert "Verifier: REJECTED — candidate 0.5600 vs current 0.6200 (delta -0.0600)" in user
        # accepted attempt: positive delta, edits applied
        assert "Verifier: ACCEPTED — candidate 0.6900 vs current 0.6200 (delta +0.0700)" in user
        # the optimizer's actual edits are shown, with honest applied/rolled-back labels
        assert "Optimizer changes (candidate rolled back — the edits never entered the skill): replace: **Implicit Query Handling**; append: prefer the surname only" in user
        assert "Optimizer changes (applied — now part of the current skill): append: prefer the surname only" in user
        # the guidance demands mechanism-level judgement with all three conditions
        assert "materially" in user
        assert "support has not grown" in user

    def test_attempt_facts_absent_renders_legacy_entries(self) -> None:
        # Entries written before the enrichment (no candidate_score /
        # edits_proposed) must render without crashing.
        stub = StubChat([_controller_json("WAIT")])
        p = LLMEvidencePolicy(chat_fn=stub, min_window_tasks=0)
        p.observe(
            "skill", _results([0]), p.initial_state(),
            context={
                "attempt_history": [
                    {
                        "attempt": 1,
                        "tasks_consumed": 28,
                        "trigger": "controller",
                        "targeted_defect": "answers are over-specified",
                        "validation": "rejected",
                        "val_before": 0.475,
                        "val_after": 0.475,
                    }
                ],
            },
        )
        user = stub.calls[0]["user"]
        assert "candidate 0." not in user
        assert "Verifier: REJECTED" in user
        assert "skill score 0.4750 -> 0.4750" in user

    def test_attempt_facts_bad_values_do_not_crash(self) -> None:
        stub = StubChat([_controller_json("WAIT")])
        p = LLMEvidencePolicy(chat_fn=stub, min_window_tasks=0)
        p.observe(
            "skill", _results([0]), p.initial_state(),
            context={
                "attempt_history": [
                    {
                        "attempt": 1,
                        "tasks_consumed": 4,
                        "trigger": "controller",
                        "targeted_defect": "x",
                        "validation": "rejected",
                        "val_before": "n/a",
                        "val_after": "n/a",
                        "candidate_score": None,
                        "edits_applied": ["not-a-dict"],
                    }
                ],
            },
        )
        user = stub.calls[0]["user"]
        assert "Previous Evolution Attempts" in user
        assert "not-a-dict" in user
        assert "candidate 0." not in user

    def test_attempt_three_sections_with_trigger_snapshot(self) -> None:
        # Full new-format entry: frozen trigger evidence, optimizer edits,
        # verifier verdict — three independently labelled sections, and the
        # base skill matched against the current skill identity.
        stub = StubChat([_controller_json("WAIT")])
        p = LLMEvidencePolicy(chat_fn=stub, min_window_tasks=0)
        p.observe(
            "skill", _results([0]), p.initial_state(),
            context={
                "skill_identity": "abcdef1234567890",
                "attempt_history": [
                    {
                        "attempt": 13,
                        "tasks_consumed": 480,
                        "trigger": "controller",
                        "base_skill": "abcdef1234567890",
                        "targeted_defect": "formal-name over-extraction",
                        "trigger_state": {
                            "hypotheses": [
                                {
                                    "defect": "formal-name over-extraction",
                                    "support_count": 8,
                                    "contradiction_count": 1,
                                    "supporting_cases": ["q1"],
                                    "contradicting_cases": ["q8"],
                                    "status": "active",
                                    "assessment": "recurring",
                                }
                            ],
                            "tasks_since_last_attempt": 50,
                            "failures_since_last_attempt": 19,
                            "unresolved": "",
                        },
                        "validation": "rejected",
                        "val_before": 0.785,
                        "val_after": 0.785,
                        "candidate_score": 0.785,
                        "edits_proposed": ["replace: pointer-resolution guidance"],
                        "edits_applied": [],
                    },
                ],
            },
        )
        user = stub.calls[0]["user"]
        assert "Current Skill (identity abcdef12)" in user
        assert "base skill = current skill" in user
        assert "Trigger evidence (1 hypothesis(es) over 50 tasks):" in user
        assert '"formal-name over-extraction" (support 8, contradiction 1)' in user
        assert "Optimizer changes (candidate rolled back — the edits never entered the skill): replace: pointer-resolution guidance" in user
        assert "Verifier: REJECTED — candidate 0.7850 vs current 0.7850 (delta +0.0000)" in user

    def test_attempt_superseded_base_skill_annotated(self) -> None:
        stub = StubChat([_controller_json("WAIT")])
        p = LLMEvidencePolicy(chat_fn=stub, min_window_tasks=0)
        p.observe(
            "skill", _results([0]), p.initial_state(),
            context={
                "skill_identity": "1111222233334444",
                "attempt_history": [
                    {
                        "attempt": 5,
                        "tasks_consumed": 200,
                        "base_skill": "abcdef1234567890",
                        "validation": "rejected",
                        "val_before": 0.5,
                        "val_after": 0.5,
                        "trigger_state": {"hypotheses": []},
                        "edits_proposed": ["append: x"],
                    },
                ],
            },
        )
        user = stub.calls[0]["user"]
        assert "base skill abcdef12 (superseded)" in user

    def test_score_view_attempt_rendering_is_numeric_only(self) -> None:
        # The score-view ablation must not receive semantic attempt content
        # (defect wording, edit targets) — only counts and scores.
        stub = StubChat([_controller_json("WAIT")])
        p = LLMEvidencePolicy(chat_fn=stub, view="score", min_window_tasks=0)
        p.observe(
            "skill", _results([0]), p.initial_state(),
            context={
                "attempt_history": [
                    {
                        "attempt": 13,
                        "tasks_consumed": 480,
                        "targeted_defect": "formal-name over-extraction",
                        "trigger_state": {
                            "hypotheses": [
                                {"defect": "formal-name over-extraction", "support_count": 8}
                            ]
                        },
                        "validation": "rejected",
                        "val_before": 0.785,
                        "val_after": 0.785,
                        "candidate_score": 0.785,
                        "edits_proposed": ["replace: pointer-resolution guidance"],
                    },
                ],
            },
        )
        user = stub.calls[0]["user"]
        assert "Previous Evolution Attempts" in user
        assert "formal-name" not in user
        assert "pointer-resolution" not in user
        assert "candidate 0.785" in user


class TestResetState:
    """Outcome-aware cycle reset: accepted → hard reset; rejected/skipped →
    weakened carry-over with magnitude memory on an unchanged skill."""

    def _trigger_state(self) -> dict:
        return {
            "hypotheses": [
                {
                    "defect": "formal-name over-extraction",
                    "support_count": 8,
                    "contradiction_count": 1,
                    "supporting_cases": ["q1", "q2"],
                    "contradicting_cases": ["q8"],
                    "status": "active",
                    "assessment": "recurring",
                }
            ],
            "tasks_since_last_attempt": 50,
            "failures_since_last_attempt": 19,
            "unresolved": "whether the canonical-name rule is at fault",
        }

    def test_accepted_hard_resets(self) -> None:
        p = LLMEvidencePolicy(chat_fn=StubChat([]))
        state = p.reset_state(outcome="accepted", trigger_state=self._trigger_state())
        assert state == p.initial_state()

    def test_rejected_carries_weakened_hypotheses(self) -> None:
        p = LLMEvidencePolicy(chat_fn=StubChat([]))
        state = p.reset_state(outcome="rejected", trigger_state=self._trigger_state())
        assert state["unresolved"] == "whether the canonical-name rule is at fault"
        assert state["tasks_since_last_attempt"] == 0
        assert state["failures_since_last_attempt"] == 0
        hyp = state["hypotheses"][0]
        assert hyp["defect"] == "formal-name over-extraction"
        assert hyp["status"] == "weakened"
        assert hyp["support_count"] == 0
        assert hyp["supporting_cases"] == []
        assert hyp["prior_support"] == 8
        assert hyp["prior_window_tasks"] == 50

    def test_skipped_keeps_hypotheses_like_rejected(self) -> None:
        p = LLMEvidencePolicy(chat_fn=StubChat([]))
        state = p.reset_state(outcome="skipped", trigger_state=self._trigger_state())
        assert state["hypotheses"][0]["status"] == "weakened"

    def test_missing_trigger_state_hard_resets(self) -> None:
        p = LLMEvidencePolicy(chat_fn=StubChat([]))
        assert p.reset_state(outcome="rejected") == p.initial_state()
        assert p.reset_state(outcome="rejected", trigger_state=None) == p.initial_state()

    def test_fixed_policies_reset_signature_unchanged(self) -> None:
        # The base-class default still accepts the new kwargs.
        p = FixedKPolicy(k=2)
        assert p.reset_state() == p.initial_state()
        assert p.reset_state(outcome="rejected", trigger_state={}) == p.initial_state()
