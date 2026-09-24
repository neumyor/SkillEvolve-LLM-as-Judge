from pathlib import Path

import pytest

from alfworld_eval.env import (
    Observation,
    StepResult,
    episode_step_budget,
    split_manifest_provenance,
)
from alfworld_eval.unified.agent import (
    FALLBACK_RESPONSE,
    RandomAgent,
    UsageAccumulator,
    _restore_think_block,
    extract_admissible_commands,
)
from alfworld_eval.unified.prompts import (
    SKILL_KNOWLEDGE_HEADER,
    SkillView,
    build_user_prompt,
    extract_task_description,
)
from alfworld_eval.unified.runner import (
    EpisodeResult,
    build_correction_prompt,
    diagnose_action,
    project_action,
    project_and_validate_action,
    result_from_row,
    result_row,
    run_unified_episode,
    safe_admissible_fallback,
    summarize,
)
from alfworld_eval.unified.skills import (
    classify_alfworld_task,
    load_skill_provider,
    task_type_from_gamefile,
)

OBS = "You arrive at loc 9. On the countertop 1, you see a mug 1."
CMDS = ["go to sinkbasin 1", "take mug 1", "help"]


def test_extract_task_description():
    obs = "Welcome. Your task is to: put a clean mug in/on desk 1."
    assert extract_task_description(obs) == "put a clean mug in/on desk 1."
    assert extract_task_description(OBS) == OBS.strip()


def test_build_prompt_no_history_and_history():
    p0 = build_user_prompt(OBS, CMDS)
    assert "Your current observation is:" in p0
    assert "'take mug 1'" in p0
    assert "help" not in p0

    p1 = build_user_prompt(
        OBS,
        CMDS,
        task_description="put a mug in/on desk 1.",
        history=[("obs one", "go to loc 1"), ("obs two", "take mug 1")],
        history_length=2,
    )
    assert "Your task is to: put a mug in/on desk 1." in p1
    assert "You are now at step 3" in p1
    assert "[Observation 2: 'obs two', Action 2: 'take mug 1']" in p1


def test_history_block_uses_skillrl_format_and_absolute_step_numbers():
    """The history block is part of the prompt, so its numbering is protocol.

    SkillRL renders one bracketed record per step (memory.py:88-97) with the
    observation and action of a step sharing the step's *absolute* number. The
    previous rendering emitted two lines numbered from 1, so at step 40 the
    history read "Obs 1 / Action 1" and could not be correlated with the
    absolute step count quoted on the next line.
    """
    history = [
        ("obs one", "go to loc 1"),
        ("obs two", "take mug 1"),
        ("obs three", "go to desk 1"),
    ]
    prompt = build_user_prompt(
        OBS,
        CMDS,
        task_description="put a mug in/on desk 1.",
        history=history,
        history_length=2,
    )
    # Only the last two steps appear, numbered 2 and 3 -- not 1 and 2.
    assert (
        "[Observation 2: 'obs two', Action 2: 'take mug 1']\n"
        "[Observation 3: 'obs three', Action 3: 'go to desk 1']"
    ) in prompt
    assert "You are now at step 4" in prompt
    assert "Prior to this step, you have already taken 3 step(s)." in prompt
    # The old two-line, relative-numbered rendering must be gone entirely.
    assert "Obs 1:" not in prompt
    assert "Obs 2:" not in prompt
    assert "\nObs " not in prompt


def test_skill_prefix_injection():
    skill = SkillView(prefix=SKILL_KNOWLEDGE_HEADER + "Always be careful.")
    p = build_user_prompt(OBS, CMDS, skill=skill)
    assert p.startswith("\n\n## Skill Knowledge")
    assert "Always be careful." in p


def test_skill_body_injection():
    skill = SkillView(body="## Retrieved Relevant Experience\n- be systematic")
    p = build_user_prompt(OBS, CMDS, skill=skill)
    assert "## Retrieved Relevant Experience" in p


def test_project_action_matches_skillrl_projection():
    good = "<think>plan</think><action>go to sinkbasin 1</action>"
    action, valid = project_action(good)
    assert action == "go to sinkbasin 1"
    assert valid

    no_think, valid = project_action("<action>look</action>")
    assert no_think == "look"
    assert not valid

    no_tags, valid = project_action("I will look around now")
    assert valid is False
    assert no_tags  # last-30-char fallback, non-empty

    _, valid = project_action("<think>思考</think><action>look</action>")
    assert not valid  # CJK response rejected


