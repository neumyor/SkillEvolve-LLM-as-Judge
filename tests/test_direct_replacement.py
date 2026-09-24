"""Offline behavioral smoke tests: evaluators fail if candidate acceptance reruns tasks."""
import json
from dataclasses import asdict
from types import SimpleNamespace

import pytest

from skillopt.evaluation.judge_gate import JudgeGate
from skillopt.evaluation.evidence import select_evidence


def response(verdict="ACCEPT", changes=None):
    payload = {"verdict": verdict, "confidence": "medium", "reason": "Repairs the observed failure while preserving successes."}
    if changes is not None:
        payload["predicted_changes"] = changes
    return json.dumps(payload)


def test_gepa_evolves_without_child_or_validation_execution(tmp_path):
    from gepa import optimize
    from gepa.core.adapter import EvaluationBatch
    from gepa.utils.stop_condition import MaxCandidateProposalsStopper
    from judge_policy import JudgePredictionPolicy
    from skillopt.evaluation.adapters import GEPAJudgeAcceptanceCriterion
    from skillopt.evaluation.usage_ledger import UsageLedger

    cost_ledger = UsageLedger(tmp_path / "usage_events.jsonl")
    cost_ledger.configure_replacement_cost("gepa", "judge")

    class Adapter:
        propose_new_texts = None
        usage_ledger = cost_ledger

        def __init__(self):
            self.calls = []

        def evaluate(self, batch, candidate, capture_traces=False):
            assert capture_traces, "Validation must not execute"
            assert all(row["split"] == "train" for row in batch)
            # The scripted second proposal is rejected, so it must never execute.
            assert candidate["skill"] != "child2"
            self.calls.append(candidate["skill"])
            cost_ledger.record({"prompt_tokens": 100, "completion_tokens": 20}, stage="rollout")
            return EvaluationBatch(outputs=["observed failure"] * len(batch), scores=[0.] * len(batch),
                                   trajectories=[{"question": "training question", "task_type": "a"}] * len(batch))

        def make_reflective_dataset(self, candidate, eval_batch, components_to_update):
            return {key: [{"Inputs": "question", "Generated Outputs": "failure", "Feedback": "failed"}]
                    for key in components_to_update}

    calls = []
    def chat(**kwargs):
        calls.append(kwargs)
        assert "candidate has NOT been executed" in kwargs["user"]
        return response("ACCEPT" if len(calls) == 1 else "REJECT", {"a": 1, "b": -1}), {"prompt_tokens": 10, "completion_tokens": 5}

    proposed = []
    def proposer(candidate, reflective_dataset, components_to_update, **kwargs):
        proposed.append(candidate)
        return {"skill": f"child{len(proposed)}"}

    adapter = Adapter()
    judge = JudgeGate(chat_fn=chat, prompt_variant="v3")
    judge.replacement_ledger = cost_ledger
    result = optimize(
        seed_candidate={"skill": "seed"}, trainset=[{"split": "train"}],
        valset=[{"split": "heldout"}], adapter=adapter,
        custom_candidate_proposer=proposer, reflection_minibatch_size=1,
        skip_perfect_score=False, max_metric_calls=20,
        stop_callbacks=[MaxCandidateProposalsStopper(2)],
        acceptance_criterion=GEPAJudgeAcceptanceCriterion(judge, prediction_axes=["a", "b"]),
        val_evaluation_policy=JudgePredictionPolicy(["a", "b"]),
        run_dir=str(tmp_path), display_progress_bar=False, raise_on_exception=True,
    )
    assert len(calls) == 2 and len(proposed) == 2
    assert len(adapter.calls) == 2  # Only parents executed to generate proposals.
    assert result.total_metric_calls == 2 and result.num_full_val_evals == 0
    assert result.val_subscores == [{"a": 0., "b": 0.}, {"a": 1., "b": -1.}]
    assert result.per_val_instance_best_candidates == {"a": {1}, "b": {0}}
    assert result.metadata["score_source"] == "judge_prediction"
    assert result.best_idx == 0  # Latest accepted is NOT automatically the best.
    assert cost_ledger.replacement_summary()["total_tokens"] == 30
    assert set(cost_ledger.replacement_summary()["components"]) == {"llm_judge"}


