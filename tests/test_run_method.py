from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import run_method  # noqa: E402
from rethinkskill_study import local_config


@pytest.fixture(autouse=True)
def isolated_outputs(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)


def _args(*argv: str):
    return run_method._parser().parse_args(list(argv))


def test_full_validation_audit_is_off_by_default_for_all_methods():
    cases = {
        "skillopt": ("--config", "config.yaml"),
        "gepa": ("--config", "config.json"),
        "skillgen": ("--benchmark", "searchqa"),
    }
    for method, extra in cases.items():
        args = _args("--method", method, "--mode", "judge", *extra)
        command, _ = run_method.build_command(args)
        assert args.full_validation_audit is False
        assert "--full-validation-audit" not in command
        if method == "skillopt":
            # SkillOpt receives an explicit false override so a config that was
            # authored with audit=true cannot silently change the campaign default.
            assert command[command.index("--judge_full_validation_audit") + 1] == "false"


def test_unified_launcher_pins_qwen_endpoint_and_benchmark_environment():
    args = _args(
        "--method", "skillopt", "--benchmark", "searchqa", "--mode", "judge",
        "--config", "config.yaml", "--model", "qwen3.7-plus",
        "--base-url", "https://example.invalid/v1", "--api-key", "secret",
    )
    command, env = run_method.build_command(args)
    assert command[0].endswith("packages/skillopt/.venv/bin/python")
    assert "model.backend=qwen_chat" in command
    assert command[command.index("--qwen_chat_base_url") + 1] == "https://example.invalid/v1"
    assert command[command.index("--qwen_chat_thinking_mode") + 1] == "disabled"
    assert command[command.index("--split_dir") + 1].endswith("packages/skillopt/data/searchqa_split")
    assert env["QWEN_CHAT_MODEL"] == "qwen3.7-plus"

    args = _args(
        "--method", "skillgen", "--benchmark", "alfworld", "--mode", "judge",
    )
    _, env = run_method.build_command(args)
    assert run_method._python_for(args).endswith("packages/alfworld-eval/.venv/bin/python")
    assert env["ALFWORLD_DATA"].endswith("packages/alfworld-eval/.data/alfworld")
    assert env["ALFWORLD_CONFIG"].endswith("packages/alfworld-eval/configs/textworld.yaml")

    skillopt_args = _args(
        "--method", "skillopt", "--benchmark", "alfworld", "--mode", "baseline",
        "--config", "config.yaml",
    )
    assert run_method._python_for(skillopt_args).endswith(
        "packages/skillopt/.venv-alfworld/bin/python"
    )


def test_external_alfworld_root_comes_from_local_setting(tmp_path, monkeypatch):
    benchmark = tmp_path / "external-alfworld"
    python = benchmark / ".venv/bin/python"
    python.parent.mkdir(parents=True)
    python.touch()
    monkeypatch.setenv("ALFWORLD_BENCHMARK_ROOT", str(benchmark))
    args = _args("--method", "rethinkskill", "--benchmark", "alfworld",
                 "--mode", "judge", "--model", "example-model",
                 "--base-url", "https://example.invalid/v1")
    command, env = run_method.build_command(args)
    assert command[0] == str(python)
    assert command[command.index("--alfworld-config") + 1] == str(
        benchmark / "configs/rethinkskill_official.yaml")
    assert env["ALFWORLD_BENCHMARK_ROOT"] == str(benchmark)


def test_missing_external_root_fails_clearly(tmp_path, monkeypatch):
    monkeypatch.delenv("ALFWORLD_BENCHMARK_ROOT", raising=False)
    monkeypatch.setattr(local_config, "CONFIG_PATH", tmp_path / "missing.json")
    with pytest.raises(ValueError, match="alfworld_benchmark_root"):
        local_config.benchmark_root()


def test_api_key_is_not_written_to_command_or_dry_run_output(monkeypatch, capsys):
    args = _args("--method", "gepa", "--benchmark", "searchqa", "--mode", "judge",
                 "--config", "config.json", "--api-key", "private-test-key")
    command, env = run_method.build_command(args)
    assert "private-test-key" not in command
    assert env["OPENAI_API_KEY"] == "private-test-key"
    monkeypatch.setattr(sys, "argv", ["run_method.py", "--method", "gepa",
                        "--benchmark", "searchqa", "--mode", "judge",
                        "--config", "config.json", "--api-key", "private-test-key",
                        "--dry-run"])
    assert run_method.main() == 0
    assert "private-test-key" not in capsys.readouterr().out


