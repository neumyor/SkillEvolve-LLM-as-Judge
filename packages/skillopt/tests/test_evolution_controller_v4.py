"""V4 — deterministic window gates + contradiction-aware controller rendering.

Covers the three failure modes the V3 run exposed:

FM1  sub-floor windows: 15 of 18 attempts had a window <= 30 tasks and only
     one was accepted; a 10-task window's failure rate carries a ~13pp
     standard error, so those triggers were taken on noise.
FM2  straddling windows: a window whose failures call for opposite
     corrections is evidence the skill contradicts itself, which another
     appended rule cannot fix.
FM3  count-inflation re-triggers: "support grew" was judged on raw counts,
     so three failures in ten tasks repeatedly broke the history block.
"""
from __future__ import annotations

import json

from skillopt.evolution_controller import (
    UPDATE,
    WAIT,
    LLMEvidencePolicy,
    failure_direction,
    summarize_window,
    window_lean,
)

from tests.test_evolution_controller import (
    StubChat,
    _controller_json,
    _results,
)


def _res(task_id: str, hard: float, pred: str, gold: str) -> dict:
    return {
        "id": task_id,
        "hard": hard,
        "soft": float(hard),
        "predicted_answer": pred,
        "gold_answers": [gold],
    }


class TestFailureDirection:
    """``None`` marks a success; a failure with no length mismatch (equal
    word counts) is ``other`` — it is a wrong answer, not a span problem."""

    def test_over_and_under_classification(self) -> None:
        assert failure_direction(_res("a", 0.0, "Sahara Desert", "Sahara")) == "over"
        assert failure_direction(_res("b", 0.0, "Arthur", "Chester A. Arthur")) == "under"
        assert failure_direction(_res("c", 1.0, "Sparta", "Sparta")) is None

    def test_equal_length_failure_is_other(self) -> None:
        # same word count, still wrong → not a span-direction failure
        assert failure_direction(_res("c", 0.0, "Sparta", "Athens")) == "other"

    def test_multiword_gold_uses_the_shortest_span(self) -> None:
        # gold has both a short and a long form; the shortest decides, so a
        # prediction matching the short form is not a span failure.
        r = {
            "id": "d", "hard": 0.0,
            "predicted_answer": "Genet",
            "gold_answers": ["Genet", "Edmond Charles Genet"],
        }
        assert failure_direction(r) == "other"
        r2 = {
            "id": "d2", "hard": 0.0,
            "predicted_answer": "Edmond Charles Genet Jr",
            "gold_answers": ["Genet", "Edmond Charles Genet"],
        }
        assert failure_direction(r2) == "over"

    def test_missing_fields_degrade_to_other(self) -> None:
        assert failure_direction({"id": "e", "hard": 0.0}) == "other"
        assert failure_direction({"hard": 1.0}) is None


class TestSumarizeWindow:
    def test_counts_tasks_failures_and_directions(self) -> None:
        batches = [
            [_res("a", 0.0, "Sahara Desert", "Sahara"), _res("b", 1.0, "x", "x")],
            [_res("c", 0.0, "Arthur", "Chester A. Arthur")],
        ]
        w = summarize_window(batches)
        assert w["n_batches"] == 2
        assert w["n_tasks"] == 3
        assert w["n_failures"] == 2
        assert w["over"] == 1 and w["under"] == 1
        assert abs(w["fail_rate"] - 2 / 3) < 1e-9

    def test_empty_window(self) -> None:
        w = summarize_window([])
        assert w["n_tasks"] == 0 and w["n_failures"] == 0 and w["fail_rate"] == 0.0


