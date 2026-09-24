#!/usr/bin/env python
"""Run a multi-concurrency ALFWorld evaluation, then merge the shards.

One ALFWorld process is one environment (``AlfredTWEnv`` is built with
``batch_size=1``) and evaluates one episode at a time. Concurrency is therefore
*process*-level: this driver launches N copies of ``run_unified_eval.py`` with
``--num-shards N --shard-index i``, which partition one items.json into strided
shards, and then hands the N output directories to ``merge_shards.py``.

That reuses the two pieces the repository already guarantees:

* ``shard_slice``/``corpus_fingerprint`` make the shards a partition of a single
  corpus, and ``merge_shards.py`` refuses to merge anything else;
* ``run_unified_eval.py`` checkpoints after every episode, so a shard that dies
  resumes instead of restarting.

Concurrency is introduced deliberately, and late: the endpoint is warmed first
(see ``warmup_endpoint.py``) -- a cold burst is what the gateway answers with
429 -- and the shards are launched with a small stagger so they do not all open
their first request in the same instant.

Usage
-----
python scripts/run_eval_concurrent.py \
    --method skillopt --shards 8 \
    --base-url "$ALF_ENDPOINT" --model qwen3.6-flash-distill \
    --api-key-env ALF_LLM_KEY \
    --unified-args "--split valid_unseen --items $ITEMS --limit 24 --record-trajectory"
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = PROJECT_ROOT / "scripts"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--method", required=True,
                   choices=["vanilla", "skillopt", "trace2skill", "skillrl", "fuse"])
    p.add_argument("--shards", default="auto",
                   help="Number of concurrent shard processes, or 'auto' to use "
                        "the warmup's measured clean concurrency")
    p.add_argument("--unified-args", required=True,
                   help="Arguments forwarded to run_unified_eval.py, as one shell "
                        "string (do NOT include --out, --num-shards, --shard-index)")
    p.add_argument("--base-url", required=True,
                   help="One endpoint, or a comma-separated list. Every shard is handed "
                        "the whole list, and run_unified_eval rotates over it, so N "
                        "servers are used without changing how shards are cut.")
    p.add_argument("--model", required=True)
    p.add_argument("--api-key", default="")
    p.add_argument("--api-key-env", default="ALF_LLM_KEY")
    p.add_argument("--out-base", default="",
                   help="Run directory (default outputs/concurrent_<method>_<ts>)")
    p.add_argument("--skip-warmup", action="store_true")
    p.add_argument("--warmup-ramp", default="1,2,4,8",
                   help="Concurrency levels the warmup probes")
    p.add_argument("--warmup-per-level", type=int, default=2)
    p.add_argument("--shard-stagger", type=float, default=0.5,
                   help="Seconds between shard launches")
    p.add_argument("--allow-incomplete", action="store_true",
                   help="Merge even if a shard recorded fewer episodes than assigned")
    p.add_argument("--dry-run", action="store_true",
                   help="Print the shard commands without running them")
    return p.parse_args()


def _log(message: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {message}", flush=True)


def _count_items(unified_args: list[str], limit: int) -> int | None:
    """Episodes the shards will cover, read from the manifest, not guessed.

    ``--limit`` truncates before sharding, so the effective corpus is
    ``min(limit, len(manifest))``; the shard assignment depends on that corpus,
    and a wrong expectation here would make the merge look incomplete.
    """
    if "--use-full-split" in unified_args:
        return None
    items_path = ""
    for i, token in enumerate(unified_args):
        if token == "--items" and i + 1 < len(unified_args):
            items_path = unified_args[i + 1]
        elif token.startswith("--items="):
            items_path = token.split("=", 1)[1]
    if not items_path:
        return None
    try:
        data = json.loads(Path(items_path).expanduser().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if isinstance(data, dict):
        data = data.get("data") or list(data.values())
    n = sum(1 for item in data if isinstance(item, dict) and item.get("gamefile"))
    return min(n, limit) if limit > 0 else n


def run_warmup(args: argparse.Namespace, out_base: Path) -> int | None:
    """Warm every endpoint, and report the smallest clean concurrency found.

    With a single ``--base-url`` this is one warmup and its measurement, exactly as
    before. With a list, the run's usable concurrency is limited by its *coldest*
    endpoint, so the reported number is the minimum over the endpoints and each
    endpoint's own report is kept in ``warmup_<index>.json``.
    """
    urls = [item.strip() for item in str(args.base_url).split(",") if item.strip()]
    if not urls:
        return None
    measurements: list[int] = []
    for index, url in enumerate(urls):
        report_path = out_base / ("warmup.json" if len(urls) == 1 else f"warmup_{index}.json")
        command = [
            sys.executable, str(SCRIPTS / "warmup_endpoint.py"),
            "--base-url", url,
            "--model", args.model,
            "--api-key-env", args.api_key_env,
            "--ramp", args.warmup_ramp,
            "--per-level", str(args.warmup_per_level),
            "--out", str(report_path),
        ]
        _log(f"warmup[{index}] {url}: {' '.join(command[2:])}")
        result = subprocess.run(command, cwd=str(PROJECT_ROOT))
        if result.returncode != 0:
            return None
        report = json.loads(report_path.read_text(encoding="utf-8"))
        measurements.append(int(report.get("max_clean_concurrency") or 0))
    return min(measurements) if measurements else None


def main() -> int:
    args = parse_args()
    env = dict(os.environ)
    if args.api_key:
        # The children read the key from the environment so it never lands in a
        # command line (visible in `ps`) or in the run metadata.
        env[args.api_key_env] = args.api_key
    if not env.get(args.api_key_env):
        raise SystemExit(f"{args.api_key_env} is not set; export it or pass --api-key")
    env.setdefault("ALFWORLD_DATA", str(PROJECT_ROOT / ".data" / "alfworld"))
    # Shard logs are the only progress signal during a long run; without this
    # the per-episode lines sit in a pipe buffer and the log looks stuck.
    env["PYTHONUNBUFFERED"] = "1"

    unified_args = shlex.split(args.unified_args)
    for forbidden in ("--out", "--num-shards", "--shard-index"):
        if forbidden in unified_args:
            raise SystemExit(f"{forbidden} is owned by this driver; remove it")

    limit = 0
    for i, token in enumerate(unified_args):
        if token == "--limit" and i + 1 < len(unified_args):
            limit = int(unified_args[i + 1])
        elif token.startswith("--limit="):
            limit = int(token.split("=", 1)[1])

    out_base = Path(args.out_base) if args.out_base else (
        PROJECT_ROOT / "outputs"
        / f"concurrent_{args.method}_{time.strftime('%Y%m%d_%H%M%S')}"
    )
    (out_base / "logs").mkdir(parents=True, exist_ok=True)

    measured = None
    if not args.skip_warmup:
        measured = run_warmup(args, out_base)
        if measured is None:
            raise SystemExit("warmup failed; fix the endpoint before spending "
                             "episodes on it (or pass --skip-warmup)")
        _log(f"warmup: max clean concurrency = {measured}")

    if args.shards == "auto":
        if not measured:
            raise SystemExit("--shards auto needs a warmup measurement; "
                             "run without --skip-warmup or pass an explicit count")
        shards = measured
    else:
        shards = int(args.shards)
        if measured and shards > measured:
            _log(f"warning: --shards {shards} exceeds the warmup's clean level "
                 f"{measured}; expect 429 backoff on some steps")
    if shards < 1:
        raise SystemExit("--shards must be >= 1")

    n_episodes = _count_items(unified_args, limit)
    _log(f"method={args.method} shards={shards} "
         f"episodes={n_episodes if n_episodes is not None else 'full split'}")

    commands: list[list[str]] = []
    shard_dirs: list[Path] = []
    for index in range(shards):
        shard_dir = out_base / f"shard{index}of{shards}"
        shard_dirs.append(shard_dir)
        commands.append([
            sys.executable, str(SCRIPTS / "run_unified_eval.py"),
            "--method", args.method,
            "--backend", "api",
            "--base-url", args.base_url,
            "--model", args.model,
            "--api-key-env", args.api_key_env,
            *unified_args,
            "--num-shards", str(shards),
            "--shard-index", str(index),
            "--out", str(shard_dir),
        ])

    if args.dry_run:
        for command in commands:
            print(" ".join(shlex.quote(part) for part in command))
        return 0

    meta = {
        "method": args.method,
        "model": args.model,
        "base_url": args.base_url,
        "base_urls": [u.strip() for u in str(args.base_url).split(",") if u.strip()],
        "shards": shards,
        "unified_args": unified_args,
        "episodes_expected": n_episodes,
        "warmup_max_clean_concurrency": measured,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    (out_base / "run_meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    started = time.time()
    processes: list[tuple[int, subprocess.Popen, object]] = []
    for index, (command, shard_dir) in enumerate(zip(commands, shard_dirs, strict=False)):
        shard_dir.mkdir(parents=True, exist_ok=True)
        log_path = out_base / "logs" / f"shard{index}of{shards}.log"
        handle = log_path.open("w", encoding="utf-8")
        _log(f"launch shard {index}/{shards} -> {log_path.name}")
        process = subprocess.Popen(
            command, cwd=str(PROJECT_ROOT), env=env, stdout=handle, stderr=subprocess.STDOUT
        )
        processes.append((index, process, handle))
        if args.shard_stagger and index + 1 < len(commands):
            time.sleep(args.shard_stagger)

    failures: list[int] = []
    for index, process, handle in processes:
        code = process.wait()
        handle.close()
        elapsed = time.time() - started
        _log(f"shard {index}/{shards} exited code={code} ({elapsed:.0f}s elapsed)")
        if code != 0:
            failures.append(index)

    meta["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    meta["wall_seconds"] = round(time.time() - started, 1)
    meta["failed_shards"] = failures
    (out_base / "run_meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    if failures:
        _log(f"shard(s) {failures} failed; see {out_base}/logs/. Re-run the same "
             "command to resume them (finished episodes are skipped), or pass "
             "--allow-incomplete to merge what completed.")
        if not args.allow_incomplete:
            return 1

    merge_command = [
        sys.executable, str(SCRIPTS / "merge_shards.py"),
        *[str(d) for d in shard_dirs],
        "--out", str(out_base / "merged"),
    ]
    if args.allow_incomplete:
        merge_command.append("--allow-incomplete")
    _log("merge: " + " ".join(merge_command[1:]))
    merged = subprocess.run(merge_command, cwd=str(PROJECT_ROOT))
    if merged.returncode != 0:
        return merged.returncode

    _log(f"done in {time.time() - started:.0f}s -> {out_base / 'merged'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
