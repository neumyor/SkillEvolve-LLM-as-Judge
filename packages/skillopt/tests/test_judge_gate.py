"""Judge gate tests — parsing, decision contract, and evidence withholding.

No network: every test injects a fake ``chat_fn``. The properties under test
are the ones the experiments depend on being true:

* an unparseable judge call is a REJECT (the gate it replaces is strict, and
  a crash must not silently become an accept);
* the judge is never shown a number that would turn it into a threshold
  (the held-out accuracy, or the window's aggregate score);
* the trainer can tell which gate produced a decision from the step record.
"""
from __future__ import annotations

import json

import pytest

from skillopt.evaluation.judge_gate import (
    JudgeGate,
    build_judge_user_message,
    judge_gate_for_config,
    normalize_gate_mode,
    parse_judge_response,
)


def _accept(**kwargs):
    reply = json.dumps({
        "verdict": "ACCEPT",
        "confidence": kwargs.get("confidence", "medium"),
        "reason": kwargs.get("reason", "the added rule is supported by the window"),
    })
    return lambda **_: (reply, {"prompt_tokens": 5})


def _reject(**kwargs):
    reply = json.dumps({
        "verdict": "REJECT",
        "confidence": kwargs.get("confidence", "low"),
        "reason": kwargs.get("reason", "names a specific room; fitted, not general"),
    })
    return lambda **_: (reply, {"prompt_tokens": 5})


def _gate(chat_fn, **kwargs):
    return JudgeGate(chat_fn=chat_fn, **kwargs)


def _call(gate, **overrides):
    kwargs = dict(
        candidate_skill="# Candidate\n- Rule A",
        current_skill="# Current\n- Rule B",
        current_score=0.7,
        best_skill="# Current\n- Rule B",
        best_score=0.7,
        best_step=1,
        global_step=2,
        ranked_patch={"reasoning": "why", "edits": [{"op": "replace", "content": "Rule A"}]},
        batches=[{
            "results": [{"id": "t1", "hard": 0, "soft": 0.0, "task_description": "do x"}],
            "rollout_dir": "",
        }],
    )
    kwargs.update(overrides)
    return gate(**kwargs)


# ── Response parsing ────────────────────────────────────────────────────────

@pytest.mark.parametrize("reply,verdict,confidence", [
    ('{"verdict": "ACCEPT", "confidence": "high", "reason": "r"}', "ACCEPT", "high"),
    ('{"verdict": "REJECT", "confidence": "low", "reason": "r"}', "REJECT", "low"),
    ('```json\n{"verdict": "ACCEPT", "confidence": "medium", "reason": "r"}\n```', "ACCEPT", "medium"),
    ('Sure.\n{"verdict": "REJECT", "confidence": "high", "reason": "r"}\nDone.', "REJECT", "high"),
    ('{"verdict": "accept", "confidence": "HIGH", "reason": "r"}', "ACCEPT", "high"),
])
def test_parses_json_verdicts(reply, verdict, confidence):
    got_verdict, got_confidence, _, error = parse_judge_response(reply)
    assert (got_verdict, got_confidence) == (verdict, confidence)
    assert error == ""


def test_unknown_confidence_degrades_to_unknown_not_failure():
    verdict, confidence, _, error = parse_judge_response(
        '{"verdict": "ACCEPT", "confidence": "pretty sure", "reason": "r"}'
    )
    assert verdict == "ACCEPT"
    assert confidence == "unknown"
    assert error == ""


def test_truncated_object_still_yields_a_verdict():
    """A reply cut off mid-object must not become an exception."""
    verdict, _, _, error = parse_judge_response('{"verdict": "ACCEPT",')
    assert verdict == "ACCEPT"
    assert error == ""


@pytest.mark.parametrize("reply", ["", "   ", "I am not sure what you want.", '{"confidence": "high"}'])
def test_unusable_replies_report_an_error_and_no_verdict(reply):
    verdict, _, _, error = parse_judge_response(reply)
    assert verdict == ""
    assert error


# ── Gate mode normalization ─────────────────────────────────────────────────

@pytest.mark.parametrize("value,expected", [
    ("rollout", "rollout"),
    ("selection", "rollout"),
    ("regression", "rollout"),
    ("judge", "judge"),
    ("greedy", "greedy"),
    ("off", "greedy"),
    (None, "rollout"),
    ("", "rollout"),
])
def test_gate_mode_aliases(value, expected):
    assert normalize_gate_mode(value) == expected


