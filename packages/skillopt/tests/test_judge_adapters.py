"""The adapters read pre-existing evidence; candidate measurements are ignored."""
import json
from types import SimpleNamespace as NS

import pytest
from skillopt.evaluation.adapters import GEPAJudgeAcceptanceCriterion, SkillGenJudgeAdapter
from skillopt.evaluation.judge_gate import JudgeGate, available_judge_prompt_variants, register_judge_prompt_variant


def test_prompt_versions_have_a_stable_registration_interface():
    assert {"v1", "v2", "v3"}.issubset(available_judge_prompt_variants())
    register_judge_prompt_variant("smoke", "Return a JSON verdict.", replace=True)
    assert "smoke" in available_judge_prompt_variants()


def judge():
    def chat(**kwargs):
        assert "SECRET GOLD ANSWER" not in kwargs["user"]
        assert "CANDIDATE RESULT MUST NOT LEAK" not in kwargs["user"]
        assert "existing_output" in kwargs["user"]
        return json.dumps({"verdict": "ACCEPT", "confidence": "high", "reason": "Addresses the observed failure."}), {}
    return JudgeGate(chat_fn=chat, prompt_variant="v3")


def test_gepa_uses_only_parent_evidence():
    proposal = NS(
        candidate={"skill": "new"}, parent_program_ids=[0], subsample_indices=["a"],
        eval_before=NS(scores=[0.], outputs=["failure"], trajectories=[{"nested": {"ground_truth": "SECRET GOLD ANSWER"}}]),
        eval_after=NS(outputs=["CANDIDATE RESULT MUST NOT LEAK"]), metadata={},
    )
    state = NS(program_candidates=[{"skill": "old"}], i=0)
    assert GEPAJudgeAcceptanceCriterion(judge()).should_accept(proposal, state)
    assert proposal.metadata["judge_gate"]["candidate_executions"] == 0


def test_skillgen_reads_existing_trajectories_and_strips_nested_privileged_fields():
    trajectory = NS(instance_id="a", final_output="failure", messages=[{"nested": {"ground_truth": "SECRET GOLD ANSWER"}}], success=False)
    instance = NS(input="question", metadata={})
    accepted, record = SkillGenJudgeAdapter(judge()).decide(
        candidate_skill="new", current_skill="", trajectories=[trajectory], instances={"a": instance},
    )
    assert accepted and record["candidate_executions"] == 0


def test_skillgen_empty_evidence_fails_closed():
    accepted, record = SkillGenJudgeAdapter(judge()).decide(
        candidate_skill="new", current_skill="", trajectories=[], instances={},
    )
    assert not accepted and "missing" in record["judge_error"]


@pytest.mark.parametrize("adapter", [GEPAJudgeAcceptanceCriterion, SkillGenJudgeAdapter])
def test_adapters_forbid_full_validation(adapter):
    with pytest.raises(ValueError, match="forbids"):
        adapter(full_validation=lambda: pytest.fail("must not execute"))