class TestDeterministicWindowGate:
    """These decisions must not reach the LLM at all."""

    def test_zero_failure_window_skips_the_consult(self) -> None:
        stub = StubChat([])  # any call would raise
        p = LLMEvidencePolicy(chat_fn=stub)
        results = [_res("a", 1.0, "x", "x"), _res("b", 1.0, "y", "y")]
        d = p.observe("skill", results, p.initial_state())
        assert d.action == WAIT
        assert d.meta.get("deterministic_skip") is True
        assert stub.calls == []
        # counters still advanced
        assert d.state["tasks_since_last_attempt"] == 2

    def test_sub_floor_window_skips_the_consult(self) -> None:
        stub = StubChat([])
        p = LLMEvidencePolicy(chat_fn=stub, min_window_tasks=40)
        # 10 tasks, 2 failures → rate 0.2, below the 0.4 exception
        results = _results([0, 0, 1, 1, 1, 1, 1, 1, 1, 1])
        d = p.observe("skill", results, p.initial_state())
        assert d.action == WAIT
        assert d.meta.get("deterministic_skip") is True
        assert stub.calls == []

    def test_sub_floor_window_with_high_failure_rate_is_consulted(self) -> None:
        stub = StubChat([_controller_json("UPDATE")])
        p = LLMEvidencePolicy(chat_fn=stub, min_window_tasks=40)
        # 10 tasks, 5 failures → rate 0.5 clears the 0.4 exception
        results = _results([0, 0, 0, 0, 0, 1, 1, 1, 1, 1])
        d = p.observe("skill", results, p.initial_state())
        assert d.action == UPDATE
        assert len(stub.calls) == 1

    def test_window_meeting_the_floor_is_consulted(self) -> None:
        stub = StubChat([_controller_json("WAIT")])
        p = LLMEvidencePolicy(chat_fn=stub, min_window_tasks=40)
        results = _results([0, 0] + [1] * 38)  # 40 tasks, 2 failures
        d = p.observe("skill", results, p.initial_state())
        assert len(stub.calls) == 1
        assert d.action == WAIT

    def test_epoch_end_boundary_still_consults(self) -> None:
        stub = StubChat([_controller_json("WAIT")])
        p = LLMEvidencePolicy(chat_fn=stub, min_window_tasks=40)
        p.observe("skill", [], p.initial_state(), epoch_end=True)
        assert len(stub.calls) == 1

    def test_floor_can_be_disabled(self) -> None:
        stub = StubChat([_controller_json("WAIT")])
        p = LLMEvidencePolicy(chat_fn=stub, min_window_tasks=0, floor_step=0)
        d = p.observe("skill", _results([0]), p.initial_state())
        assert len(stub.calls) == 1
        assert not d.meta.get("deterministic_skip")


class TestEscalatingFloor:
    """A static floor is wrong in both directions: high enough to block
    noise-triggers also blocks the small window V3's best candidate came
    from. The floor escalates per consecutive rejection instead."""

    def test_default_floor_allows_a_ten_task_window(self) -> None:
        stub = StubChat([_controller_json("WAIT")])
        p = LLMEvidencePolicy(chat_fn=stub)  # defaults 10 / 30
        p.observe("skill", _results([0, 1, 1, 1, 1, 1, 1, 1, 1, 1]), p.initial_state())
        assert len(stub.calls) == 1

    def test_floor_escalates_with_a_rejection_streak(self) -> None:
        stub = StubChat([_controller_json("WAIT")])
        p = LLMEvidencePolicy(chat_fn=stub)  # base 10, step 30 → streak 1 = 40
        state = p.initial_state()
        state["consecutive_rejects"] = 1
        d = p.observe("skill", _results([0] + [1] * 9), state)
        assert d.meta.get("deterministic_skip") is True
        assert stub.calls == []  # 10-task window under a 40-task floor
        assert "after 1 rejected attempt(s)" in d.reason

    def test_escalated_floor_is_cleared_by_a_large_window(self) -> None:
        stub = StubChat([_controller_json("WAIT")])
        p = LLMEvidencePolicy(chat_fn=stub, floor_step=30)
        state = p.initial_state()
        state["consecutive_rejects"] = 2  # floor 10 + 60 = 70
        results = _results([0, 0] + [1] * 68)  # 70 tasks
        d = p.observe("skill", results, state)
        assert len(stub.calls) == 1
        assert not d.meta.get("deterministic_skip")

    def test_failure_rate_exception_still_applies_after_a_streak(self) -> None:
        stub = StubChat([_controller_json("UPDATE")])
        p = LLMEvidencePolicy(chat_fn=stub)
        state = p.initial_state()
        state["consecutive_rejects"] = 1
        # 10 tasks, 6 failures → rate 0.6 clears the exception
        d = p.observe("skill", _results([0] * 6 + [1] * 4), state)
        assert d.action == UPDATE
        assert len(stub.calls) == 1