def test_prompt_requires_short_protocol_complete_output():
    prompt = build_user_prompt(OBS, CMDS)
    assert "no more than two short" in prompt
    assert "<think>brief reason</think><action>one admissible action</action>" in prompt


def test_invalid_actions_use_only_a_safe_admissible_fallback():
    assert safe_admissible_fallback(["go to sinkbasin 1", "look"]) == "look"
    assert safe_admissible_fallback(["go to sinkbasin 1"]) == "look"

    malformed, format_valid, requested_admissible = project_and_validate_action(
        "unfinished reasoning", ["look", "inventory"]
    )
    assert malformed == "look"
    assert format_valid is False
    assert requested_admissible is False

    inadmissible, format_valid, requested_admissible = project_and_validate_action(
        "<think>reason</think><action>go to nowhere 1</action>",
        ["look", "inventory"],
    )
    assert inadmissible == "look"
    assert format_valid is True
    assert requested_admissible is False

    allowed, format_valid, requested_admissible = project_and_validate_action(
        "<think>reason</think><action>inventory</action>",
        ["look", "inventory"],
    )
    assert (allowed, format_valid, requested_admissible) == ("inventory", True, True)


def test_diagnosis_is_actionable_and_correction_prompt_contains_it():
    diagnostic = diagnose_action(
        "unfinished response",
        ["look", "take mug 1"],
    )
    assert diagnostic["valid"] is False
    assert "missing opening <think> tag" in diagnostic["issues"]
    assert "missing closing </action> tag" in diagnostic["issues"]
    assert diagnostic["requested_admissible"] is False

    prompt = build_correction_prompt(
        "current observation and action list",
        "unfinished response",
        diagnostic,
    )
    assert "VALIDATION FAILED" in prompt
    assert "missing opening <think> tag" in prompt
    assert "['look', 'take mug 1']" in prompt
    assert "<think>brief reason</think><action>one admissible action</action>" in prompt


class _CorrectionAgent:
    name = "test"

    def __init__(self, responses):
        self.responses = iter(responses)
        self.prompts = []

    def respond(self, user_prompt):
        self.prompts.append(user_prompt)
        return next(self.responses), {}


class _OneStepEnv:
    def __init__(self):
        self.actions = []
        self._observation = Observation(
            text="Your task is to: look at the mug.",
            admissible_commands=("look", "take mug 1"),
            game_file=(
                "json_2.1.1/valid_seen/look_at_obj_in_light-Mug-None-DeskLamp-1/"
                "trial/game.tw-pddl"
            ),
            won=False,
        )

    def reset(self):
        return self._observation

    def step(self, action):
        self.actions.append(action)
        return StepResult(
            observation=self._observation,
            reward=1.0 if action == "look" else 0.0,
            done=True,
            won=action == "look",
            info={},
        )


def test_episode_step_budget_mirrors_alfworld_registration():
    """The budget must come from the config key ALFWorld actually registers.

    alfred_tw_env.py reads rl.training or dagger.training according to
    general.training_method and passes it to register_games(max_episode_steps=).
    Reading the wrong section would silently fork the protocol.
    """
    dagger = {
        "general": {"training_method": "dagger"},
        "dagger": {"training": {"max_nb_steps_per_episode": 37}},
        # A decoy rl section must NOT win when training_method is dagger.
        "rl": {"training": {"max_nb_steps_per_episode": 50}},
    }
    assert episode_step_budget(dagger) == 37
    dqn = {
        "general": {"training_method": "dqn"},
        "rl": {"training": {"max_nb_steps_per_episode": 21}},
    }
    assert episode_step_budget(dqn) == 21
    with pytest.raises(ValueError, match="training_method"):
        episode_step_budget({"general": {"training_method": "unknown"}})
    with pytest.raises(ValueError, match="max_nb_steps_per_episode"):
        episode_step_budget({"general": {"training_method": "dagger"}, "dagger": {}})


def test_shipped_config_agrees_with_the_papers_protocol():
    """configs/textworld.yaml is the single source of the 50-step cut-off."""
    import yaml

    config_path = Path(__file__).resolve().parents[1] / "configs/textworld.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert episode_step_budget(config) == 50


