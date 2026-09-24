#!/usr/bin/env python3
"""Build Trace2Skill error-analysis workspaces from an ALFWorld eval run.

The ALFWorld analogue of ``setup_analysis_dir`` in Trace2Skill's
``analysis/run_error_analysis.py``::

    {output_dir}/{episode_id}/
        agent_log.md          # the episode as a step-by-step transcript
        agent_work/
            input.json        # task statement + initial observation
            output.json       # {"gamefile": ..., "actions": [...]}  <- candidate
            gold.txt          # pointer to the game file (the ground truth)

Two things distinguish this from the spreadsheet case:

* The ground truth is not a file to diff but the game's own goal condition.
  ``gold.txt`` therefore records the path to ``game.tw-pddl``; the verifier
  replays the candidate inside it. ``output.json`` is written in exactly the
  shape ``verify_episode`` consumes, so the analyst's edit-and-re-verify loop
  works without any format translation.

* The initial observation — which is where TextWorld renders the task
  statement — is not stored in the trajectory, whose first entry is already
  post-step feedback. It is recovered by resetting the environment on the game
  file. That costs one env reset per episode and no LLM call.

Usage::

    python -m alfworld_eval.analysis.dump_artifacts \\
        --run-dir outputs/unified_vanilla_20260911_104928 \\
        --output-dir analysis_workspaces \\
        --failures-only
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from alfworld_eval.analysis.verify_episode import DEFAULT_CONFIG, extract_goal
from alfworld_eval.env import split_for_gamefile
from alfworld_eval.unified.runner import episode_id


def load_results(run_dir: Path) -> list[dict]:
    path = run_dir / "results.jsonl"
    if not path.is_file():
        raise SystemExit(f"No results.jsonl in {run_dir}")
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_trajectory(run_dir: Path, row: dict, index: int) -> list[dict]:
    """Find the trajectory for an episode, accepting both on-disk formats."""
    path = run_dir / "trajectories" / f"{episode_id(row.get('gamefile', ''), index)}.json"
    if not path.is_file():
        # Runs produced before trajectories carried metadata were named by the
        # trial directory alone.
        legacy = run_dir / "trajectories" / f"{Path(row.get('gamefile', '')).parent.name}.json"
        if not legacy.is_file():
            return []
        path = legacy
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return list(data.get("trajectory", []))
    return list(data)


def fetch_initial_observation(gamefile: str, config_path: Path) -> tuple[str, str]:
    """Reset the game to recover the opening observation. Returns (obs, error)."""
    try:
        from alfworld_eval.env import AlfworldTextEnv
    except Exception as exc:  # noqa: BLE001
        return "", f"ALFWorld env unavailable: {type(exc).__name__}: {exc}"
    split = split_for_gamefile(gamefile)
    try:
        env = AlfworldTextEnv(config_path=config_path, split=split, gamefiles=[gamefile])
    except Exception as exc:  # noqa: BLE001
        return "", f"Could not open game: {type(exc).__name__}: {exc}"
    try:
        return env.reset().text, ""
    except Exception as exc:  # noqa: BLE001
        return "", f"Could not reset game: {type(exc).__name__}: {exc}"
    finally:
        env.close()


def render_log(row: dict, trajectory: list[dict], initial_obs: str, task: str) -> str:
    lines = [
        f"# ALFWorld Episode — {episode_id(row.get('gamefile', ''))}",
        "",
        f"- Task type: {row.get('task_type', '?')}",
        f"- Outcome: {'SUCCESS' if row.get('success') else 'FAILURE'}",
        f"- Steps taken: {row.get('steps', '?')}",
        f"- Invalid actions: {row.get('invalid_actions', '?')}",
        f"- Termination: {row.get('termination_reason', '?')}",
        "",
        "## Task",
        "",
        task,
        "",
        "## Initial observation",
        "",
        "```",
        initial_obs or "(unavailable)",
        "```",
        "",
        "## Trajectory",
        "",
    ]
    if not trajectory:
        lines += [
            "_(no trajectory recorded — re-run the eval with `--record-trajectory` "
            "to capture the model's per-step reasoning)_",
        ]
        return "\n".join(lines) + "\n"

    for step in trajectory:
        lines.append(f"### Step {step.get('step', '?')}")
        lines.append("")
        response = str(step.get("model_response", "")).strip()
        if response:
            lines += ["Model response:", "", "```", response, "```", ""]
        flag = "" if step.get("valid", True) else "  **(failed to parse as an action)**"
        lines.append(f"Action taken: `{step.get('action', '')}`{flag}")
        lines.append("")
        lines += ["Environment feedback:", "", "```",
                  str(step.get("env_feedback", "")).strip(), "```", ""]
        if step.get("done"):
            lines.append(f"Episode ended here (won={step.get('won')}).")
            lines.append("")
    return "\n".join(lines) + "\n"


def setup_analysis_dir(output_dir: Path, row: dict, trajectory: list[dict],
                       initial_obs: str, task: str, index: int) -> Path:
    ep_id = episode_id(row.get("gamefile", ""), index)
    analysis_dir = output_dir / ep_id
    agent_work = analysis_dir / "agent_work"
    agent_work.mkdir(parents=True, exist_ok=True)

    (analysis_dir / "agent_log.md").write_text(
        render_log(row, trajectory, initial_obs, task), encoding="utf-8")

    (agent_work / "input.json").write_text(json.dumps({
        "episode_id": ep_id,
        "task_type": row.get("task_type", ""),
        "task": task,
        "initial_observation": initial_obs,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    # Written in the exact shape verify_episode consumes, so the analyst can
    # copy it to output_fixed.json, edit the action list, and re-verify.
    (agent_work / "output.json").write_text(json.dumps({
        "gamefile": row.get("gamefile", ""),
        "actions": [str(s.get("action", "")) for s in trajectory],
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    (agent_work / "gold.txt").write_text(
        f"{row.get('gamefile', '')}\n", encoding="utf-8")

    return analysis_dir


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--failures-only", action="store_true",
                        help="Only dump unsuccessful episodes (the error-analyst input)")
    parser.add_argument("--successes-only", action="store_true",
                        help="Only dump successful episodes")
    parser.add_argument("--limit", type=int, default=0, help="Cap the number dumped (0 = all)")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG),
                        help="ALFWorld textworld.yaml")
    parser.add_argument("--no-env", action="store_true",
                        help="Skip the env reset that recovers the task statement "
                             "(faster; agent_log.md will lack the initial observation)")
    args = parser.parse_args()

    if args.failures_only and args.successes_only:
        raise SystemExit("--failures-only and --successes-only are mutually exclusive")

    rows = load_results(args.run_dir)
    selected = [
        (i, r) for i, r in enumerate(rows)
        if not ((args.failures_only and r.get("success"))
                or (args.successes_only and not r.get("success")))
    ]
    if args.limit:
        selected = selected[:args.limit]

    missing_traj = 0
    env_errors: list[str] = []
    for index, row in selected:
        trajectory = load_trajectory(args.run_dir, row, index)
        if not trajectory:
            missing_traj += 1
        initial_obs, error = ("", "") if args.no_env else fetch_initial_observation(
            row.get("gamefile", ""), Path(args.config))
        if error:
            env_errors.append(error)
        task = extract_goal(initial_obs) if initial_obs else "(task statement unavailable)"
        setup_analysis_dir(args.output_dir, row, trajectory, initial_obs, task, index)

    print(f"Wrote {len(selected)} analysis workspace(s) to {args.output_dir}")
    if missing_traj:
        print(f"  WARNING: {missing_traj} episode(s) had no trajectory on disk; "
              "re-run the eval with --record-trajectory for full analyst input")
    if env_errors:
        print(f"  WARNING: {len(env_errors)} episode(s) could not be opened; "
              f"first error: {env_errors[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