class TestRejectStreakMaintenance:
    def test_reset_increments_on_reject(self) -> None:
        p = LLMEvidencePolicy(chat_fn=StubChat([]))
        s0 = p.initial_state()
        assert s0["consecutive_rejects"] == 0
        s1 = p.reset_state(outcome="rejected", trigger_state=s0)
        assert s1["consecutive_rejects"] == 1
        s2 = p.reset_state(outcome="rejected", trigger_state=s1)
        assert s2["consecutive_rejects"] == 2

    def test_reset_clears_on_accept(self) -> None:
        p = LLMEvidencePolicy(chat_fn=StubChat([]))
        state = p.initial_state()
        state["consecutive_rejects"] = 3
        assert p.reset_state(outcome="accepted", trigger_state=state)["consecutive_rejects"] == 0

    def test_llm_cannot_override_the_streak(self) -> None:
        stub = StubChat([json.dumps({
            "decision": "WAIT",
            "evidence_state": {"hypotheses": [], "consecutive_rejects": 99},
            "reason": "r",
        })])
        p = LLMEvidencePolicy(chat_fn=stub, min_window_tasks=0)
        state = p.initial_state()
        state["consecutive_rejects"] = 2
        d = p.observe("skill", _results([0]), state)
        assert d.state["consecutive_rejects"] == 2

    def test_streak_is_rendered_in_the_window_summary(self) -> None:
        stub = StubChat([_controller_json("WAIT")])
        p = LLMEvidencePolicy(chat_fn=stub, min_window_tasks=0)
        state = p.initial_state()
        state["consecutive_rejects"] = 2
        results = _results([0, 1])
        p.observe("skill", results, state, context={"buffered_batches": [results]})
        assert "consecutive rejected attempts on this unchanged skill: 2" in stub.calls[0]["user"]

    def test_streak_line_absent_when_zero(self) -> None:
        stub = StubChat([_controller_json("WAIT")])
        p = LLMEvidencePolicy(chat_fn=stub, min_window_tasks=0)
        results = _results([0, 1])
        p.observe("skill", results, p.initial_state(),
                  context={"buffered_batches": [results]})
        assert "consecutive rejected attempts" not in stub.calls[0]["user"]


class TestWindowLean:
    """`other` must participate in the lean verdict.

    The V5 run's worst attempt was triggered on a 200-task window that was
    ``over=16 under=9 other=18``; the old formula looked only at 16/(16+9)
    and rendered "leans OVER-specified (the failures share a direction)",
    which the controller then cited verbatim as its justification.
    """

    def test_dominant_other_forces_straddle(self) -> None:
        assert window_lean({"over": 16, "under": 9, "other": 18}) == "straddle"

    def test_clear_directional_lean_survives(self) -> None:
        assert window_lean({"over": 8, "under": 2, "other": 1}) == "over"
        assert window_lean({"over": 2, "under": 8, "other": 1}) == "under"

    def test_balanced_directions_straddle(self) -> None:
        assert window_lean({"over": 4, "under": 4, "other": 0}) == "straddle"

    def test_all_undirected_is_none(self) -> None:
        assert window_lean({"over": 0, "under": 0, "other": 5}) == "none"
        assert window_lean({"over": 0, "under": 0, "other": 0}) == "none"

    def test_one_sided_window_leads(self) -> None:
        assert window_lean({"over": 4, "under": 0, "other": 0}) == "over"

    def test_the_v5_regression_case_renders_as_straddle(self) -> None:
        window = {"n_batches": 20, "n_tasks": 200, "n_failures": 43,
                  "fail_rate": 0.215, "over": 16, "under": 9, "other": 18}
        p = LLMEvidencePolicy(chat_fn=StubChat([]), min_window_tasks=0)
        text = p._render_window(window)
        assert "STRADDLES" in text
        assert "unrelated corrections" in text
        assert "leans OVER-specified" not in text

    def test_straddle_mentioning_undirected_count(self) -> None:
        window = {"n_batches": 2, "n_tasks": 20, "n_failures": 5,
                  "fail_rate": 0.25, "over": 1, "under": 1, "other": 3}
        p = LLMEvidencePolicy(chat_fn=StubChat([]), min_window_tasks=0)
        assert "3 undirected" in p._render_window(window)


