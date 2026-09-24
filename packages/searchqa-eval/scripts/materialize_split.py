#!/usr/bin/env python
"""Materialize runnable SearchQA splits from SkillOpt's released ID manifest.

SkillOpt ships only ID lists (``data/searchqa_id_split/{train,val,test}/items.json``),
not the question/context/answers payloads. This script joins those IDs against
the HuggingFace ``lucadiliello/searchqa`` dataset and writes runnable
``{split}/items.json`` files with fields ``id, question, context, answers``.

Usage
-----
    uv run --group materialize python scripts/materialize_split.py
    uv run --group materialize python scripts/materialize_split.py --splits test
"""
from __future__ import annotations

import argparse
import json
from collections.abc import Iterable, Mapping
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parents[1]
SPLITS = ("train", "val", "test")
REQUIRED_FIELDS = ("question", "context", "answers")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--manifest-dir",
        type=Path,
        default=PROJECT_ROOT.parent / "skillopt/data/searchqa_id_split",
    )
    p.add_argument("--output-dir", type=Path,
                   default=PROJECT_ROOT / "data/searchqa_split")
    p.add_argument("--dataset", default="lucadiliello/searchqa")
    p.add_argument("--splits", nargs="+", default=list(SPLITS), choices=list(SPLITS))
    p.add_argument("--limit", type=int, default=0,
                   help="Only materialize the first N ids per split (0 = all)")
    return p.parse_args()


def load_manifest_ids(manifest_dir: Path, splits: Iterable[str]) -> dict[str, list[str]]:
    split_ids: dict[str, list[str]] = {}
    for split in splits:
        path = manifest_dir / split / "items.json"
        with path.open(encoding="utf-8") as f:
            items = json.load(f)
        split_ids[split] = [str(item["id"]) for item in items]
    return split_ids


def _iter_dataset_rows(dataset: Mapping[str, Iterable[dict]]) -> Iterable[dict]:
    for source_split in dataset.values():
        yield from source_split


def _normalize_row(row: dict) -> dict:
    key = str(row["key"])
    missing = [field for field in REQUIRED_FIELDS if field not in row]
    if missing:
        raise ValueError(f"SearchQA source row {key!r} missing fields: {', '.join(missing)}")
    return {
        "id": key,
        "question": row["question"],
        "context": row["context"],
        "answers": row["answers"],
    }


def _provenance_path(path: Path) -> str:
    """Keep generated provenance portable when the input is inside this repo."""
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(path)


def materialize(
    manifest_dir: Path,
    output_dir: Path,
    dataset: Mapping[str, Iterable[dict]],
    *,
    dataset_name: str,
    splits: Iterable[str] = SPLITS,
    limit: int = 0,
) -> dict[str, int]:
    split_ids = load_manifest_ids(manifest_dir, splits)
    if limit > 0:
        split_ids = {s: ids[:limit] for s, ids in split_ids.items()}
    wanted = {item_id for ids in split_ids.values() for item_id in ids}

    selected: dict[str, dict] = {}
    for row in _iter_dataset_rows(dataset):
        key = str(row.get("key", ""))
        if key in wanted and key not in selected:
            selected[key] = _normalize_row(row)

    missing = sorted(wanted - selected.keys())
    if missing:
        raise RuntimeError(
            f"Source dataset is missing {len(missing)} manifest IDs. "
            f"First: {', '.join(missing[:5])}"
        )

    counts: dict[str, int] = {}
    for split, ids in split_ids.items():
        items = [selected[item_id] for item_id in ids]
        split_dir = output_dir / split
        split_dir.mkdir(parents=True, exist_ok=True)
        with (split_dir / "items.json").open("w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        counts[split] = len(items)

    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "split_manifest.json").open("w", encoding="utf-8") as f:
        json.dump(
            {
                "source_manifest_dir": _provenance_path(manifest_dir),
                "source_dataset": dataset_name,
                "counts": counts,
                "item_fields": ["id", *REQUIRED_FIELDS],
            },
            f,
            indent=2,
            ensure_ascii=False,
        )
    return counts


def main() -> int:
    args = parse_args()
    manifest_dir = args.manifest_dir.resolve()
    if not manifest_dir.exists():
        raise SystemExit(
            f"Manifest dir not found: {manifest_dir}\n"
            "Point --manifest-dir at SkillOpt's data/searchqa_id_split."
        )
    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise SystemExit(
            "Missing dependency 'datasets'. Install with:\n"
            "  uv sync --group materialize"
        ) from exc

    print(f"Loading {args.dataset} ...")
    dataset = load_dataset(args.dataset)
    counts = materialize(
        manifest_dir,
        args.output_dir.resolve(),
        dataset,
        dataset_name=args.dataset,
        splits=args.splits,
        limit=args.limit,
    )
    print(f"Wrote splits to {args.output_dir.resolve()}: {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