def test_unknown_gate_mode_is_a_config_error():
    with pytest.raises(ValueError, match="gate_mode"):
        normalize_gate_mode("majority-vote")


def test_judge_gate_is_only_built_in_judge_mode():
    assert judge_gate_for_config({"gate_mode": "rollout"}) is None
    assert judge_gate_for_config({"gate_mode": "greedy"}) is None
    assert isinstance(judge_gate_for_config({"gate_mode": "judge"}), JudgeGate)


def test_judge_gate_reads_its_config_keys():
    gate = judge_gate_for_config({
        "gate_mode": "judge",
        "judge_max_completion_tokens": 1234,
        "judge_retries": 5,
        "judge_max_evidence_cards": 7,
        "judge_evidence_card_chars": 99,
    })
    assert gate.max_completion_tokens == 1234
    assert gate.retries == 5
    assert gate.max_cards == 7
    assert gate.card_chars == 99


# ── Decision contract ───────────────────────────────────────────────────────

def test_accept_replaces_current_and_best():
    result, record = _call(_gate(_accept()))
    assert result.action == "accept_new_best"
    assert result.current_skill == "# Candidate\n- Rule A"
    assert result.best_skill == "# Candidate\n- Rule A"
    assert result.best_step == 2
    assert record["gate_kind"] == "judge"
    assert record["judge_verdict"] == "ACCEPT"
    assert record["judge_parse_failed"] is False


def test_reject_leaves_state_untouched():
    result, record = _call(_gate(_reject()))
    assert result.action == "reject"
    assert result.current_skill == "# Current\n- Rule B"
    assert result.current_score == 0.7
    assert result.best_skill == "# Current\n- Rule B"
    assert result.best_score == 0.7
    assert result.best_step == 1
    assert record["judge_verdict"] == "REJECT"
    assert record["judge_confidence"] == "low"
    assert record["judge_reason"]


def test_unparseable_judge_rejects_and_says_so():
    """A broken judge must fail closed: the gate it replaces rejects ties."""
    def bad_chat(**_):
        return "no idea, sorry", {}

    result, record = _call(_gate(bad_chat, retries=1))
    assert result.action == "reject"
    assert record["judge_parse_failed"] is True
    assert record["judge_verdict"] == "REJECT"
    assert record["judge_calls"] == 2  # 1 + retries
    assert record["judge_error"]


def test_retries_then_succeeds():
    seen = {"n": 0}

    def flaky(**_):
        seen["n"] += 1
        if seen["n"] == 1:
            return "garbage", {}
        return json.dumps({"verdict": "ACCEPT", "confidence": "high", "reason": "ok"}), {}

    result, record = _call(_gate(flaky, retries=2))
    assert result.action == "accept_new_best"
    assert record["judge_calls"] == 2
    assert record["judge_parse_failed"] is False


def test_backend_exception_does_not_crash_training():
    def exploding(**_):
        raise RuntimeError("endpoint closed the connection")

    result, record = _call(_gate(exploding, retries=1))
    assert result.action == "reject"
    assert "endpoint closed" in record["judge_error"]


def test_judge_reuses_the_optimizer_backend_stage_name():
    seen = {}

    def chat(**kwargs):
        seen.update(kwargs)
        return json.dumps({"verdict": "REJECT", "confidence": "low", "reason": "r"}), {}

    _call(_gate(chat))
    assert seen["stage"] == "judge_gate"


# ── Evidence the judge must and must not see ────────────────────────────────

def test_judge_sees_the_patch_the_evidence_and_the_trajectory_hook(tmp_path):
    rollout_dir = tmp_path / "rollout"
    (rollout_dir / "predictions" / "t1").mkdir(parents=True)
    (rollout_dir / "predictions" / "t1" / "conversation.json").write_text(json.dumps([
        {"role": "user", "content": "you are in a room"},
        {"role": "assistant", "content": "go to desk 1"},
    ]))

    gate = _gate(_reject(), max_cards=5)
    seen = {}
    gate._chat_fn = lambda **kw: (seen.update(kw) or (
        json.dumps({"verdict": "REJECT", "confidence": "low", "reason": "r"}), {}
    ))
    _call(gate, batches=[{
        "results": [{"id": "t1", "hard": 0, "soft": 0.0, "task_description": "do x",
                     "fail_reason": "ran out of steps"}],
        "rollout_dir": str(rollout_dir),
    }])

    user = seen["user"]
    assert "## Current Skill" in user
    assert "## Candidate Skill" in user
    assert "## Patch That Produced the Candidate" in user
    assert "## Execution Evidence Window" in user
    assert "do x" in user
    assert "ran out of steps" in user
    assert "go to desk 1" in user  # trajectory excerpt reached the judge


