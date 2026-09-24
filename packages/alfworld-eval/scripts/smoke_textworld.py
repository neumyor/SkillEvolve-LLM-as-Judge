from __future__ import annotations

import argparse
from pathlib import Path

from alfworld_eval.env import AlfworldTextEnv
from alfworld_eval.runner import first_admissible_action, run_episode


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one ALFWorld TextWorld smoke episode.")
    parser.add_argument(
        "--split",
        choices=("train", "valid_seen", "valid_unseen"),
        default="valid_seen",
    )
    parser.add_argument("--steps", type=int, default=1)
    parser.add_argument("--config", type=Path, default=Path("configs/textworld.yaml"))
    args = parser.parse_args()

    with AlfworldTextEnv(config_path=args.config, split=args.split) as env:
        result = run_episode(env, first_admissible_action, max_steps=args.steps)

    print(f"split: {result.split}")
    print(f"game_file: {result.game_file}")
    print(f"steps: {result.steps}")
    print(f"success: {result.success}")
    print(f"termination_reason: {result.termination_reason}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