def test_episode_step_budget_defaults_to_env_and_rejects_disagreement():
    """A separately supplied cap must never silently override the config."""
    env = _OneStepEnv()
    env.step_budget = 50

    # Omitting max_steps follows the environment's budget.
    agent = _CorrectionAgent(["unfinished response", "still unfinished"])
    run_unified_episode(env, agent, load_skill_provider("vanilla"))
    assert agent.prompts  # ran without error

    # An explicit, *agreeing* value is accepted.
    agent = _CorrectionAgent(["unfinished response", "still unfinished"])
    run_unified_episode(env, agent, load_skill_provider("vanilla"), max_steps=50)
    assert agent.prompts

    # An explicit disagreement is refused rather than silently forking the
    # episode cut-off.
    with pytest.raises(ValueError, match="disagrees with the environment"):
        run_unified_episode(
            env,
            _CorrectionAgent(["look"]),
            load_skill_provider("vanilla"),
            max_steps=8,
        )


def test_episode_step_budget_requires_a_source_when_env_has_none():
    env = _OneStepEnv()
    env.step_budget = 0
    with pytest.raises(ValueError, match="cannot determine the episode cut-off"):
        run_unified_episode(env, _CorrectionAgent(["look"]), load_skill_provider("vanilla"))


def test_split_audit_rejects_a_manifest_from_another_split():
    """`--split valid_seen` with a valid_unseen manifest must not run.

    Nothing checked this before: split_for_gamefile() was only used by the
    analysis side, so a mismatched pairing produced a plausible summary.
    """
    items = [{"gamefile": "json_2.1.1/valid_unseen/foo/trial/game.tw-pddl"}]
    with pytest.raises(ValueError, match="does not match the manifest"):
        split_manifest_provenance(items, "valid_seen")
    # The matching pairing is accepted and reports its coverage.
    prov = split_manifest_provenance(items, "valid_unseen")
    assert prov["split"] == "valid_unseen"
    assert prov["manifest_episodes"] == 1


def test_split_audit_records_that_a_manifest_is_a_subsample():
    """A released manifest is a subset of the official split, so say so.

    SkillOpt's alfworld_path_split ships 39/18/134 episodes against the
    official 3553/140/134; only the test manifest is a complete cover.
    """
    subsample = [
        {"gamefile": f"json_2.1.1/valid_seen/task-{i}/trial/game.tw-pddl"}
        for i in range(18)
    ]
    prov = split_manifest_provenance(subsample, "valid_seen")
    assert prov["manifest_episodes"] == 18
    assert prov["covers_official_split"] is False
    assert prov["official_episodes"] is None or prov["official_episodes"] >= 18

    full = [
        {"gamefile": f"json_2.1.1/valid_unseen/task-{i}/trial/game.tw-pddl"}
        for i in range(134)
    ]
    assert split_manifest_provenance(full, "valid_unseen")["covers_official_split"] is True


def test_invalid_response_gets_one_correction_without_extra_env_step():
    agent = _CorrectionAgent([
        "unfinished response",
        "<think>correct</think><action>look</action>",
    ])
    env = _OneStepEnv()
    result = run_unified_episode(
        env,
        agent,
        load_skill_provider("vanilla"),
        max_steps=1,
        record_trajectory=True,
    )

    assert env.actions == ["look"]
    assert result.success is True
    assert result.steps == 1
    assert result.invalid_actions == 1
    assert result.invalid_requests == 1
    assert result.correction_attempts == 1
    assert result.correction_successes == 1
    assert result.uncorrected_invalid_requests == 0
    assert len(agent.prompts) == 2
    assert "VALIDATION FAILED" in agent.prompts[1]
    assert result.trajectory[0]["correction_succeeded"] is True
    assert result.trajectory[0]["action"] == "look"


def test_failed_correction_uses_safe_fallback_and_records_diagnostic():
    agent = _CorrectionAgent(["unfinished response", "still unfinished"])
    env = _OneStepEnv()
    result = run_unified_episode(
        env,
        agent,
        load_skill_provider("vanilla"),
        max_steps=1,
        record_trajectory=True,
    )

    assert env.actions == ["look"]
    assert result.success is True
    assert result.invalid_actions == 1
    assert result.invalid_requests == 1
    assert result.correction_attempts == 1
    assert result.correction_successes == 0
    assert result.uncorrected_invalid_requests == 1
    assert result.trajectory[0]["correction_succeeded"] is False
    assert result.trajectory[0]["correction_diagnostic"]["valid"] is False


