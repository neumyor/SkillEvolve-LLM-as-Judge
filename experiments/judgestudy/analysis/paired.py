#!/usr/bin/env python3
"""Paired comparison between two evaluation runs on an identical item list.

Mirrors the statistics the repo's existing reports use (paired bootstrap CI on
the accuracy difference, exact McNemar on the discordant pairs) so the numbers
here are directly comparable to the ALFWorld/SearchQA reports already on disk.

A difference is only reported as a finding when its CI excludes 0; anything
smaller than the measured same-skill noise band is labelled as indistinguishable
from evaluation noise.
"""
from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path


def load_rows(path: Path, id_key: str, score_key: str) -> dict[str, float]:
    """Map item id -> hard score for one results.jsonl.

    SearchQA rows carry ``id`` / ``hard``; ALFWorld rows carry the game path
    and a boolean ``success``. The caller names the keys, so one script covers
    both environments.
    """
    rows: dict[str, float] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            raw_id = row.get(id_key)
            if raw_id is None:
                raise KeyError(f"{path}: row has no {id_key!r} key")
            score = row.get(score_key, 0)
            if isinstance(score, bool):
                score = 1.0 if score else 0.0
            rows[str(raw_id)] = float(score or 0)
    return rows


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact McNemar p-value for discordant counts b and c."""
    n = b + c
    if n == 0:
        return 1.0
    # Two-sided binomial test with p=0.5 on min(b, c).
    k = min(b, c)
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) / (2 ** n)
    return min(1.0, 2 * tail)


def bootstrap_ci(diffs: list[float], iterations: int = 10000, alpha: float = 0.05,
                 seed: int = 42) -> tuple[float, float, float]:
    rng = random.Random(seed)
    n = len(diffs)
    if n == 0:
        return 0.0, 0.0, 0.0
    mean = sum(diffs) / n
    samples = []
    for _ in range(iterations):
        total = 0.0
        for _ in range(n):
            total += diffs[rng.randrange(n)]
        samples.append(total / n)
    samples.sort()
    lo = samples[int((alpha / 2) * iterations)]
    hi = samples[int((1 - alpha / 2) * iterations) - 1]
    return mean, lo, hi


def compare(a_path: Path, b_path: Path, label_a: str, label_b: str,
            id_key: str = "id", score_key: str = "hard") -> dict:
    a = load_rows(a_path, id_key, score_key)
    b = load_rows(b_path, id_key, score_key)
    ids = sorted(set(a) & set(b))
    only_a, only_b = sorted(set(a) - set(b)), sorted(set(b) - set(a))
    hits_a = sum(a[i] for i in ids)
    hits_b = sum(b[i] for i in ids)
    both = sum(1 for i in ids if a[i] >= 1.0 and b[i] >= 1.0)
    only_b_pass = sum(1 for i in ids if a[i] < 1.0 <= b[i])
    only_a_pass = sum(1 for i in ids if b[i] < 1.0 <= a[i])
    neither = len(ids) - both - only_a_pass - only_b_pass
    mean, lo, hi = bootstrap_ci([a[i] - b[i] for i in ids])
    return {
        "id_key": id_key,
        "score_key": score_key,
        "n_paired": len(ids),
        "only_in_a": only_a,
        "only_in_b": only_b,
        "accuracy_a": hits_a / len(ids) if ids else 0.0,
        "accuracy_b": hits_b / len(ids) if ids else 0.0,
        "delta": (hits_a - hits_b) / len(ids) if ids else 0.0,
        "delta_ci_low": lo,
        "delta_ci_high": hi,
        "ci_excludes_zero": lo > 0 or hi < 0,
        "both_pass": both,
        "only_a_pass": only_a_pass,
        "only_b_pass": only_b_pass,
        "neither_pass": neither,
        "mcnemar_p": mcnemar_exact(only_a_pass, only_b_pass),
        "label_a": label_a,
        "label_b": label_b,
    }


def fmt(result: dict) -> str:
    return (
        f"{result['label_a']} {result['accuracy_a']:.4f} vs "
        f"{result['label_b']} {result['accuracy_b']:.4f} "
        f"(n={result['n_paired']}): delta {result['delta']:+.4f} "
        f"CI [{result['delta_ci_low']:+.4f}, {result['delta_ci_high']:+.4f}] "
        f"mcnemar p={result['mcnemar_p']:.3g} "
        f"[both {result['both_pass']} / only-A {result['only_a_pass']} / "
        f"only-B {result['only_b_pass']} / neither {result['neither_pass']}]"
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True, help="results.jsonl for condition A")
    ap.add_argument("--b", required=True, help="results.jsonl for condition B")
    ap.add_argument("--label-a", default="A")
    ap.add_argument("--label-b", default="B")
    ap.add_argument("--out", default="")
    ap.add_argument("--id-key", default="id",
                    help="row key holding the item id (ALFWorld: gamefile)")
    ap.add_argument("--score-key", default="hard",
                    help="row key holding the 0/1 outcome (ALFWorld: success)")
    args = ap.parse_args()

    result = compare(Path(args.a), Path(args.b), args.label_a, args.label_b,
                     id_key=args.id_key, score_key=args.score_key)
    print(fmt(result))
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            json.dump(result, handle, indent=2, ensure_ascii=False)
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
