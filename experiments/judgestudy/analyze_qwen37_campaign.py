#!/usr/bin/env python3
"""Build a fixed-metric comparison for the qwen3.7-plus campaign.

The script is deliberately read-only with respect to experiment outputs.  It
uses validation and test measurements made after optimization, never the
optional per-decision full-validation audit.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


BENCHMARKS = ("searchqa", "alfworld")
METHODS = ("skillopt", "trace2skill", "gepa", "skillgen")
MODES = ("baseline", "judge")


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _output(root: Path, skillopt_root: Path | None, benchmark: str, method: str, mode: str) -> Path:
    path = root / benchmark / f"{method}_{mode}"
    if method == "skillopt" and not (path / "condition_status.json").is_file():
        legacy = skillopt_root or root.parent / "qwen37_campaign_searchqa_skillopt"
        candidate = legacy / benchmark / f"{method}_{mode}"
        if (candidate / "condition_status.json").is_file():
            return candidate
    return path


def _metric(summary: dict[str, Any], benchmark: str) -> float | None:
    if benchmark == "searchqa":
        value = summary.get("em")
    else:
        value = summary.get("success_rate")
    return float(value) if value is not None else None


def _trace_summary(path: Path, benchmark: str) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    payload = _read(path)
    return payload.get("summary") or payload


def _condition(benchmark: str, method: str, mode: str, output: Path) -> dict[str, Any]:
    row: dict[str, Any] = {
        "benchmark": benchmark, "method": method, "mode": mode,
        "output": str(output), "status": "missing",
        "validation": None, "test": None, "tokens": None,
    }
    status_path = output / "condition_status.json"
    if status_path.is_file():
        status = _read(status_path)
        row["status"] = status.get("status")
        row["full_validation_audit"] = status.get("full_validation_audit")

    if method == "skillopt":
        summary_path = output / "summary.json"
        if summary_path.is_file():
            summary = _read(summary_path)
            row["validation"] = summary.get("final_selection_hard")
            row["test"] = summary.get("final_test_hard")
            row["tokens"] = ((summary.get("token_summary") or {}).get("_total") or {}).get("total_tokens")
    elif method == "trace2skill":
        val = _trace_summary(output / "val_run/summary.json", benchmark)
        test = _trace_summary(output / "test_run/summary.json", benchmark)
        row["validation"] = _metric(val or {}, benchmark)
        row["test"] = _metric(test or {}, benchmark)
        usage = []
        for split in ("train_run", "val_run", "test_run"):
            payload = _trace_summary(output / split / "summary.json", benchmark)
            if payload and payload.get("usage"):
                usage.append(payload["usage"].get("total_tokens", 0))
        row["tokens"] = sum(usage) if usage else None
    elif method == "gepa":
        val_path, test_path = output / "validation_eval.json", output / "test_eval.json"
        if val_path.is_file():
            row["validation"] = _read(val_path).get("best_mean")
        if test_path.is_file():
            row["test"] = _read(test_path).get("best_mean")
    else:
        val_path, test_path = output / "validation_summary.json", output / "test_summary.json"
        if val_path.is_file():
            row["validation"] = _read(val_path).get("skill_success_rate")
        if test_path.is_file():
            row["test"] = _read(test_path).get("skill_success_rate")
    return row


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("campaign_root", type=Path)
    parser.add_argument("--skillopt-root", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    rows = [
        _condition(b, m, mode, _output(args.campaign_root, args.skillopt_root, b, m, mode))
        for b in BENCHMARKS for m in METHODS for mode in MODES
    ]
    comparisons = []
    for benchmark in BENCHMARKS:
        for method in METHODS:
            pair = [r for r in rows if r["benchmark"] == benchmark and r["method"] == method]
            base, judge = next(r for r in pair if r["mode"] == "baseline"), next(r for r in pair if r["mode"] == "judge")
            comparisons.append({
                "benchmark": benchmark, "method": method,
                "validation_baseline": base["validation"], "validation_judge": judge["validation"],
                "validation_delta_judge_minus_baseline": (
                    judge["validation"] - base["validation"]
                    if base["validation"] is not None and judge["validation"] is not None else None
                ),
                "test_baseline": base["test"], "test_judge": judge["test"],
                "test_delta_judge_minus_baseline": (
                    judge["test"] - base["test"]
                    if base["test"] is not None and judge["test"] is not None else None
                ),
            })
    payload = {"conditions": rows, "comparisons": comparisons,
               "complete": all(r["status"] == "completed" and r["validation"] is not None and r["test"] is not None for r in rows)}
    target = args.output or args.campaign_root / "comparison.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(target), "complete": payload["complete"], "conditions": len(rows)}, indent=2))
    return 0 if payload["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
