#!/usr/bin/env python
"""Merge shard output directories from a multi-sandbox ALFWorld run.

Each sandbox runs one shard with ``run_unified_eval.py --num-shards N
--shard-index i``, writing its own ``outputs/<run>_shard<i>ofN/`` directory.
Episodes are keyed by ``episode_id()`` (task + trial directory names) rather
than the raw ``gamefile`` path, because each sandbox resolves gamefiles under
its own ``$ALFWORLD_DATA`` and records the absolute path -- two sandboxes
naming the same game will disagree on that path but agree on the id.

This script concatenates ``results.jsonl`` rows, checks the shards partition
one corpus (same fingerprint, no missing/duplicate episodes), copies
``trajectories/*.json`` through untouched, and re-runs the same
``summarize()`` used for a single serial run.

Usage
-----
python scripts/merge_shards.py outputs/unified_skillopt_20260101_120000_shard0of4 \
    ... outputs/unified_skillopt_20260101_120000_shard3of4 \
    --out outputs/unified_skillopt_20260101_120000_merged
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from alfworld_eval.unified.runner import (  # noqa: E402
    episode_id,
    result_from_row,
    result_row,
    summarize,
)
from alfworld_eval.unified.shards import read_jsonl  # noqa: E402


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Merge alfworld-eval shard outputs")
    p.add_argument("shard_dirs", nargs="+", help="Shard output directories to merge")
    p.add_argument("--out", required=True, help="Directory to write the merged results into")
    p.add_argument("--allow-incomplete", action="store_true",
                   help="Merge even if a shard's summary.json reports fewer games "
                        "than it was assigned (e.g. a sandbox died mid-run)")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    metas = []
    fingerprints = set()
    num_shards_seen = set()
    shard_indices_seen: list[int] = []
    by_key: dict[str, dict] = {}
    dup_keys: list[str] = []
    traj_sources: dict[str, Path] = {}

    for shard_dir in args.shard_dirs:
        d = Path(shard_dir)
        meta_path = d / "summary.json"
        if not meta_path.exists():
            raise SystemExit(f"{d}: no summary.json -- shard did not finish writing output")
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        metas.append(meta)

        fp = meta.get("corpus_fingerprint", "")
        if fp:
            fingerprints.add(fp)
        if "num_shards" in meta:
            num_shards_seen.add(meta["num_shards"])
        if "shard_index" in meta:
            shard_indices_seen.append(meta["shard_index"])

        rows = read_jsonl(d / "results.jsonl")
        n_expected = meta.get("n_games")
        if n_expected is not None and len(rows) < n_expected and not args.allow_incomplete:
            raise SystemExit(
                f"{d}: only {len(rows)}/{n_expected} games recorded -- shard looks "
                "incomplete. Re-run that shard (it will resume) or pass "
                "--allow-incomplete to merge a partial result."
            )
        traj_dir = d / "trajectories"
        for i, row in enumerate(rows):
            key = episode_id(str(row.get("gamefile", "")), i)
            if key in by_key:
                dup_keys.append(key)
            by_key[key] = row
            traj_path = traj_dir / f"{key}.json"
            if traj_path.exists():
                traj_sources[key] = traj_path

    if len(fingerprints) > 1:
        raise SystemExit(
            f"Shards do not share one corpus -- found {len(fingerprints)} distinct "
            f"corpus_fingerprint values: {sorted(fingerprints)}. Refusing to merge "
            "mismatched runs."
        )
    if len(num_shards_seen) > 1:
        raise SystemExit(f"Shards disagree on --num-shards: {sorted(num_shards_seen)}")
    if num_shards_seen:
        expected_n = next(iter(num_shards_seen))
        missing = sorted(set(range(expected_n)) - set(shard_indices_seen))
        if missing:
            raise SystemExit(
                f"Missing shard(s) {missing} of {expected_n} -- pass every shard "
                "directory, not a subset."
            )
    if dup_keys:
        raise SystemExit(
            f"{len(dup_keys)} episode(s) appear in more than one shard (e.g. "
            f"{dup_keys[:5]}) -- shards overlap, refusing to merge."
        )

    results = [result_from_row(row) for row in by_key.values()]
    keys = list(by_key.keys())
    results.sort(key=lambda r: episode_id(r.gamefile, 0))
    keys.sort()
    summary = summarize(results)

    out_dir = Path(args.out)
    (out_dir / "predictions").mkdir(parents=True, exist_ok=True)
    with (out_dir / "results.jsonl").open("w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(result_row(r), ensure_ascii=False) + "\n")

    if traj_sources:
        traj_out = out_dir / "trajectories"
        traj_out.mkdir(exist_ok=True)
        for key, src in traj_sources.items():
            shutil.copyfile(src, traj_out / f"{key}.json")

    base_meta = {k: v for k, v in metas[0].items() if k != "summary"}
    base_meta.pop("shard_index", None)
    base_meta["n_games"] = len(results)
    base_meta["merged_from"] = [str(Path(d).name) for d in args.shard_dirs]
    base_meta["num_shards"] = len(args.shard_dirs)
    with (out_dir / "summary.json").open("w", encoding="utf-8") as f:
        json.dump({**base_meta, "summary": summary}, f, indent=2, ensure_ascii=False)

    print(f"Merged {len(results)} episodes from {len(args.shard_dirs)} shards -> {out_dir}")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