def test_judge_never_sees_the_held_out_selection_score():
    """The core design constraint: no held-out number that makes it a threshold.

    v2 deliberately *does* show the training window's own counts (the fix for
    v1's "strictly better with nothing to compare" defect), but the held-out
    selection split must never reach the builder — a judge shown "the current
    skill scores 0.77 on held-out data" is a threshold with extra steps, and
    the experiment is about whether judgement can replace measurement.
    """
    user = build_judge_user_message(
        current_skill="# C",
        candidate_skill="# N",
        ranked_patch=None,
        batches=[{"results": [
            {"id": "a", "hard": 1, "soft": 1.0, "task_description": "t"},
            {"id": "b", "hard": 0, "soft": 0.0, "task_description": "t"},
        ], "rollout_dir": ""}],
    )
    window = user.split("## Execution Evidence Window", 1)[1]
    # Per-task outcomes and the window's own counts are fine — the gate has
    # always been entitled to those.
    assert "1 of 2" in window or "2 of 2" in window
    assert "window success rate" in window.lower()
    # The held-out selection accuracy has no route in at all: the builder
    # takes no score argument.
    import inspect
    params = inspect.signature(build_judge_user_message).parameters
    assert "current_score" not in params
    assert "cand_hard" not in params
    assert "selection" not in " ".join(params).lower()


def test_window_counts_are_shown_but_there_is_no_held_out_number():
    """v2's central fix: give a comparable quantity, but not the measured one."""
    user = build_judge_user_message(
        current_skill="x" * 100,
        candidate_skill="x" * 200,
        ranked_patch=None,
        batches=[{"results": [
            {"id": "a", "hard": 1},
            {"id": "b", "hard": 0},
            {"id": "c", "hard": 0},
        ], "rollout_dir": ""}],
        max_growth_ratio=1.5,
    )
    # The window's own counts, and the growth ratio, are what v1 lacked.
    assert "tasks in this window: 3" in user
    assert "failed: 2" in user
    assert "window success rate: 0.333" in user
    assert "growth factor: 2.00x" in user
    # Still no held-out number anywhere.
    assert "selection" not in user.lower()
    assert "held-out accuracy" not in user.lower()


def test_previous_attempts_are_rendered_so_a_repeat_is_visible():
    """v2's anti-repeat fix: SearchQA v1 re-accepted one defect family 6x."""
    user = build_judge_user_message(
        current_skill="# C",
        candidate_skill="# N",
        ranked_patch=None,
        batches=[{"results": [{"id": "a", "hard": 0}], "rollout_dir": ""}],
        previous_attempts=[{
            "step": 5,
            "action": "accept_new_best",
            "targeted_defect": "entity length normalization conflict",
            "window_hard_before": 0.775,
            "window_hard_after": 0.750,
        }],
    )
    assert "Previous Attempts" in user
    assert "entity length normalization conflict" in user
    assert "0.775 -> 0.750" in user


def test_no_previous_attempts_is_stated_explicitly():
    user = build_judge_user_message(
        current_skill="# C",
        candidate_skill="# N",
        ranked_patch=None,
        batches=[{"results": [{"id": "a", "hard": 0}], "rollout_dir": ""}],
    )
    assert "first attempt of the run" in user


# ── v2 prompt variant + its enforceable rules ───────────────────────────────

def _v2_reply(**overrides):
    payload = {
        "verdict": "ACCEPT",
        "confidence": "high",
        "defect_mechanism": "answer span includes the descriptive category",
        "evidence_count": 3,
        "counter_evidence_count": 1,
        "expected_window_delta": "improve",
        "falsifier": "a task where the truncated span is the gold answer",
        "reason": "supported by three independent failures",
    }
    payload.update(overrides)
    return json.dumps(payload)


def test_v2_variant_selects_a_different_prompt():
    v1 = _gate(_accept(), prompt_variant="v1")
    v2 = _gate(_accept(), prompt_variant="v2")
    assert v1.system_prompt != v2.system_prompt
    assert "defect_mechanism" in v2.system_prompt
    assert "defect_mechanism" not in v1.system_prompt


