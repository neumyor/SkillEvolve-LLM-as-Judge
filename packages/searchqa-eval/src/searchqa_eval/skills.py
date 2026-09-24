"""Per-method skill loading for the unified SearchQA evaluation.

Methods
-------
vanilla      frozen base model, no skill text
skillopt     SkillOpt's released SearchQA skill (ckpt/searchqa/gpt5.5_skill.md)
trace2skill  Trace2Skill skill document (not released for SearchQA — provide
             your own generated file)

For both skill methods the document is placed in the system prompt's
``## Skill`` section, exactly as SkillOpt does (this is also how SkillOpt ran
Trace2Skill as a baseline).
"""
from __future__ import annotations

from pathlib import Path

METHODS = ("vanilla", "skillopt", "trace2skill")

_SKILLS_DIR = Path(__file__).resolve().parent / "skills_docs"

_DEFAULT_SKILL = {
    "skillopt": _SKILLS_DIR / "skillopt_searchqa.md",
    "trace2skill": _SKILLS_DIR / "trace2skill_searchqa.md",
}


def load_skill_content(method: str, skill_path: str | Path | None = None) -> str:
    """Return the skill document text for a method ("" for vanilla)."""
    if method not in METHODS:
        raise ValueError(f"Unknown method {method!r}; choose one of {METHODS}")
    if method == "vanilla":
        return ""
    path = Path(skill_path).expanduser() if skill_path else _DEFAULT_SKILL[method]
    return path.resolve().read_text(encoding="utf-8")