def test_task_type_and_category_mapping():
    gf = (
        "json_2.1.1/valid_unseen/pick_heat_then_place_in_recep-Potato-None-"
        "Microwave-301/game.tw-pddl"
    )
    assert task_type_from_gamefile(gf) == "pick_heat_then_place_in_recep"
    assert task_type_from_gamefile("no match here") == "other"

    assert classify_alfworld_task("put a clean mug in/on desk 1.") == "clean"
    assert (
        classify_alfworld_task("look at alarm clock under the desklamp")
        == "look_at_obj_in_light"
    )
    assert classify_alfworld_task("heat some potato and put it on the table") == "heat"
    assert classify_alfworld_task("cool a tomato and place it on the counter") == "cool"
    assert classify_alfworld_task("put two candles on the toilet") == "pick_and_place"


def test_load_skill_providers():
    provider = load_skill_provider("vanilla")
    assert provider.view_for("x", "y").prefix == ""

    provider = load_skill_provider("skillopt")
    view = provider.view_for("any", "Your task is to: put a mug down.")
    assert "## Skill Knowledge" in view.prefix
    assert len(view.prefix) > 1000  # real released skill doc

    provider = load_skill_provider("skillrl")
    view_clean = provider.view_for("gf", "Your task is to: put a clean mug in/on desk 1.")
    view_heat = provider.view_for("gf", "Your task is to: heat some potato.")
    assert "### Clean Skills" in view_clean.body
    assert "### Heat Skills" in view_heat.body
    assert "### General Principles" in view_clean.body


def test_reasoning_model_think_block_is_restored():
    """A split `reasoning_content` must not make valid actions look invalid.

    Reasoning endpoints return CoT in a sibling field, so `content` starts
    mid-thought and carries only the orphaned `</think>`. Without rejoining,
    project_action sees no opening tag and marks every step invalid even when
    the action parsed and executed correctly.
    """
    # Tail of the CoT spilled into content, bringing the closing tag with it.
    spilled = _restore_think_block(
        "the alarmclock is elsewhere.\n</think>\n<action>look</action>", "Hmm, let me think."
    )
    assert spilled.count("</think>") == 1
    assert project_action(spilled) == ("look", True)

    # Clean split: content holds only the action, no tag at all.
    clean = _restore_think_block("<action>go to desk 1</action>", "I should go to desk 1")
    assert project_action(clean) == ("go to desk 1", True)

    # Non-reasoning models are untouched, and a genuine protocol violation
    # (no think tags, no reasoning field) must still be reported invalid.
    inline = "<think>abc</think><action>look</action>"
    assert _restore_think_block(inline, "") == inline
    assert project_action(_restore_think_block("<action>look</action>", "")) == ("look", False)


def test_rehearsed_action_in_cot_is_not_executed():
    """CoT that rehearses the output format must not hijack action extraction.

    project_action takes the *first* `<action>`, so splicing raw reasoning in
    front of the real action makes the parser read the rehearsal. Observed in a
    live run at 4/100 steps: the model wrote `<action>look</action>` while
    thinking, then committed to `inventory` — and `look` was executed.
    """
    restored = _restore_think_block(
        "So inventory it is.\n</think>\n<action>inventory</action>",
        "I could do <action>look</action> but that repeats; check inventory.",
    )
    assert project_action(restored) == ("inventory", True)
    # The rehearsal survives as readable text for error analysis, just defused.
    assert "[action]look[/action]" in restored


def test_closing_think_tag_inside_the_cot_does_not_split_early():
    """The boundary is the *last* `</think>`, not the first.

    This model quotes the protocol while reasoning, so a `</think>` can appear
    inside the CoT itself. Splitting there leaves the rest of the reasoning in
    the half the action is parsed from. Observed live at step 33: the agent
    executed `look` where the model had committed to `examine desk 1`.
    """
    restored = _restore_think_block(
        'reasoning MUST be in <think></think> tags.\n'
        "I'll examine the desk.\n</think>\n<action>examine desk 1</action>",
        "The alarmclock is likely on the desk.",
    )
    assert project_action(restored) == ("examine desk 1", True)


