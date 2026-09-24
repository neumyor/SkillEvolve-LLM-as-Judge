"""Only replacement costs count, even when all stages use the same LLM backend."""
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import pytest

from skillopt.evaluation.usage_ledger import UsageLedger

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from compare_replacement_tokens import compare  # noqa: E402


def ledger(root, mode, method="gepa"):
    result = UsageLedger(root / "usage_events.jsonl")
    result.configure_replacement_cost(method, mode)
    return result


def record(target, prompt, completion):
    target.record({"prompt_tokens": prompt, "completion_tokens": completion}, stage="same_backend")


def test_compare_excludes_other_stages_and_resumes(tmp_path):
    base = ledger(tmp_path / "baseline", "baseline")
    record(base, 9000, 9000)  # Normal training.
    with base.capture_replacement("candidate_validation"):
        with ThreadPoolExecutor(2) as workers:
            list(workers.map(lambda _: record(base, 100, 20), range(2)))
    record(base, 8000, 8000)  # Final test.
    base = ledger(tmp_path / "baseline", "baseline")
    with base.capture_replacement("candidate_minibatch"):
        record(base, 100, 20)
    judged = ledger(tmp_path / "judge", "judge")
    with judged.capture_replacement("llm_judge"):
        record(judged, 50, 10)
    record(judged, 7000, 7000)  # Reflection.
    result = compare(tmp_path / "baseline", tmp_path / "judge")
    assert result["baseline_rerun"] == {"prompt_tokens": 300, "completion_tokens": 60, "total_tokens": 360}
    assert result["llm_judge"]["total_tokens"] == 60
    assert result["saved_tokens"] == 300
    assert result["saving_fraction"] == pytest.approx(5 / 6)


def test_zero_baseline_and_missing_usage_do_not_fabricate_savings(tmp_path):
    base = ledger(tmp_path / "baseline", "baseline")
    judged = ledger(tmp_path / "judge", "judge")
    assert compare(base.path.parent, judged.path.parent)["saving_fraction"] is None
    with judged.capture_replacement("llm_judge"):
        judged.record(None, stage="judge")
    assert compare(base.path.parent, judged.path.parent)["saved_tokens"] is None


def test_legacy_records_cannot_be_relabelled_as_zero_cost(tmp_path):
    target = UsageLedger(tmp_path / "usage_events.jsonl")
    record(target, 10, 20)
    with pytest.raises(ValueError, match="Legacy usage"):
        target.configure_replacement_cost("gepa", "baseline")


def test_judge_meter_counts_retries_without_double_counting_backend(tmp_path):
    from skillopt.evaluation.judge_gate import JudgeGate
    target = ledger(tmp_path, "judge")
    calls = []
    def chat(**kwargs):
        calls.append(True)
        record(target, 10, 2)
        return ("invalid" if len(calls) == 1 else json.dumps({
            "verdict": "ACCEPT", "confidence": "medium", "reason": "observed repair"
        })), {"prompt_tokens": 10, "completion_tokens": 2}
    judge = JudgeGate(chat_fn=chat, prompt_variant="v3")
    judge.replacement_ledger = target
    judge(candidate_skill="new", current_skill="old", current_score=0,
          best_skill="old", best_score=0, best_step=0, global_step=1)
    assert target.replacement_summary()["total_tokens"] == 24
    assert len(target.events()) == 2


def test_skillgen_excludes_case_analysis_and_revision_guidance(tmp_path, monkeypatch):
    import llm
    import agents.verification as verification
    from models import CandidateSkill, CaseAnalysis, TaskType
    llm.reset_token_stats()
    target = llm.initialize_token_ledger(tmp_path / "usage_events.jsonl")
    target.configure_replacement_cost("skillgen", "baseline")
    def effectiveness(*args, **kwargs):
        llm.record_external_usage({"prompt_tokens": 100, "completion_tokens": 20}, model="fake")
        return SimpleNamespace(cases=[{"instance_id": "a", "outcome": "repair"}], diagnostic_summary="repair"), {}
    def analyse(*args, **kwargs):
        llm.record_external_usage({"prompt_tokens": 900, "completion_tokens": 90}, model="fake")
        return CaseAnalysis("a", "repair", "reason", "helped", "keep")
    def guidance(*args, **kwargs):
        llm.record_external_usage({"prompt_tokens": 800, "completion_tokens": 80}, model="fake")
        return "keep"
    monkeypatch.setattr(verification, "verify_effectiveness", effectiveness)
    monkeypatch.setattr(verification, "_analyse_one_case", analyse)
    monkeypatch.setattr(verification, "_synthesise_revision_guidance", guidance)
    verification.run_verification(CandidateSkill("c", "a", "body", ""), [], [], next(iter(TaskType)))
    assert target.replacement_summary()["total_tokens"] == 120
    assert target.summary()["total_tokens"] == 1990
    llm.reset_token_stats()