def test_full_validation_audit_is_rejected_in_judge_mode():
    for method, extra in {
        "skillopt": ("--config", "config.yaml"),
        "gepa": ("--config", "config.json"),
        "skillgen": ("--benchmark", "searchqa"),
    }.items():
        args = _args("--method", method, "--mode", "judge", "--full-validation-audit", *extra)
        with pytest.raises(ValueError, match="forbids"):
            run_method.build_command(args)


def test_gepa_qwen_judge_disables_extra_reasoning():
    sys.path.insert(0, str(ROOT / "packages/gepa"))
    import run as gepa_run
    calls = []
    response = SimpleNamespace(usage=None, choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))])
    judge = gepa_run._OpenAIJudgeFn.__new__(gepa_run._OpenAIJudgeFn)
    judge._model = "qwen3.7-plus"
    judge._client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
        create=lambda **kwargs: calls.append(kwargs) or response)))
    judge(system="system", user="user", max_completion_tokens=512, retries=1, stage="judge")
    assert calls[0]["extra_body"] == {"enable_thinking": False}
    assert calls[0]["max_tokens"] == 512


def test_trace2skill_is_not_a_supported_method():
    with pytest.raises(SystemExit):
        _args("--method", "trace2skill")


def test_checked_in_campaign_configs_keep_audit_disabled():
    """The standard campaign must not spend validation tokens per decision."""
    gepa_configs = [
        ROOT / "configs/gepa/searchqa.json",
        ROOT / "configs/gepa/alfworld.json",
    ]
    for path in gepa_configs:
        assert json.loads(path.read_text(encoding="utf-8"))["full_validation_audit"] is False

    # SearchQA's final split requests use the same bounded completion budget
    # as the other benchmark runners; the larger development default can
    # otherwise keep a single final request active for an excessive time.
    assert json.loads((ROOT / "configs/gepa/searchqa.json").read_text(encoding="utf-8"))["builder_kwargs"]["max_tokens"] == 4096

    skillgen_config = (ROOT / "packages/skillgen/config.yaml").read_text(encoding="utf-8")
    assert "full_validation: false" in skillgen_config

    skillopt_config = (ROOT / "packages/skillopt/configs/_base_/default.yaml").read_text(
        encoding="utf-8"
    )
    assert "full_validation_audit: false" in skillopt_config


def test_gepa_config_cannot_implicitly_enable_full_validation_audit(tmp_path, monkeypatch):
    """The costly audit is enabled only by the explicit CLI switch."""
    sys.path.insert(0, str(ROOT / "packages" / "gepa"))
    import run as gepa_run  # noqa: E402

    config = tmp_path / "config.json"
    config.write_text(json.dumps({
        "builder": "unused:factory",
        "full_validation_audit": True,
        "validation_result_path": str(tmp_path / "validation.json"),
    }), encoding="utf-8")

    captured = {}

    class FakeAdapter:
        def evaluate(self, items, candidate, capture_traces=False):
            return SimpleNamespace(scores=[0.0 for _ in items])

    def fake_factory(_config):
        return {
            "seed_candidate": {"skill": "seed"},
            "trainset": ["train"],
            "valset": ["validation"],
            "testset": [],
            "adapter": FakeAdapter(),
            "max_metric_calls": 20,
        }

    monkeypatch.setattr(gepa_run, "_load_factory", lambda _spec: fake_factory)
    monkeypatch.setattr(sys, "argv", ["run.py", "--config", str(config), "--mode", "baseline"])
    import gepa
    import gepa_judge

    def fake_optimize(**kwargs):
        captured["kwargs"] = kwargs
        return SimpleNamespace(best_candidate={"skill": "best"})

    monkeypatch.setattr(gepa, "optimize", fake_optimize)
    monkeypatch.setattr(gepa_judge, "GEPAFullValidationAudit",
                        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("audit enabled")))

    assert gepa_run.main() == 0
    assert "acceptance_criterion" in captured["kwargs"]


