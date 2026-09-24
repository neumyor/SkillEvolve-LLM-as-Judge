"""SearchQA data loading and context truncation.

The truncation logic is a verbatim port of SkillOpt's
``skillopt/envs/searchqa/rollout.py::_truncate_context``: trim the joined
``[DOC]``-separated context to a character budget without splitting a
document, falling back to a hard cut when the first document alone exceeds
the budget.
"""
from __future__ import annotations

import json
from pathlib import Path

MAX_CONTEXT_CHARS = 6000


def load_items(path: str | Path) -> list[dict]:
    """Load items from a JSON array (or {"data": [...]}) file."""
    path = Path(path).expanduser()
    content = path.read_text(encoding="utf-8").strip()
    try:
        data = json.loads(content)
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = data.get("data") or list(data.values())
        else:
            items = []
    except json.JSONDecodeError:
        items = [json.loads(line) for line in content.splitlines() if line.strip()]

    required = ("id", "question", "context", "answers")
    for i, item in enumerate(items):
        missing = [key for key in required if key not in item]
        if missing:
            raise ValueError(f"{path} item #{i} is missing required fields: {missing}")
    return items


def truncate_context(context: str, max_chars: int = MAX_CONTEXT_CHARS) -> str:
    """Truncate context at [DOC] boundaries to stay within budget."""
    if len(context) <= max_chars:
        return context
    docs = context.split("[DOC]")
    result = ""
    for doc in docs:
        candidate = result + "[DOC]" + doc if result else doc
        if len(candidate) > max_chars:
            break
        result = candidate
    if not result:
        result = context[:max_chars] + "\n...[truncated]"
    return result