def test_qwen_missing_usage_is_unknown_instead_of_free(tmp_path):
    from skillopt.model.common import TokenTracker, configure_usage_ledger
    from skillopt.model.qwen_backend import _usage_from_payload
    target = configure_usage_ledger(tmp_path / "usage_events.jsonl")
    target.configure_replacement_cost("skillopt", "baseline")
    usage = _usage_from_payload({})
    with target.capture_replacement("candidate_validation"):
        TokenTracker().record("rollout", usage["prompt_tokens"], usage["completion_tokens"],
                              usage_complete=usage["usage_complete"])
    assert target.replacement_summary()["usage_complete"] is False
    configure_usage_ledger(None)


def test_skillgen_qwen_judge_thinking_override_reaches_api(monkeypatch):
    import llm
    calls = []
    response = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="ok", tool_calls=None))])
    monkeypatch.setattr(llm, "_router_chat_create", lambda **kwargs: calls.append(kwargs) or response)
    monkeypatch.setattr(llm, "_record_usage", lambda *args, **kwargs: None)
    llm.chat("judge", model="qwen3.7-plus", max_tokens=512, enable_thinking=False)
    assert calls[0]["extra_body"] == {"enable_thinking": False}
    assert calls[0]["max_tokens"] == 512


def test_judge_reaches_real_skillopt_backend_retry_loop(monkeypatch, tmp_path):
    from skillopt.evaluation.judge_gate import JudgeGate
    from skillopt.model import qwen_backend
    from skillopt.model.common import configure_usage_ledger
    requests = []
    def respond(payload, timeout, config):
        requests.append(payload)
        return {"choices": [{"message": {"content": json.dumps({"verdict": "ACCEPT", "confidence": "medium", "reason": "repair"})}}],
                "usage": {"prompt_tokens": 50, "completion_tokens": 20}}
    monkeypatch.setattr(qwen_backend, "_post_chat_completion", respond)
    monkeypatch.setenv("QWEN_CHAT_API_KEY", "test-only")
    monkeypatch.setenv("QWEN_CHAT_BASE_URL", "https://example.invalid/v1")
    ledger = configure_usage_ledger(tmp_path / "usage_events.jsonl")
    ledger.configure_replacement_cost("skillopt", "judge")
    judge = JudgeGate(chat_fn=qwen_backend.chat_optimizer, prompt_variant="v3")
    judge.replacement_ledger = ledger
    result, record = judge(candidate_skill="new", current_skill="old", current_score=0,
                          best_skill="old", best_score=0, best_step=0, global_step=1)
    assert len(requests) == 1
    assert result.action == "accept_new_best"
    assert ledger.replacement_summary()["total_tokens"] == 70
    configure_usage_ledger(None)


def test_compare_command_reports_negative_savings_when_judge_costs_more(tmp_path):
    import subprocess
    base = ledger(tmp_path / "baseline", "baseline")
    judged = ledger(tmp_path / "judge", "judge")
    with base.capture_replacement("candidate_validation"):
        record(base, 10, 2)
    with judged.capture_replacement("llm_judge"):
        record(judged, 20, 4)
    script = Path(__file__).resolve().parents[1] / "scripts/compare_replacement_tokens.py"
    result = subprocess.run([sys.executable, str(script), "--baseline", str(base.path.parent),
                             "--judge", str(judged.path.parent)], check=True, capture_output=True, text=True)
    payload = json.loads(result.stdout)
    assert payload["saved_tokens"] == -12
    assert payload["saving_fraction"] == -1
