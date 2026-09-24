#!/usr/bin/env python
"""Paired comparison of two ALFWorld runs over the same episode list.

The harness already refuses to compare mismatched splits (``split_manifest_provenance``
+ ``corpus_fingerprint``), but nothing turned two runs into a comparison. Reporting
"82% vs 66%" side by side is not that comparison: the two runs played the *same*
episodes, so the episodes they disagree on are the only evidence, and the pairing
is what makes a 15-point gap testable on a 134-episode split.

This script reports, for two run directories (a shard directory or a merged one):

* each run's success rate with a bootstrap 95% CI;
* the paired 2x2 table (both solved / only A / only B / neither);
* McNemar's exact test on the discordant pairs -- the right test for a paired
  binary outcome, and the reason a paired comparison is more sensitive than
  comparing two independent CIs;
* the same difference broken down per task type, so a gap that lives in one
  task type is visible instead of averaged away.

Usage
-----
python scripts/compare_runs.py outputs/final_skillopt_test/merged \
    outputs/final_t2s_test/merged --label-a skillopt --label-b trace2skill
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from math import comb
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from alfworld_eval.unified.runner import episode_id  # noqa: E402
from alfworld_eval.unified.shards import read_jsonl  # noqa: E402


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("run_a")
    p.add_argument("run_b")
    p.add_argument("--label-a", default="run_a")
    p.add_argument("--label-b", default="run_b")
    p.add_argument("--bootstrap", type=int, default=10000)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", default="", help="Write the comparison as JSON here")
    return p.parse_args()


def load_run(run_dir: str) -> dict[str, dict]:
    rows = read_jsonl(Path(run_dir) / "results.jsonl")
    if not rows:
        raise SystemExit(f"{run_dir}: no results.jsonl rows")
    by_key: dict[str, dict] = {}
    for index, row in enumerate(rows):
        by_key[episode_id(str(row.get("gamefile", "")), index)] = row
    return by_key


def bootstrap_ci(
    values: list[int], iterations: int, rng: random.Random
) -> tuple[float, float]:
    """Percentile bootstrap CI for a mean of 0/1 outcomes."""
    n = len(values)
    if n == 0:
        return (0.0, 0.0)
    means = []
    for _ in range(iterations):
        means.append(sum(values[rng.randrange(n)] for _ in range(n)) / n)
    means.sort()
    lo = means[int(0.025 * iterations)]
    hi = means[min(iterations - 1, int(0.975 * iterations))]
    return (round(lo, 4), round(hi, 4))


def bootstrap_ci_difference(
    a_hits: list[int], b_hits: list[int], iterations: int, rng: random.Random
) -> tuple[float, float]:
    """Percentile bootstrap CI for ``mean(a) - mean(b)`` on paired episodes.

    The pairing must be respected: each resampled episode contributes its own
    ``a - b``, which is what makes this more informative than subtracting two
    independent interval endpoints.
    """
    n = len(a_hits)
    if n == 0:
        return (0.0, 0.0)
    deltas = []
    for _ in range(iterations):
        total = 0
        for _ in range(n):
            i = rng.randrange(n)
            total += a_hits[i] - b_hits[i]
        deltas.append(total / n)
    deltas.sort()
    lo = deltas[int(0.025 * iterations)]
    hi = deltas[min(iterations - 1, int(0.975 * iterations))]
    return (round(lo, 4), round(hi, 4))


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p-value for discordant counts b and c."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(comb(n, i) for i in range(k + 1)) * (0.5**n)
    return round(min(1.0, 2 * tail), 6)


def main() -> int:
    args = parse_args()
    a = load_run(args.run_a)
    b = load_run(args.run_b)

    only_a = sorted(set(a) - set(b))
    only_b = sorted(set(b) - set(a))
    if only_a or only_b:
        raise SystemExit(
            "runs do not cover the same episodes: "
            f"{len(only_a)} only in {args.label_a} (e.g. {only_a[:3]}), "
            f"{len(only_b)} only in {args.label_b} (e.g. {only_b[:3]}). "
            "A paired comparison needs one shared episode list."
        )

    keys = sorted(a)
    rng = random.Random(args.seed)
    a_hits = [int(bool(a[k].get("success"))) for k in keys]
    b_hits = [int(bool(b[k].get("success"))) for k in keys]

    both = sum(1 for x, y in zip(a_hits, b_hits, strict=False) if x and y)
    a_only = sum(1 for x, y in zip(a_hits, b_hits, strict=False) if x and not y)
    b_only = sum(1 for x, y in zip(a_hits, b_hits, strict=False) if y and not x)
    neither = len(keys) - both - a_only - b_only

    n = len(keys)
    rate_a = round(sum(a_hits) / n, 4)
    rate_b = round(sum(b_hits) / n, 4)
    ci_a = bootstrap_ci(a_hits, args.bootstrap, rng)
    ci_b = bootstrap_ci(b_hits, args.bootstrap, rng)
    ci_d = bootstrap_ci_difference(a_hits, b_hits, args.bootstrap, rng)
    p = mcnemar_exact(a_only, b_only)

    per_type: dict[str, dict] = {}
    for key, x, y in zip(keys, a_hits, b_hits, strict=False):
        task = str(a[key].get("task_type", "other"))
        bucket = per_type.setdefault(
            task, {"count": 0, "label_a": 0, "label_b": 0, "a_only": 0, "b_only": 0}
        )
        bucket["count"] += 1
        bucket["label_a"] += x
        bucket["label_b"] += y
        bucket["a_only"] += int(x and not y)
        bucket["b_only"] += int(y and not x)
    for bucket in per_type.values():
        bucket["label_a_rate"] = round(bucket["label_a"] / bucket["count"], 4)
        bucket["label_b_rate"] = round(bucket["label_b"] / bucket["count"], 4)
        bucket["delta"] = round(bucket["label_a_rate"] - bucket["label_b_rate"], 4)
        bucket["mcnemar_p"] = mcnemar_exact(bucket["a_only"], bucket["b_only"])

    report = {
        "episodes": n,
        "label_a": args.label_a,
        "label_b": args.label_b,
        "run_a": args.run_a,
        "run_b": args.run_b,
        "success_rate_a": rate_a,
        "success_rate_b": rate_b,
        "difference": round(rate_a - rate_b, 4),
        "bootstrap_ci95_a": ci_a,
        "bootstrap_ci95_b": ci_b,
        "bootstrap_ci95_difference": ci_d,
        "paired_table": {
            "both_solved": both,
            "only_a_solved": a_only,
            "only_b_solved": b_only,
            "neither_solved": neither,
        },
        "mcnemar_exact_p": p,
        "per_task_type": per_type,
    }

    print(f"paired comparison over {n} shared episodes")
    print(f"  {args.label_a:<12} {rate_a:.4f}  95% CI {ci_a}")
    print(f"  {args.label_b:<12} {rate_b:.4f}  95% CI {ci_b}")
    print(f"  difference   {rate_a - rate_b:+.4f}"
          f"  (paired bootstrap 95% CI {ci_d[0]:+.4f}..{ci_d[1]:+.4f} for a-b)")
    print()
    print(f"  both solved   : {both}")
    print(f"  only {args.label_a:<10}: {a_only}")
    print(f"  only {args.label_b:<10}: {b_only}")
    print(f"  neither       : {neither}")
    print(f"  McNemar exact p = {p}")
    print()
    print(f"  {'task type':<34}{'n':>4}{args.label_a[:11].rjust(13)}"
          f"{args.label_b[:11].rjust(13)}{'delta':>9}{'p':>9}")
    for task in sorted(per_type):
        t = per_type[task]
        print(f"  {task:<34}{t['count']:>4}{t['label_a_rate']:>13.3f}"
              f"{t['label_b_rate']:>13.3f}{t['delta']:>+9.3f}{t['mcnemar_p']:>9.4f}")

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                       encoding="utf-8")
        print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
