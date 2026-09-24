"""Entry point: load a dataset and run the skill discovery pipeline."""

from __future__ import annotations
import argparse, json
import os
from pathlib import Path
from models import TaskInstance, TaskDataset, TaskType
from benchmarks.judgegate_benchmark import load_benchmark_dataset
from artifacts import write_json, write_trajectories
from trajectory import AgentConfig, collect_trajectories
import llm
from logging_utils import configure_logging
from pipeline import run_pipeline


def load_dataset(path: str | None) -> TaskDataset:
    """Load a JSON dataset. Expected format:
    {
      "dataset_id": "...",
      "task_name": "...",
      "task_type": "binary" | "scored" | "open_ended",
      "instances": [
        {"instance_id": "...", "input": "...", "ground_truth": "..."},
        ...
      ]
    }
    """
    if not path:
        raise ValueError("dataset path is required when --benchmark is not set")
    with open(path) as f:
        data = json.load(f)
    instances = [
        TaskInstance(
            instance_id=d["instance_id"],
            input=d["input"],
            ground_truth=d.get("ground_truth"),
            metadata=d.get("metadata", {}),
        )
        for d in data["instances"]
    ]
    return TaskDataset(
        dataset_id=data.get("dataset_id", "default"),
        task_name=data.get("task_name", "unnamed"),
        task_type=TaskType(data["task_type"]),
        instances=instances,
        metadata=data.get("metadata", {}),
    )