class TestSkillResendSuppression:
    """The skill text is unchanged between 95% of consecutive consults
    (V5: 38 of 41 pairs), so re-sending it every time is pure waste."""

    def _policy(self) -> LLMEvidencePolicy:
        return LLMEvidencePolicy(chat_fn=StubChat([]), min_window_tasks=0)

    def test_first_consult_sends_the_full_skill(self) -> None:
        stub = StubChat([_controller_json("WAIT")])
        p = LLMEvidencePolicy(chat_fn=stub, min_window_tasks=0)
        p.observe("THE FULL SKILL TEXT", _results([0]), p.initial_state(),
                  context={"skill_identity": "abc123"})
        assert "THE FULL SKILL TEXT" in stub.calls[0]["user"]

    def test_second_consult_confirms_instead_of_resending(self) -> None:
        stub = StubChat([_controller_json("WAIT"), _controller_json("WAIT")])
        p = LLMEvidencePolicy(chat_fn=stub, min_window_tasks=0)
        ctx = {"skill_identity": "abc123"}
        d1 = p.observe("THE FULL SKILL TEXT", _results([0]), p.initial_state(), context=ctx)
        d2 = p.observe("THE FULL SKILL TEXT", _results([0]), d1.state, context=ctx)
        assert "THE FULL SKILL TEXT" in stub.calls[0]["user"]
        assert "THE FULL SKILL TEXT" not in stub.calls[1]["user"]
        assert "unchanged since" in stub.calls[1]["user"]

    def test_changed_skill_is_resent(self) -> None:
        stub = StubChat([_controller_json("WAIT"), _controller_json("WAIT")])
        p = LLMEvidencePolicy(chat_fn=stub, min_window_tasks=0)
        d1 = p.observe("OLD SKILL", _results([0]), p.initial_state(),
                       context={"skill_identity": "aaa"})
        p.observe("NEW SKILL", _results([0]), d1.state,
                  context={"skill_identity": "bbb"})
        assert "NEW SKILL" in stub.calls[1]["user"]

    def test_seen_identity_survives_the_llm_reply(self) -> None:
        # The LLM returns a state with no skill_seen_identity; the policy's
        # own bookkeeping must put it back so the next consult still elides.
        stub = StubChat([_controller_json("WAIT")])
        p = LLMEvidencePolicy(chat_fn=stub, min_window_tasks=0)
        d = p.observe("SKILL", _results([0]), p.initial_state(),
                      context={"skill_identity": "deadbeef"})
        assert d.state["skill_seen_identity"] == "deadbeef"

    def test_seen_identity_is_not_invented_by_the_llm(self) -> None:
        stub = StubChat([json.dumps({
            "decision": "WAIT",
            "evidence_state": {"hypotheses": [], "skill_seen_identity": "spoofed"},
            "reason": "r",
        })])
        p = LLMEvidencePolicy(chat_fn=stub, min_window_tasks=0)
        d = p.observe("SKILL", _results([0]), p.initial_state(),
                      context={"skill_identity": "real"})
        assert d.state["skill_seen_identity"] == "real"

    def test_missing_identity_keeps_sending_the_skill(self) -> None:
        stub = StubChat([_controller_json("WAIT"), _controller_json("WAIT")])
        p = LLMEvidencePolicy(chat_fn=stub, min_window_tasks=0)
        d1 = p.observe("SKILL", _results([0]), p.initial_state())
        p.observe("SKILL", _results([0]), d1.state)
        assert "SKILL" in stub.calls[1]["user"]


