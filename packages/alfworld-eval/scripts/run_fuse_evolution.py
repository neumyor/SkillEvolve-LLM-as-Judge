#!/usr/bin/env python
"""FUSE skill evolution on ALFWorld: stage-wise CLI.

Adapts the SkillEvolveCPM FUSE cluster-evolution flow to this harness with
family := ALFWorld task type. Every stage is idempotent and resumable; run
them in order, or use `all`:

  # 0. baseline (once, outside this CLI): a train-split run of the parent
  #    skill with --record-trajectory, e.g.
  #    scripts/run_eval_concurrent.py --method skillopt --shards 8 \
  #      --out-base outputs/fuse_baseline_train \
  #      --unified-args "--split train --items .../train/items.json \
  #                      --seed 42 --record-trajectory"
  #
  # 1. export public evidence + manifest
  python scripts/run_fuse_evolution.py export \
      --baseline-run outputs/fuse_baseline_train/merged \
      --parent-skill src/alfworld_eval/skills_docs/skillopt_alfworld.md \
      --out outputs/fuse_run

  # 2-5. sessions (diagnosis for failures, tagging for all, clustering,
  #      per-type authoring)
  python scripts/run_fuse_evolution.py all --out outputs/fuse_run \
      --baseline-run outputs/fuse_baseline_train/merged \
      --parent-skill src/alfworld_eval/skills_docs/skillopt_alfworld.md

  # 6-7. validation (N attempts per family member) + acceptance
  python scripts/run_fuse_evolution.py validate --out outputs/fuse_run ...
  python scripts/run_fuse_evolution.py accept --out outputs/fuse_run

  # 8. stage the routed publish set (accepted candidates, parent fallback)
  python scripts/run_fuse_evolution.py stage --out outputs/fuse_run

The eval/val/test comparison runs are ordinary run_eval_concurrent.py calls
with --method fuse --skill-dir <out>/staged_skills (see the FUSE runbook).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from alfworld_eval.fuse.evolution import (  # noqa: E402
    FuseEvolution,
    FuseEvolutionConfig,
)
from alfworld_eval.unified.skills import TASKS  # noqa: E402


def _load_llm_config(section: str = "alfworld-eval") -> dict:
    path = PROJECT_ROOT.parents[1] / "benchmark/llm_config.local.json"
    if not path.is_file():
        path = PROJECT_ROOT.parents[1] / "benchmark/llm_config.example.json"
    config = json.loads(path.read_text(encoding="utf-8"))
    if section not in config:
        raise SystemExit(f"section {section!r} missing in {path}")
    return config[section]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("stage", choices=[
        "export", "diagnose", "tag", "cluster", "author",
        "validate", "accept", "stage", "all", "status",
    ])
    p.add_argument("--baseline-run", default="",
                   help="merged/ directory of the train baseline run "
                        "(required for 'export' and stages that reload the manifest)")
    p.add_argument("--parent-skill", default="",
                   help="path of the parent (baseline) skill document")
    p.add_argument("--out", default="", help="evolution output root")
    p.add_argument("--llm-config-section", default="alfworld-eval",
                   help="section of benchmark/llm_config.local.json for the session model")
    p.add_argument("--attempts", type=int, default=3,
                   help="validation attempts per episode (majority gate)")
    p.add_argument("--shards", type=int, default=8,
                   help="shard processes for validation runs")
    p.add_argument("--max-skill-chars", type=int, default=16000)
    p.add_argument("--types", default="",
                   help="comma-separated task types to process (author/validate/accept)")
    p.add_argument("--limit", type=int, default=0,
                   help="diagnose/tag only the first N incidents (smoke)")
    p.add_argument("--parent-skill-dir", default="",
                   help="per-task-type parent skills directory (staged_skills "
                        "layout) for later rounds; overrides --parent-skill "
                        "for authoring")
    p.add_argument("--extra-diagnoses", default="",
                   help="comma-separated incident ids to diagnose even though "
                        "their baseline outcome is success (later-round "
                        "regressions)")
    p.add_argument("--validation-summary", default="",
                   help="JSON file {incident_id: {passed, regression, ...}} "
                        "from a previous round, injected into authoring evidence")
    p.add_argument("--baseline-outcomes", default="",
                   help="JSON file {incident_id: {success: bool}} overriding the "
                        "acceptance baseline (previous round's published system)")
    args = p.parse_args()

    if not args.out:
        raise SystemExit("--out is required")
    if args.stage in ("export", "all") and not (args.baseline_run and args.parent_skill):
        raise SystemExit(
            f"'{args.stage}' needs --baseline-run and --parent-skill"
        )
    return args


def main() -> int:
    args = parse_args()
    llm = _load_llm_config(args.llm_config_section)

    # Persistent context: once the manifest exists, the fixed inputs can be
    # recovered from it, but the baseline/parent must still be provided for
    # stages that read them; require them whenever given, else reuse saved.
    context_path = Path(args.out) / "context.json"
    context: dict = {}
    if context_path.is_file():
        context = json.loads(context_path.read_text(encoding="utf-8"))
    baseline_run = args.baseline_run or context.get("baseline_run", "")
    parent_skill = args.parent_skill or context.get("parent_skill", "")
    if not baseline_run or not parent_skill:
        if args.stage in ("export", "all", "diagnose", "validate"):
            raise SystemExit(
                "this stage needs --baseline-run and --parent-skill (or a "
                "previous run's context.json)"
            )

    validation_summary = None
    if args.validation_summary:
        validation_summary = json.loads(
            Path(args.validation_summary).read_text(encoding="utf-8")
        )
    baseline_override = None
    if args.baseline_outcomes:
        baseline_override = json.loads(
            Path(args.baseline_outcomes).read_text(encoding="utf-8")
        )

    config = FuseEvolutionConfig(
        baseline_run_dir=Path(baseline_run) if baseline_run else Path("/nonexistent"),
        parent_skill=Path(parent_skill) if parent_skill else Path("/nonexistent"),
        out_dir=Path(args.out),
        project_root=PROJECT_ROOT,
        base_url=llm["base_url"],
        model=llm["model"],
        api_key=llm.get("api_key", ""),
        attempts=args.attempts,
        shards=args.shards,
        max_skill_chars=args.max_skill_chars,
        parent_skills_dir=(
            Path(args.parent_skill_dir) if args.parent_skill_dir else None
        ),
        extra_diagnoses=tuple(
            i.strip() for i in args.extra_diagnoses.split(",") if i.strip()
        ),
        validation_summary=validation_summary,
        baseline_outcomes_override=baseline_override,
    )
    if baseline_run and parent_skill:
        context = {
            "baseline_run": str(Path(baseline_run).resolve()),
            "parent_skill": str(Path(parent_skill).resolve()),
            "model": llm["model"],
            "base_url": llm["base_url"],
            "attempts": args.attempts,
        }
        context_path.parent.mkdir(parents=True, exist_ok=True)
        context_path.write_text(
            json.dumps(context, indent=2) + "\n", encoding="utf-8"
        )

    evo = FuseEvolution(config)
    only_types = tuple(
        t.strip() for t in args.types.split(",") if t.strip()
    )
    unknown = [t for t in only_types if t not in TASKS]
    if unknown:
        raise SystemExit(f"unknown task types {unknown}; choose from {list(TASKS)}")

    if args.stage == "status":
        print(json.dumps(evo.status(), indent=2))
        return 0
    if args.stage == "export" or args.stage == "all":
        evo.stage_export()
        if args.stage == "export":
            return 0
    if args.stage == "diagnose" or args.stage == "all":
        evo.stage_diagnose(limit=args.limit)
    if args.stage == "tag" or args.stage == "all":
        evo.stage_tag(limit=args.limit)
    if args.stage == "cluster" or args.stage == "all":
        evo.stage_cluster()
    if args.stage == "author" or args.stage == "all":
        evo.stage_author(only_types=only_types)
    if args.stage == "validate":
        evo.stage_validate(only_types=only_types)
    if args.stage == "accept":
        evo.stage_accept(only_types=only_types)
    if args.stage == "stage":
        evo.stage_stage()
    if args.stage == "all":
        evo.stage_validate(only_types=only_types)
        evo.stage_accept(only_types=only_types)
        evo.stage_stage()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
