#!/usr/bin/env python3
"""Compare real ALFWorld observations in serial and concurrent execution."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/alfworld-eval/src"))
os.environ.setdefault("ALFWORLD_DATA", str(ROOT / "packages/alfworld-eval/.data/alfworld"))
from alfworld_eval.env import AlfworldTextEnv


def execute(row):
    with AlfworldTextEnv(config_path=str(ROOT / "packages/alfworld-eval/configs/textworld.yaml"),
                         split="train", seed=42, gamefiles=[row["gamefile"]]) as env:
        initial = env.reset()
        assert initial.game_file.endswith(row["gamefile"])
        records = [asdict(initial)]
        for action in ("go to desk 1", "look", "inventory"):
            result = env.step(action)
            records.append(asdict(result.observation))
        return records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = json.loads((ROOT / "packages/skillopt/data/alfworld_path_split/train/items.json").read_text())[:2]
    serial = [execute(row) for row in rows]
    with ThreadPoolExecutor(max_workers=100) as pool:
        concurrent = list(pool.map(execute, rows * 2))
    assert concurrent == serial * 2, "Concurrent environment operations changed observations"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"passed": True, "workers": 100, "units": 2, "repeats": 2,
                                     "serial": serial, "concurrent": concurrent}, indent=2))
    print("PASS: serial/concurrent observations and action lists are exactly identical")


if __name__ == "__main__":
    main()
