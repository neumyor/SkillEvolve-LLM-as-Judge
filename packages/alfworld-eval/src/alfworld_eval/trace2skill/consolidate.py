"""Trace2Skill memory consolidation for a single ALFWorld Markdown skill."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .llm import OpenAICompatibleClient


def _memory_text(records: list[dict[str, Any]]) -> str:
    chunks = []
    for record in records:
        for item in record.get("items", []):
            if item.get("type") not in {"failure_memory", "success_memory"}:
                continue
            chunks.append(
                f"- {item.get('title', '')}: {item.get('description', '')} "
                f"{item.get('content', '')}".strip()
            )
    return "\n".join(chunks)


def _clean_markdown(text: str) -> str:
    text = text.strip()
    match = re.fullmatch(r"```(?:markdown|md|text)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        text = match.group(1).strip()
    if not text.startswith("#"):
        raise ValueError("consolidation response is not Markdown")
    return text + "\n"


def _fallback_skill(base_skill: str, records: list[dict[str, Any]]) -> str:
    additions: list[str] = []
    seen: set[str] = set()
    for record in records:
        for item in record.get("items", []):
            if item.get("type") not in {"failure_memory", "success_memory"}:
                continue
            content = " ".join(
                str(item.get(key, "")).strip() for key in ("description", "content")
            ).strip()
            key = re.sub(r"\W+", " ", content.lower()).strip()
            if content and key not in seen:
                seen.add(key)
                additions.append(f"- {content}")
    if not additions:
        return base_skill.rstrip() + "\n"
    return (
        base_skill.rstrip()
        + "\n\n## Lessons from Verified Trajectories\n\n"
        + "\n".join(additions)
        + "\n"
    )


def consolidate_skill(
    base_skill: str | Path,
    records: list[dict[str, Any]],
    *,
    client: OpenAICompatibleClient | None = None,
    task_type: str = "ALFWorld",
) -> str:
    """Merge verified memories into a reusable skill document.

    Only failure memories and success memories are eligible.  Failure causes
    are evidence for the analyst but are intentionally not copied verbatim.
    """
    base = (
        Path(base_skill).read_text(encoding="utf-8")
        if isinstance(base_skill, str | Path) and Path(base_skill).is_file()
        else str(base_skill)
    )
    memories = _memory_text(records)
    if not client:
        return _fallback_skill(base, records)

    system = """You are a skill editor implementing Trace2Skill.
Return only one concise Markdown skill document. Preserve useful generic rules
from the current document, merge only reusable lessons supported by the memory
items, remove duplicates and contradictions, and never include a fixed object,
room, trial, absolute path, or episode-specific action sequence. Do not mention
the analysis process or memory items."""
    user = (
        f"Task domain: {task_type}\n\nCURRENT SKILL:\n{base}\n\n"
        f"VERIFIED MEMORY ITEMS:\n{memories or '(none)'}\n\n"
        "Return the complete replacement Markdown skill."
    )
    response = client.complete(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        max_tokens=4096,
    )
    try:
        return _clean_markdown(response.content)
    except ValueError:
        return _fallback_skill(base, records)


def write_skill(path: str | Path, content: str) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content if content.endswith("\n") else content + "\n", encoding="utf-8")
    return target