def test_vanilla_prompt_has_no_skill_artifacts():
    """The {skill_block} slot must vanish entirely when nothing is injected.

    vanilla/skillopt prompts are verbatim copies of the SkillRL/SkillOpt text, so
    an empty slot must not leave a doubled blank line behind.
    """
    p = build_user_prompt(OBS, CMDS)
    assert f"{OBS}\nYour admissible actions" in p
    assert "{skill_block}" not in p
    assert "\n\n\n" not in p


def test_skillrl_body_lands_before_the_state_and_protocol_reminder():
    """Retrieved experience belongs directly after the task line.

    SkillRL's own ALFWORLD_TEMPLATE_WITH_MEMORY puts the block between the task
    and the state; appending it at the end of the message instead would place it
    after "Do not output anything after </action>".
    """
    skill = SkillView(body="## Retrieved Relevant Experience\n- be systematic")
    for prompt in (
        build_user_prompt(
            OBS,
            CMDS,
            skill=skill,
            task_description="put a mug in/on desk 1.",
            history=[("obs one", "go to loc 1")],
            history_length=2,
        ),
        build_user_prompt(OBS, CMDS, skill=skill),
    ):
        body = prompt.index("## Retrieved Relevant Experience")
        assert body < prompt.index("admissible actions of the current situation")
        assert body < prompt.index("Do not output anything after")

    # In the with-history template the block sits directly after the task line,
    # matching SkillRL's ALFWORLD_TEMPLATE_WITH_MEMORY.
    with_history = build_user_prompt(
        OBS,
        CMDS,
        skill=skill,
        task_description="put a mug in/on desk 1.",
        history=[("obs one", "go to loc 1")],
        history_length=2,
    )
    assert with_history.index("Your task is to:") < with_history.index(
        "## Retrieved Relevant Experience"
    ) < with_history.index("Prior to this step")


def test_history_length_zero_sends_no_history():
    """history_length=0 means "no history", not "the whole history".

    Negative slicing made history[-0:] the entire list, so asking for zero turns
    of history silently sent every past observation instead.
    """
    p = build_user_prompt(
        OBS,
        CMDS,
        task_description="put a mug in/on desk 1.",
        history=[("OLD OBSERVATION", "old action")],
        history_length=0,
    )
    assert "OLD OBSERVATION" not in p
    assert "old action" not in p
    assert "Prior to this step" not in p  # no-history template


def test_agents_ignore_brackets_inside_injected_skill_text():
    """The admissible list is located by its label, not the first '['.

    A skill document is injected around the template, so a markdown link in the
    skill used to become the "action list" and silently degrade every step to
    `look` while the run still looked healthy.
    """
    prompt = "## Skill Knowledge\nsee [the docs](http://example.com)\n\n" + build_user_prompt(
        OBS, CMDS
    )
    assert extract_admissible_commands(prompt) == ["go to sinkbasin 1", "take mug 1"]

    action = project_action(RandomAgent(seed=0).respond(prompt)[0])[0]
    assert action in {"go to sinkbasin 1", "take mug 1"}


def test_extract_admissible_commands_returns_empty_when_label_absent():
    assert extract_admissible_commands("no action list here") == []


def test_episode_usage_is_a_delta_not_the_running_total():
    """Each episode records only the requests it issued.

    The agent is reused across episodes, so its accumulator is cumulative.
    Storing the running total per episode made summarize() sum those totals,
    overstating api_calls quadratically with episode count.
    """
    agent = _UsageAgent()
    env = _OneStepEnv()
    results = [
        run_unified_episode(env, agent, load_skill_provider("vanilla"), max_steps=1)
        for _ in range(3)
    ]
    assert [r.usage["api_calls"] for r in results] == [1, 1, 1]
    assert agent.usage.api_calls == 3  # the accumulator itself still totals

    summary = summarize(results)
    assert summary["usage"]["api_calls"] == 3
    assert summary["usage"]["prompt_tokens"] == 30


