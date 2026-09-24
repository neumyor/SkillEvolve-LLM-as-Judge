import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run_method


def test_rethinkskill_unified_commands_cover_both_benchmarks():
    for benchmark in ("searchqa", "alfworld"):
        args = run_method._parser().parse_args([
            "--method", "rethinkskill", "--benchmark", benchmark,
            "--mode", "judge", "--model", "qwen3.7-plus",
            "--base-url", "https://example.invalid/v1", "--output-dir", "/tmp/r",
            "--dry-run",
        ])
        command, env = run_method.build_command(args)
        assert command[1].endswith("packages/rethinkskill_runner.py")
        assert "--mode" in command and "judge" in command
        assert "--train-items" in command and "--test-items" in command
        if benchmark == "alfworld":
            assert "--alfworld-config" in command
            assert command[0] == str(ROOT.parents[1]/'benchmark/alfworld-eval/.venv/bin/python')
            assert env['ALFWORLD_DATA'] == str(ROOT.parents[1]/'benchmark/alfworld-eval/.data/alfworld')
            assert command[command.index('--alfworld-config')+1] == str(ROOT.parents[1]/'benchmark/alfworld-eval/configs/rethinkskill_official.yaml')


def test_rethinkskill_comparison_is_quarantined_by_audit(tmp_path):
    import run_direct_campaign
    report = run_direct_campaign.audit({"output": str(tmp_path), "method": "rethinkskill",
        "mode": "judge", "counts": {"test": 2}}, smoke=False)
    assert not report["passed"]
    assert any("Incomplete or invalid study evidence" in failure for failure in report["failures"])
