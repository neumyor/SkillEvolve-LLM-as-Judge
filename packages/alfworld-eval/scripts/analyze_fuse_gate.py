"""Val/test gate analysis: paired per-episode comparison of staged fuse vs parent.

Reads N attempt runs for each system, computes the per-episode majority
verdict (>=2 of 3 attempts), then the paired transition table
(both_pass / neither / gain / regression) and per-type breakdown.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from alfworld_eval.unified.runner import episode_id


def load_attempts(base: str | Path) -> dict[str, list[bool]]:
    """{episode_id: [success per attempt]} over all attempt-*/merged runs.

    A directory without attempt-N subdirectories (a historical single merged
    run) is loaded as one attempt.
    """
    base = Path(base)
    results_files = sorted(base.glob("attempt-*/merged/results.jsonl"))
    if not results_files:
        direct = base / "merged" / "results.jsonl"
        if direct.is_file():
            results_files = [direct]
    outcomes: dict[str, list[bool]] = {}
    for merged in results_files:
        with merged.open(encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                row = json.loads(line)
                outcomes.setdefault(episode_id(row["gamefile"], 0), []).append(
                    bool(row["success"])
                )
    return outcomes


def majority(successes: list[bool], attempts: int) -> bool | None:
    """True/False by strict majority, None when attempts are missing."""
    if len(successes) < attempts:
        return None
    return sum(successes) * 2 > attempts


def main() -> int:
    staged_base, parent_base, attempts = sys.argv[1], sys.argv[2], int(sys.argv[3])
    staged = load_attempts(staged_base)
    parent = load_attempts(parent_base)

    episode_ids = sorted(set(staged) | set(parent))
    rows = []
    for eid in episode_ids:
        # Symmetric comparison: each side uses at most its first `attempts`
        # recorded runs, so a 3-attempt system can be compared against a
        # single historical run with attempts=1 without asymmetry.
        s = majority(staged.get(eid, [])[:attempts], attempts)
        p = majority(parent.get(eid, [])[:attempts], attempts)
        if s is None or p is None:
            verdict = "infra_unresolved"
        elif s and p:
            verdict = "both_pass"
        elif not s and not p:
            verdict = "neither"
        elif s and not p:
            verdict = "gain"
        else:
            verdict = "regression"
        task_type = eid.split("-")[0]
        for t in ("pick_two", "pick_clean", "pick_cool", "pick_heat", "pick_and_place",
                  "look_at"):
            if eid.startswith(t):
                task_type = t
                break
        rows.append((eid, task_type, s, p, verdict))

    counts: dict[str, int] = {}
    for _, _, _, _, verdict in rows:
        counts[verdict] = counts.get(verdict, 0) + 1
    print(f"episodes: {len(rows)} (attempts={attempts}, majority gate)")
    print("transitions:", counts)
    print()
    print(f"{'task_type':<32}{'both':>6}{'neither':>9}{'gain':>6}{'reg':>6}{'infra':>7}")
    types = sorted({r[1] for r in rows})
    for t in types:
        sub = [r for r in rows if r[1] == t]
        c = {v: sum(1 for r in sub if r[4] == v)
             for v in ("both_pass", "neither", "gain", "regression", "infra_unresolved")}
        print(f"{t:<32}{c['both_pass']:>6}{c['neither']:>9}{c['gain']:>6}"
              f"{c['regression']:>6}{c['infra_unresolved']:>7}")
    print()
    for eid, t, s, p, verdict in rows:
        if verdict in ("gain", "regression", "infra_unresolved"):
            print(f"  {verdict:<16}{t:<28}{eid[:60]}")

    # Pass rates for reference
    for name, data in (("staged", staged), ("parent", parent)):
        passed = sum(1 for v in data.values() if majority(v, attempts))
        print(f"{name}: pass@majority {passed}/{len(data)}")
    out = Path(staged_base).parent / "gate_analysis.json"
    out.write_text(json.dumps({
        "attempts": attempts,
        "transitions": counts,
        "rows": [{"episode": r[0], "task_type": r[1], "staged": r[2],
                  "parent": r[3], "verdict": r[4]} for r in rows],
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"saved -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