def main():
    parser = argparse.ArgumentParser(description="Failure-driven skill discovery")
    parser.add_argument("dataset", nargs="?", help="Path to dataset JSON file")
    parser.add_argument("--config", default="config.yaml", help="Config file path")
    parser.add_argument(
        "--generate-scripts",
        action="store_true",
        default=None,
        help=(
            "Ask the generation agent to produce callable Python helper functions "
            "alongside each skill. Each skill with scripts gets a companion "
            "<skill_id>_helpers.py file in the skill repo. "
            "Overrides generation.generate_scripts in config.yaml."
        ),
    )
    parser.add_argument(
        "--resume",
        metavar="RUN_DIR",
        default=None,
        help=(
            "Resume a crashed run from its artifact directory "
            "(e.g. ./artifacts/runs/20260415-103000). "
            "Re-uses the saved baseline trajectories and (if present) the saved "
            "induction analysis so you don't have to repeat the expensive early stages."
        ),
    )
    parser.add_argument("--verbose-http", action="store_true",
                        help="Show raw HTTP request logs from SDK clients")
    parser.add_argument("--judge", action="store_true",
                        help="Use the shared LLM JudgeGate for verification acceptance")
    parser.add_argument("--mode", choices=["baseline", "judge"], default=None,
                        help="Explicitly select the original net-gain gate or JudgeGate")
    parser.add_argument("--benchmark", choices=["searchqa", "alfworld"], default=None,
                        help="Benchmark label stored in run metadata")
    parser.add_argument("--benchmark-split", default="train",
                        help="Manifest split used when dataset is omitted")
    parser.add_argument("--benchmark-items", default=None,
                        help="Override the benchmark manifest path")
    parser.add_argument("--validation-items", default=None,
                        help="Validation manifest for the final evaluation")
    parser.add_argument("--test-items", default=None,
                        help="Test manifest for the final evaluation")
    parser.add_argument("--output-dir", default=None,
                        help="Directory for final validation/test evaluation artifacts")
    parser.add_argument("--run-root", default=None,
                        help="Per-condition root for SkillGen checkpoints and skills")
    parser.add_argument("--model", default=None,
                        help="Inference model override for all SkillGen stages")
    parser.add_argument("--judge-model", default=None,
                        help="Judge/evaluator model override")
    parser.add_argument("--base-url", default=None,
                        help="OpenAI-compatible endpoint for SkillGen")
    parser.add_argument("--api-key", default=None,
                        help="Endpoint key (prefer SKILLGEN_API_KEY or OPENAI_API_KEY)")
    parser.add_argument("--alfworld-config", default=None,
                        help="ALFWorld environment config for benchmark runs")
    parser.add_argument("--judge-prompt-variant", default=None,
                        help="Judge prompt version: v3 (default), v1 or v2")
    parser.add_argument("--full-validation-audit", action="store_true",
                        help="Legacy flag: rejected in judge mode")
    args = parser.parse_args()

    # ``local-hashing`` is the declared no-extra-service embedding backend for
    # the qwen endpoint. Make the runtime switch explicit from the config so a
    # smoke or campaign cannot accidentally call an unavailable embeddings API.
    with open(args.config) as f:
        import yaml
        initial_cfg = yaml.safe_load(f) or {}
    if (initial_cfg.get("embedding") or {}).get("model") == "local-hashing":
        os.environ["SKILLGEN_LOCAL_EMBEDDINGS"] = "1"

    # Keep the benchmark run pinned to the requested endpoint/model without
    # rewriting the checked-in YAML. All model slots are updated together so
    # baseline, generation, verification and final evaluation are comparable.
    cfg_data = None
    if args.model or args.judge_model or args.base_url or args.api_key:
        with open(args.config) as f:
            import yaml
            cfg_data = yaml.safe_load(f) or {}
        if args.model:
            cfg_data.setdefault("models", {})
            for key in (
                "default", "baseline_agent", "induction", "induction_contextual",
                "induction_summary", "induction_pattern", "induction_contrastive",
                "generation_plan", "generation_execute", "refinement",
                "verification_agent", "verification_case_analyst",
                "verification_revision_synthesiser",
            ):
                cfg_data["models"][key] = args.model
        if args.judge_model:
            cfg_data.setdefault("models", {})
            for key in ("baseline_judge", "verification_judge"):
                cfg_data["models"][key] = args.judge_model
        if args.run_root:
            run_root = Path(args.run_root).expanduser().resolve()
            cfg_data.setdefault("pipeline", {})["artifact_root"] = str(run_root / "runs")
            cfg_data.setdefault("skill_output", {})["path"] = str(run_root / "skills")
        temporary_config = Path(args.output_dir or ".") / ".skillgen_runtime_config.yaml"
        temporary_config.parent.mkdir(parents=True, exist_ok=True)
        with temporary_config.open("w", encoding="utf-8") as f:
            yaml.safe_dump(cfg_data, f, sort_keys=False)
        args.config = str(temporary_config)
    if args.base_url:
        os.environ["SKILLGEN_BASE_URL"] = args.base_url
    if args.api_key:
        os.environ["SKILLGEN_API_KEY"] = args.api_key

    log = configure_logging(verbose_http=args.verbose_http)
    dataset = (
        load_benchmark_dataset(args.benchmark, split=args.benchmark_split,
                               items_path=args.benchmark_items)
        if args.benchmark and not args.dataset
        else load_dataset(args.dataset)
    )
    if args.benchmark:
        dataset.metadata = {**dataset.metadata, "benchmark": args.benchmark}
    if args.benchmark == "alfworld" and args.alfworld_config:
        for instance in dataset.instances:
            instance.metadata["env_config"] = str(Path(args.alfworld_config).resolve())
    log.info(
        "Loaded dataset '%s' with %d instances (%s)",
        dataset.task_name,
        len(dataset.instances),
        dataset.task_type.value,
    )

    judge_enabled = args.mode == "judge" if args.mode else args.judge
    judge_model = args.judge_model or initial_cfg.get("models", {}).get(
        "baseline_judge", "qwen3.7-plus"
    )

    def _judge_chat_fn(*, system, user, max_completion_tokens, retries, stage):
        # Reuse SkillGen's OpenAI-compatible client, which carries the qwen
        # endpoint and retry policy configured for this run. JudgeGate only
        # needs text plus optional usage metadata.
        before = {key: sum(row[key] for row in llm.get_token_stats())
                  for key in ("prompt_tokens", "completion_tokens", "total_tokens")}
        response = llm.chat(
            user,
            system=system,
            model=str(judge_model),
            temperature=0.0,
            max_tokens=int(max_completion_tokens),
            **({"enable_thinking": False} if "qwen" in str(judge_model).lower() else {}),
        )
        usage = {key: sum(row[key] for row in llm.get_token_stats()) - value
                 for key, value in before.items()}
        return str(response or ""), {**usage, "model": str(judge_model), "stage": stage}

    skill = run_pipeline(
        dataset.instances,
        dataset.task_type,
        config_path=args.config,
        dataset_id=dataset.dataset_id,
        task_name=dataset.task_name,
        dataset_metadata=dataset.metadata,
        generate_scripts=args.generate_scripts,
        resume_dir=args.resume,
        judge_overrides=(
            {
                "enabled": True,
                **({"prompt_variant": args.judge_prompt_variant}
                   if args.judge_prompt_variant else {}),
                "full_validation": args.full_validation_audit,
            }
            if judge_enabled else ({"enabled": False} if args.mode == "baseline" else None)
        ),
        judge_chat_fn=_judge_chat_fn if judge_enabled else None,
    )
    if skill is None:
        log.info("Done. No skill was produced (no failures to learn from).")
    else:
        log.info("Done. Generated skill id=%s", skill.skill_id)
    if args.validation_items or args.test_items:
        _run_final_evaluations(args, dataset, skill)
    llm.dump_token_stats(Path(args.output_dir or "./artifacts/final_eval") / "token_usage.json")


