#!/usr/bin/env python
"""Unified ALFWorld evaluation across methods.

Runs the same TextWorld episodes with the same <think>/<action> protocol for:
  vanilla | skillopt | trace2skill | skillrl

Examples
--------
# 1. Engine smoke test (no API needed): mock agent on 2 games
python scripts/run_unified_eval.py --method vanilla --backend mock --limit 2

# 2. SkillOpt released skill on the 134-game test split with a local vLLM model
python scripts/run_unified_eval.py --method skillopt --backend api \
    --base-url http://127.0.0.1:8000/v1 --model Qwen/Qwen2.5-7B-Instruct \
    --items ../../skillopt/data/alfworld_path_split/test/items.json

# 3. SkillRL SkillBank prompting with a fine-tuned checkpoint served via API
python scripts/run_unified_eval.py --method skillrl --backend api \
    --base-url http://127.0.0.1:8000/v1 --model Jianwen/Alfworld-7B-RL

# 4. Multi-sandbox: shard 0 of 4 (same args except --shard-index)
python scripts/run_unified_eval.py --method skillopt --backend api \
    --base-url http://127.0.0.1:8000/v1 --model Qwen/Qwen2.5-7B-Instruct \
    --items .../items.json --num-shards 4 --shard-index 0 \
    --out outputs/unified_skillopt_20260101_120000_shard0of4
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

from alfworld_eval.env import split_manifest_provenance  # noqa: E402
from alfworld_eval.unified.agent import build_agent  # noqa: E402
from alfworld_eval.unified.runner import (  # noqa: E402
    episode_id,
    result_from_row,
    result_row,
    run_unified_episode,
    save_results,
    summarize,
)
from alfworld_eval.unified.shards import (  # noqa: E402
    corpus_fingerprint,
    key_of,
    read_jsonl,
    shard_slice,
    validate_shard,
)
from alfworld_eval.unified.skills import (  # noqa: E402
    load_skill_provider,
    skill_provenance,
)

DEFAULT_ITEMS = PROJECT_ROOT.parent / "skillopt/data/alfworld_path_split/test/items.json"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Unified ALFWorld evaluation")
    p.add_argument("--method", required=True,
                   choices=["vanilla", "skillopt", "trace2skill", "skillrl", "fuse"])
    p.add_argument("--backend", default="mock", choices=["api", "mock", "random"])
    p.add_argument("--base-url", default="",
                   help="OpenAI-compatible endpoint, e.g. http://127.0.0.1:8000/v1. "
                        "A comma-separated list is also accepted, in which case shard i "
                        "spreads its episodes across every endpoint (round-robin), so one "
                        "shard process can use several servers.")
    p.add_argument("--model", default="", help="Model name/deployment for --backend api")
    p.add_argument("--api-key-env", default="",
                   help="Env var name holding the API key (optional)")
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument(
        "--max-tokens",
        type=int,
        default=4096,
        help="Maximum completion tokens for the model protocol and one correction attempt",
    )
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--max-steps", type=int, default=None,
                   help="Episode step cap. Defaults to the environment's own "
                        "max_nb_steps_per_episode from --config, which is the "
                        "single source of truth; an explicit value that "
                        "disagrees with the config is rejected.")
    p.add_argument("--history-length", type=int, default=2)
    p.add_argument("--config", default=str(PROJECT_ROOT / "configs/textworld.yaml"))
    p.add_argument("--split", default="valid_unseen",
                   choices=["train", "valid_seen", "valid_unseen"],
                   help="Which ALFWorld split gamefiles belong to")
    p.add_argument("--items", default=str(DEFAULT_ITEMS),
                   help="items.json with [{'gamefile': ...}, ...] (SkillOpt split format); "
                        "or omit --use-full-split to fall back to the whole split")
    p.add_argument("--use-full-split", action="store_true",
                   help="Ignore --items and run every game in the split directory")
    p.add_argument("--limit", type=int, default=0, help="Only run the first N games (0 = all)")
    p.add_argument("--num-shards", type=int, default=1,
                   help="Split the corpus into N strided shards (1 = no sharding)")
    p.add_argument("--shard-index", type=int, default=0,
                   help="Which shard this process runs, in [0, --num-shards)")
    p.add_argument("--record-trajectory", action="store_true",
                   help="Save per-step trajectories (larger output)")
    p.add_argument("--no-resume", action="store_true",
                   help="Ignore episodes already present in out_dir/results.jsonl "
                        "and re-run everything")
    p.add_argument("--skill-path", default="",
                   help="Override the Markdown skill for skillopt/trace2skill")
    p.add_argument("--skillrl-bank-path", default="",
                   help="Override the SkillBank JSON for skillrl")
    p.add_argument("--skill-dir", default="",
                   help="Directory of per-task-type Markdown skills (<task_type>.md) "
                        "for the fuse method (deterministic routing by gamefile)")
    p.add_argument("--out", default="",
                   help="Output directory (default: outputs/unified_<method>_<ts>)")
    return p.parse_args()


def load_gamefiles(items_path: str) -> list[dict]:
    path = Path(items_path).expanduser()
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        data = data.get("data") or list(data.values())
    items = [item for item in data if isinstance(item, dict) and item.get("gamefile")]
    if not items:
        raise SystemExit(f"No gamefiles found in {path}")
    return items


def validate_split_consistency(
    items: list[dict],
    split: str,
    *,
    data_root: str | None = None,
) -> dict:
    """CLI wrapper that turns the manifest/split mismatch into a clean exit."""
    try:
        provenance = split_manifest_provenance(items, split, data_root=data_root)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    official_n = provenance["official_episodes"]
    if official_n is not None and not provenance["covers_official_split"]:
        print(
            f"note: manifest covers {provenance['manifest_episodes']}/{official_n} "
            f"episodes of the official '{split}' split; report this coverage "
            "alongside results."
        )
    return provenance


def parse_base_urls(raw: str) -> list[str]:
    """Every endpoint in ``--base-url``, which may be a comma-separated list.

    Endpoint parallelism is the one axis the shard mechanism cannot express: N shards
    give N *processes*, but they all point at a single ``--base-url``, so they queue on
    one server. Accepting a list here keeps sharding untouched (the shards still
    partition one corpus, which is what ``merge_shards`` verifies) while letting a run
    spread its requests over several identical servers.
    """
    return [item.strip() for item in str(raw or "").split(",") if item.strip()]


def pick_base_url(urls: list[str], shard_index: int, seed: int) -> str:
    """The endpoint this shard uses for its *first* episode.

    The shard's start offset is ``shard_index + seed`` so that shards sharing a seed
    begin on the same endpoint (reproducible per shard) while consecutive shards start
    on different ones, which is what actually balances the load instead of having
    every shard begin on endpoint 0.
    """
    if not urls:
        return ""
    return urls[(shard_index + seed) % len(urls)]


def main() -> int:
    args = parse_args()

    validate_shard(args.shard_index, args.num_shards)
    api_key = os.environ.get(args.api_key_env, "") if args.api_key_env else ""

    if args.use_full_split:
        if args.num_shards > 1:
            # The split directory's order comes from AlfredTWEnv's own scan, so
            # "index i" is not a stable contract across sandboxes and a strided
            # slice could silently overlap. Sharding requires an explicit list.
            raise SystemExit(
                "--use-full-split is incompatible with --num-shards > 1: shard "
                "from an items.json manifest instead."
            )
        items: list[dict] = []  # empty list -> whole split directory
        shard_items: list[dict] = []
        split_provenance: dict = {"split": args.split, "manifest_episodes": None}
    else:
        items = load_gamefiles(args.items)
        # Validate *before* --limit truncates: the limit is a deliberate
        # subsample of a comparable split, not a licence to mix splits.
        split_provenance = validate_split_consistency(items, args.split)
        split_provenance["manifest_path"] = str(args.items)
        if args.limit > 0:
            items = items[: args.limit]
        split_provenance["effective_episodes"] = len(items)
        shard_items = shard_slice(items, args.shard_index, args.num_shards)

    base_urls = parse_base_urls(args.base_url)
    start_url = pick_base_url(base_urls, args.shard_index, args.seed)
    agent = build_agent(
        args.backend,
        base_url=start_url,
        model=args.model,
        api_key=api_key,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        seed=args.seed,
    )
    # One agent per endpoint. With a single --base-url this list holds exactly that
    # agent, so nothing about the existing behaviour changes; with a list, the episode
    # loop rotates and this shard uses every server instead of queueing on one.
    agents = [
        agent
        if url == start_url
        else build_agent(
            args.backend,
            base_url=url,
            model=args.model,
            api_key=api_key,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            seed=args.seed,
        )
        for url in (base_urls or [start_url])
    ]
    skill_provider = load_skill_provider(
        args.method,
        skill_path=args.skill_path or None,
        skillrl_bank_path=args.skillrl_bank_path or None,
        skill_dir=args.skill_dir or None,
    )

    from alfworld_eval.env import AlfworldTextEnv

    if args.out:
        out_dir = Path(args.out)
    elif args.num_shards > 1:
        out_dir = PROJECT_ROOT / "outputs" / (
            f"unified_{args.method}_{time.strftime('%Y%m%d_%H%M%S')}"
            f"_shard{args.shard_index}of{args.num_shards}"
        )
    else:
        out_dir = PROJECT_ROOT / "outputs" / (
            f"unified_{args.method}_{time.strftime('%Y%m%d_%H%M%S')}"
        )
    out_dir.mkdir(parents=True, exist_ok=True)

    # Resume: episodes already recorded in this out_dir are skipped, so a
    # sandbox that dies mid-shard can be relaunched and only pays for what is
    # left. save_results truncates results.jsonl, so the prior rows are carried
    # forward in `results` and rewritten -- never dropped.
    results: list = []
    done_ids: set[str] = set()
    if not args.no_resume and not args.use_full_split:
        for row in read_jsonl(out_dir / "results.jsonl"):
            key = episode_id(str(row.get("gamefile", "")), 0)
            if key in done_ids:
                continue
            done_ids.add(key)
            results.append(result_from_row(row))

    # The env advances its own gamefile list on every reset(), so it must be
    # handed exactly the episodes still to run. Passing the whole shard and
    # skipping after the fact would re-serve gamefiles[0] on a resumed run.
    if args.use_full_split:
        pending = shard_items
        env_gamefiles = None
    else:
        pending = [it for it in shard_items if key_of(it) not in done_ids]
        env_gamefiles = [it["gamefile"] for it in pending]

    n_games = len(shard_items) if not args.use_full_split else "full split"
    print(f"method={args.method} backend={agent.name} games={n_games}")
    print(f"out_dir={out_dir}")
    if len(agents) > 1:
        print(f"endpoints: {len(agents)} (round-robin) {base_urls}")
    if args.num_shards > 1:
        print(
            f"shard {args.shard_index}/{args.num_shards}: "
            f"{len(shard_items)} of {len(items)} games "
            f"(corpus {corpus_fingerprint([key_of(i) for i in items])})"
        )
    if done_ids:
        print(f"resume: {len(done_ids)} episodes already recorded, skipping them")

    env = AlfworldTextEnv(
        config_path=args.config,
        split=args.split,
        seed=args.seed,
        gamefiles=env_gamefiles,
    )
    n_episodes = len(pending) if not args.use_full_split else 0
    resumed = len(results)
    try:
        if n_episodes == 0 and args.use_full_split:
            # Full-split mode: run until the env cycles (num_games from collect).
            n_episodes = env.num_games
            pending = [None] * n_episodes
        total = len(results) + len(pending)
        for index in range(len(pending)):
            t0 = time.time()
            result = run_unified_episode(
                env,
                agents[index % len(agents)],
                skill_provider,
                max_steps=args.max_steps,
                history_length=args.history_length,
                record_trajectory=args.record_trajectory,
            )
            results.append(result)
            done_ids.add(episode_id(result.gamefile, 0))
            print(
                f"[{len(results)}/{total}] {result.task_type:<28} "
                f"success={result.success} steps={result.steps} "
                f"invalid={result.invalid_actions} ({time.time() - t0:.1f}s)"
            )
            # Flush after every episode: a sandbox can be reclaimed at any time
            # and the episodes already paid for must survive it.
            _checkpoint(out_dir, results)
    finally:
        env.close()

    summary = summarize(results)
    if resumed:
        print(f"note: summary covers {len(results)} episodes "
              f"({resumed} resumed from a previous run)")
    meta = {
        "method": args.method,
        "backend": agent.name,
        "model": args.model,
        "split": args.split,
        "max_steps": env.step_budget,
        "max_steps_source": (
            f"config:{Path(args.config).name}"
            " -> alfred_tw_env max_nb_steps_per_episode"
        ),
        "history_length": args.history_length,
        "seed": args.seed,
        "skill_provider": args.method,
        "skill_path": args.skill_path,
        # Digest of the bytes actually injected: the skill document is an
        # editable artifact that a later pipeline stage can rewrite, so the path
        # alone cannot prove which version a score belongs to.
        "skill": skill_provenance(
            args.method,
            skill_path=args.skill_path or None,
            skillrl_bank_path=args.skillrl_bank_path or None,
            skill_dir=args.skill_dir or None,
        ),
        "items_path": str(args.items) if not args.use_full_split else "",
        "n_games": len(shard_items) if not args.use_full_split else None,
        "split_provenance": split_provenance,
        "shard_index": args.shard_index,
        "num_shards": args.num_shards,
        # Digest of the *full* corpus, identical on every shard: a merge checks
        # this to prove the shards sliced the same list.
        "corpus_fingerprint": (
            corpus_fingerprint([key_of(i) for i in items]) if not args.use_full_split else ""
        ),
    }
    save_results(out_dir, results, summary, meta)

    print("\n==== Summary ====")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"\nSaved to {out_dir}")
    return 0


def _checkpoint(out_dir: Path, results: list) -> None:
    """Rewrite results.jsonl after each episode so a killed sandbox loses at most one."""
    with (out_dir / "results.jsonl").open("w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(result_row(r), ensure_ascii=False) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
