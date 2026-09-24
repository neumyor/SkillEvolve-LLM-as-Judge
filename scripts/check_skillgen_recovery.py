#!/usr/bin/env python3
"""Real small SkillGen runs, then resume and require no additional LLM calls."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import copy
from pathlib import Path
import subprocess

import yaml
import run_direct_campaign as campaign


def check(root, manifest, mode):
    spec = copy.deepcopy(manifest["settings"][f"smoke/searchqa_skillgen_{mode}"])
    output = root / "recovery" / f"searchqa_skillgen_{mode}"
    output.mkdir(parents=True, exist_ok=True)
    config = yaml.safe_load(Path(spec["config"]).read_text())
    config["generation"]["candidate_output_dir"] = str(output / "candidates")
    config_path = output / "input.yaml"
    config_path.write_text(yaml.safe_dump(config))
    command = spec["command"]
    for option, value in (("--output-dir", output), ("--run-root", output / "run"),
                          ("--skillgen-config", config_path)):
        command[command.index(option) + 1] = str(value)
    env = campaign.environment("searchqa", manifest)
    with (output / "fresh.log").open("w") as log:
        subprocess.run(command, cwd=campaign.ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    checkpoint = list(output.glob("run/runs/*/pipeline_complete.json"))
    assert len(checkpoint) == 1
    events = checkpoint[0].with_name("usage_events.jsonl")
    before = events.read_bytes()
    before_test = campaign.read(output / "test_summary.json")
    command += ["--resume", str(checkpoint[0].parent)]
    with (output / "resume.log").open("w") as log:
        subprocess.run(command, cwd=campaign.ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    report = {"mode": mode, "passed": before == events.read_bytes() and before_test == campaign.read(output / "test_summary.json"),
              "events_before": len(before.splitlines()), "events_after": len(events.read_bytes().splitlines()),
              "output": str(output)}
    campaign.write(output / "recovery_check.json", report)
    assert report["passed"], report
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    manifest = campaign.read(root / "manifest.json")
    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda mode: check(root, manifest, mode), ("baseline", "judge")))
    report = {"passed": all(r["passed"] for r in results), "results": results}
    campaign.write(root / "skillgen_resume.json", report)
    print(report)


if __name__ == "__main__":
    main()
