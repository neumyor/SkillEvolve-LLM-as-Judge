#!/usr/bin/env python
"""Prepare a FUSE round-2 working directory from a completed round-1 run.

FUSE round-2 semantics (ported from SkillEvolveCPM):

* every family is re-authored regardless of its round-1 status -- no
  cherry-picking by gain/regression/decision;
* round-1 products are read-only; round 2 writes to a new out directory;
* round-2 candidates derive from the round-1 *published* set (per-type
  parent), preserving evidence-supported successes and repairing the
  previous round's validation failures;
* the acceptance baseline becomes the round-1 published system's train
  record (not the original baseline), so a round-2 candidate must not
  regress against what round 1 already achieved.

This script copies the data artifacts (manifest, source, tags, clusters,
diagnoses), computes the round-1 published-system baseline
(``baseline_outcomes.json``), the authoring validation summary
(``validation_summary.json``) and the regression incident list
(``extra_diagnoses.txt``).

Usage:
  python scripts/prepare_fuse_round2.py \
      --round1 outputs/fuse_run \
      --round2 outputs/fuse_run_round2
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from alfworld_eval.fuse.evidence import load_manifest  # noqa: E402
from alfworld_eval.unified.runner import episode_id  # noqa: E402


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--round1", required=True, help="round-1 out directory")
    p.add_argument("--round2", required=True, help="round-2 out directory (created)")
    return p.parse_args()


def majority(attempt_rows: list[bool]) -> bool:
    return sum(attempt_rows) * 2 > len(attempt_rows)


def main() -> int:
    args = parse_args()
    round1 = Path(args.round1).resolve()
    round2 = Path(args.round2).resolve()
    report = json.loads((round1 / "report.json").read_text(encoding="utf-8"))
    manifest = load_manifest(round1 / "manifest.jsonl")

    # 1. Copy the data artifacts (not validations/skills: round 2 re-authors).
    if round2.exists():
        raise SystemExit(f"{round2} already exists; remove it or pick a new name")
    for name in ("manifest.jsonl", "source", "tagging", "diagnoses"):
        src = round1 / name
        if not src.exists():
            raise SystemExit(f"round-1 artifact missing: {src}")
        dst = round2 / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        (shutil.copytree if src.is_dir() else shutil.copyfile)(src, dst)

    # 2. Round-1 per-episode validation record.
    attempts_path = round1 / "validations" / "attempts.json"
    attempts = json.loads(attempts_path.read_text(encoding="utf-8"))
    validation_rows: dict[str, dict] = {}
    for task_type, family_report in attempts.items():
        if family_report.get("status") != "validated":
            continue
        for incident in manifest:
            if incident.task_type != task_type:
                continue
            rows = [
                bool(a.get(incident.incident_id, {}).get("success"))
                if a.get(incident.incident_id) else False
                for a in family_report["attempts"]
            ]
            present = sum(
                1 for a in family_report["attempts"] if incident.incident_id in a
            )
            validation_rows[incident.incident_id] = {
                "task_type": task_type,
                "attempt_successes": sum(rows),
                "attempts_present": present,
                "passed": majority(rows),
            }

    # 3. Round-1 published system's train record (acceptance baseline):
    #    accepted families -> their candidate's majority verdict;
    #    fallback families -> the original baseline outcome (the parent ran).
    baseline_rows: dict[str, dict] = {}
    by_type = {i.task_type: [] for i in manifest}
    for incident in manifest:
        by_type.setdefault(incident.task_type, []).append(incident)
    for incident in manifest:
        family = report.get("families", {}).get(incident.task_type, {})
        if family.get("status") == "accepted":
            row = validation_rows.get(incident.incident_id, {})
            success = bool(row.get("passed", False))
            source = "round1_candidate"
        else:
            success = incident.outcome == "success"
            source = "parent_fallback_baseline"
        baseline_rows[incident.incident_id] = {"success": success, "source": source}

    # 4. Regression incidents (baseline success -> round-1 validation fail)
    #    become round-2 diagnosis targets.
    regressions = []
    for incident_id, row in validation_rows.items():
        incident = next(i for i in manifest if i.incident_id == incident_id)
        if incident.outcome == "success" and not row["passed"]:
            regressions.append(incident_id)

    (round2 / "baseline_outcomes.json").write_text(
        json.dumps(baseline_rows, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (round2 / "validation_summary.json").write_text(
        json.dumps(validation_rows, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (round2 / "extra_diagnoses.txt").write_text(
        "\n".join(regressions) + ("\n" if regressions else ""),
        encoding="utf-8",
    )

    n_pass = sum(1 for r in baseline_rows.values() if r["success"])
    print(f"round-2 prepared at {round2}")
    print(f"  round-1 published baseline: {n_pass}/{len(baseline_rows)} train episodes pass")
    print(f"  regression incidents to re-diagnose: {len(regressions)}")
    for r in regressions:
        print(f"    {r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