def test_gepa_baseline_still_performs_official_regression_steps(tmp_path):
    from gepa import optimize
    from gepa.core.adapter import EvaluationBatch
    from gepa.utils.stop_condition import MaxCandidateProposalsStopper
    from skillopt.evaluation.usage_ledger import UsageLedger

    cost_ledger = UsageLedger(tmp_path / "usage_events.jsonl")
    cost_ledger.configure_replacement_cost("gepa", "baseline")

    calls = []
    class Adapter:
        propose_new_texts = None
        usage_ledger = cost_ledger
        def evaluate(self, batch, candidate, capture_traces=False):
            calls.append((candidate["skill"], batch[0]["split"], len(batch)))
            cost_ledger.record({"prompt_tokens": 10 * len(batch), "completion_tokens": 2 * len(batch)}, stage="rollout")
            return EvaluationBatch(outputs=["out"] * len(batch),
                                   scores=[float(candidate["skill"] == "child")] * len(batch),
                                   trajectories=[{"observed": "failure"}] * len(batch) if capture_traces else None)
        def make_reflective_dataset(self, candidate, eval_batch, components_to_update):
            return {"skill": [{"Inputs": "question", "Generated Outputs": "out", "Feedback": "failed"}]}
    result = optimize(seed_candidate={"skill": "seed"}, trainset=[{"split": "train"}],
                      valset=[{"split": "val"}, {"split": "val"}], adapter=Adapter(),
                      custom_candidate_proposer=lambda *args, **kwargs: {"skill": "child"},
                      reflection_minibatch_size=1, skip_perfect_score=False,
                      max_metric_calls=20, stop_callbacks=[MaxCandidateProposalsStopper(1)],
                      run_dir=str(tmp_path), display_progress_bar=False, raise_on_exception=True)
    assert calls == [("seed", "val", 2), ("seed", "train", 1), ("child", "train", 1), ("child", "val", 2)]
    assert result.total_metric_calls == 6
    assert result.best_candidate == {"skill": "child"}
    assert result.metadata["score_source"] == "measured_validation"
    # Seed validation (2), child minibatch (1), accepted child validation (2).
    # The parent training minibatch (1) is NOT charged to replacement cost.
    cost = cost_ledger.replacement_summary()
    assert cost["total_tokens"] == 60
    assert cost["components"]["candidate_minibatch"]["total_tokens"] == 12