def test_gepa_judge_mode_does_not_supply_heldout_validation_to_optimizer(tmp_path, monkeypatch):
    """Judge mode retains training evidence and removes GEPA's regression valset."""
    sys.path.insert(0, str(ROOT / "packages" / "gepa"))
    import run as gepa_run  # noqa: E402
    import gepa

    config = tmp_path / "config.json"
    config.write_text(json.dumps({"builder": "unused:factory", "validation_result_path": str(tmp_path / "validation.json")}), encoding="utf-8")
    captured = {}

    class FakeAdapter:
        def evaluate(self, items, candidate, capture_traces=False):
            return SimpleNamespace(scores=[0.0 for _ in items])

    def fake_factory(_config):
        return {
            "seed_candidate": {"skill": "seed"},
            "trainset": [{"task_type": "a"}, {"task_type": "b"}],
            "valset": ["heldout-a", "heldout-b"],
            "testset": [],
            "adapter": FakeAdapter(),
            "max_metric_calls": 20,
        }

    def fake_optimize(**kwargs):
        captured["kwargs"] = kwargs
        return SimpleNamespace(best_candidate={"skill": "best"})

    monkeypatch.setattr(gepa_run, "_load_factory", lambda _spec: fake_factory)
    monkeypatch.setattr(gepa, "optimize", fake_optimize)
    monkeypatch.setattr(gepa_run, "_OpenAIJudgeFn", lambda **_kwargs: SimpleNamespace())
    monkeypatch.setattr(sys, "argv", ["run.py", "--config", str(config), "--mode", "judge"])

    assert gepa_run.main() == 0
    assert captured["kwargs"]["valset"] == [{"prediction_axis": "a"}, {"prediction_axis": "b"}]
    assert type(captured["kwargs"]["val_evaluation_policy"]).__name__ == "JudgePredictionPolicy"


def test_gepa_final_evaluation_resumes_from_chunk_checkpoint(tmp_path, monkeypatch):
    """A partial final split checkpoint must avoid repeating completed items."""
    sys.path.insert(0, str(ROOT / "packages" / "gepa"))
    import run as gepa_run  # noqa: E402
    import gepa

    validation_path = tmp_path / "validation_eval.json"
    test_path = tmp_path / "test_eval.json"
    checkpoint_path = test_path.with_suffix(".jsonl")
    test_path.with_suffix(".identity.json").write_text(json.dumps(gepa_run._evaluation_identity(
        ["0", "1", "2", "3"], {"skill": "seed"}, {"skill": "best"}
    )))
    checkpoint_path.write_text(
        json.dumps({"index": 0, "baseline_score": 0.25, "best_score": 0.75}) + "\n",
        encoding="utf-8",
    )
    config = tmp_path / "config.json"
    config.write_text(json.dumps({
        "builder": "unused:factory",
        "validation_result_path": str(validation_path),
        "test_result_path": str(test_path),
    }), encoding="utf-8")
    calls = []

    class FakeAdapter:
        def evaluate(self, items, candidate, capture_traces=False):
            calls.append((tuple(items), candidate["skill"]))
            offset = 1.0 if candidate["skill"] == "best" else 0.0
            return SimpleNamespace(scores=[float(item) + offset for item in items])

    def fake_factory(_config):
        return {
            "seed_candidate": {"skill": "seed"},
            "trainset": ["train"],
            "valset": ["4"],
            "testset": ["0", "1", "2", "3"],
            "adapter": FakeAdapter(),
            "max_metric_calls": 20,
        }

    monkeypatch.setattr(gepa_run, "_load_factory", lambda _spec: fake_factory)
    monkeypatch.setattr(
        gepa, "optimize", lambda **_kwargs: SimpleNamespace(best_candidate={"skill": "best"})
    )
    monkeypatch.setenv("GEPA_FINAL_EVAL_CHUNK_SIZE", "2")
    monkeypatch.setattr(sys, "argv", ["run.py", "--config", str(config), "--mode", "baseline"])

    assert gepa_run.main() == 0
    assert ("0",) not in [items for items, _candidate in calls]
    assert json.loads(test_path.read_text(encoding="utf-8"))["best_scores"] == [0.75, 2.0, 3.0, 4.0]
    rows = [json.loads(line) for line in checkpoint_path.read_text(encoding="utf-8").splitlines()]
    assert [row["index"] for row in rows] == [0, 1, 2, 3]
