#!/usr/bin/env python3
"""Run the Trace2Skill skill-generation and ALFWorld evaluation pipeline.

The pipeline follows the method's environment-independent structure:

1. collect train trajectories with a seed skill;
2. build per-episode workspaces;
3. run verified error analysis on failures and optional success analysis;
4. consolidate reusable memories into a Markdown skill;
5. evaluate that skill on valid_seen and valid_unseen.

The command intentionally keeps the actual episode runner in
``run_unified_eval.py`` so all methods share the same protocol and metrics.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
# load_gamefiles lives with the other CLI helpers; the split audit itself is in
# the package so both entry points share one implementation.
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from run_unified_eval import load_gamefiles  # noqa: E402

from alfworld_eval.analysis.dump_artifacts import (  # noqa: E402
    fetch_initial_observation,
    load_results,
    load_trajectory,
    setup_analysis_dir,
)
from alfworld_eval.analysis.verify_episode import DEFAULT_CONFIG, extract_goal  # noqa: E402
from alfworld_eval.env import split_manifest_provenance  # noqa: E402
from alfworld_eval.trace2skill.analyst import (  # noqa: E402
    run_error_analysis,
    run_success_analysis,
)
from alfworld_eval.trace2skill.consolidate import (  # noqa: E402
    consolidate_skill,
    write_skill,
)
from alfworld_eval.trace2skill.llm import client_from_env  # noqa: E402


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--base-url", default=None)
    p.add_argument("--model", default=None)
    p.add_argument("--judge-model", default=None,
                   help="Model used only by the judge verifier; defaults to --model")
    p.add_argument("--api-key", default=None)
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--max-tokens", type=int, default=4096)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--max-steps", type=int, default=None,
                   help="Episode step cap. Omit to follow the environment's "
                        "max_nb_steps_per_episode from --config, which is the "
                        "single source of truth.")
    p.add_argument("--history-length", type=int, default=2)
    p.add_argument("--config", default=str(DEFAULT_CONFIG))
    p.add_argument("--train-items", required=True)
    p.add_argument("--selection-items", default="")
    p.add_argument("--test-items", required=True)
    p.add_argument("--base-skill", default=str(
        PROJECT_ROOT / "src/alfworld_eval/skills_docs/trace2skill_seed_alfworld.md"
    ))
    p.add_argument("--work-dir", default=str(PROJECT_ROOT / "outputs/trace2skill_alfworld"))
    p.add_argument("--train-run-dir", default="",
                   help="Reuse an existing run directory for the train segment "
                        "(e.g. a merged multi-shard output) instead of running it "
                        "here. Implies --skip-train for that directory.")
    p.add_argument("--analyst-mode", choices=["error", "combined"], default="combined")
    p.add_argument("--verifier", choices=["replay", "judge"], default="replay",
                   help="What the analyst's evaluate_output tool consults. "
                        "'replay' (default) executes the corrected sequence in the "
                        "real TextWorld game -- the regression test. 'judge' asks a "
                        "judging agent whether the repair is justified by the "
                        "transcript; the game file is never opened.")
    p.add_argument("--judge-prompt-variant", default="v1",
                   help="Prompt version used by the judge verifier")
    p.add_argument("--max-analyst-turns", type=int, default=20)
    p.add_argument("--analysis-workers", type=int, default=8,
                   help="Concurrent independent workspace analyses (default: 8)")
    p.add_argument("--limit", type=int, default=0,
                   help="Limit train episodes; 0 means all")
    p.add_argument("--skip-train", action="store_true",
                   help="Reuse an existing train run at --train-run-dir")
    p.add_argument("--skip-prepare", action="store_true",
                   help="Reuse existing analysis workspaces (required when the "
                        "analysis stage is sharded: one process prepares, N analyse)")
    p.add_argument("--skip-analysis", action="store_true",
                   help="Reuse existing analysis reports")
    p.add_argument("--skip-consolidate", action="store_true",
                   help="Do not build the skill document (analysis-shard processes set this)")
    p.add_argument("--skip-eval", action="store_true")
    p.add_argument("--full-validation-audit", action="store_true",
                   help="Run the extra baseline-vs-candidate validation audit "
                        "(default: disabled)")
    p.add_argument("--analysis-shards", type=int, default=1,
                   help="Split the analyst stage into N strided shards; each process "
                        "analyses only its own workspaces. Writing the skill document "
                        "stays a single-process step (--skip-consolidate on shards).")
    p.add_argument("--analysis-shard-index", type=int, default=0)
    return p.parse_args()


def _judge_env(args: argparse.Namespace) -> dict[str, str]:
    """Environment for the judge subprocess: which endpoint, which model.

    The judge runs as its own process (it is a tool the analyst calls), so it
    cannot share the analyst's in-memory client. Credentials pass through the
    environment, never a command line.
    """
    env: dict[str, str] = {}
    env["TRACE2SKILL_JUDGE_PROMPT_VARIANT"] = args.judge_prompt_variant
    base_url = args.base_url or os.environ.get("OPENAI_BASE_URL", "")
    if base_url:
        env["TRACE2SKILL_BASE_URL"] = base_url
    model = args.judge_model or args.model or os.environ.get("OPENAI_MODEL", "")
    if model:
        env["TRACE2SKILL_MODEL"] = model
    api_key = args.api_key or os.environ.get("OPENAI_API_KEY", "")
    if api_key:
        env["TRACE2SKILL_API_KEY"] = api_key
    return env


def _run(command: list[str], *, env: dict[str, str]) -> None:
    print("$ " + " ".join(command))
    subprocess.run(command, cwd=str(PROJECT_ROOT), env=env, check=True)


def _eval_command(
    args: argparse.Namespace,
    *,
    split: str,
    out: Path,
    skill_path: Path,
    items: str = "",
    use_full_split: bool = False,
    limit: int = 0,
) -> list[str]:
    command = [
        sys.executable,
        str(PROJECT_ROOT / "scripts/run_unified_eval.py"),
        "--method", "trace2skill",
        "--backend", "api",
        "--base-url", args.base_url or os.environ.get("OPENAI_BASE_URL", ""),
        "--model", args.model or os.environ.get("OPENAI_MODEL", ""),
        "--temperature", str(args.temperature),
        "--max-tokens", str(args.max_tokens),
        "--seed", str(args.seed),
        *(["--max-steps", str(args.max_steps)] if args.max_steps is not None else []),
        "--history-length", str(args.history_length),
        "--split", split,
        "--config", args.config,
        "--skill-path", str(skill_path),
        "--record-trajectory",
        "--out", str(out),
    ]
    if args.api_key or os.environ.get("TRACE2SKILL_API_KEY") or os.environ.get("OPENAI_API_KEY"):
        command += ["--api-key-env", "TRACE2SKILL_API_KEY"]
    if use_full_split:
        command.append("--use-full-split")
    else:
        command += ["--items", items]
        if limit:
            command += ["--limit", str(limit)]
    return command


def _write_full_validation_audit(
    *, args: argparse.Namespace, work_dir: Path, selection_items: str,
    base_skill: Path, candidate_skill: Path, env: dict[str, str], judge_accepted: bool,
) -> None:
    """Run deterministic ALFWorld selection evaluation for both skills."""
    baseline_dir = work_dir / "selection_baseline_run"
    if selection_items:
        baseline_cmd = _eval_command(
            args, split="valid_seen", out=baseline_dir, skill_path=base_skill,
            items=selection_items, limit=args.limit,
        )
    else:
        baseline_cmd = _eval_command(
            args, split="valid_seen", out=baseline_dir, skill_path=base_skill,
            use_full_split=True,
        )
    _run(baseline_cmd, env=env)
    candidate_summary = json.loads((work_dir / "selection_run" / "summary.json").read_text())
    baseline_summary = json.loads((baseline_dir / "summary.json").read_text())
    after = float(candidate_summary.get("summary", {}).get("success_rate", 0.0))
    before = float(baseline_summary.get("summary", {}).get("success_rate", 0.0))
    validation_accepted = after > before
    if judge_accepted and validation_accepted:
        error_type = "correct_accept"
    elif not judge_accepted and not validation_accepted:
        error_type = "correct_reject"
    elif judge_accepted:
        error_type = "false_accept"
    else:
        error_type = "false_reject"
    record = {
        "method": "trace2skill",
        "benchmark": "alfworld",
        "split": "valid_seen",
        "judge_accepted": bool(judge_accepted),
        "validation_accepted": validation_accepted,
        "before_score": before,
        "after_score": after,
        "delta": after - before,
        "error_type": error_type,
        "judge_prompt_variant": args.judge_prompt_variant,
    }
    (work_dir / "judge_full_validation.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def _prepare_workspaces(run_dir: Path, output_dir: Path, config: str) -> list[Path]:
    rows = load_results(run_dir)
    workspaces: list[Path] = []
    for index, row in enumerate(rows):
        trajectory = load_trajectory(run_dir, row, index)
        initial_obs, error = fetch_initial_observation(
            row.get("gamefile", ""), Path(config)
        )
        if error:
            print(f"warning: {row.get('gamefile')}: {error}", file=sys.stderr)
        task = extract_goal(initial_obs) if initial_obs else "(task unavailable)"
        workspaces.append(
            setup_analysis_dir(
                output_dir, row, trajectory, initial_obs, task, index
            )
        )
    return workspaces


def _write_report(workspace: Path, report: str, *, success: bool) -> None:
    name = "success_analysis.md" if success else "analysis_report.md"
    (workspace / name).write_text(report.rstrip() + "\n", encoding="utf-8")


def _write_analysis_summary(
    work_dir: Path, workspaces_dir: Path, records: list[dict[str, Any]]
) -> dict:
    """Aggregate the per-shard analysis reports into one auditable record.

    The verification gate is the method's core claim, so how many episodes
    actually passed it -- and under which turn budget -- belongs with the
    generated skill, not only in the run log.
    """
    shard_paths = sorted(work_dir.glob("analysis_shard_*of*.json"))
    shards = [json.loads(p.read_text(encoding="utf-8")) for p in shard_paths]

    contributing = {str(r.get("instance_id")) for r in records}
    # "Analysed" is read off the artifacts, not the shard counters: a workspace
    # with a report but no evaluate_passed.flag is exactly the case the gate
    # drops, and that list is the honest record of what was discarded.
    analysed = sorted(
        p.name
        for p in (workspaces_dir.iterdir() if workspaces_dir.is_dir() else [])
        if p.is_dir()
        and ((p / "analysis_report.md").is_file() or (p / "success_analysis.md").is_file())
    )
    summary = {
        "analysis_shards": shards[0]["num_shards"] if shards else 1,
        "shard_reports": [p.name for p in shard_paths],
        "workspaces_analysed": len(analysed),
        "workspaces_verified": len(contributing),
        "verified_rate": (
            round(len(contributing) / len(analysed), 4) if analysed else 0.0
        ),
        "discarded_episodes": sorted(set(analysed) - contributing),
        "analyst_mode": shards[0]["analyst_mode"] if shards else "",
        "verifier": shards[0].get("verifier", "replay") if shards else "",
        "max_analyst_turns": shards[0]["max_analyst_turns"] if shards else None,
        "model": shards[0]["model"] if shards else "",
        "episodes_contributing_memory": len(records),
        "memory_items": sum(len(r["items"]) for r in records),
    }
    (work_dir / "analysis_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return summary


def _records_from_workspaces(workspaces: list[Path]) -> list[dict[str, Any]]:
    from alfworld_eval.trace2skill.parser import parse_analysis_file, parse_success_file

    records: list[dict[str, Any]] = []
    for workspace in workspaces:
        report = workspace / "analysis_report.md"
        success_report = workspace / "success_analysis.md"
        if report.is_file() and (workspace / "evaluate_passed.flag").is_file():
            items = parse_analysis_file(report)
        elif success_report.is_file():
            items = parse_success_file(success_report)
        else:
            continue
        if items:
            records.append({"instance_id": workspace.name, "items": items})
    return records


def main() -> int:
    args = parse_args()
    # Stage subprocesses run with ``PROJECT_ROOT`` as cwd. Normalize paths at
    # the boundary so relative manifests work through every stage.
    for name in (
        "config", "train_items", "selection_items", "test_items", "base_skill",
        "work_dir", "train_run_dir",
    ):
        value = getattr(args, name, "")
        if value:
            setattr(args, name, str(Path(value).expanduser().resolve()))
    if not args.base_url and not os.environ.get("OPENAI_BASE_URL"):
        raise SystemExit("--base-url or OPENAI_BASE_URL is required")
    if not args.model and not os.environ.get("OPENAI_MODEL"):
        raise SystemExit("--model or OPENAI_MODEL is required")
    if args.api_key:
        os.environ["TRACE2SKILL_API_KEY"] = args.api_key
    env = dict(os.environ)
    if "TRACE2SKILL_API_KEY" not in env and env.get("OPENAI_API_KEY"):
        env["TRACE2SKILL_API_KEY"] = env["OPENAI_API_KEY"]
    env["ALFWORLD_DATA"] = env.get(
        "ALFWORLD_DATA", str(PROJECT_ROOT / ".data/alfworld")
    )

    work_dir = Path(args.work_dir).resolve()
    train_run = (
        Path(args.train_run_dir).resolve()
        if args.train_run_dir
        else work_dir / "train_run"
    )
    workspaces_dir = work_dir / "analysis_workspaces"
    candidate_skill = work_dir / "trace2skill_alfworld.md"
    work_dir.mkdir(parents=True, exist_ok=True)

    # Record which episodes each stage actually consumed. `--limit` shrinks the
    # induction set (39 -> 15, say) with no other trace, and the selection and
    # test stages then run a subsample, so without this file two runs of
    # different coverage are indistinguishable after the fact.
    provenance = {
        "train_items": args.train_items,
        "selection_items": args.selection_items,
        "test_items": args.test_items,
        "limit": args.limit,
        "base_skill": str(Path(args.base_skill).resolve()),
        "max_steps": args.max_steps,
        "model": args.model,
        "judge_model": args.judge_model or args.model,
        "judge_prompt_variant": args.judge_prompt_variant,
        "train_run_dir": str(train_run),
        "segments": {},
    }

    def _segment(split: str, items_path: str) -> dict:
        if not items_path:
            return {"split": split, "manifest_path": "", "effective_episodes": None}
        items = load_gamefiles(items_path)
        try:
            segment = split_manifest_provenance(items, split)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        segment["manifest_path"] = items_path
        segment["effective_episodes"] = (
            len(items[: args.limit]) if args.limit > 0 else len(items)
        )
        return segment

    provenance["segments"]["train"] = _segment("train", args.train_items)
    provenance["segments"]["selection"] = _segment(
        "valid_seen", args.selection_items
    )
    provenance["segments"]["test"] = _segment("valid_unseen", args.test_items)
    (work_dir / "provenance.json").write_text(
        json.dumps(provenance, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    if not args.skip_train:
        _run(
            _eval_command(
                args,
                split="train",
                out=train_run,
                skill_path=Path(args.base_skill).resolve(),
                items=args.train_items,
                limit=args.limit,
            ),
            env=env,
        )

    # Workspaces are built unless explicitly reused. Preparing and analysing are
    # separate steps because the analysis stage is the one that is sharded: one
    # process prepares (--skip-analysis --skip-consolidate), then N processes
    # analyse disjoint slices with --skip-prepare.
    if args.skip_prepare:
        # Sorted so every analysis shard slices the *same* list.
        workspaces = (
            sorted(p for p in workspaces_dir.iterdir() if p.is_dir())
            if workspaces_dir.is_dir()
            else []
        )
    else:
        workspaces = _prepare_workspaces(train_run, workspaces_dir, args.config)
        print(f"prepared {len(workspaces)} analysis workspace(s) in {workspaces_dir}")

    if not args.skip_analysis:
        shard = workspaces[args.analysis_shard_index :: args.analysis_shards]
        print(
            f"analysis shard {args.analysis_shard_index}/{args.analysis_shards}: "
            f"{len(shard)} of {len(workspaces)} workspace(s)"
        )
        client = client_from_env(
            base_url=args.base_url,
            model=args.model,
            api_key=args.api_key,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
        )
        def _analyse_workspace(workspace: Path):
            try:
                outcome = (workspace / "agent_log.md").read_text(encoding="utf-8")
                is_success = "Outcome: SUCCESS" in outcome
                existing_report = workspace / (
                    "success_analysis.md" if is_success and args.analyst_mode == "combined"
                    else "analysis_report.md"
                )
                if existing_report.is_file():
                    return workspace.name, (workspace / "evaluate_passed.flag").is_file(), 0, 0, ""
                if is_success and args.analyst_mode == "combined":
                    result = run_success_analysis(workspace, client)
                    _write_report(workspace, result.report, success=True)
                elif not is_success:
                    result = run_error_analysis(
                        workspace,
                        client,
                        config=args.config,
                        max_turns=args.max_analyst_turns,
                        verifier=args.verifier,
                        verifier_env=_judge_env(args),
                    )
                    _write_report(workspace, result.report, success=False)
                    if result.error:
                        print(f"warning: analyst {workspace.name}: {result.error}", file=sys.stderr)
                else:
                    return workspace.name, False, 0, 0, ""
                return workspace.name, bool(result.verified), result.turns, len(result.items), ""
            except Exception as exc:  # noqa: BLE001
                warning = f"{type(exc).__name__}: {exc}"
                print(f"warning: analyst {workspace.name}: {warning}", file=sys.stderr)
                return workspace.name, False, 0, 0, warning

        analysis_workers = max(1, int(args.analysis_workers))
        if analysis_workers == 1 or len(shard) <= 1:
            analysed = [_analyse_workspace(workspace) for workspace in shard]
        else:
            with ThreadPoolExecutor(max_workers=analysis_workers) as executor:
                analysed = list(executor.map(_analyse_workspace, shard))
        verified = sum(int(row[1]) for row in analysed)
        verified_episodes = [row[0] for row in analysed if row[1]]
        analysis_errors = {row[0]: row[4] for row in analysed if row[4]}
        for workspace_name, is_verified, turns, item_count, _error in analysed:
            print(f"analysed {workspace_name}: verified={is_verified} "
                  f"turns={turns} items={item_count}")
        print(f"analysis shard {args.analysis_shard_index}/{args.analysis_shards}: "
              f"{verified}/{len(shard)} workspace(s) verified")
        # One file per shard, written by the shard itself. `provenance.json` is
        # rewritten by every invocation, so an analysis-shard count stored there
        # would be silently replaced by the default whenever a later step (e.g.
        # consolidation) ran without the sharding flags -- the artifact would
        # then claim a serial analysis that never happened.
        shard_report = (
            work_dir
            / f"analysis_shard_{args.analysis_shard_index}of{args.analysis_shards}.json"
        )
        shard_report.write_text(
            json.dumps(
                {
                    "shard_index": args.analysis_shard_index,
                    "num_shards": args.analysis_shards,
                    "model": args.model,
                    "analyst_mode": args.analyst_mode,
                    "verifier": args.verifier,
                    "max_analyst_turns": args.max_analyst_turns,
                    "analysis_workers": analysis_workers,
                    "analysis_errors": analysis_errors,
                    "workspaces": len(shard),
                    "verified": verified,
                    "verified_episodes": verified_episodes,
                    "total_workspaces": len(workspaces),
                },
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

    if args.skip_consolidate:
        print("skipping consolidation (--skip-consolidate)")
        return 0

    workspace_paths = (
        sorted(workspaces_dir.iterdir()) if workspaces_dir.is_dir() else []
    )
    records = _records_from_workspaces(workspace_paths)
    analysis = _write_analysis_summary(work_dir, workspaces_dir, records)
    print(
        f"verification gate: {analysis['workspaces_verified']}/"
        f"{analysis['workspaces_analysed']} workspace(s) contributed "
        f"(verified_rate={analysis['verified_rate']}); "
        f"{len(analysis['discarded_episodes'])} discarded"
    )
    base_skill = Path(args.base_skill)
    skill = consolidate_skill(
        base_skill,
        records,
        client=client_from_env(
            base_url=args.base_url,
            model=args.model,
            api_key=args.api_key,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
        ),
    )
    write_skill(candidate_skill, skill)
    print(
        f"Consolidated {sum(len(r['items']) for r in records)} memory item(s) "
        f"into {candidate_skill}"
    )

    if not args.skip_eval:
        if args.selection_items:
            _run(
                _eval_command(
                    args, split="valid_seen", out=work_dir / "selection_run",
                    skill_path=candidate_skill, items=args.selection_items,
                    limit=args.limit,
                ),
                env=env,
            )
        else:
            _run(
                _eval_command(
                    args, split="valid_seen", out=work_dir / "selection_run",
                    skill_path=candidate_skill, use_full_split=True,
                ),
                env=env,
            )
        _run(
            _eval_command(
                args, split="valid_unseen", out=work_dir / "test_run",
                skill_path=candidate_skill, items=args.test_items,
                limit=args.limit,
            ),
            env=env,
        )
        if args.verifier == "judge" and args.full_validation_audit:
            _write_full_validation_audit(
                args=args, work_dir=work_dir, selection_items=args.selection_items,
                base_skill=Path(args.base_skill).resolve(), candidate_skill=candidate_skill,
                env=env, judge_accepted=bool(analysis["workspaces_verified"]),
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
