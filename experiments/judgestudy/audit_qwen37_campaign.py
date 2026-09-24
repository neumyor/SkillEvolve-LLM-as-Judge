#!/usr/bin/env python3
"""Audit completed qwen3.7-plus campaign conditions before analysis."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


EXPECTED = {
    "searchqa": {"train": 400, "val": 200, "test": 1400},
    "alfworld": {"train": 39, "val": 18, "test": 134},
}


def _json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _jsonl(path: Path) -> list[dict]:
    rows = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _check_jsonl(path: Path, expected: int, id_keys: tuple[str, ...]) -> list[str]:
    errors = []
    rows = _jsonl(path)
    if len(rows) != expected:
        errors.append(f"{path.name}: {len(rows)} rows, expected {expected}")
    ids = []
    for row in rows:
        value = next((row.get(key) for key in id_keys if row.get(key) is not None), None)
        if value is not None:
            ids.append(str(value))
    if len(ids) != len(set(ids)):
        errors.append(f"{path.name}: duplicate item ids")
    return errors


def audit_condition(benchmark: str, method: str, mode: str, output: Path) -> dict:
    expected = EXPECTED[benchmark]
    errors: list[str] = []
    status_path = output / "condition_status.json"
    if not status_path.is_file():
        errors.append("missing condition_status.json")
    elif _json(status_path).get("full_validation_audit") is not False:
        errors.append("condition did not explicitly disable per-decision full-validation audit")
    if mode == "judge":
        forbidden = [p for p in output.rglob("*") if p.is_file() and "judge_full_validation" in p.name]
        if forbidden:
            errors.append("judge condition contains per-decision full-validation audit artifact")

    if method == "skillopt":
        summary = output / "summary.json"
        test = output / "test_eval" / "results.jsonl"
        if not summary.is_file():
            errors.append("missing summary.json")
        if test.is_file():
            errors.extend(_check_jsonl(test, expected["test"], ("id", "instance_id", "gamefile")))
        else:
            errors.append("missing test_eval/results.jsonl")
        config = output / "config.json"
        if config.is_file():
            cfg = _json(config)
            if cfg.get("optimizer_model") != "qwen3.7-plus" or cfg.get("target_model") != "qwen3.7-plus":
                errors.append("SkillOpt model metadata is not qwen3.7-plus")
            if mode == "judge" and cfg.get("judge_full_validation_audit", False):
                errors.append("SkillOpt judge config enabled full validation audit")
    elif method == "trace2skill":
        for name in (
            "provenance.json", "analysis_summary.json", "val_run/summary.json",
            "test_run/summary.json",
        ):
            if not (output / name).is_file():
                errors.append(f"missing {name}")
        errors.extend(_check_jsonl(
            output / "val_run/results.jsonl", expected["val"], ("id", "instance_id", "gamefile")
        ))
        errors.extend(_check_jsonl(output / "test_run/results.jsonl", expected["test"], ("id", "instance_id", "gamefile")))
        provenance = output / "provenance.json"
        if provenance.is_file() and _json(provenance).get("model") != "qwen3.7-plus":
            errors.append("Trace2Skill model metadata is not qwen3.7-plus")
    elif method == "gepa":
        for name in ("result.json", "run_metadata.json", "validation_eval.json", "test_eval.json"):
            if not (output / name).is_file():
                errors.append(f"missing {name}")
        for name, count in (("validation_eval.json", expected["val"]), ("test_eval.json", expected["test"])):
            path = output / name
            if path.is_file():
                data = _json(path)
                if data.get("items") != count:
                    errors.append(f"{name}: items={data.get('items')}, expected {count}")
                if len(data.get("best_scores", [])) != count:
                    errors.append(f"{name}: score vector length mismatch")
                if data.get("audit_enabled"):
                    errors.append(f"{name}: audit_enabled=true")
        meta = output / "run_metadata.json"
        if meta.is_file() and _json(meta).get("model") != "qwen3.7-plus":
            errors.append("GEPA model metadata is not qwen3.7-plus")
    elif method == "skillgen":
        for name in ("validation_summary.json", "test_summary.json"):
            if not (output / name).is_file():
                errors.append(f"missing {name}")
        for name, count in (("validation_summary.json", expected["val"]), ("test_summary.json", expected["test"])):
            path = output / name
            if path.is_file() and _json(path).get("items") != count:
                errors.append(f"{name}: items={_json(path).get('items')}, expected {count}")

    return {
        "benchmark": benchmark, "method": method, "mode": mode,
        "output": str(output),
        "model": "qwen3.7-plus", "passed": not errors, "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("campaign_root", type=Path)
    parser.add_argument(
        "--skillopt-root",
        type=Path,
        default=None,
        help="Optional legacy root containing completed SearchQA SkillOpt conditions",
    )
    args = parser.parse_args()
    rows = []
    for benchmark in EXPECTED:
        for method in ("skillopt", "trace2skill", "gepa", "skillgen"):
            for mode in ("baseline", "judge"):
                output = args.campaign_root / benchmark / f"{method}_{mode}"
                if method == "skillopt" and not (output / "condition_status.json").is_file():
                    legacy_root = args.skillopt_root
                    if legacy_root is None:
                        legacy_root = args.campaign_root.parent / "qwen37_campaign_searchqa_skillopt"
                    legacy_output = legacy_root / benchmark / f"{method}_{mode}"
                    if (legacy_output / "condition_status.json").is_file():
                        output = legacy_output
                status = output / "condition_status.json"
                if not status.is_file():
                    row = {
                        "benchmark": benchmark, "method": method, "mode": mode,
                        "output": str(output), "model": "qwen3.7-plus",
                        "passed": False, "errors": ["missing condition_status.json"],
                    }
                    rows.append(row)
                    continue
                row = audit_condition(benchmark, method, mode, output)
                rows.append(row)
                (output / "integrity_audit.json").write_text(
                    json.dumps(row, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
                )
    report = {
        "conditions": rows,
        "condition_count": len(rows),
        "expected_condition_count": len(EXPECTED) * 4 * 2,
        "passed": len(rows) == len(EXPECTED) * 4 * 2 and all(row["passed"] for row in rows),
    }
    out = args.campaign_root / "integrity_audit.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
