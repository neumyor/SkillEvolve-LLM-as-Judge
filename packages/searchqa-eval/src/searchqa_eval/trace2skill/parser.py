"""Parsers for Trace2Skill analyst reports."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_ITEM_RE = re.compile(
    r"^#\s+(Failure Cause Item|Failure Memory Item)\s+(\d+)\s*\n"
    r"(.*?)(?=\n#\s+(?:Failure Cause Item|Failure Memory Item)\s+\d+|\Z)",
    re.MULTILINE | re.DOTALL,
)
_SECTION_RE = re.compile(
    r"^##\s+(Title|Description|Content|Relation to Skill|Skill Reflection)\s*\n"
    r"(.*?)(?=\n##\s+|\Z)",
    re.MULTILINE | re.DOTALL,
)
_SUCCESS_ITEM_RE = re.compile(
    r"^#\s+Success Memory Item\s+(\d+)\s*\n"
    r"(.*?)(?=\n#\s+Success Memory Item\s+\d+\s*\n|\Z)",
    re.MULTILINE | re.DOTALL,
)


def _strip_wrappers(text: str) -> str:
    text = text.strip()
    if "</think>" in text:
        text = text.rsplit("</think>", 1)[-1].strip()
    match = re.fullmatch(r"```(?:markdown|md|text)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    return match.group(1).strip() if match else text


def _sections(body: str) -> dict[str, str]:
    return {
        match.group(1): match.group(2).strip()
        for match in _SECTION_RE.finditer(body)
    }


def parse_analysis_report(text: str) -> list[dict[str, Any]]:
    """Parse failure cause/memory items, tolerating reasoning wrappers."""
    records = []
    for match in _ITEM_RE.finditer(_strip_wrappers(text)):
        kind = "failure_cause" if match.group(1) == "Failure Cause Item" else "failure_memory"
        sections = _sections(match.group(3))
        records.append(
            {
                "type": kind,
                "number": int(match.group(2)),
                "title": sections.get("Title", ""),
                "description": sections.get("Description", ""),
                "content": sections.get("Content", ""),
                "relation_to_skill": sections.get("Relation to Skill", ""),
                "skill_reflection": sections.get("Skill Reflection", ""),
            }
        )
    return records


def parse_success_report(text: str) -> list[dict[str, Any]]:
    """Parse the success-memory format used by Trace2Skill."""
    records = []
    for match in _SUCCESS_ITEM_RE.finditer(_strip_wrappers(text)):
        sections = _sections(match.group(2))
        records.append(
            {
                "type": "success_memory",
                "number": int(match.group(1)),
                "title": sections.get("Title", ""),
                "description": sections.get("Description", ""),
                "content": sections.get("Content", ""),
            }
        )
    return records


def parse_analysis_file(path: str | Path) -> list[dict[str, Any]]:
    return parse_analysis_report(Path(path).read_text(encoding="utf-8", errors="replace"))


def parse_success_file(path: str | Path) -> list[dict[str, Any]]:
    return parse_success_report(Path(path).read_text(encoding="utf-8", errors="replace"))
