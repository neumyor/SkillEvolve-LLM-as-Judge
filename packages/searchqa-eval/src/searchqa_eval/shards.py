"""Deterministic sample sharding for multi-sandbox evaluation.

A shard is a strided slice of the corpus: shard ``i`` of ``n`` takes
``items[i::n]``. The slice is by index into the already-ordered corpus, so the
shards form a true partition -- their union is the corpus, with no overlap and
no gaps -- and every sandbox computes the same slice from its own command line
alone, with no shared state to coordinate.

Striding rather than carving contiguous blocks matters for partial results: a
contiguous split would cut the corpus into blocks with different difficulty
profiles, so a straggler that never finishes would bias the aggregate. Striding
interleaves the corpus, so any subset of the shards stays representative.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def validate_shard(shard_index: int, num_shards: int) -> None:
    if num_shards < 1:
        raise SystemExit(f"--num-shards must be >= 1 (got {num_shards})")
    if not 0 <= shard_index < num_shards:
        raise SystemExit(
            f"--shard-index must be in [0, {num_shards}) (got {shard_index})"
        )


def shard_slice(items: list, shard_index: int, num_shards: int) -> list:
    """Return this shard's strided slice of ``items`` (a true partition)."""
    if num_shards == 1:
        return list(items)
    return list(items[shard_index::num_shards])


def key_of(item: dict) -> str:
    """Identity of an items.json entry or a results.jsonl row."""
    return str(item.get("id", ""))


def corpus_fingerprint(keys) -> str:
    """Short digest of the ordered key list, to prove shards share a corpus."""
    digest = hashlib.sha256()
    for key in keys:
        digest.update(str(key).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()[:16]


def read_jsonl(path: str | Path) -> list[dict]:
    """Read JSONL, skipping blank and truncated lines (a killed run can leave one)."""
    path = Path(path)
    if not path.exists():
        return []
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows
