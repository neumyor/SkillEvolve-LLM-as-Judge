"""Small adapters from the shared benchmark manifests to SkillGen records."""
from __future__ import annotations

import json
from pathlib import Path

from models import TaskDataset, TaskInstance, TaskType

ROOT = Path(__file__).resolve().parents[2]


def _load(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else list(data.get("data", []))


def load_benchmark_dataset(benchmark: str, *, split: str = "train",
                           items_path: str | None = None) -> TaskDataset:
    name = str(benchmark).strip().lower()
    if name == "searchqa":
        default = ROOT / "searchqa-eval/data/searchqa_split" / split / "items.json"
        rows = _load(Path(items_path) if items_path else default)
        instances = [TaskInstance(
            instance_id=str(row["id"]),
            input=f"## Context\n{row.get('context', '')}\n\n## Question\n{row.get('question', '')}",
            ground_truth=row.get("answers", []),
            metadata={"benchmark": "searchqa", "raw": row},
        ) for row in rows]
        return TaskDataset("searchqa", "SearchQA", TaskType.BINARY, instances,
                           {"benchmark": "searchqa", "split": split,
                            "items_path": str(items_path or default)})
    if name == "alfworld":
        # SkillGen's public labels follow the evaluator (`valid_seen` /
        # `valid_unseen`), while the copied manifests use `val` / `test`.
        manifest_split = {
            "valid_seen": "val",
            "valid_unseen": "test",
        }.get(split, split)
        default = ROOT / "skillopt/data/alfworld_path_split" / manifest_split / "items.json"
        rows = _load(Path(items_path) if items_path else default)
        env_config = ROOT / "alfworld-eval/configs/textworld.yaml"
        instances = [TaskInstance(
            instance_id=str(index), input=str(row["gamefile"]),
            metadata={
                "benchmark": "alfworld",
                "gamefile": row["gamefile"],
                "split": split,
                "env_config": str(env_config),
            },
        ) for index, row in enumerate(rows)]
        return TaskDataset("alfworld", "ALFWorld", TaskType.BINARY, instances,
                           {"benchmark": "alfworld", "split": split,
                            "items_path": str(items_path or default)})
    raise ValueError(f"unsupported SkillGen benchmark: {benchmark!r}")


__all__ = ["load_benchmark_dataset"]
