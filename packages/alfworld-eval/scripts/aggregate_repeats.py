#!/usr/bin/env python
"""Aggregate repeated ALFWorld runs (same episodes, k rollouts each).

Why this exists: the harness resumes by gamefile, so k independent rollouts of
one corpus live in k separate run directories. Side-by-side rates do not answer
the questions a repeat experiment is for -- how much does the score move between
rollouts, and which episodes flip. This script reports, for k runs over one
shared episode list:

* each run's success rate and the mean +/- std across runs (temperature>0 or a
  non-deterministic endpoint both make these differ);
* mean@k -- the per-episode mean over the k rollouts, which is the estimator a
  "roll out each case 3 times" protocol is usually after;
* stability -- how many episodes are unanimous vs mixed, the honest noise floor
  for any per-episode claim;
* per-task-type mean +/- std across runs.

Usage
-----
python scripts/aggregate_repeats.py outputs/rep0/merged outputs/rep1/merged \\
    outputs/rep2/merged --out outputs/repeats_summary.json
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from alfworld_eval.unified.runner import episode_id  # noqa: E402
from alfworld_eval.unified.shards import read_jsonl  # noqa: E402


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("runs", nargs="+", help="run directories (merged/ or shard root)")
    p.add_argument("--out", default="", help="write the aggregate JSON here")
    return p.parse_args()


def load_run(run_dir: str) -> dict[str, dict]:
    root = Path(run_dir)
    path = root / "results.jsonl" if (root / "results.jsonl").is_file() else (
        root / "merged" / "results.jsonl"
    )
    rows = read_jsonl(path)
    if not rows:
        raise SystemExit(f"{run_dir}: no results.jsonl (looked in {path})")
    return {
        episode_id(str(row.get("gamefile", "")), i): row
        for i, row in enumerate(rows)
    }


def main() -> int:
    args = parse_args()
    runs = [load_run(r) for r in args.runs]
    k = len(runs)

    keys = set(runs[0])
    for index, run in enumerate(runs[1:], start=1):
        diff = keys ^ set(run)
        if diff:
            raise SystemExit(
                f"run {args.runs[index]} does not cover the same episodes "
                f"(first difference: {sorted(diff)[:3]}); repeats must share one list"
            )
    keys = sorted(keys)

    rates = []
    steps = []
    for run in runs:
        hits = [int(bool(run[key].get("success"))) for key in keys]
        rates.append(sum(hits) / len(keys))
        steps.append(statistics.mean(int(run[key].get("steps", 0)) for key in keys))

    per_episode = [
        statistics.mean(int(bool(run[key].get("success"))) for run in runs)
        for key in keys
    ]
    unanimous = sum(1 for v in per_episode if v in (0.0, 1.0))
    always = sum(1 for v in per_episode if v == 1.0)
    never = sum(1 for v in per_episode if v == 0.0)
    mean_at_k = statistics.mean(per_episode)

    per_type: dict[str, dict] = {}
    for key in keys:
        task = str(runs[0][key].get("task_type", "other"))
        per_type.setdefault(task, []).append(
            statistics.mean(int(bool(run[key].get("success"))) for run in runs)
        )

    aggregate = {
        "runs": args.runs,
        "k_rollouts": k,
        "episodes": len(keys),
        "success_rate_per_run": [round(r, 4) for r in rates],
        "success_rate_mean": round(statistics.mean(rates), 4),
        "success_rate_std": round(statistics.pstdev(rates), 4),
        "mean_at_k": round(mean_at_k, 4),
        "avg_steps_per_run": [round(s, 2) for s in steps],
        "stability": {
            "always_solved": always,
            "never_solved": never,
            "mixed": len(keys) - unanimous,
            "unanimous_rate": round(unanimous / len(keys), 4),
        },
        "per_task_type": {
            task: {
                "count": len(vals),
                "mean": round(statistics.mean(vals), 4),
            }
            for task, vals in sorted(per_type.items())
        },
    }

    print(f"{k} rollouts over {len(keys)} shared episodes")
    print(f"  success rate per run : {[round(r, 4) for r in rates]}")
    print(f"  mean +/- std         : {aggregate['success_rate_mean']:.4f} "
          f"+/- {aggregate['success_rate_std']:.4f}")
    print(f"  mean@{k}               : {mean_at_k:.4f}")
    print(f"  avg steps per run    : {aggregate['avg_steps_per_run']}")
    print(f"  stability            : always {always} / never {never} / "
          f"mixed {len(keys) - unanimous} "
          f"(unanimous {aggregate['stability']['unanimous_rate']:.1%})")
    print(f"  {'task type':<34}{'n':>4}{'mean@k':>9}")
    for task, vals in sorted(per_type.items()):
        print(f"  {task:<34}{len(vals):>4}{statistics.mean(vals):>9.3f}")

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(aggregate, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
