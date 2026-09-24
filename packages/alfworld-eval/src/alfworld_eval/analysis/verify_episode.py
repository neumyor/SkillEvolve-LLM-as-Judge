#!/usr/bin/env python3
"""Verify a proposed ALFWorld action sequence by replaying it in the real game.

This is the ALFWorld analogue of Trace2Skill's ``analysis/evaluate_output.py``.

In the spreadsheet setting the agent produces a file (``output.xlsx``) that can
be diffed against a static ground truth (``gold.xlsx``). ALFWorld has no such
artifact: correctness is a property of the *environment's* goal condition after
a sequence of actions. So the ground truth here is the game itself
(``game.tw-pddl``), and "comparing" means replaying the candidate action
sequence in that game and asking whether the goal was reached.

That keeps the analyst loop intact — propose a minimal fix, write
``output_fixed.json``, re-verify — while making the verdict as objective as a
cell-by-cell diff. No LLM is involved.

Candidate file format (JSON)::

    {"gamefile": "<path to game.tw-pddl>", "actions": ["go to desk 1", "..."]}

``gamefile`` may be omitted when ``--ground_truth`` is passed.

Usage::

    python -m alfworld_eval.analysis.verify_episode \\
        --output_file agent_work/output_fixed.json \\
        --ground_truth agent_work/game.tw-pddl
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

from alfworld_eval.analysis.report import RULE, THIN, header

# Observation text ALFWorld emits when an action parses but changes nothing.
NO_OP_TEXT = "nothing happens"
#: Navigation dominates an ALFWorld admissible list (a room has dozens of
#: receptacles) and it is almost never the repair for a rejected action.
NAV_PREFIX = "go to "
_TOKEN_RE = re.compile(r"[a-z0-9]+")
#: How many admissible commands the failure report prints.
ADMISSIBLE_SHOWN = 40


def rank_admissible_commands(
    proposed: str,
    commands: list[str] | tuple[str, ...],
    limit: int = ADMISSIBLE_SHOWN,
) -> tuple[list[str], int]:
    """Order one step's admissible commands by how likely they are the repair.

    ALFWorld rejects an action by grammar, not by intent: ``put kettle 1 in
    cabinet 1`` is inadmissible while the accepted form is ``move kettle 1 to
    cabinet 1``. The failed proposal therefore names the object and the
    destination it wanted, and the fix is the admissible command that shares
    those words -- so those commands are printed first.

    This matters because the list is long. Printing the environment's own order
    (or any alphabetical order) buries ``move ... to ...`` after dozens of
    ``go to ...`` lines and truncates it away: a measured failure where the
    analyst looped until its turn budget ran out, calling the verifier five
    times, without ever being shown the one command that satisfied the goal.
    Ranking keeps the fix visible; the omitted tail is now navigation, which is
    the least informative class.
    """
    wanted = set(_TOKEN_RE.findall(str(proposed).lower()))

    def sort_key(indexed: tuple[int, str]) -> tuple[int, bool, int]:
        index, command = indexed
        overlap = len(wanted & set(_TOKEN_RE.findall(command.lower())))
        return (-overlap, command.lower().startswith(NAV_PREFIX), index)

    ordered = [command for _, command in sorted(enumerate(commands), key=sort_key)]
    return ordered[:limit], max(0, len(ordered) - limit)

DEFAULT_CONFIG = Path(__file__).resolve().parents[3] / "configs" / "textworld.yaml"


def load_candidate(path: str) -> tuple[list[str], str | None, str]:
    """Read a candidate action sequence. Returns (actions, gamefile, error)."""
    p = Path(path)
    if not p.is_file():
        return [], None, f"Candidate file does not exist: {path}"
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [], None, f"Candidate file is not valid JSON: {exc}"

    if isinstance(data, list):
        # Bare action list is accepted for convenience.
        actions, gamefile = data, None
    elif isinstance(data, dict):
        actions = data.get("actions")
        gamefile = data.get("gamefile")
        if actions is None:
            return [], None, "Candidate JSON has no 'actions' key"
    else:
        return [], None, "Candidate JSON must be an object or a list"

    if not isinstance(actions, list) or not all(isinstance(a, str) for a in actions):
        return [], None, "'actions' must be a list of strings"
    return [a.strip() for a in actions], gamefile, ""


def replay(gamefile: str, actions: list[str], max_steps: int,
           config_path: Path) -> dict:
    """Replay *actions* in *gamefile*. Returns a structured trace."""
    from alfworld_eval.env import AlfworldTextEnv, split_for_gamefile

    split = split_for_gamefile(gamefile)
    env = AlfworldTextEnv(config_path=config_path, split=split, gamefiles=[gamefile])
    try:
        obs = env.reset()
        initial_obs = obs.text
        steps: list[dict] = []
        won = False
        done = False
        for i, action in enumerate(actions):
            if i >= max_steps:
                break
            admissible = list(obs.admissible_commands)
            was_admissible = action in admissible
            result = env.step(action)
            obs = result.observation
            feedback = obs.text
            steps.append({
                "step": i,
                "action": action,
                "admissible": was_admissible,
                "feedback": feedback,
                "no_op": NO_OP_TEXT in feedback.lower(),
                "reward": result.reward,
                "done": result.done,
                "won": result.won,
                # Kept only for the step that needs it, to bound report size.
                "admissible_commands": admissible,
            })
            won, done = result.won, result.done
            if done:
                break
        return {
            "task": extract_goal(initial_obs),
            "initial_observation": initial_obs,
            "steps": steps,
            "won": won,
            "done": done,
            "n_actions": len(actions),
            "n_executed": len(steps),
        }
    finally:
        env.close()


def extract_goal(initial_obs: str) -> str:
    """Pull the task statement out of ALFWorld's initial observation.

    The goal is not stored in game.tw-pddl under a readable key; TextWorld
    renders it into the opening observation as 'Your task is to: ...'.
    """
    marker = "Your task is to:"
    idx = initial_obs.find(marker)
    if idx == -1:
        return "(task statement not found in initial observation)"
    return initial_obs[idx + len(marker):].strip().split("\n")[0].strip()


def build_report(trace: dict, output_file: str, gamefile: str,
                 max_steps: int) -> tuple[bool, str, str]:
    """Render the verification report. Returns (passed, summary, text)."""
    won = trace["won"]
    steps = trace["steps"]

    if won:
        summary = f"PASS — goal reached in {trace['n_executed']} action(s)."
    elif trace["done"]:
        summary = (
            f"FAIL — episode terminated after {trace['n_executed']} action(s) "
            "without reaching the goal."
        )
    elif trace["n_executed"] >= max_steps:
        summary = f"FAIL — step budget ({max_steps}) exhausted; goal not reached."
    else:
        summary = (
            f"FAIL — action sequence ran out after {trace['n_executed']} "
            "action(s); goal not reached."
        )

    lines = header(
        "ALFWORLD EPISODE VERIFICATION REPORT",
        {
            "Candidate file": output_file,
            "Game file": gamefile,
            "Task": trace["task"],
        },
        won,
        summary,
    )

    inadmissible = [s for s in steps if not s["admissible"]]
    no_ops = [s for s in steps if s["no_op"]]

    if won:
        lines.append(f"All {trace['n_executed']} action(s) executed; goal condition satisfied.")
        if inadmissible:
            lines.append(
                f"Note: {len(inadmissible)} action(s) were not in the admissible "
                "list but the goal was still reached."
            )
        lines.append(RULE)
        return True, summary, "\n".join(lines)

    lines.append("Diagnostics:")
    lines.append(f"  actions proposed : {trace['n_actions']}")
    lines.append(f"  actions executed : {trace['n_executed']}")
    lines.append(f"  inadmissible     : {len(inadmissible)}")
    lines.append(f"  no-op steps      : {len(no_ops)}")

    if inadmissible:
        first = inadmissible[0]
        lines.append("")
        lines.append(f"  First inadmissible action at step {first['step']}:")
        lines.append(f"    Proposed : {first['action']!r}")
        lines.append(f"    Feedback : {first['feedback'].strip()!r}")
        lines.append("    Admissible commands at that step:")
        shown, extra = rank_admissible_commands(
            first["action"], first["admissible_commands"]
        )
        for cmd in shown:
            lines.append(f"      - {cmd}")
        if extra > 0:
            lines.append(
                f"      ... and {extra} more (navigation commands, shown last)"
            )

    if no_ops and not inadmissible:
        first = no_ops[0]
        lines.append("")
        lines.append(f"  First no-op action at step {first['step']}:")
        lines.append(f"    Proposed : {first['action']!r}")
        lines.append(f"    Feedback : {first['feedback'].strip()!r}")

    lines.append("")
    lines.append("  Action trace:")
    for s in steps[:40]:
        flags = []
        if not s["admissible"]:
            flags.append("INADMISSIBLE")
        if s["no_op"]:
            flags.append("NO-OP")
        flag = f"  [{', '.join(flags)}]" if flags else ""
        feedback = s["feedback"].strip().replace("\n", " ")
        if len(feedback) > 100:
            feedback = feedback[:100] + "..."
        lines.append(f"    {s['step']:>3}. {s['action']!r}{flag}")
        lines.append(f"         -> {feedback}")
    if len(steps) > 40:
        lines.append(f"    ... and {len(steps) - 40} more step(s)")

    lines.append(THIN)
    lines.append(RULE)
    return False, summary, "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify an ALFWorld action sequence by replaying it in the game."
    )
    parser.add_argument("--output_file", required=True,
                        help="Candidate JSON with an 'actions' list")
    parser.add_argument("--ground_truth", default=None,
                        help="Path to game.tw-pddl (defaults to 'gamefile' in the candidate)")
    parser.add_argument("--max_steps", type=int, default=50,
                        help="Step budget, matching the eval harness default")
    parser.add_argument("--config", default=str(DEFAULT_CONFIG),
                        help="ALFWorld textworld.yaml")
    args = parser.parse_args()

    actions, embedded_gamefile, error = load_candidate(args.output_file)
    if error:
        print(RULE)
        print("ALFWORLD EPISODE VERIFICATION REPORT")
        print(RULE)
        print("Result:          FAIL")
        print(f"Summary:         {error}")
        print(RULE)
        return 1

    gamefile = args.ground_truth or embedded_gamefile
    if not gamefile:
        print("Result:          FAIL")
        print("Summary:         No game file given (--ground_truth absent and "
              "candidate has no 'gamefile' key).")
        return 1
    if not os.path.isfile(gamefile):
        print("Result:          FAIL")
        print(f"Summary:         Game file does not exist: {gamefile}")
        return 1

    if not actions:
        print("Result:          FAIL")
        print("Summary:         Candidate contains an empty action sequence.")
        return 1

    trace = replay(gamefile, actions, args.max_steps, Path(args.config))
    passed, _, text = build_report(trace, args.output_file, gamefile, args.max_steps)
    print(text)
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
