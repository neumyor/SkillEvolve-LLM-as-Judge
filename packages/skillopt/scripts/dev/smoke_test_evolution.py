#!/usr/bin/env python3
"""Offline end-to-end smoke test for evidence-triggered evolution.

Drives the REAL SearchQA environment, the REAL reflect → aggregate → select
→ update → gate pipeline and the REAL Evolution Controller LLM calls through
``backend=openai_compatible`` pointed at ``scripts/dev/mock_openai_server.py``
— zero external services, deterministic, fast.

Checks per evolution mode:
  - the trainer completes and writes summary.json;
  - observation / attempt / decision artifacts exist;
  - the schedule semantics match the mode (immediate: 1 obs per attempt;
    fixed_k: K obs per attempt; end: one attempt per epoch; controller:
    adaptive trigger intervals from evolution_decisions.jsonl);
  - the original fixed mode still works.

Usage:
    .venv/bin/python scripts/dev/smoke_test_evolution.py [--out-dir DIR]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

MOCK_PORT = 8765
MOCK_BASE = f"http://127.0.0.1:{MOCK_PORT}"

N_TRAIN, N_VAL, N_TEST = 12, 4, 4


def make_split(root: str) -> str:
    """Create a tiny synthetic SearchQA split directory."""
    split_dir = os.path.join(root, "searchqa_split")

    def items(prefix: str, n: int) -> list[dict]:
        return [
            {
                "id": f"{prefix}_{i:03d}",
                "question": f"What is the answer to synthetic question {i}?",
                "context": f"[DOC] Synthetic passage {i}: the answer is yes. [DOC] Distractor passage {i}: irrelevant.",
                "answers": ["yes"],
            }
            for i in range(n)
        ]

    for name, data in (
        ("train", items("train", N_TRAIN)),
        ("val", items("val", N_VAL)),
        ("test", items("test", N_TEST)),
    ):
        d = os.path.join(split_dir, name)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "items.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    return split_dir


def wait_for_server(timeout: float = 15.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{MOCK_BASE}/v1/models", timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.3)
    return False


def run_mode(out_root: str, split_dir: str, mode: str, extra: list[str] | None = None) -> dict:
    env = dict(os.environ)
    env.update(
        {
            "OPENAI_COMPATIBLE_BASE_URL": f"{MOCK_BASE}/v1",
            "OPENAI_COMPATIBLE_API_KEY": "mock",
            "OPENAI_COMPATIBLE_MODEL": "mock-model",
            "PYTHONPATH": PROJECT_ROOT,
        }
    )
    cmd = [
        sys.executable,
        os.path.join(PROJECT_ROOT, "scripts", "train.py"),
        "--config", os.path.join(PROJECT_ROOT, "configs", "searchqa", "default.yaml"),
        "--cfg-options", "model.backend=openai_compatible",
        "--optimizer_model", "mock-model",
        "--target_model", "mock-model",
        "--split_dir", split_dir,
        "--train_size", str(N_TRAIN),
        "--num_epochs", "1",
        "--batch_size", "4",
        "--lr_scheduler", "constant",
        "--edit_budget", "4",
        "--use_slow_update", "false",
        "--use_meta_skill", "false",
        "--eval_test", "true",
        "--out_root", out_root,
        "--evolution_mode", mode,
        "--observation_batch_size", "4",
        *(extra or []),
    ]
    print(f"\n{'=' * 70}\n  SMOKE: evolution_mode={mode}\n{'=' * 70}", flush=True)
    proc = subprocess.run(
        cmd, cwd=PROJECT_ROOT, env=env, capture_output=True, text=True, timeout=600,
    )
    log_path = os.path.join(os.path.dirname(out_root), f"smoke_{mode}.log")
    with open(log_path, "w", encoding="utf-8") as f:
        f.write(proc.stdout + "\n--- stderr ---\n" + proc.stderr)
    if proc.returncode != 0:
        print(proc.stdout[-4000:])
        print(proc.stderr[-2000:])
        raise SystemExit(f"mode={mode} failed with exit code {proc.returncode} (log: {log_path})")
    with open(os.path.join(out_root, "summary.json"), encoding="utf-8") as f:
        return json.load(f)


def read_decisions(out_root: str) -> list[dict]:
    path = os.path.join(out_root, "evolution_decisions.jsonl")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def check(condition: bool, message: str) -> None:
    status = "ok  " if condition else "FAIL"
    print(f"  [{status}] {message}")
    if not condition:
        raise SystemExit(f"SMOKE CHECK FAILED: {message}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default=None, help="where to place run outputs")
    args = parser.parse_args()

    out_base = args.out_dir or tempfile.mkdtemp(prefix="skillopt_ete_smoke_")
    os.makedirs(out_base, exist_ok=True)
    split_dir = make_split(out_base)
    print(f"smoke outputs: {out_base}")
    print(f"synthetic split: {split_dir} (train={N_TRAIN} val={N_VAL} test={N_TEST})")

    # Start the mock server as a subprocess of this script.
    server = subprocess.Popen(
        [sys.executable, os.path.join(PROJECT_ROOT, "scripts", "dev", "mock_openai_server.py"),
         "--port", str(MOCK_PORT)],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    try:
        if not wait_for_server():
            raise SystemExit("mock server did not come up")
        print("mock OpenAI-compatible server is up")

        # ── fixed (original schedule) ────────────────────────────────
        s = run_mode(os.path.join(out_base, "run_fixed"), split_dir, "fixed")
        check(s["evolution"] is None, "fixed mode: no evolution summary")
        check(
            os.path.exists(os.path.join(out_base, "run_fixed", "steps", "step_0001", "rollout")),
            "fixed mode: original steps/ layout present",
        )
        check(
            not os.path.exists(os.path.join(out_base, "run_fixed", "evolution_decisions.jsonl")),
            "fixed mode: no evolution artifacts",
        )
        check(s["total_steps"] == N_TRAIN // 4, f"fixed mode: {N_TRAIN // 4} steps")

        # ── immediate ────────────────────────────────────────────────
        s = run_mode(os.path.join(out_base, "run_immediate"), split_dir, "immediate")
        evo = s["evolution"]
        check(evo["policy"] == "immediate", "immediate: policy name")
        check(evo["total_observations"] == N_TRAIN // 4, "immediate: one observation per m tasks")
        check(evo["total_attempts"] == N_TRAIN // 4, "immediate: an attempt per observation")
        check(
            all(t["observations"] == 1 for t in evo["trigger_intervals"]),
            "immediate: every window is exactly 1 observation",
        )
        check(
            len(read_decisions(os.path.join(out_base, "run_immediate"))) == N_TRAIN // 4,
            "immediate: decision log has one entry per observation",
        )

        # ── fixed_k (K=2 → windows of 2 observations = 8 tasks) ──────
        s = run_mode(
            os.path.join(out_base, "run_fixed_k"), split_dir, "fixed_k",
            extra=["--evolution_fixed_k", "2"],
        )
        evo = s["evolution"]
        check(evo["policy"] == "fixed_k", "fixed_k: policy name")
        check(
            all(t["observations"] == 2 for t in evo["trigger_intervals"]),
            "fixed_k: every window is exactly 2 observations",
        )
        check(evo["total_attempts"] == 1, "fixed_k: 3 obs / K=2 → 1 attempt")
        check(evo["leftover_buffer_observations"] == 1, "fixed_k: 1 leftover observation carries over")

        # ── end (one attempt per epoch) ──────────────────────────────
        s = run_mode(os.path.join(out_base, "run_end"), split_dir, "end")
        evo = s["evolution"]
        check(evo["policy"] == "end", "end: policy name")
        check(evo["total_attempts"] == 1, "end: exactly one attempt in one epoch")
        check(evo["trigger_intervals"][0]["tasks"] == N_TRAIN, "end: window covers the whole epoch")
        check(
            evo["trigger_intervals"][0]["trigger"] == "end:epoch_end",
            "end: attempt triggered at the epoch boundary",
        )

        # ── controller (ours; adaptive timing from the mock LLM) ─────
        s = run_mode(os.path.join(out_base, "run_controller"), split_dir, "controller")
        evo = s["evolution"]
        check(evo["policy"] == "controller", "controller: policy name")
        check(evo["total_observations"] == N_TRAIN // 4, "controller: observed the full stream")
        decisions = read_decisions(os.path.join(out_base, "run_controller"))
        check(len(decisions) >= N_TRAIN // 4, "controller: every observation consulted the policy")
        check(
            any(d["action"] == "WAIT" for d in decisions)
            and any(d["action"] == "UPDATE" for d in decisions),
            "controller: both WAIT and UPDATE decisions occurred (adaptive timing)",
        )
        intervals = evo["trigger_intervals"]
        check(
            all(t["observations"] >= 1 for t in intervals),
            "controller: every attempt consumed a non-empty evidence window",
        )
        # the mock controller updates once ≥8 tasks are buffered: the first
        # window must be larger than the immediate baseline's
        if intervals:
            check(
                intervals[0]["observations"] >= 2,
                "controller: first window accumulated multiple observations (evidence-triggered, not per-batch)",
            )
        check(
            evo["total_attempts"] == sum(1 for d in decisions if d["action"] == "UPDATE"),
            "controller: attempt count matches UPDATE decisions",
        )
        # history records carry the evolution window metadata
        history_path = os.path.join(out_base, "run_controller", "history.json")
        with open(history_path, encoding="utf-8") as f:
            history = json.load(f)
        check(
            all("evolution" in rec for rec in history),
            "controller: every attempt record carries evolution window metadata",
        )
        # observation artifacts on disk
        obs_dir = os.path.join(out_base, "run_controller", "observations")
        check(os.path.isdir(obs_dir), "controller: observations/ directory exists")
        obs_entries = sorted(os.listdir(obs_dir))
        check(
            len(obs_entries) == N_TRAIN // 4,
            "controller: one artifact directory per observation",
        )
        # controller LLM calls were tracked under their own stage
        tokens = s.get("token_summary", {})
        check(
            "evolution_controller" in tokens,
            "controller: token usage tracked under the evolution_controller stage",
        )

        # ── controller resume (idempotent rerun) ─────────────────────
        out_root = os.path.join(out_base, "run_controller")
        before = len(read_decisions(out_root))
        s2 = run_mode(out_root, split_dir, "controller")
        after = len(read_decisions(out_root))
        check(
            s2["evolution"]["total_observations"] == evo["total_observations"],
            "controller resume: no new observations after a completed run",
        )
        check(before == after, "controller resume: no new decisions logged")
        check(
            s2["evolution"]["total_attempts"] == evo["total_attempts"],
            "controller resume: no new attempts",
        )

        print("\n" + "=" * 70)
        print("  ALL SMOKE CHECKS PASSED")
        print("=" * 70)
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()


if __name__ == "__main__":
    main()
