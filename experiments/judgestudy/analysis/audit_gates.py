#!/usr/bin/env python3
"""Per-decision gate audit: what each gate did, decision by decision.

Reads the history.json of every completed condition and emits one row per
optimizer attempt, with the three things the experiment is about side by side:

  * what the optimizer produced (candidate hash, edit count, train-window score)
  * what the regression test would have said (measured selection accuracy)
  * what the judge said (verdict, confidence, how much evidence it saw)

For `greedy` runs there is no gate decision, which is the point: everything is
accepted, so its row shows the measured selection accuracy with no verdict.

Usage: python audit_gates.py --suite searchqa --out audit_searchqa.json
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys


def load_history(run_dir: str) -> list[dict]:
    path = os.path.join(run_dir, "history.json")
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def row_for(condition: str, step: dict) -> dict:
    return {
        "condition": condition,
        "step": step.get("step"),
        "epoch": step.get("epoch"),
        "action": step.get("action"),
        "gate_kind": step.get("gate_kind"),
        "judge_verdict": step.get("judge_verdict"),
        "judge_confidence": step.get("judge_confidence"),
        "judge_calls": step.get("judge_calls"),
        "judge_parse_failed": step.get("judge_parse_failed"),
        "judge_evidence_cards": step.get("judge_evidence_cards"),
        "judge_evidence_total": step.get("judge_evidence_total"),
        "judge_reason": (step.get("judge_reason") or "")[:400],
        # The measured selection split score. Present for rollout/greedy; None
        # under judge mode, where no per-candidate selection rollout ran.
        "selection_hard": step.get("selection_hard"),
        "rollout_hard": step.get("rollout_hard"),
        "rollout_n": step.get("rollout_n"),
        "candidate_gate_score": step.get("candidate_gate_score"),
        "current_score_after": step.get("current_score"),
        "best_score_after": step.get("best_score"),
        "candidate_hash": step.get("candidate_hash"),
        "candidate_skill_len": step.get("candidate_skill_len"),
        "skill_len": step.get("skill_len"),
        "n_edits_ranked": step.get("n_edits_ranked"),
        "edit_budget": step.get("edit_budget"),
        "wall_time_s": step.get("wall_time_s"),
    }


def summarize(run_dir: str, condition: str) -> dict:
    history = load_history(run_dir)
    rows = [row_for(condition, step) for step in history]
    accepts = [r for r in rows if r["action"] in ("accept", "accept_new_best", "force_accept")]
    rejects = [r for r in rows if r["action"] == "reject"]
    summary_path = os.path.join(run_dir, "summary.json")
    summary: dict = {}
    if os.path.isfile(summary_path):
        with open(summary_path, encoding="utf-8") as handle:
            data = json.load(handle)
        tokens = data.get("tokens") or {}
        summary = {
            "baseline_test_hard": data.get("baseline_test_hard"),
            "test_hard": data.get("test_hard"),
            "final_test_hard": data.get("final_test_hard"),
            "best_step": data.get("best_step"),
            "tokens_total": (tokens.get("_total") or {}).get("total_tokens"),
            "tokens_judge": (tokens.get("judge_gate") or {}).get("total_tokens", 0),
            "tokens_selection": (tokens.get("selection") or {}).get("total_tokens", 0),
        }
    return {
        "run_dir": run_dir,
        "condition": condition,
        "attempts": len(rows),
        "accepted": len(accepts),
        "rejected": len(rejects),
        "judge_calls": sum(r["judge_calls"] or 0 for r in rows),
        "judge_parse_failures": sum(1 for r in rows if r["judge_parse_failed"]),
        "rows": rows,
        "summary": summary,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--glob", required=True,
                    help="glob matching one run dir per condition, e.g. "
                         "'tmp/judgestudy/sq_k40_*'")
    ap.add_argument("--out", required=True)
    ap.add_argument("--condition-from-suffix", action="store_true", default=True)
    args = ap.parse_args()

    results = {}
    for run_dir in sorted(glob.glob(args.glob)):
        if not os.path.isdir(run_dir):
            continue
        condition = os.path.basename(run_dir.rstrip("/")).split("_")[-1]
        results[condition] = summarize(run_dir, condition)

    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(results, handle, indent=2, ensure_ascii=False)

    print(f"wrote {args.out}")
    header = f"{'condition':<10} {'attempts':>8} {'accept':>7} {'reject':>7} {'judge^':>7} {'parse_fail':>10} {'test':>8} {'final':>8}"
    print(header)
    print("-" * len(header))
    for condition, data in results.items():
        summary = data["summary"]
        test = summary.get("test_hard")
        final = summary.get("final_test_hard")
        print(f"{condition:<10} {data['attempts']:>8} {data['accepted']:>7} "
              f"{data['rejected']:>7} {data['judge_calls']:>7} "
              f"{data['judge_parse_failures']:>10} "
              f"{(f'{test:.4f}' if test is not None else 'n/a'):>8} "
              f"{(f'{final:.4f}' if final is not None else 'n/a'):>8}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