def test_unknown_prompt_variant_is_a_config_error():
    with pytest.raises(ValueError, match="prompt_variant"):
        _gate(_accept(), prompt_variant="unknown-version")


def test_v2_accepts_a_well_formed_improving_verdict():
    gate = _gate(lambda **_: (_v2_reply(), {}), prompt_variant="v2")
    result, record = _call(gate)
    assert result.action == "accept_new_best"
    assert record["judge_accepted"] is True
    assert record["judge_rule_override"] == ""
    assert record["judge_evidence_count"] == 3
    assert record["judge_expected_window_delta"] == "improve"


@pytest.mark.parametrize("overrides,fragment", [
    ({"defect_mechanism": "none"}, "no defect mechanism"),
    ({"defect_mechanism": ""}, "no defect mechanism"),
    ({"evidence_count": 1}, "min_evidence"),
    ({"evidence_count": None}, "min_evidence"),
    ({"expected_window_delta": "worse"}, "allowed here"),
    ({"falsifier": ""}, "no falsifier"),
    ({"confidence": "low"}, "confidence=low"),
])
def test_v2_rules_downgrade_a_weak_accept(overrides, fragment):
    """Each v2 rule is enforced, not merely stated. v1 stated four rules and
    acted on none — 14/14 accepted.

    The call uses a *consolidated* current skill, because that is the regime
    where every v2 rule binds. The bootstrap regime is covered separately below.
    """
    gate = _gate(lambda **_: (_v2_reply(**overrides), {}), prompt_variant="v2",
                 require_high_confidence=True)
    result, record = _call(gate, current_skill="x" * 3000, candidate_skill="x" * 3300)
    assert result.action == "reject"
    assert record["judge_verdict"] == "ACCEPT"      # what the model said
    assert record["judge_accepted"] is False        # what the gate did
    assert fragment in record["judge_rule_override"]


def test_v2_growth_rule_fires_above_the_ratio():
    gate = _gate(lambda **_: (_v2_reply(), {}), prompt_variant="v2",
                 max_growth_ratio=1.5)
    result, record = _call(
        gate,
        current_skill="x" * 1000,
        candidate_skill="x" * 4000,
    )
    assert result.action == "reject"
    assert "growth 4.00x" in record["judge_rule_override"]


@pytest.mark.parametrize("direction", ["improve", "flat"])
def test_v2_accepts_improve_or_flat_while_the_skill_is_bootstrap(direction):
    """At bootstrap the real gate also accepts a tie-that-helps.

    The regression test compares a candidate against the *current* skill; while
    that is a placeholder, a candidate merely matching it is still worth taking.
    Requiring `improve` unconditionally deadlocked the run (both archived
    attempts), so the rule mirrors the gate's own regime behaviour.
    """
    gate = _gate(
        lambda **_: (_v2_reply(expected_window_delta=direction), {}),
        prompt_variant="v2", min_growth_floor=600,
    )
    result, record = _call(
        gate,
        current_skill="x" * 104,
        candidate_skill="x" * 2247,
    )
    assert result.action == "accept_new_best"
    assert record["judge_rule_override"] == ""


def test_v2_rejects_flat_once_the_skill_is_consolidated():
    """The stricter bar the paper gate actually applies to a grown skill."""
    gate = _gate(
        lambda **_: (_v2_reply(expected_window_delta="flat"), {}),
        prompt_variant="v2", min_growth_floor=600,
    )
    result, record = _call(
        gate,
        current_skill="x" * 3000,
        candidate_skill="x" * 3300,
    )
    assert result.action == "reject"
    assert "allowed here: improve" in record["judge_rule_override"]


def test_growth_prompt_line_says_when_the_ratio_does_not_apply():
    """The judge must not cite a rule the gate itself is not applying.

    Measured on the archived bootstrap run: the model refused with
    "inflates the skill by 19.20x" as its stated reason, on a rule that the
    gate had already waived for a below-floor skill — a second, model-side
    deadlock on top of the coded one.
    """
    user = build_judge_user_message(
        current_skill="x" * 104,
        candidate_skill="x" * 2247,
        ranked_patch=None,
        batches=[{"results": [{"id": "a", "hard": 0}], "rollout_dir": ""}],
        min_growth_floor=600,
    )
    assert "NOT a constraint here" in user
    assert "consolidation floor" in user


