from __future__ import annotations

import importlib.metadata
import os
import sys
from pathlib import Path

import yaml

REQUIRED_DATA_PATHS = (
    "json_2.1.1/train",
    "json_2.1.1/valid_seen",
    "json_2.1.1/valid_unseen",
    "logic/alfred.pddl",
    "logic/alfred.twl2",
)


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    config_path = project_root / "configs" / "textworld.yaml"
    data_root = Path(
        os.path.expandvars(
            os.path.expanduser(
                os.environ.get("ALFWORLD_DATA", str(project_root / ".data" / "alfworld"))
            )
        )
    )

    print(f"Python: {sys.version.split()[0]}")
    for package in ("alfworld", "textworld", "PyYAML"):
        print(f"{package}: {importlib.metadata.version(package)}")

    with config_path.open(encoding="utf-8") as config_file:
        yaml.safe_load(config_file)
    print(f"Config: OK ({config_path})")

    missing = [relative for relative in REQUIRED_DATA_PATHS if not (data_root / relative).exists()]
    if missing:
        print(f"Data root: INCOMPLETE ({data_root})")
        for relative in missing:
            print(f"  missing: {relative}")
        print("Run: uv run alfworld-download")
        return 1

    print(f"Data root: OK ({data_root})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
