#!/usr/bin/env python
"""Warm up an OpenAI-compatible endpoint before a concurrent ALFWorld run.

Why this exists
---------------
The gateway in front of the evaluation endpoint answers a cold burst of
concurrent requests with ``HTTP 429``. ``run_unified_eval.py`` does retry 429
(five attempts with exponential backoff), but a whole concurrent run starting
cold pays that backoff on every shard at once, so the first minutes of a run
are spent re-proving the endpoint is alive instead of evaluating episodes.

This script front-loads that cost and, more usefully, *measures* it:

1. **probe** -- one sequential request. A 401/404 here is a hard failure (bad
   key, unknown model), so it exits immediately with the status that came back
   instead of letting a 100-episode run discover it per step.
2. **sequential** -- a few more sequential requests, so the model is resident
   and the gateway's rate limiter has seen this key.
3. **ramp** -- a tiny burst at each concurrency level (default 1, 2, 4, 8, 16),
   recording latency and the 429 rate per level. The highest clean level is the
   empirically supported shard count, which is what ``--suggest`` prints.

Exit status is 0 only when at least one concurrency level completed with a 429
rate at or below ``--max-429-rate``.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

RETRYABLE_STATUS = frozenset({408, 409, 425, 429, 500, 502, 503, 504, 529})
#: Kept short: a warmup request only has to prove the path is open, and this
#: model bills reasoning tokens even when asked for one word.
WARMUP_PROMPT = "Reply with the single word: ok"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--base-url", required=True,
                   help="OpenAI-compatible base URL, e.g. https://host/v1")
    p.add_argument("--model", required=True)
    p.add_argument("--api-key", default="", help="Inline key (avoid: use --api-key-env)")
    p.add_argument("--api-key-env", default="",
                   help="Env var holding the key, e.g. ALF_LLM_KEY")
    p.add_argument("--max-tokens", type=int, default=64)
    p.add_argument("--timeout", type=float, default=120.0)
    p.add_argument("--sequential", type=int, default=3,
                   help="Sequential requests before the concurrency ramp")
    p.add_argument("--ramp", default="1,2,4,8,16",
                   help="Comma-separated concurrency levels to test")
    p.add_argument("--per-level", type=int, default=2,
                   help="Requests fired at each ramp level")
    p.add_argument("--max-429-rate", type=float, default=0.25,
                   help="A level counts as clean at or below this 429 rate")
    p.add_argument("--retries", type=int, default=4,
                   help="Per-request retries on a retryable status")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", default="", help="Write the JSON report here")
    return p.parse_args()


def _payload(model: str, max_tokens: int, seed: int) -> bytes:
    return json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": WARMUP_PROMPT}],
        "temperature": 0,
        "max_tokens": max_tokens,
        "seed": seed,
    }).encode("utf-8")


def request_once(
    base_url: str,
    headers: dict[str, str],
    payload: bytes,
    timeout: float,
    retries: int,
) -> dict:
    """One warmup request, retrying retryable statuses. Never raises for 429.

    Returns a record with ``ok``, ``status``, ``seconds`` and (on failure) the
    status that ended the attempt sequence, so the caller can compute a 429 rate
    without exception plumbing.
    """
    url = base_url.rstrip("/") + "/chat/completions"
    started = time.time()
    status: int | None = None
    detail = ""
    for attempt in range(max(1, retries)):
        try:
            request = urllib.request.Request(
                url, data=payload, headers=headers, method="POST"
            )
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
            status = 200
            usage = body.get("usage") or {}
            return {
                "ok": True,
                "status": 200,
                "seconds": round(time.time() - started, 3),
                "attempts": attempt + 1,
                "completion_tokens": int(usage.get("completion_tokens", 0) or 0),
                "id": str(body.get("id", "")),
            }
        except urllib.error.HTTPError as exc:
            status = exc.code
            detail = f"HTTP {exc.code} {exc.reason}"
            if exc.code not in RETRYABLE_STATUS:
                # Bad key / unknown model: retrying cannot fix it, and letting a
                # long run discover this per step is exactly the failure this
                # script exists to prevent.
                return {
                    "ok": False,
                    "status": exc.code,
                    "seconds": round(time.time() - started, 3),
                    "attempts": attempt + 1,
                    "fatal": True,
                    "error": detail,
                }
            time.sleep(min(2.0 * (2**attempt), 10.0))
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            detail = repr(exc)
            time.sleep(min(2.0 * (2**attempt), 10.0))
    return {
        "ok": False,
        "status": status,
        "seconds": round(time.time() - started, 3),
        "attempts": max(1, retries),
        "error": detail or "exhausted retries",
    }


def burst(
    level: int,
    count: int,
    base_url: str,
    headers: dict[str, str],
    payload: bytes,
    timeout: float,
    retries: int,
) -> dict:
    with ThreadPoolExecutor(max_workers=level) as pool:
        records = list(pool.map(
            lambda _: request_once(base_url, headers, payload, timeout, retries),
            range(count),
        ))
    n = len(records)
    n_429 = sum(1 for r in records if r.get("status") == 429)
    n_ok = sum(1 for r in records if r.get("ok"))
    fatal = [r for r in records if r.get("fatal")]
    return {
        "concurrency": level,
        "requests": n,
        "ok": n_ok,
        "rate_limited": n_429,
        "rate_limit_rate": round(n_429 / n, 3) if n else 1.0,
        "errors": [r.get("error") for r in records if not r.get("ok")],
        "fatal": bool(fatal),
        "median_seconds": round(
            sorted(r["seconds"] for r in records)[n // 2], 3
        ) if n else None,
        "wall_seconds": None,
    }


def main() -> int:
    args = parse_args()
    api_key = args.api_key or (os.environ.get(args.api_key_env, "") if args.api_key_env else "")
    if not api_key:
        raise SystemExit(
            "no API key: pass --api-key-env (preferred) or --api-key"
        )
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    payload = _payload(args.model, args.max_tokens, args.seed)

    report: dict = {
        "base_url": args.base_url,
        "model": args.model,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "sequential": [],
        "ramp": [],
    }

    print(f"warmup: {args.base_url} model={args.model}")
    probe = request_once(args.base_url, headers, payload, args.timeout, retries=1)
    report["probe"] = probe
    if not probe["ok"]:
        print(f"probe FAILED: {probe.get('error')}", file=sys.stderr)
        _write(args, report)
        return 2
    print(f"probe ok ({probe['seconds']}s, {probe['completion_tokens']} completion tokens)")

    for i in range(max(0, args.sequential)):
        record = request_once(args.base_url, headers, payload, args.timeout, args.retries)
        report["sequential"].append(record)
        state = "ok" if record["ok"] else f"FAILED {record.get('error')}"
        print(f"sequential {i + 1}/{args.sequential}: {state} ({record['seconds']}s)")
        if record.get("fatal"):
            _write(args, report)
            return 2
        time.sleep(0.5)

    levels = [int(x) for x in str(args.ramp).split(",") if x.strip()]
    best = 0
    for level in levels:
        started = time.time()
        result = burst(
            level, max(level, args.per_level), args.base_url, headers, payload,
            args.timeout, args.retries,
        )
        result["wall_seconds"] = round(time.time() - started, 3)
        report["ramp"].append(result)
        print(
            f"ramp c={level}: ok={result['ok']}/{result['requests']} "
            f"429={result['rate_limited']} median={result['median_seconds']}s "
            f"wall={result['wall_seconds']}s"
        )
        if result["fatal"]:
            print("fatal error during ramp; stopping", file=sys.stderr)
            break
        if result["rate_limit_rate"] <= args.max_429_rate and result["ok"]:
            best = level
        else:
            # Sustained 429s: a higher level will only make it worse, so the
            # ramp stops at the first level that is not clean.
            print(f"  level {level} exceeds the clean threshold; stopping the ramp")
            break
        time.sleep(1.0)

    report["max_clean_concurrency"] = best
    report["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    _write(args, report)

    if best <= 0:
        print("warmup FAILED: no concurrency level came back clean", file=sys.stderr)
        return 1
    print(f"warmup done: max clean concurrency = {best}")
    return 0


def _write(args: argparse.Namespace, report: dict) -> None:
    if not args.out:
        return
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"warmup report -> {path}")


if __name__ == "__main__":
    raise SystemExit(main())
