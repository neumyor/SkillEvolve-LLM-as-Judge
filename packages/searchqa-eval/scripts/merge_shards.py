#!/usr/bin/env python
"""Merge shard output directories from a multi-sandbox run into one summary.

Each sandbox runs one shard with ``run_unified_eval.py --num-shards N
--shard-index i``, writing its own ``outputs/<run>_shard<i>ofN/`` directory.
This script concatenates their ``results.jsonl`` rows, checks that the shards
partition one corpus (same fingerprint, no missing/duplicate ids), and
re-runs the same ``summarize()`` used for a single serial run -- so the merged
numbers are exactly what an unsharded run would have produced, not an
approximation.

Usage
-----
python scripts/merge_shards.py outputs/unified_skillopt_20260101_120000_shard0of4 \
    outputs/unified_skillopt_20260101_120000_shard1of4 \
    outputs/unified_skillopt_20260101_120000_shard2of4 \
    outputs/unified_skillopt_20260101_120000_shard3of4 \
    --out outputs/unified_skillopt_20260101_120000_merged

# or glob the shard family in one shot:
python scripts/merge_shards.py outputs/unified_skillopt_20260101_120000_shard*of4
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from searchqa_eval.runner import ItemResult, summarize  # noqa: E402
from searchqa_eval.shards import key_of, read_jsonl  # noqa: E402


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Merge searchqa-eval shard outputs")
    p.add_argument("shard_dirs", nargs="+", help="Shard output directories to merge")
    p.add_argument("--out", required=True, help="Directory to write the merged results into")
    p.add_argument("--allow-incomplete", action="store_true",
                   help="Merge even if a shard's meta.json reports fewer items than "
                        "it was assigned (e.g. a sandbox died mid-run)")
    return p.parse_args()


def _row_to_result(row: dict) -> ItemResult:
    return ItemResult(
        id=str(row["id"]),
        question=str(row.get("question", "")),
        em=row.get("em", 0.0),
        f1=row.get("f1", 0.0),
        sub_em=row.get("sub_em", 0.0),
        hard=int(row.get("hard", 0)),
        soft=row.get("soft", 0.0),
        predicted_answer=str(row.get("predicted_answer", "")),
        gold_answers=list(row.get("gold_answers", [])),
        response=str(row.get("response", "")),
        agent_ok=bool(row.get("agent_ok", False)),
        fail_reason=str(row.get("fail_reason", "")),
        usage=row.get("usage", {}),
    )


def main() -> int:
    args = parse_args()

    metas = []
    fingerprints = set()
    num_shards_seen = set()
    shard_indices_seen: list[int] = []
    by_id: dict[str, dict] = {}
    dup_ids: list[str] = []

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
        n_expected = meta.get("n_items_this_shard", meta.get("n_items_requested"))
        if n_expected is not None and len(rows) < n_expected and not args.allow_incomplete:
            raise SystemExit(
                f"{d}: only {len(rows)}/{n_expected} items recorded -- shard looks "
                "incomplete. Re-run that shard (it will resume) or pass "
                "--allow-incomplete to merge a partial result."
            )
        for row in rows:
            rid = key_of(row)
            if rid in by_id:
                dup_ids.append(rid)
            by_id[rid] = row

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
    if dup_ids:
        raise SystemExit(
            f"{len(dup_ids)} item id(s) appear in more than one shard (e.g. "
            f"{dup_ids[:5]}) -- shards overlap, refusing to merge."
        )

    results = [_row_to_result(row) for row in by_id.values()]
    results.sort(key=lambda r: r.id)
    summary = summarize(results)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "results.jsonl").open("w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r.to_row(include_response=bool(r.response)), ensure_ascii=False) + "\n")

    base_meta = {k: v for k, v in metas[0].items() if k not in ("summary",)}
    base_meta.pop("shard_index", None)
    base_meta.pop("n_items_this_shard", None)
    base_meta["n_items_requested"] = sum(m.get("n_items_this_shard", 0) for m in metas)
    base_meta["merged_from"] = [str(Path(d).name) for d in args.shard_dirs]
    base_meta["num_shards"] = len(args.shard_dirs)
    with (out_dir / "summary.json").open("w", encoding="utf-8") as f:
        json.dump({**base_meta, "summary": summary}, f, indent=2, ensure_ascii=False)

    print(f"Merged {len(results)} items from {len(args.shard_dirs)} shards -> {out_dir}")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
