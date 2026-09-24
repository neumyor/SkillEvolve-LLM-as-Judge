#!/usr/bin/env python
"""Build a stratified subsample of an ALFWorld items.json manifest.

``run_unified_eval.py --limit N`` takes the *first* N entries of a manifest, and
the SkillOpt manifests are grouped by task type: the first six ``test`` entries
are all ``look_at_obj_in_light`` in the same trial directory. A smoke test built
that way exercises one of ALFWorld's six task types and reports its success rate
as if it were the benchmark's.

This script samples evenly across the six task types instead, so a small run
still covers every task type. The output is a normal items.json, so it flows
through the same split validation and provenance recording as the full manifest
(``summary.json.split_provenance.manifest_episodes`` will say it is a subsample).

Usage
-----
python scripts/sample_manifest.py \
    --items ../../skillopt/data/alfworld_path_split/test/items.json \
    --per-type 2 --out outputs/_smoke/manifests/test_2per_type.json
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from alfworld_eval.unified.skills import task_type_from_gamefile  # noqa: E402


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--items", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--per-type", type=int, default=2,
                   help="Episodes to take from each of the six task types")
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    data = json.loads(Path(args.items).expanduser().read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("data") or list(data.values())
    items = [item for item in data if isinstance(item, dict) and item.get("gamefile")]
    if not items:
        raise SystemExit(f"no gamefiles in {args.items}")

    by_type: dict[str, list[tuple[int, dict]]] = {}
    for index, item in enumerate(items):
        by_type.setdefault(task_type_from_gamefile(item["gamefile"]), []).append(
            (index, item)
        )

    rng = random.Random(args.seed)
    picked: list[tuple[int, dict]] = []
    for task_type in sorted(by_type):
        pool = by_type[task_type]
        rng.shuffle(pool)
        # Re-sort each pick by manifest position so the output order -- and
        # therefore the shard assignment -- is reproducible from
        # (manifest, per-type, seed) alone.
        chosen = sorted(pool[: args.per_type], key=lambda pair: pair[0])
        picked.extend(chosen)
        print(f"{task_type:<32} pool={len(pool):<4} picked={len(chosen)}")

    picked.sort(key=lambda pair: pair[0])
    picked_items = [item for _, item in picked]
    out_path = Path(args.out).expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(picked_items, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"wrote {len(picked_items)} episode(s) of {len(items)} to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