@pytest.mark.parametrize("verdicts, expected_active", [(["ACCEPT"], True), (["REJECT", "ACCEPT"], True), (["REJECT", "REJECT"], False)])
def test_skillgen_direct_gate_and_official_first_pass_stop(tmp_path, monkeypatch, verdicts, expected_active):
    import pipeline
    import llm
    from models import CandidateSkill, SkillAnalysis, SkillItem, SkillStatus, TaskInstance, TaskType, Trajectory

    cfg = {"llm": {"temperature": 0}, "pipeline": {"max_refine_rounds": 2, "artifact_root": str(tmp_path / "runs")},
           "generation": {"use_web_search": False}, "skill_output": {"path": str(tmp_path / "skills")},
           "judge": {"enabled": True, "prompt_variant": "v3"}}
    monkeypatch.setattr(pipeline, "load_config", lambda _: cfg)
    instances = [TaskInstance("a", "question a"), TaskInstance("b", "question b")]
    trajectories = [Trajectory("ta", "a", {}, [{"role": "assistant", "content": "failure"}], "wrong", False),
                    Trajectory("tb", "b", {}, [], "right", True)]
    monkeypatch.setattr(pipeline, "collect_trajectories", lambda *a, **k: trajectories)
    analysis = SkillAnalysis("analysis", None, None, "qa", "repair failures", 2, 1, 1)
    def induct(*args, **kwargs):
        pipeline.write_json(kwargs["artifact_dir"] / "skill_analysis.json", asdict(analysis))
        return analysis
    monkeypatch.setattr(pipeline, "run_induction", induct)
    monkeypatch.setattr(pipeline, "load_analysis", lambda _: analysis)
    monkeypatch.setattr(pipeline, "save_analysis", lambda *a: None)
    generated = []
    def generate(*args, **kwargs):
        generated.append(True)
        return CandidateSkill("c1", "analysis", "first", "abstract", scripts=["SCRIPT CONTENT"])
    def refine(candidate, analysis, feedback, **kwargs):
        assert feedback.effectiveness is None
        assert "Judge prediction" in feedback.revision_guidance
        return CandidateSkill("c2", "analysis", "second", "abstract")
    monkeypatch.setattr(pipeline, "generate_skill", generate)
    monkeypatch.setattr(pipeline, "refine_skill", refine)
    monkeypatch.setattr(pipeline, "run_verification", lambda *a, **k: pytest.fail("candidate verification executed"))
    finalized = []
    def finalize(candidate, *args, **kwargs):
        finalized.append(candidate)
        return SkillItem(f"final-{len(finalized)}", candidate.body, candidate.contextual_abstract)
    monkeypatch.setattr(pipeline, "finalize_skill", finalize)
    monkeypatch.setattr(pipeline, "save_skill", lambda *a: None)
    calls = []
    def chat(**kwargs):
        if not calls:
            assert "SCRIPT CONTENT" in kwargs["user"]
        calls.append(kwargs)
        assert "predicted_changes" not in kwargs["system"]
        return response(verdicts[len(calls) - 1]), {}
    task_type = next(iter(TaskType))
    skill = pipeline.run_pipeline(instances, task_type, judge_chat_fn=chat)
    assert len(calls) == len(verdicts)
    assert (skill.status == SkillStatus.ACTIVE) is expected_active
    assert skill.verification_history[0]["net_gain"] is None
    run_dir = next((tmp_path / "runs").iterdir())
    resumed = pipeline.run_pipeline(instances, task_type, judge_chat_fn=chat, resume_dir=str(run_dir))
    assert len(calls) == len(verdicts) and len(generated) == 1
    assert resumed.status == skill.status
    assert resumed.skill_id == skill.skill_id and len(finalized) == 1
    llm.reset_token_stats()

    # Baseline retains the official measured gate and stops on its first pass.
    if verdicts == ["ACCEPT"]:
        cfg["pipeline"]["artifact_root"] = str(tmp_path / "baseline_runs")
        verification_calls = []
        def verify(*args, **kwargs):
            from models import VerificationFeedback, EffectivenessResult
            verification_calls.append(True)
            eff = EffectivenessResult(passed=True, n_target=1, n_boundary=1, paired_n=2, baseline_acc=.5, skill_acc=1.,
                repair_count=1, regression_count=0, repair_rate=1., regression_rate=0., net_gain=1,
                target_repair_count=1, target_fail_count=0, success_guard_regression_count=0, success_guard_pass_count=1,
                repaired_ids=["a"], regression_ids=[], failed_ids_after_skill=[], diagnostic_summary="measured repair")
            return VerificationFeedback(effectiveness=eff), {}
        monkeypatch.setattr(pipeline, "run_verification", verify)
        baseline = pipeline.run_pipeline(instances, task_type, judge_overrides={"enabled": False})
        assert len(verification_calls) == 1
        assert baseline.verification_history[0]["net_gain"] == 1
        baseline_run = next((tmp_path / "baseline_runs").iterdir())
        recovered = pipeline.run_pipeline(instances, task_type, judge_overrides={"enabled": False}, resume_dir=str(baseline_run))
        assert recovered.skill_id == baseline.skill_id
        assert len(verification_calls) == 1
        # Simulate a stop after the round decision but before final persistence.
        (baseline_run / "pipeline_complete.json").unlink()
        pipeline.run_pipeline(instances, task_type, judge_overrides={"enabled": False}, resume_dir=str(baseline_run))
        assert len(verification_calls) == 1 and len(generated) == 2
        llm.reset_token_stats()


def test_evidence_balances_outcomes_and_types_and_deduplicates():
    rows = [{"id": str(i), "task_type": "a" if i < 4 else "b", "hard": i % 2} for i in range(8)]
    selected, counts = select_evidence([{"results": rows + rows}], 4)
    assert {(r["task_type"], r["hard"]) for r, _ in selected} == {("a", 0), ("a", 1), ("b", 0), ("b", 1)}
    assert counts == {"available": 16, "unique": 8, "shown": 4, "omitted": 12}


