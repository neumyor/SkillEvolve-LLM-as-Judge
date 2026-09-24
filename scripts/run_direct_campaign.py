#!/usr/bin/env python3
"""Reproducible, detached baseline/Judge experiment supervisor.

Prepare -> real health check -> smoke -> inspect audits -> full. A failed
condition blocks promotion. Credentials are read only by the child environment.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
METHODS = ("skillopt", "gepa", "skillgen", "rethinkskill")
BENCHMARKS = ("searchqa", "alfworld")
MODES = ("baseline", "judge")
PYTHON = ROOT / "packages/skillopt/.venv/bin/python"


def read(path):
    return json.loads(Path(path).read_text())


def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    temp.replace(path)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_digest():
    paths = []
    for directory in (ROOT / "packages", ROOT / "scripts"):
        for parent, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("__pycache__", "site-packages")]
            paths.extend(Path(parent) / f for f in files if f.endswith(".py"))
    return hashlib.sha256("\n".join(f"{p.relative_to(ROOT)}:{digest(p)}"
                                  for p in sorted(paths)).encode()).hexdigest()


def environment(benchmark, manifest):
    config = read(ROOT / "benchmark/llm_config.local.json")
    section = config.get(f"{benchmark}-eval", config.get("default", {}))
    key = section.get("api_key") or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise ValueError("Missing endpoint credentials")
    env = dict(os.environ)
    for prefix in ("OPENAI", "QWEN_CHAT", "OPTIMIZER_QWEN_CHAT", "TARGET_QWEN_CHAT", "SKILLGEN"):
        env.update({f"{prefix}_API_KEY": key, f"{prefix}_BASE_URL": manifest["base_url"],
                    f"{prefix}_MODEL": manifest["model"]})
    env.update({"PYTHONUNBUFFERED": "1", "GEPA_FINAL_EVAL_CHUNK_SIZE": "100",
                "TOKENIZERS_PARALLELISM": "false", "OMP_NUM_THREADS": "1",
                "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"})
    return env


def prepare(root, model, base_url, selected_methods=None):
    import yaml
    manifest_path = root / "manifest.json"
    if manifest_path.exists():
        raise ValueError("Campaign already prepared; use --resume with the existing manifest")
    methods = tuple(selected_methods or METHODS)
    if not methods or any(method not in METHODS for method in methods):
        raise ValueError(f"Unsupported methods: {methods}")
    manifest = {
        "methods": list(methods),
        "protocol": "direct_replacement_v3", "model": model, "base_url": base_url,
        "judge_prompt_variant": "v3", "full_validation_audit": False,
        "max_concurrency_per_setting": 100, "seed": 42,
        "metrics": {"performance": "frozen output test exact-match / task success rate",
                    "tokens": "LLM Judge vs replaced baseline re-executions only",
                    "saved_tokens": "baseline replacement tokens - judge replacement tokens",
                    "saving_fraction": "saved_tokens / baseline; null for incomplete usage or zero denominator"},
        "control": "Within each method: identical data, model, generation settings and stopping rules; only gate changes. Actual rounds may differ.",
        "smoke": "Two training units that exercise failure-driven proposals; first two val/test units; one proposal/refinement round. Not performance estimates.",
        "smoke_train_indices": {"searchqa": [94, 312], "alfworld": [35, 38]},
        "splits": {}, "settings": {}, "created_at": time.time(),
    }
    for bench in BENCHMARKS:
        data = ROOT / "packages/skillopt/data" / ("searchqa_split" if bench == "searchqa" else "alfworld_path_split")
        manifest["splits"][bench] = {}
        for split in ("train", "val", "test"):
            path = data / split / "items.json"
            rows = read(path)
            manifest["splits"][bench][split] = {"path": str(path), "count": len(rows), "sha256": digest(path)}
            indices = manifest["smoke_train_indices"][bench] if split == "train" else [0, 1]
            write(root / "smoke_data" / bench / split / "items.json", [rows[i] for i in indices])
        for phase in ("smoke", "full"):
            split_root = root / "smoke_data" / bench if phase == "smoke" else data
            for method in methods:
                for mode in MODES:
                    name = f"{bench}_{method}_{mode}"
                    output = root / phase / name
                    cmd = [str(PYTHON), str(ROOT / "scripts/run_method.py"),
                           "--method", method, "--benchmark", bench, "--mode", mode,
                           "--model", model, "--judge-model", model, "--base-url", base_url,
                           "--judge-prompt-variant", "v3", "--output-dir", str(output)]
                    config_path = root / "configs" / phase / f"{name}.json"
                    if method == "gepa":
                        config = read(ROOT / f"configs/gepa/{bench}.json")
                        opts = config["builder_kwargs"]
                        opts.update({f"{s}_items": str(split_root / s / "items.json") for s in ("train", "val", "test")})
                        opts.update(workers=100, max_candidate_proposals=1 if phase == "smoke" else 8)
                        if phase == "smoke":
                            opts.update(max_metric_calls=20, skip_perfect_score=False)
                        if bench == "alfworld":
                            opts["max_steps"] = 50
                        write(config_path, config)
                        cmd += ["--config", str(config_path)]
                    elif method == "rethinkskill":
                        rethink_config = {
                            "method": "rethinkskill", "benchmark": bench,
                            "rounds": 1 if phase == "smoke" else 10,
                            "max_steps": 1 if phase == "smoke" else 50,
                            "hard_dead_band": .01 if bench == "searchqa" else .02,
                            "soft_rescue_delta": .02 if bench == "searchqa" else None,
                            "final_selection": "best", "full_validation_audit": False,
                        }
                        write(config_path, rethink_config)
                        cmd += ["--", "--train-items", str(split_root / "train/items.json"),
                                "--val-items", str(split_root / "val/items.json"),
                                "--test-items", str(split_root / "test/items.json"),
                                "--seed-skill", str(ROOT / f"packages/skillopt/skillopt/envs/{bench}/skills/initial.md"),
                                "--workers", "100", "--rounds", str(rethink_config["rounds"])]
                        if bench == "alfworld":
                            cmd += ["--max-steps", str(rethink_config["max_steps"])]
                    elif method == "skillgen":
                        config = yaml.safe_load((ROOT / "configs/skillgen/qwen_campaign.yaml").read_text())
                        config["pipeline"].update(max_workers=100, max_refine_rounds=1 if phase == "smoke" else 8)
                        config["verification_analysis"]["case_analyst_workers"] = 100
                        config["router"]["max_workers"] = 100
                        config["generation"].update(candidate_output_dir=str(output / "candidates"), resource_gen_workers=100)
                        config["judge"].update(prompt_variant="v3", full_validation=False)
                        if phase == "smoke":
                            config["verification"].update(sample_size=2, min_sample=1, min_net_gain_abs=1)
                            config["clustering"].update(n_clusters=1, min_clusters=1, max_failure_clusters=1, max_success_clusters=1)
                        config_path = config_path.with_suffix(".yaml")
                        config_path.parent.mkdir(parents=True, exist_ok=True)
                        config_path.write_text(yaml.safe_dump(config, sort_keys=False))
                        cmd += ["--skillgen-config", str(config_path), "--run-root", str(output / "run"), "--",
                                "--benchmark-items", str(split_root / "train/items.json"),
                                "--validation-items", str(split_root / "val/items.json"),
                                "--test-items", str(split_root / "test/items.json")]
                        if bench == "alfworld" and phase == "smoke":
                            env_config = yaml.safe_load((ROOT / "packages/alfworld-eval/configs/textworld.yaml").read_text())
                            env_config["rl"]["training"]["max_nb_steps_per_episode"] = 3
                            env_path = root / "configs/smoke/skillgen_alfworld_environment.yaml"
                            env_path.write_text(yaml.safe_dump(env_config))
                            cmd += ["--alfworld-config", str(env_path)]
                    else:
                        config_path = ROOT / f"packages/skillopt/configs/{bench}/judge_gate.yaml"
                        cmd += ["--config", str(config_path), "--",
                                "--split_dir", str(split_root),
                                "--train_size", "2" if phase == "smoke" else ("400" if bench == "searchqa" else "39"),
                                "--num_epochs", "1" if phase == "smoke" or bench == "searchqa" else "4",
                                "--batch_size", "2" if phase == "smoke" else "40",
                                "--lr_scheduler", "constant", "--edit_budget", "4",
                                "--use_slow_update", "false", "--use_meta_skill", "false",
                                "--eval_test", "true", "--workers", "100", "--analyst_workers", "100",
                                "--shuffle_train_items", "true", "--seed", "42",
                                "--qwen_chat_timeout_seconds", "180",
                                "--optimizer_qwen_chat_timeout_seconds", "180",
                                "--target_qwen_chat_timeout_seconds", "180"]
                        if bench == "alfworld":
                            cmd += ["--max_api_workers", "100", "--max_steps", "50"]
                    manifest["settings"][f"{phase}/{name}"] = {
                        "benchmark": bench, "method": method, "mode": mode, "output": str(output),
                        "command": cmd, "config": str(config_path), "config_sha256": digest(config_path),
                        "counts": {s: len(read(split_root / s / "items.json")) for s in ("train", "val", "test")},
                        "extra_inputs": {cmd[i + 1]: digest(cmd[i + 1]) for i, arg in enumerate(cmd)
                                         if arg == "--alfworld-config"},
                    }
    write(manifest_path, manifest)
    print(json.dumps({"prepared": str(root), "conditions_per_phase": 16, "model": model}))


def health(root, manifest):
    from openai import OpenAI
    results = {}
    for bench in BENCHMARKS:
        env = environment(bench, manifest)
        client = OpenAI(base_url=manifest["base_url"], api_key=env["OPENAI_API_KEY"], timeout=45, max_retries=0)
        start = time.time()
        response = client.chat.completions.create(model=manifest["model"],
            messages=[{"role": "user", "content": "Reply with OK."}], temperature=0, max_tokens=32,
            extra_body={"enable_thinking": False})
        usage = response.usage
        assert response.choices[0].message.content and usage and usage.prompt_tokens > 0
        results[bench] = {"elapsed_seconds": time.time() - start, "model": response.model,
                          "usage": usage.model_dump(), "content": response.choices[0].message.content}
    write(root / "health.json", {"passed": True, "time": time.time(), "results": results})
    print(json.dumps(results))


def is_http_500(error):
    """Only explicitly recorded HTTP 500s are ordinary failed executions."""
    return bool(re.search(r"(?:Error code:|HTTP Error|HTTP status|status_code[=:])\s*500\b", str(error)))


def audit(spec, *, smoke):
    out = Path(spec["output"])
    method, mode = spec["method"], spec["mode"]
    failures = []
    warnings = []
    if method == "rethinkskill":
        import sys
        sys.path[:0] = [str(ROOT / "packages"), str(ROOT / "packages/rethinkskill/src")]
        from rethinkskill_study.audit import audit_run
        failures.extend(audit_run(out))
    execution_failures = []
    cost_complete = False
    needed = {"skillopt": ["summary.json", "test_eval/summary.json"],
              "gepa": ["result.json", "run_metadata.json", "validation_eval.json", "test_eval.json"],
              "skillgen": ["validation_summary.json", "test_summary.json"],
              "rethinkskill": ["summary.json", "test_summary.json"]}[method]
    for name in needed:
        if not (out / name).is_file():
            failures.append(f"missing {name}")
    cost = out / "replacement_cost.json"
    rows = []
    if cost.exists():
        summary = read(cost)
        events = Path(summary["usage_events_path"])
        rows = [json.loads(line) for line in events.read_text().splitlines() if line.strip()] if events.exists() else []
        labeled = [r for r in rows if r.get("replacement_component")]
        cost_complete = bool(summary.get("usage_complete")) and all(r.get("usage_complete") for r in labeled)
        missing = [r for r in rows if not r.get("usage_complete")]
        if missing:
            warnings.append(f"{len(missing)} usage events incomplete; unknown tokens are not zero cost")
            if smoke:
                failures.append("incomplete usage")
        for row in rows:
            error = row.get("error") or row.get("fail_reason")
            if error:
                if is_http_500(error):
                    execution_failures.append({"item_id": row.get("item_id"), "error": error})
                else:
                    failures.append("execution/usage errors")
        allowed = {"llm_judge"} if mode == "judge" else {"seed_validation", "candidate_validation", "candidate_minibatch", "verification_execution"}
        if method == "rethinkskill": allowed = {"llm_judge"} if mode == "judge" else {"seed_validation", "candidate_validation"}
        if any(r["replacement_component"] not in allowed for r in labeled):
            failures.append("wrong replacement component for mode")
        if sum(r["total_tokens"] for r in labeled) != summary["total_tokens"]:
            failures.append("cost summary/event mismatch")
        if smoke:
            required = "llm_judge" if mode == "judge" else {"skillopt": "candidate_validation", "gepa": "candidate_minibatch", "skillgen": "verification_execution", "rethinkskill": "candidate_validation"}[method]
            if not any(r.get("replacement_component") == required and r["total_tokens"] > 0 for r in rows):
                failures.append(f"smoke did not exercise {required}")
    else:
        failures.append("missing replacement cost")
    if list(out.rglob("*judge_full_validation*")):
        failures.append("candidate full-validation audit artifact found")
    for name in ("test_eval.json", "test_summary.json"):
        p = out / name
        if p.exists():
            data = read(p)
            count = data.get("items", data.get("n_items"))
            if count is not None and count != spec["counts"]["test"]:
                failures.append("test item count mismatch")
    if method == "skillopt" and (out / "summary.json").exists():
        data = read(out / "summary.json")
        if data.get("test_hard") is None or data.get("final_test_hard") is None:
            failures.append("missing final test measurement")
        expected = ROOT / f"packages/skillopt/skillopt/envs/{spec['benchmark']}/skills/initial.md"
        initial = out / "skills/skill_v0000.md"
        if not initial.exists() or initial.read_text() != expected.read_text():
            failures.append("initial skill differs from configured benchmark seed")
        history = read(out / "history.json")
        if mode == "judge" and any(r.get("judge_parse_failed") or r.get("judge_error") for r in history):
            failures.append("Judge response failure")
    if method == "gepa" and (out / "gepa_run/run_log.json").exists():
        for item in read(out / "gepa_run/run_log.json"):
            for decision in item.get("judge_decisions", []):
                if decision and (decision.get("judge_parse_failed") or decision.get("judge_error")):
                    failures.append("Judge response failure")
    if method == "skillgen":
        paths = list(out.glob("run/runs/*/baseline_units/*.json")) + list(out.glob("*_units/*.json"))
        for trajectory in paths:
            data = read(trajectory)
            if data.get("metadata", {}).get("agent_exception"):
                error = data.get("error_summary", "")
                if is_http_500(error) and data.get("success") is False and data.get("score") == 0:
                    execution_failures.append({"item_id": data.get("instance_id"),
                                               "path": str(trajectory), "error": error})
                else:
                    failures.append("trajectory contains unexpected agent exception")
    return {"passed": not failures, "failures": failures, "warnings": warnings,
            "replacement_usage_complete": cost_complete,
            "recorded_http_500_failures": execution_failures,
            "usage_events": len(rows), "time": time.time()}


def verify_inputs(manifest):
    for splits in manifest["splits"].values():
        for item in splits.values():
            if digest(item["path"]) != item["sha256"]:
                raise ValueError(f"Changed dataset: {item['path']}")
    for spec in manifest["settings"].values():
        if digest(spec["config"]) != spec["config_sha256"]:
            raise ValueError(f"Changed configuration: {spec['config']}")
        for path, expected in spec.get("extra_inputs", {}).items():
            if digest(path) != expected:
                raise ValueError(f"Changed input: {path}")


def preflight(root):
    tests = ["tests", "packages/skillopt/tests/test_judge_gate.py",
             "tests/test_rethinkskill_integration.py", "packages/skillopt/tests/test_judge_adapters.py",
             "packages/skillopt/tests/test_trainer_judge_gate.py", "packages/skillopt/tests/test_trainer_evolution_mode.py",
             "packages/skillopt/tests/test_qwen_backend.py", "packages/skillopt/tests/test_azure_openai_compat.py",
             "packages/skillopt/tests/test_model_change_warning.py"]
    env = dict(os.environ, PYTHONPATH=os.pathsep.join(str(ROOT / p) for p in (
        "packages/skillopt", "packages/gepa/src", "packages/gepa", "packages/skillgen")))
    command = [str(PYTHON), "-m", "pytest", "--import-mode=importlib", *tests, "-q", "--disable-warnings", "--tb=short"]
    completed = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True)
    (root / "preflight.log").write_text(completed.stdout + completed.stderr)
    concurrency = read(root / "alfworld_concurrency.json")
    write(root / "preflight.json", {"passed": completed.returncode == 0 and concurrency["passed"],
        "tests_returncode": completed.returncode, "test_output": completed.stdout,
        "environment_invariants": concurrency["passed"], "source_sha256": source_digest(), "time": time.time()})
    print(completed.stdout)
    return completed.returncode


def supervise(root, manifest, phase, max_active, resume):
    phase_root = root / phase
    phase_root.mkdir(parents=True, exist_ok=True)
    lock = (phase_root / "supervisor.lock").open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    verify_inputs(manifest)
    write(phase_root / "supervisor.json", {"pid": os.getpid(), "status": "running", "started": time.time()})
    queue = [(key, spec) for key, spec in manifest["settings"].items() if key.startswith(phase + "/")]
    active = {}
    failed = []

    def stop(signum, frame):
        for process, _, _ in active.values():
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    while queue or active:
        while queue and len(active) < max_active:
            key, spec = queue.pop(0)
            out = Path(spec["output"])
            out.mkdir(parents=True, exist_ok=True)
            status_path = out / "condition_status.json"
            if status_path.exists():
                prior = read(status_path)
                if prior.get("status") == "complete" and audit(spec, smoke=phase == "smoke")["passed"]:
                    continue
                if not resume:
                    raise ValueError("Existing incomplete run requires --resume")
                pid = prior.get("pid")
                if pid:
                    try:
                        os.kill(pid, 0)
                    except ProcessLookupError:
                        pass
                    else:
                        raise ValueError(f"Existing child still alive: {pid}; refusing duplicate writer")
            command = list(spec["command"])
            if spec["method"] == "skillgen":
                checkpoints = sorted(out.glob("run/runs/*/run_metadata.json"))
                if len(checkpoints) > 1:
                    raise ValueError("Multiple SkillGen checkpoints; explicit recovery required")
                if checkpoints:
                    command += ["--resume", str(checkpoints[0].parent)]
            log = (out / "stdout.log").open("a")
            child = subprocess.Popen(command, cwd=ROOT, env=environment(spec["benchmark"], manifest),
                                     stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            log.close()
            write(status_path, {"status": "running", "pid": child.pid, "started": time.time(), "command": command})
            active[key] = (child, spec, time.time())
        for key, (child, spec, started) in list(active.items()):
            rc = child.poll()
            if rc is None:
                continue
            report = audit(spec, smoke=phase == "smoke")
            if rc:
                report["passed"] = False
                report["failures"].append(f"process exit {rc}")
            out = Path(spec["output"])
            write(out / "audit.json", report)
            write(out / "condition_status.json", {"status": "complete" if report["passed"] else "failed",
                "pid": child.pid, "returncode": rc, "started": started, "finished": time.time(), "audit": report})
            if not report["passed"]:
                failed.append(key)
            del active[key]
        if active:
            time.sleep(2)
    write(phase_root / "supervisor.json", {"pid": os.getpid(), "status": "failed" if failed else "complete",
                                          "failed": failed, "finished": time.time(), "source_sha256": source_digest()})
    return int(bool(failed))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--action", required=True, choices=["prepare", "health", "preflight", "launch", "supervise", "status"])
    parser.add_argument("--phase", choices=["smoke", "full"], default="smoke")
    parser.add_argument("--model")
    parser.add_argument("--base-url")
    parser.add_argument("--max-active", type=int, default=2)
    parser.add_argument("--methods", nargs="+", choices=METHODS, default=None)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    if args.action == "prepare":
        section = read(ROOT / "benchmark/llm_config.local.json").get("default", {})
        model = args.model or section.get("model")
        base_url = args.base_url or section.get("base_url")
        if not model or not base_url:
            raise ValueError("Set default.model and default.base_url in benchmark/llm_config.local.json")
        prepare(root, model, base_url, args.methods)
        return 0
    manifest = read(root / "manifest.json")
    if args.action == "health":
        health(root, manifest)
    elif args.action == "preflight":
        return preflight(root)
    elif args.action == "status":
        for key, spec in manifest["settings"].items():
            if key.startswith(args.phase + "/"):
                p = Path(spec["output"]) / "condition_status.json"
                print(key, json.dumps(read(p) if p.exists() else {"status": "pending"}))
    elif args.action in ("launch", "supervise"):
        if args.max_active < 1:
            raise ValueError("max-active must be positive")
        verify_inputs(manifest)
        if args.action == "launch":
            if not read(root / "health.json")["passed"]:
                raise ValueError("Real service health check required")
            if args.phase == "full":
                smoke = read(root / "smoke/supervisor.json")
                if smoke.get("status") != "complete" or smoke.get("source_sha256") != source_digest():
                    raise ValueError("All smoke audits must pass on the current code before full launch")
                checks = read(root / "preflight.json")
                if not checks.get("passed") or checks.get("source_sha256") != source_digest():
                    raise ValueError("Independent preflight checks must pass before full launch")
            phase_root = root / args.phase
            phase_root.mkdir(parents=True, exist_ok=True)
            command = [str(PYTHON), str(Path(__file__).resolve()), "--root", str(root), "--action", "supervise",
                       "--phase", args.phase, "--max-active", str(args.max_active)]
            if args.resume:
                command.append("--resume")
            with (phase_root / "supervisor.log").open("a") as log:
                child = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            print(json.dumps({"supervisor_pid": child.pid, "phase": args.phase, "root": str(root)}))
        else:
            return supervise(root, manifest, args.phase, args.max_active, args.resume)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