def test_growth_prompt_line_states_the_allowance_once_consolidated():
    user = build_judge_user_message(
        current_skill="x" * 1000,
        candidate_skill="x" * 2000,
        ranked_patch=None,
        batches=[{"results": [{"id": "a", "hard": 0}], "rollout_dir": ""}],
        max_growth_ratio=1.5,
        min_growth_floor=600,
    )
    assert "exceeds the 1.50x allowance" in user


def test_v2_growth_rule_does_not_bind_on_a_bootstrap_skill():
    """A ratio rule on a placeholder skill can never be satisfied.

    Measured on SearchQA: the initial skill is a 104-character placeholder, so
    1.5x permits 156 characters while every real candidate is ~2500 — so the
    rule rejected all of them, which kept the skill at 104 characters, which
    rejected the next candidate the same way. The run could not start. The
    floor makes the constraint apply to a consolidated document, which is what
    it is for.
    """
    gate = _gate(lambda **_: (_v2_reply(), {}), prompt_variant="v2",
                 max_growth_ratio=1.5, min_growth_floor=600)
    result, record = _call(
        gate,
        current_skill="x" * 104,          # the real SearchQA placeholder size
        candidate_skill="x" * 2247,       # a real candidate size
    )
    assert record["judge_rule_override"] == ""
    assert result.action == "accept_new_best"


def test_v2_growth_rule_binds_once_the_skill_is_consolidated():
    gate = _gate(lambda **_: (_v2_reply(), {}), prompt_variant="v2",
                 max_growth_ratio=1.5, min_growth_floor=600)
    result, record = _call(
        gate,
        current_skill="x" * 2247,         # now past the floor
        candidate_skill="x" * 6741,
    )
    assert result.action == "reject"
    assert "growth 3.00x" in record["judge_rule_override"]


def test_v2_growth_rule_allows_a_candidate_inside_the_ratio():
    gate = _gate(lambda **_: (_v2_reply(), {}), prompt_variant="v2",
                 max_growth_ratio=2.0, min_growth_floor=600)
    result, _ = _call(gate, current_skill="x" * 1000, candidate_skill="x" * 1800)
    assert result.action == "accept_new_best"


def test_v1_behaviour_is_unchanged_by_the_v2_rules():
    """The v1/v2 comparison is only meaningful if v1 stays as measured."""
    gate = _gate(lambda **_: (_v2_reply(
        defect_mechanism="none", evidence_count=0,
        expected_window_delta="flat", falsifier="", confidence="low",
    ), {}), prompt_variant="v1")
    result, record = _call(gate, current_skill="x" * 1000, candidate_skill="x" * 4000)
    assert result.action == "accept_new_best"
    assert record["judge_rule_override"] == ""


def test_confidence_defaults_to_not_gating():
    """The field is uncalibrated (v1: 13/14 "high" while accepting everything),
    and gating on it deadlocked v2 (archived). It is recorded, not enforced."""
    from skillopt.evaluation.judge_gate import DEFAULT_REQUIRE_HIGH_CONFIDENCE
    assert DEFAULT_REQUIRE_HIGH_CONFIDENCE is False
    gate = _gate(lambda **_: (_v2_reply(confidence="medium"), {}),
                 prompt_variant="v2")
    result, record = _call(gate, current_skill="x" * 3000, candidate_skill="x" * 3300)
    assert result.action == "accept_new_best"
    assert record["judge_confidence"] == "medium"   # still recorded


def test_confidence_can_be_gated_when_a_run_asks_for_it():
    gate = _gate(lambda **_: (_v2_reply(confidence="medium"), {}),
                 prompt_variant="v2", require_high_confidence=True)
    result, record = _call(gate, current_skill="x" * 3000, candidate_skill="x" * 3300)
    assert result.action == "reject"
    assert "confidence=medium" in record["judge_rule_override"]


def test_evidence_cards_are_capped_and_the_omission_is_disclosed():
    gate = _gate(_reject(), max_cards=2)
    results = [
        {"id": f"t{i}", "hard": 0, "soft": 0.0, "task_description": f"task {i}"}
        for i in range(5)
    ]
    _, record = _call(gate, batches=[{"results": results, "rollout_dir": ""}])
    assert record["judge_evidence_cards"] == 2
    assert record["judge_evidence_total"] == 5


def test_empty_window_does_not_crash_the_judge():
    result, record = _call(_gate(_reject()), batches=[])
    assert result.action == "reject"
    assert record["judge_evidence_total"] == 0