def test_usage_ledger_retains_retries_and_resume(tmp_path):
    from skillopt.evaluation.usage_ledger import UsageLedger
    ledger = UsageLedger(tmp_path / "usage.jsonl")
    ledger.record({"prompt_tokens": 10, "completion_tokens": 2}, stage="judge")
    resumed = UsageLedger(ledger.path)
    resumed.record({"prompt_tokens": 10, "completion_tokens": 3}, stage="judge")
    assert resumed.summary()["total_tokens"] == 25
    resumed.record(None, stage="failed_request")
    assert resumed.summary()["usage_complete"] is False


def test_judge_retry_usage_and_local_extension_validation():
    responses = iter([response(changes={"type": True}), response(changes={"type": 1})])
    requests = []
    def chat(**kwargs):
        requests.append(kwargs)
        return next(responses), {"prompt_tokens": 10, "completion_tokens": 5}
    gate = JudgeGate(chat_fn=chat, prompt_variant="v3")
    result, record = gate(candidate_skill="new", current_skill="old", current_score=0,
                          best_skill="old", best_score=0, best_step=0, global_step=1,
                          prediction_axes=["type"], batches=[{"results": [{"judge_evidence": "failure"}]}])
    assert result.action == "accept_new_best" and record["judge_calls"] == 2
    assert record["judge_usage"]["total_tokens"] == 30
    assert all(req["max_completion_tokens"] == 512 for req in requests)


def test_skillopt_usage_restores_and_does_not_double_count(tmp_path):
    from skillopt.model import get_token_summary, reset_token_tracker
    from skillopt.model.common import TokenTracker, configure_usage_ledger
    from skillopt.model.azure_openai import TokenTracker as AzureTracker
    path = tmp_path / "usage.jsonl"
    reset_token_tracker()
    configure_usage_ledger(path)
    TokenTracker().record("judge", 10, 2)
    AzureTracker().record("rollout", 20, 3)
    reset_token_tracker()
    configure_usage_ledger(path)
    TokenTracker().record("judge", 5, 1)
    assert get_token_summary()["_total"]["total_tokens"] == 41
    assert get_token_summary()["judge"]["calls"] == 2
    reset_token_tracker()


def test_skillgen_final_eval_does_not_use_rejected_skill(tmp_path, monkeypatch):
    import main
    from models import SkillItem, SkillStatus
    config = tmp_path / "config.yaml"
    config.write_text("models: {}\nllm: {}\n")
    args = SimpleNamespace(output_dir=str(tmp_path), config=str(config), alfworld_config=None,
                           validation_items="manifest", test_items=None, benchmark="searchqa", full_validation_audit=False)
    dataset = SimpleNamespace(metadata={"benchmark": "searchqa"}, instances=["one"], task_type="qa")
    monkeypatch.setattr(main, "load_benchmark_dataset", lambda *a, **k: dataset)
    calls = []
    def collect(*args, **kwargs):
        calls.append(kwargs)
        assert not kwargs.get("skill"), "Rejected skill must not be evaluated as selected output"
        return [SimpleNamespace(success=True)]
    monkeypatch.setattr(main, "collect_trajectories", collect)
    monkeypatch.setattr(main, "write_trajectories", lambda *a: None)
    main._run_final_evaluations(args, dataset, SkillItem("c", "rejected", "", status=SkillStatus.DEPRECATED))
    assert len(calls) == 1
    summary = json.loads((tmp_path / "validation_summary.json").read_text())
    assert summary["delta"] == 0


def test_skillgen_task_checkpoint_is_bound_to_candidate(tmp_path, monkeypatch):
    import trajectory
    from models import TaskInstance, TaskType, Trajectory, SkillItem
    calls = []
    def run(instance, *args):
        calls.append(instance.instance_id)
        return Trajectory("t" + instance.instance_id, instance.instance_id, {}, [], "answer", True)
    monkeypatch.setattr(trajectory, "_run_and_eval", run)
    kwargs = dict(checkpoint_dir=str(tmp_path), max_workers=1)
    instances = [TaskInstance("a", "question a"), TaskInstance("b", "question b")]
    task_type = next(iter(TaskType))
    trajectory.collect_trajectories(instances, task_type, **kwargs)
    trajectory.collect_trajectories(instances, task_type, **kwargs)
    assert calls == ["a", "b"]
    trajectory.collect_trajectories(instances, task_type, skill=SkillItem("c", "new skill", ""), **kwargs)
    assert calls == ["a", "b", "a", "b"]