class TestValidatedRulesContext:
    """Fix ④: reflect/select must know which lines an ACCEPTED candidate
    introduced, so a fresh failure does not rewrite validated content."""

    def test_format_lists_accepted_edits(self) -> None:
        from skillopt.engine.trainer import _format_validated_rules

        entries = [
            {"step": 1, "action": "reject",
             "rejected_edits": [{"op": "replace", "content": "rejected thing"}]},
            {"step": 3, "action": "accept_new_best",
             "edits": [{"op": "insert_after",
                        "content": "- **Avoid Frequency Bias**: prefer the linked entity"}]},
        ]
        text = _format_validated_rules(entries)
        assert "Validated Rules" in text
        assert "Avoid Frequency Bias" in text
        assert "rejected thing" not in text
        assert "requires failure evidence that *directly contradicts*" in text

    def test_empty_when_nothing_accepted(self) -> None:
        from skillopt.engine.trainer import _format_validated_rules

        assert _format_validated_rules([]) == ""
        assert _format_validated_rules(
            [{"step": 1, "action": "reject", "rejected_edits": []}]
        ) == ""

    def test_dedupes_repeated_content(self) -> None:
        from skillopt.engine.trainer import _format_validated_rules

        same = {"op": "append", "content": "- **Same Rule**: body"}
        text = _format_validated_rules(
            [{"step": 1, "action": "accept", "edits": [same]},
             {"step": 2, "action": "accept", "edits": [same]}]
        )
        assert text.count("Same Rule") == 1

    def test_stage_prefixes_are_stripped_to_first_line(self) -> None:
        from skillopt.engine.trainer import _format_validated_rules

        long_body = "x" * 500
        text = _format_validated_rules(
            [{"step": 4, "action": "accept",
              "edits": [{"op": "append", "content": f"- **Rule A**: {long_body}"}]}]
        )
        assert "Rule A" in text
        assert long_body not in text


class TestWindowRendering:
    def _prompt(self, context: dict, results: list[dict]) -> str:
        stub = StubChat([_controller_json("WAIT")])
        p = LLMEvidencePolicy(chat_fn=stub, min_window_tasks=0)
        p.observe("skill", results, p.initial_state(), context=context)
        return stub.calls[0]["user"]

    def test_window_summary_reports_size_and_rate(self) -> None:
        batches = [[_res("a", 0.0, "Sahara Desert", "Sahara")] + _results([1] * 9)]
        user = self._prompt({"buffered_batches": batches}, batches[0])
        assert "## Window Summary" in user
        assert "tasks: 10 (failures 1, rate 0.10)" in user

    def test_straddling_window_is_flagged_as_contradiction(self) -> None:
        batches = [[
            _res("a", 0.0, "Sahara Desert", "Sahara"),
            _res("b", 0.0, "Arthur", "Chester A. Arthur"),
            _res("c", 1.0, "x", "x"),
        ]]
        user = self._prompt({"buffered_batches": batches}, batches[0])
        assert "STRADDLES both directions" in user
        assert "contradict" in user

    def test_directional_window_reports_the_lean(self) -> None:
        batches = [[
            _res("a", 0.0, "Sahara Desert", "Sahara"),
            _res("b", 0.0, "Gobi Desert", "Gobi"),
            _res("c", 0.0, "Atacama Desert", "Atacama"),
            _res("d", 1.0, "x", "x"),
        ]]
        user = self._prompt({"buffered_batches": batches}, batches[0])
        assert "leans OVER-specified" in user

    def test_window_with_no_directional_failures_says_so(self) -> None:
        batches = [[_res("a", 0.0, "Athens", "Sparta"), _res("b", 1.0, "x", "x")]]
        user = self._prompt({"buffered_batches": batches}, batches[0])
        assert "no directional failure evidence" in user


class TestContradictionGuidance:
    def test_system_prompt_carries_the_straddle_rule(self) -> None:
        from skillopt.evolution_controller import _CONTROLLER_SYSTEM_PROMPT as sys_p

        assert "Fragmented windows" in sys_p
        assert "RULES X AND Y CONFLICT" in sys_p
        assert "evidence the *diagnosis* is wrong" in sys_p

    def test_system_prompt_defines_growth_as_rate_not_count(self) -> None:
        from skillopt.evolution_controller import _CONTROLLER_SYSTEM_PROMPT as sys_p

        assert "three failures in ten tasks is noise" in sys_p

    def test_attempt_guidance_warns_against_repeated_same_wording(self) -> None:
        stub = StubChat([_controller_json("WAIT")])
        p = LLMEvidencePolicy(chat_fn=stub, min_window_tasks=0)
        p.observe(
            "skill", _results([0]), p.initial_state(),
            context={"attempt_history": [{
                "attempt": 1, "tasks_consumed": 10, "trigger": "controller",
                "validation": "rejected", "val_before": 0.81, "val_after": 0.81,
                "candidate_score": 0.79,
            }]},
        )
        user = stub.calls[0]["user"]
        assert "series* of rejected attempts" in user
        assert "reformulate" in user
