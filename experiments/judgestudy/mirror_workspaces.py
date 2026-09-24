#!/usr/bin/env python3
"""Copy Trace2Skill analysis workspaces into a fresh work dir, dropping verdicts.

The analyst loop reads `agent_log.md` and writes reports + `evaluate_passed.flag`.
Re-running the *analyst* under a different verifier needs the inputs (trajectories,
gold) but must not inherit the previous verifier's verdicts -- a stale flag would
let the consolidation stage admit an episode the new verifier rejected.

Success analyses are copied with their reports (they are verifier-independent:
they distill a lesson from an episode that already succeeded, and both conditions
reuse them). Failure workspaces are copied WITHOUT `analysis_report.md`,
`analyst_transcript.json` and `evaluate_passed.flag`, so the analyst has to run
again under the new verifier.
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

VERDICT_ARTIFACTS = ("analysis_report.md", "analyst_transcript.json", "evaluate_passed.flag")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--dst", required=True)
    args = ap.parse_args()

    src, dst = Path(args.src), Path(args.dst)
    dst.mkdir(parents=True, exist_ok=True)
    n_fail = n_ok = 0
    for workspace in sorted(p for p in src.iterdir() if p.is_dir()):
        log = workspace / "agent_log.md"
        outcome = log.read_text(encoding="utf-8", errors="replace") if log.is_file() else ""
        target = dst / workspace.name
        shutil.copytree(workspace, target, dirs_exist_ok=True)
        if "Outcome: FAILURE" in outcome:
            n_fail += 1
            for name in VERDICT_ARTIFACTS:
                (target / name).unlink(missing_ok=True)
        else:
            n_ok += 1
    print(f"mirrored {n_fail + n_ok} workspace(s): {n_fail} failure (verdicts cleared), "
          f"{n_ok} success (reports kept) -> {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