def test_result_row_round_trip_preserves_usage():
    """resume and merge rebuild episodes from results.jsonl rows."""
    result = EpisodeResult(
        gamefile="json_2.1.1/valid_seen/task/trial/game.tw-pddl",
        task_type="look_at_obj_in_light",
        success=True,
        steps=3,
        invalid_actions=1,
        termination_reason="success",
        usage={"prompt_tokens": 5, "completion_tokens": 2, "api_calls": 4, "api_errors": 1},
    )
    restored = result_from_row(result_row(result))
    assert restored.usage == result.usage
    assert restored.gamefile == result.gamefile
    assert restored.task_type == result.task_type
    assert restored.success is True
    assert restored.steps == 3
    assert restored.invalid_actions == 1
    assert restored.termination_reason == "success"

    # Rows written before usage was persisted must degrade to zero, not crash.
    legacy = result_row(result)
    del legacy["usage"]
    assert result_from_row(legacy).usage == {}
    assert summarize([result_from_row(legacy)])["usage"]["api_calls"] == 0


class _UsageAgent:
    """Mock-style agent that accounts tokens, like OpenAIChatAgent does."""

    name = "test"

    def __init__(self):
        self.usage = UsageAccumulator()

    def respond(self, user_prompt):
        usage = {"prompt_tokens": 10, "completion_tokens": 4}
        self.usage.add(usage)
        # A known-good protocol response, reused so this test cannot drift from
        # the real wire format.
        return FALLBACK_RESPONSE, usage


# Derived from the known-good wire literal instead of retyped, so the test
# cannot drift from the real protocol.
_OPEN_TAG, _, _REST = FALLBACK_RESPONSE.partition("empty")
_CLOSE_TAG = _REST.partition("<action>")[0].split()[-1]


def test_truncated_completion_is_diagnosed_as_truncation():
    """A completion cut off at max_tokens ends inside its reasoning.

    Observed live on trace2skill: responses arrived as ~16k-character think
    blocks with no <action> at all. The diagnostic blamed the missing tags, so
    the repair request never mentioned the real cause and 2 of 7 corrections
    failed -- each costing an extra full request.
    """
    cut_off = _OPEN_TAG + "long reasoning that never reaches an action" + _CLOSE_TAG

    d = diagnose_action(cut_off, ["look", "inventory"], truncated=True)
    assert d["truncated"] is True
    assert d["valid"] is False
    assert any("cut off" in issue for issue in d["issues"])

    prompt = build_correction_prompt("base prompt", cut_off, d)
    assert "ran out of output tokens" in prompt
    assert "at most one short sentence" in prompt

    # The same response without the flag keeps the old wording.
    plain = diagnose_action(cut_off, ["look", "inventory"])
    assert plain["truncated"] is False
    assert not any("cut off" in issue for issue in plain["issues"])
    assert "ran out of output tokens" not in build_correction_prompt("base", cut_off, plain)


def test_truncated_responses_are_counted_per_episode():
    """Truncation must be visible in the summary, not just the trajectory."""

    class _TruncatingAgent:
        name = "api"

        def __init__(self):
            self.usage = UsageAccumulator()
            self.last_finish_reason = "length"

        def respond(self, user_prompt):
            # Truncated: think block closed, no <action> emitted.
            self.usage.add({"prompt_tokens": 1, "completion_tokens": 1})
            return _OPEN_TAG + "cut off" + _CLOSE_TAG, {}

    agent = _TruncatingAgent()
    env = _OneStepEnv()
    result = run_unified_episode(env, agent, load_skill_provider("vanilla"), max_steps=1)

    assert result.truncated_responses == 2  # initial response + one correction
    assert result.uncorrected_invalid_requests == 1
    assert env.actions == ["look"]  # safe fallback still executed
    assert summarize([result])["corrections"]["truncated_responses"] == 2
    assert result_row(result)["truncated_responses"] == 2


def test_valid_first_response_records_trajectory_without_a_correction():
    """Trajectory rows are built for every step, including clean ones.

    A per-step variable bound only inside the correction branch made a valid
    first response crash the runner as soon as --record-trajectory was on.
    """
    agent = _UsageAgent()
    env = _OneStepEnv()
    result = run_unified_episode(
        env,
        agent,
        load_skill_provider("vanilla"),
        max_steps=1,
        record_trajectory=True,
    )
    assert result.correction_attempts == 0
    assert result.truncated_responses == 0
    assert result.trajectory[0]["correction_attempted"] is False
    assert result.trajectory[0]["truncated"] is False
    assert result.trajectory[0]["valid"] is True
