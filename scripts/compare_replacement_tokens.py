#!/usr/bin/env python3
"""Compare only Judge calls against the baseline re-executions they replace."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/skillopt"))
from skillopt.evaluation.usage_ledger import UsageLedger  # noqa: E402


def read_cost(path, mode):
    path = Path(path)
    if path.is_dir():
        path = path / "replacement_cost.json"
    summary = json.loads(path.read_text())
    if summary.get("schema") != "replacement_cost_v1" or summary.get("mode") != mode:
        raise ValueError(f"{path}: requires a replacement_cost_v1 {mode} run")
    # Events are authoritative if a process stopped before refreshing its summary.
    local_events = path.with_name("usage_events.jsonl")
    events = local_events if local_events.exists() else Path(summary["usage_events_path"])
    if events.exists():
        ledger = UsageLedger(events)
        summary.update(ledger.replacement_summary())
    components = set(summary.get("components", {}))
    if mode == "judge" and components - {"llm_judge"}:
        raise ValueError("Judge cost contains baseline re-execution events")
    if mode == "baseline" and "llm_judge" in components:
        raise ValueError("Baseline cost contains Judge events")
    return summary


def compare(baseline_path, judge_path):
    baseline, judge = read_cost(baseline_path, "baseline"), read_cost(judge_path, "judge")
    if baseline["method"] != judge["method"]:
        raise ValueError("Compare baseline and Judge runs of the same method")
    complete = baseline["usage_complete"] and judge["usage_complete"]
    keys = ("prompt_tokens", "completion_tokens", "total_tokens")
    saved = baseline["total_tokens"] - judge["total_tokens"] if complete else None
    return {
        "method": baseline["method"],
        "baseline_rerun": {key: baseline[key] for key in keys},
        "llm_judge": {key: judge[key] for key in keys},
        "saved_tokens": saved,
        "saving_fraction": saved / baseline["total_tokens"] if complete and baseline["total_tokens"] else None,
        "usage_complete": complete,
        "baseline_components": baseline["components"],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True, help="Run directory or replacement_cost.json")
    parser.add_argument("--judge", type=Path, required=True, help="Run directory or replacement_cost.json")
    parser.add_argument("--output", type=Path, help="Optional JSON comparison file")
    args = parser.parse_args()
    result = compare(args.baseline, args.judge)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
