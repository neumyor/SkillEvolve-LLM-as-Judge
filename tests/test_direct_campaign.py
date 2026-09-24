import json
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import run_direct_campaign as campaign


def test_prepare_keeps_controls_equal_and_isolates_outputs(tmp_path):
    campaign.prepare(tmp_path, "test-model", "https://example.invalid/v1")
    manifest = campaign.read(tmp_path / "manifest.json")
    assert len(manifest["settings"]) == 32
    for phase in ("smoke", "full"):
        for benchmark in campaign.BENCHMARKS:
            for method in campaign.METHODS:
                key = f"{phase}/{benchmark}_{method}"
                a, b = [manifest["settings"][key + "_" + mode] for mode in campaign.MODES]
                assert a["counts"] == b["counts"]
                assert a["output"] != b["output"]
                normalize = lambda command: [part.replace("_baseline", "_MODE").replace("_judge", "_MODE")
                                             if part not in ("baseline", "judge") else "MODE" for part in command]
                assert normalize(a["command"]) == normalize(b["command"])
                assert "--full-validation-audit" not in a["command"]
                if method == "gepa":
                    config = campaign.read(a["config"])
                    assert config == campaign.read(b["config"])
                    opts = config["builder_kwargs"]
                    assert opts["workers"] == 100
                    assert opts["max_metric_calls"] > a["counts"]["val"] + 2 * opts["reflection_minibatch_size"]
                elif method == "skillgen":
                    config = yaml.safe_load(Path(a["config"]).read_text())
                    assert config["pipeline"]["max_workers"] == 100
                    assert config["generation"]["candidate_output_dir"].startswith(a["output"])
    campaign.verify_inputs(manifest)
    with pytest.raises(ValueError, match="already prepared"):
        campaign.prepare(tmp_path, "other-model", "https://example.invalid/v1")


def test_audit_does_not_accept_exit_artifacts_without_actual_gate(tmp_path):
    from skillopt.evaluation.usage_ledger import UsageLedger
    spec = {"output": str(tmp_path), "method": "gepa", "mode": "judge", "counts": {"test": 2}}
    for name in ("result.json", "run_metadata.json", "validation_eval.json", "test_eval.json"):
        campaign.write(tmp_path / name, {"items": 2})
    ledger = UsageLedger(tmp_path / "usage_events.jsonl")
    ledger.configure_replacement_cost("gepa", "judge")
    ledger.record({"prompt_tokens": 100, "completion_tokens": 1}, stage="train")
    report = campaign.audit(spec, smoke=True)
    assert not report["passed"]
    assert "smoke did not exercise llm_judge" in report["failures"]
    with ledger.capture_replacement("llm_judge"):
        ledger.record({"prompt_tokens": 10, "completion_tokens": 1}, stage="judge")
    assert campaign.audit(spec, smoke=True)["passed"]
    with ledger.capture_replacement("candidate_validation"):
        ledger.record({"prompt_tokens": 10, "completion_tokens": 1}, stage="validation")
    assert not campaign.audit(spec, smoke=True)["passed"]


def _completed_spec(tmp_path, method="gepa"):
    spec = {"output": str(tmp_path), "method": method, "mode": "baseline", "counts": {"test": 2}}
    names = ("result.json", "run_metadata.json", "validation_eval.json", "test_eval.json") if method == "gepa" else ("validation_summary.json", "test_summary.json")
    for name in names:
        campaign.write(tmp_path / name, {"items": 2})
    from skillopt.evaluation.usage_ledger import UsageLedger
    ledger = UsageLedger(tmp_path / "usage_events.jsonl")
    ledger.configure_replacement_cost(method, "baseline")
    return spec, ledger


def test_missing_usage_does_not_invalidate_completed_run_or_invent_tokens(tmp_path):
    spec, ledger = _completed_spec(tmp_path)
    with ledger.capture_replacement("candidate_validation"):
        ledger.record(None, stage="evolution_execution", item_id="unknown")
    report = campaign.audit(spec, smoke=False)
    assert report["passed"]
    assert not report["replacement_usage_complete"]
    assert report["warnings"]
    assert not campaign.audit(spec, smoke=True)["passed"]
    assert not ledger.replacement_summary()["usage_complete"]


@pytest.mark.parametrize("error,passed", [("InternalServerError: Error code: 500 - content rejected", True), ("ValueError: bad shape", False), ("HTTP Error 429: throttled", False)])
def test_skillgen_http500_is_recorded_as_failed_execution(tmp_path, error, passed):
    spec, ledger = _completed_spec(tmp_path, "skillgen")
    campaign.write(tmp_path / "run/runs/one/baseline_units/1.json", {
        "instance_id": "1", "success": False, "score": 0,
        "metadata": {"agent_exception": "error"}, "error_summary": error})
    report = campaign.audit(spec, smoke=False)
    assert report["passed"] is passed
    assert len(report["recorded_http_500_failures"]) == int(passed)


def test_gepa_http500_keeps_unknown_usage_and_zero_score(tmp_path):
    spec, ledger = _completed_spec(tmp_path)
    with ledger.capture_replacement("candidate_validation"):
        ledger.record(None, stage="evolution_execution", agent_ok=False, score=0,
                      fail_reason="RuntimeError: HTTP Error 500: Internal Server Error")
    report = campaign.audit(spec, smoke=False)
    assert report["passed"]
    assert len(report["recorded_http_500_failures"]) == 1
    assert not report["replacement_usage_complete"]
