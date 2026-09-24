#!/usr/bin/env python3
"""Unified launcher for the four JudgeGate-enabled methods.

Examples:
  python scripts/run_method.py --method skillopt --mode judge --config packages/skillopt/configs/searchqa/judge_gate.yaml
  python scripts/run_method.py --method skillgen --benchmark searchqa --mode judge --skillgen-config packages/skillgen/config.yaml
  python scripts/run_method.py --method gepa --benchmark searchqa --mode judge --config configs/gepa/searchqa.json

Arguments after ``--`` are passed to the selected method runner.  Every method
uses the same mode and prompt-version switches. Judge mode rejects per-candidate
full-validation audit; final validation/test measures the frozen output.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages"))
from rethinkskill_study.local_config import benchmark_root  # noqa: E402


def _python_for(args: argparse.Namespace) -> str:
    """Choose the environment that owns the selected benchmark runtime."""
    if args.benchmark == "alfworld":
        if args.method == "rethinkskill":
            candidate = benchmark_root() / ".venv/bin/python"
            if not candidate.is_file():
                raise SystemExit(f"Required benchmark Python is missing: {candidate}")
        elif args.method == "skillopt":
            # SkillOpt's ALFWorld adapter imports OmegaConf in addition to
            # alfworld/textworld; those dependencies live in its dedicated
            # environment. The benchmark venv is used by the other methods.
            candidate = ROOT / "packages/skillopt/.venv-alfworld/bin/python"
        else:
            candidate = ROOT / "packages/alfworld-eval/.venv/bin/python"
    else:
        # SkillOpt, GEPA, and the SearchQA/SkillGen API clients share the
        # SkillOpt environment; it contains the OpenAI-compatible client.
        candidate = ROOT / "packages/skillopt/.venv/bin/python"
    return str(candidate) if candidate.is_file() else sys.executable


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--method", required=True,
                        choices=["skillopt", "gepa", "skillgen", "rethinkskill"])
    parser.add_argument("--benchmark", choices=["searchqa", "alfworld"],
                        help="Benchmark name recorded by the method runner")
    parser.add_argument("--config", default=None,
                        help="Method config (SkillOpt YAML, GEPA JSON, or SkillGen dataset JSON)")
    parser.add_argument("--skillgen-config", default=None,
                        help="SkillGen YAML config; --config remains the dataset JSON")
    parser.add_argument("--mode", choices=["baseline", "judge"], default="judge",
                        help="baseline keeps the method's original regression gate; "
                        "judge replaces that acceptance decision")
    parser.add_argument("--judge-prompt-variant", default="v3",
                        help="Named JudgeGate prompt version (default: v3)")
    parser.add_argument("--judge-model", default=None,
                        help="Judge model passed through to method-specific backends")
    parser.add_argument("--model", default=None,
                        help="Inference/reflection model used by the selected method")
    parser.add_argument("--base-url", default=None,
                        help="OpenAI-compatible endpoint override")
    parser.add_argument("--api-key", default=None,
                        help="Endpoint key override (prefer environment/config)")
    parser.add_argument("--output-dir", default=None,
                        help="Per-condition output directory where supported")
    parser.add_argument("--run-root", default=None,
                        help="Per-condition checkpoint root for SkillGen")
    parser.add_argument("--full-validation-audit", action="store_true",
                        help="Legacy flag: rejected in judge mode; final evaluation is separate")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("method_args", nargs=argparse.REMAINDER,
                        help="Arguments for the selected method after --")
    return parser


def _strip_separator(args: list[str]) -> list[str]:
    return args[1:] if args[:1] == ["--"] else args


def build_command(args: argparse.Namespace) -> tuple[list[str], dict[str, str]]:
    if args.mode == "judge" and args.full_validation_audit:
        raise ValueError("Judge mode forbids candidate full-validation audit; final evaluation remains available")
    extra = _strip_separator(list(args.method_args))
    env = dict(os.environ)
    env["JUDGE_GATE_PROMPT_VARIANT"] = args.judge_prompt_variant
    if args.judge_model:
        env["JUDGE_GATE_MODEL"] = args.judge_model
    if args.model:
        env["OPENAI_MODEL"] = args.model
        env["QWEN_CHAT_MODEL"] = args.model
        env["OPTIMIZER_QWEN_CHAT_MODEL"] = args.model
        env["TARGET_QWEN_CHAT_MODEL"] = args.model
    if args.base_url:
        env["OPENAI_BASE_URL"] = args.base_url
        env["QWEN_CHAT_BASE_URL"] = args.base_url
        env["OPTIMIZER_QWEN_CHAT_BASE_URL"] = args.base_url
        env["TARGET_QWEN_CHAT_BASE_URL"] = args.base_url
    if args.api_key:
        env["OPENAI_API_KEY"] = args.api_key
        env["QWEN_CHAT_API_KEY"] = args.api_key
        env["OPTIMIZER_QWEN_CHAT_API_KEY"] = args.api_key
        env["TARGET_QWEN_CHAT_API_KEY"] = args.api_key
    if args.benchmark == "alfworld":
        if args.method == "rethinkskill":
            root = benchmark_root()
            env["ALFWORLD_BENCHMARK_ROOT"] = str(root)
            env["ALFWORLD_DATA"] = str(root / ".data/alfworld")
            env["ALFWORLD_CONFIG"] = str(root / "configs/rethinkskill_official.yaml")
            env["ALFWORLD_BENCH_SRC"] = str(root / "src")
        else:
            env.setdefault("ALFWORLD_DATA", str(ROOT / "packages/alfworld-eval/.data/alfworld"))
            env.setdefault("ALFWORLD_CONFIG", str(ROOT / "packages/alfworld-eval/configs/textworld.yaml"))
            env.setdefault("ALFWORLD_BENCH_SRC", str(ROOT / "packages/alfworld-eval/src"))
    python = _python_for(args)
    if args.method == "skillopt":
        if not args.config:
            raise SystemExit("skillopt requires --config")
        # SkillOpt resolves ``split_dir`` relative to its package checkout,
        # while the unified launcher runs from the repository root. Pin the
        # benchmark manifest root here so direct commands and campaign
        # commands have identical data selection.
        skillopt_extra = list(extra)
        if args.benchmark in {"searchqa", "alfworld"} and "--split_dir" not in skillopt_extra:
            skillopt_extra += [
                "--split_dir", str(ROOT / "packages/skillopt/data" / (
                    "searchqa_split" if args.benchmark == "searchqa" else "alfworld_path_split"
                )),
            ]
        command = [python, str(ROOT / "packages/skillopt/scripts/train.py"),
                   "--config", args.config,
                   "--gate_mode", "judge" if args.mode == "judge" else "rollout",
                   "--judge_prompt_variant", args.judge_prompt_variant,
                   "--judge_full_validation_audit", str(args.full_validation_audit).lower(),
                   *( ["--cfg-options", "model.backend=qwen_chat",
                       "model.optimizer_backend=qwen_chat",
                       "model.target_backend=qwen_chat"]
                      if (args.model or args.base_url) and "--cfg-options" not in skillopt_extra
                      else [] ),
                   *( ["--optimizer_model", args.model, "--target_model", args.model]
                      if args.model else [] ),
                   *( ["--qwen_chat_base_url", args.base_url,
                       "--optimizer_qwen_chat_base_url", args.base_url,
                       "--target_qwen_chat_base_url", args.base_url]
                      if args.base_url else [] ),
                   *( ["--qwen_chat_temperature", "0",
                       "--qwen_chat_thinking_mode", "disabled",
                       "--optimizer_qwen_chat_thinking_mode", "disabled",
                       "--target_qwen_chat_thinking_mode", "disabled"]
                      if args.model or args.base_url else [] ),
                   *( ["--judge_model", args.judge_model] if args.judge_model else [] ),
                   *(["--out_root", args.output_dir] if args.output_dir else []),
                   *skillopt_extra]
    elif args.method == "gepa":
        if not args.config:
            raise SystemExit("gepa requires --config JSON")
        command = [python, str(ROOT / "packages/gepa/run.py"),
                   "--config", args.config,
                   *( ["--benchmark", args.benchmark] if args.benchmark else [] ),
                   "--mode", args.mode,
                   "--judge-prompt-variant", args.judge_prompt_variant,
                   *( ["--judge-model", args.judge_model] if args.judge_model else [] ),
                   *( ["--model", args.model] if args.model else [] ),
                   *( ["--base-url", args.base_url] if args.base_url else [] ),
                   *( ["--output-dir", args.output_dir] if args.output_dir else [] ),
                   *(["--full-validation-audit"] if args.full_validation_audit else []),
                   *extra]
    elif args.method == "rethinkskill":
        if not args.benchmark:
            raise SystemExit("rethinkskill requires --benchmark")
        data_root = ROOT / "packages/skillopt/data" / ("searchqa_split" if args.benchmark == "searchqa" else "alfworld_path_split")
        seed = ROOT / "packages/skillopt/skillopt/envs" / args.benchmark / "skills/initial.md"
        command = [python, str(ROOT / "packages/rethinkskill_runner.py"),
                   "--benchmark", args.benchmark, "--mode", args.mode,
                   "--model", args.model or os.environ.get("OPENAI_MODEL", ""),
                   "--judge-model", args.judge_model or args.model or os.environ.get("OPENAI_MODEL", ""),
                   "--base-url", args.base_url or os.environ.get("OPENAI_BASE_URL", ""),
                   "--output-dir", args.output_dir or str(ROOT / "outputs/rethinkskill"),
                   "--judge-prompt-variant", args.judge_prompt_variant]
        # Campaigns pass their frozen split and run controls after the separator;
        # do not duplicate them with repository-default paths.
        flags = {value.split("=", 1)[0] for value in extra if value.startswith("--")}
        if "--train-items" not in flags: command += ["--train-items", str(data_root / "train/items.json")]
        if "--val-items" not in flags: command += ["--val-items", str(data_root / "val/items.json")]
        if "--test-items" not in flags: command += ["--test-items", str(data_root / "test/items.json")]
        if "--seed-skill" not in flags: command += ["--seed-skill", str(seed)]
        if "--workers" not in flags: command += ["--workers", "64"]
        if "--alfworld-config" not in flags and args.benchmark == "alfworld": command += ["--alfworld-config", str(benchmark_root() / "configs/rethinkskill_official.yaml")]
        if "--max-steps" not in flags and args.benchmark == "alfworld": command += ["--max-steps", "50"]
        command += extra
    else:
        if not args.config and not args.benchmark:
            raise SystemExit("skillgen requires --config dataset JSON or --benchmark")
        command = [python, str(ROOT / "packages/skillgen/main.py"),
                   *( [args.config] if args.config else [] ),
                   *( ["--benchmark", args.benchmark] if args.benchmark else [] ),
                   "--mode", args.mode,
                   *( ["--model", args.model] if args.model else [] ),
                   *( ["--base-url", args.base_url] if args.base_url else [] ),
                   *( ["--judge-model", args.judge_model] if args.judge_model else [] ),
                   *( ["--judge-prompt-variant", args.judge_prompt_variant]
                      if args.mode == "judge" else [] ),
                   *( ["--output-dir", args.output_dir] if args.output_dir else [] ),
                   *( ["--run-root", args.run_root] if args.run_root else [] ),
                   *(["--full-validation-audit"] if args.full_validation_audit else []),
                   *([] if not args.skillgen_config else ["--config", args.skillgen_config]),
                   *extra]
    return command, env


def main() -> int:
    args = _parser().parse_args()
    command, env = build_command(args)
    env["PYTHONPATH"] = os.pathsep.join(
        str(path) for path in (
            ROOT / "packages/skillopt",
            ROOT / "packages/gepa/src",
            ROOT / "packages/gepa",
            ROOT / "packages/skillgen",
            ROOT / "packages/searchqa-eval/src",
            benchmark_root() / "src" if args.method == "rethinkskill" and args.benchmark == "alfworld" else ROOT / "packages/alfworld-eval/src",
            Path(env.get("PYTHONPATH", "")) if env.get("PYTHONPATH") else None,
        ) if path is not None
    )
    secret_flags = {"--api-key", "--qwen_chat_api_key", "--optimizer_qwen_chat_api_key",
                    "--target_qwen_chat_api_key"}
    display = []
    hide_next = False
    for arg in command:
        if hide_next:
            display.append("<redacted>")
            hide_next = False
        elif arg in secret_flags:
            display.append(arg)
            hide_next = True
        elif any(arg.startswith(flag + "=") for flag in secret_flags):
            display.append(arg.split("=", 1)[0] + "=<redacted>")
        else:
            display.append(arg)
    print("[judgegate]", " ".join(display))
    if args.dry_run:
        return 0
    completed = subprocess.run(command, cwd=str(ROOT), env=env)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