def _run_final_evaluations(args, train_dataset: TaskDataset, skill) -> None:
    """Score the produced skill once on validation/test; never a gate audit."""
    import yaml
    from models import SkillStatus

    if skill is not None and skill.status != SkillStatus.ACTIVE:
        skill = None

    out = Path(args.output_dir or "./artifacts/final_eval")
    out.mkdir(parents=True, exist_ok=True)
    with open(args.config) as f:
        cfg = yaml.safe_load(f) or {}
    models = cfg.get("models", {})
    model = str(models.get("default") or models.get("baseline_agent") or "")
    judge_model = str(models.get("baseline_judge") or model)
    common = dict(
        model=model,
        judge_model=judge_model,
        temperature=float((cfg.get("llm") or {}).get("temperature", 0.0)),
        alfworld_backend="api",
        alfworld_base_url=os.environ.get("SKILLGEN_BASE_URL", os.environ.get("OPENAI_BASE_URL", "")),
        alfworld_api_key=os.environ.get("SKILLGEN_API_KEY", os.environ.get("OPENAI_API_KEY", "")),
        alfworld_config=args.alfworld_config or "",
    )
    for label, manifest in (("validation", args.validation_items), ("test", args.test_items)):
        if not manifest:
            continue
        benchmark = str((train_dataset.metadata or {}).get("benchmark") or args.benchmark)
        if benchmark == "searchqa":
            split = "val" if label == "validation" else "test"
        else:
            split = "valid_seen" if label == "validation" else "valid_unseen"
        eval_dataset = load_benchmark_dataset(benchmark, split=split, items_path=manifest)
        with llm.stage_scope(f"final_{label}"):
            baseline = collect_trajectories(
                eval_dataset.instances, eval_dataset.task_type,
                config=AgentConfig(**common), max_workers=int((cfg.get("pipeline") or {}).get("max_workers", 16)),
                progress_desc=f"Final {label} baseline",
                checkpoint_dir=str(out / f"{label}_baseline_units"),
            )
            augmented = baseline if skill is None else collect_trajectories(
                eval_dataset.instances, eval_dataset.task_type,
                skill=skill, config=AgentConfig(**common),
                max_workers=int((cfg.get("pipeline") or {}).get("max_workers", 16)),
                progress_desc=f"Final {label} skill",
                checkpoint_dir=str(out / f"{label}_skill_units"),
            )
        write_trajectories(out / f"{label}_baseline.jsonl", baseline)
        write_trajectories(out / f"{label}_skill.jsonl", augmented)
        before = sum(float(bool(t.success)) for t in baseline) / max(len(baseline), 1)
        after = sum(float(bool(t.success)) for t in augmented) / max(len(augmented), 1)
        write_json(out / f"{label}_summary.json", {
            "benchmark": benchmark,
            "split": split,
            "items": len(eval_dataset.instances),
            "baseline_success_rate": before,
            "skill_success_rate": after,
            "delta": after - before,
            "model": model,
            # This is a final measurement, not the optional per-decision
            # audit. Record the switch so explicitly enabled audit runs are
            # distinguishable without changing the final-eval semantics.
            "full_validation_audit": bool(args.full_validation_audit),
        })


if __name__ == "__main__":
    main()
