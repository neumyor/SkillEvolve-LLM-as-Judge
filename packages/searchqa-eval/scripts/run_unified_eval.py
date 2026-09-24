#!/usr/bin/env python
"""Unified single-turn SearchQA evaluation across methods.

Runs the same items with the same SkillOpt protocol (system prompt +
`## Skill` injection, 6000-char [DOC]-truncated context, <answer> extraction,
SQuAD EM/F1) for: vanilla | skillopt | trace2skill

Examples
--------
# 1. Smoke test (no network): mock agent on 5 synthetic-free items
python scripts/run_unified_eval.py --method skillopt --backend mock --limit 5

# 2. Full 1400-item test split with a local vLLM model
python scripts/run_unified_eval.py --method skillopt --backend api \
    --base-url http://127.0.0.1:8000/v1 --model Qwen/Qwen2.5-7B-Instruct

# 3. Custom skill document
python scripts/run_unified_eval.py --method trace2skill --backend api \
    --base-url http://127.0.0.1:8000/v1 --model Qwen/Qwen2.5-7B-Instruct \
    --skill /path/to/trace2skill_searchqa.md

# 4. Multi-sandbox: shard 1 of 8 (same args on each sandbox, differing only in --shard-index)
python scripts/run_unified_eval.py --method skillopt --backend api \
    --base-url http://127.0.0.1:8000/v1 --model Qwen/Qwen2.5-7B-Instruct \
    --num-shards 8 --shard-index 1
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from searchqa_eval.agent import build_agent  # noqa: E402
from searchqa_eval.data import MAX_CONTEXT_CHARS, load_items  # noqa: E402
from searchqa_eval.prompts import build_system_prompt  # noqa: E402
from searchqa_eval.runner import run_batch, save_results, summarize  # noqa: E402
from searchqa_eval.shards import (  # noqa: E402
    corpus_fingerprint,
    key_of,
    shard_slice,
    validate_shard,
)
from searchqa_eval.skills import load_skill_content  # noqa: E402

DEFAULT_ITEMS = PROJECT_ROOT / "data/searchqa_split/test/items.json"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Unified single-turn SearchQA evaluation")
    p.add_argument("--method", required=True,
                   choices=["vanilla", "skillopt", "trace2skill"])
    p.add_argument("--backend", default="mock", choices=["api", "mock", "random"])
    p.add_argument("--base-url", default="",
                   help="OpenAI-compatible endpoint, e.g. http://127.0.0.1:8000/v1")
    p.add_argument("--model", default="", help="Model name/deployment for --backend api")
    p.add_argument("--api-key-env", default="",
                   help="Env var name holding the API key (optional)")
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--record-response", action="store_true",
                   help="Persist the raw model response in results.jsonl "
                        "(needed for Trace2Skill-style error analysis)")
    p.add_argument("--max-tokens", type=int, default=16384)
    p.add_argument("--items", default=str(DEFAULT_ITEMS),
                   help="items.json with id/question/context/answers")
    p.add_argument("--limit", type=int, default=0, help="Only run the first N items (0 = all)")
    p.add_argument("--num-shards", type=int, default=1,
                   help="Split the corpus into N strided shards (1 = no sharding)")
    p.add_argument("--shard-index", type=int, default=0,
                   help="Which shard this process runs, in [0, --num-shards)")
    p.add_argument("--workers", type=int, default=24)
    p.add_argument("--failed-retries", type=int, default=1,
                   help="Retry an item after an API failure (default: 1)")
    p.add_argument("--max-context-chars", type=int, default=MAX_CONTEXT_CHARS)
    p.add_argument("--skill", default="",
                   help="Override path to the skill document for skill methods")
    p.add_argument("--out", default="",
                   help="Output directory (default: outputs/unified_<method>_<ts>)")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    validate_shard(args.shard_index, args.num_shards)
    items_path = Path(args.items).expanduser()
    if not items_path.exists():
        raise SystemExit(
            f"Items file not found: {items_path}\n"
            "Materialize the split first:\n"
            "  uv run --group materialize python scripts/materialize_split.py --splits test"
        )
    items = load_items(items_path)
    if args.limit > 0:
        items = items[: args.limit]

    # Digest the full corpus before slicing: every shard must stamp the same
    # value, which is what lets a merge prove the shards share one item list.
    fingerprint = corpus_fingerprint([key_of(i) for i in items])
    shard_items = shard_slice(items, args.shard_index, args.num_shards)

    skill_content = load_skill_content(args.method, args.skill or None)
    system_prompt = build_system_prompt(skill_content)

    api_key = os.environ.get(args.api_key_env, "") if args.api_key_env else ""
    agent = build_agent(
        args.backend,
        base_url=args.base_url,
        model=args.model,
        api_key=api_key,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        seed=args.seed,
    )

    if args.out:
        out_dir = Path(args.out)
    elif args.num_shards > 1:
        out_dir = PROJECT_ROOT / "outputs" / (
            f"unified_{args.method}_{time.strftime('%Y%m%d_%H%M%S')}"
            f"_shard{args.shard_index}of{args.num_shards}"
        )
    else:
        out_dir = PROJECT_ROOT / "outputs" / f"unified_{args.method}_{time.strftime('%Y%m%d_%H%M%S')}"

    print(f"method={args.method} backend={agent.name} items={len(shard_items)} "
          f"skill_chars={len(skill_content)}")
    print(f"out_dir={out_dir}")
    if args.num_shards > 1:
        print(f"shard {args.shard_index}/{args.num_shards}: {len(shard_items)} of "
              f"{len(items)} items (corpus {fingerprint})")

    def on_progress(done: int, total: int, result) -> None:
        print(f"[{done}/{total}] id={result.id} em={result.em} f1={result.f1:.2f} "
              f"pred={result.predicted_answer!r}", flush=True)

    results = run_batch(
        shard_items,
        system_prompt,
        agent,
        out_dir=out_dir,
        workers=args.workers,
        max_context_chars=args.max_context_chars,
        on_progress=on_progress,
        record_response=args.record_response,
        failed_retries=max(0, args.failed_retries),
    )

    summary = summarize(results)
    meta = {
        "method": args.method,
        "backend": agent.name,
        "model": args.model,
        "items_path": str(items_path),
        "n_items_requested": len(items),
        "n_items_this_shard": len(shard_items),
        "shard_index": args.shard_index,
        "num_shards": args.num_shards,
        "corpus_fingerprint": fingerprint,
        "skill_path": args.skill or _default_skill_path(args.method),
        "skill_chars": len(skill_content),
        "max_context_chars": args.max_context_chars,
        "temperature": args.temperature,
        "seed": args.seed,
    }
    save_results(out_dir, summary, meta)

    print("\n==== Summary ====")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"\nSaved to {out_dir}")
    return 0


def _default_skill_path(method: str) -> str:
    if method == "vanilla":
        return ""
    from searchqa_eval.skills import _DEFAULT_SKILL
    return str(_DEFAULT_SKILL[method])


if __name__ == "__main__":
    raise SystemExit(main())
