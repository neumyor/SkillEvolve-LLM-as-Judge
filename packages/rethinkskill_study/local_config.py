"""Machine-local settings shared by the study launchers and benchmark bridge."""
from __future__ import annotations

import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "benchmark/llm_config.local.json"


def load_local_config() -> dict:
    if not CONFIG_PATH.is_file():
        raise ValueError(
            f"Missing local configuration: {CONFIG_PATH}. "
            "Copy benchmark/llm_config.example.json and fill in your settings."
        )
    config = json.loads(CONFIG_PATH.read_text())
    if not isinstance(config, dict):
        raise ValueError(f"Local configuration must be a JSON object: {CONFIG_PATH}")
    return config


def benchmark_root(*, required: bool = True) -> Path | None:
    raw = os.environ.get("ALFWORLD_BENCHMARK_ROOT")
    if not raw or str(raw).startswith("<"):
        raw = load_local_config().get("alfworld_benchmark_root") if CONFIG_PATH.is_file() else None
    if not raw:
        if required:
            raise ValueError(
                "Set alfworld_benchmark_root in benchmark/llm_config.local.json "
                "or ALFWORLD_BENCHMARK_ROOT in the environment."
            )
        return None
    path = Path(raw).expanduser()
    path = (path if path.is_absolute() else ROOT / path).resolve()
    if required and not path.is_dir():
        raise ValueError(f"Configured ALFWorld benchmark directory does not exist: {path}")
    return path


def endpoint_config(benchmark: str) -> dict:
    config = load_local_config()
    section = config.get(f"{benchmark}-eval") or config.get("default") or {}
    if not isinstance(section, dict) or not section.get("base_url"):
        raise ValueError(f"Set {benchmark}-eval.base_url in {CONFIG_PATH}")
    return section
