"""Per-method skill loading for the unified ALFWorld evaluation.

Methods
-------
vanilla      frozen base model, no skill text
skillopt     SkillOpt's released skill document (ckpt/alfworld/gpt5.5_skill.md),
             injected as a prompt prefix
trace2skill  Trace2Skill skill document injected the same way (Trace2Skill
             released no ALFWorld skills, so provide your own generated file)
skillrl      SkillRL's hierarchical SkillBank (claude_style_skills.json),
             rendered per-task-category exactly as SkillRL's
             format_skills_block does
fuse         a directory of per-task-type Markdown skills (``<task_type>.md``),
             routed deterministically by the episode's gamefile — the adapted
             FUSE publish form (one evolved skill per family, family := task
             type). Injection channel is the same as skillopt (prompt prefix).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .prompts import SKILL_KNOWLEDGE_HEADER, SkillView, extract_task_description

# SkillOpt rollout.py TASKS — parsed from the gamefile path.
TASKS = [
    "pick_and_place",
    "pick_two_obj_and_place",
    "look_at_obj_in_light",
    "pick_heat_then_place_in_recep",
    "pick_cool_then_place_in_recep",
    "pick_clean_then_place_in_recep",
]

# SkillRL's classifier keyword table (skill_retrieval.py). Order matters:
# look_at/examine wins over the put/place catch-all.
_TASK_KEYWORDS = [
    ("look_at_obj_in_light", ("look at", "examine")),
    ("clean", ("clean",)),
    ("heat", ("heat", "hot")),
    ("cool", ("cool", "cold")),
    ("pick_and_place", ("put", "place")),
]

_METHODS = ("vanilla", "skillopt", "trace2skill", "skillrl", "fuse")

_SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills_docs"


def task_type_from_gamefile(gamefile: str) -> str:
    for task in TASKS:
        if task in str(gamefile):
            return task
    return "other"


def classify_alfworld_task(task_description: str) -> str:
    task_l = task_description.lower()
    for category, keywords in _TASK_KEYWORDS:
        if any(kw in task_l for kw in keywords):
            return category
    return "pick_and_place"


def _read_text(path: str | Path) -> str:
    return Path(path).expanduser().resolve().read_text(encoding="utf-8")


def _render_skillrl_block(bank: dict, category: str) -> str:
    out = ["## Retrieved Relevant Experience", "", "### General Principles"]
    for p in bank.get("general_skills", []):
        title = p.get("title", "")
        principle = (p.get("principle") or "").rstrip(".")
        out.append(f"- **{title}**: {principle}.")

    cat_skills = bank.get("task_specific_skills", {}).get(category, [])
    if cat_skills:
        label = category.replace("_", " ").title()
        out.append("")
        out.append(f"### {label} Skills")
        for s in cat_skills:
            title = s.get("title", "")
            principle = (s.get("principle") or "").rstrip(".")
            when = (s.get("when_to_apply") or "").rstrip(".")
            out.append(f"- **{title}**: {principle}.")
            if when:
                out.append(f"  _Apply when: {when}._")

    mistakes = bank.get("common_mistakes", [])
    if mistakes:
        out.append("")
        out.append("### Mistakes to Avoid")
        for mis in mistakes:
            desc = (mis.get("description") or "").rstrip(".")
            fix = (mis.get("how_to_avoid") or "").rstrip(".")
            if not desc:
                continue
            out.append(f"- **Don't**: {desc}.")
            if fix:
                out.append(f"  **Instead**: {fix}.")

    return "\n".join(out)


class SkillProvider:
    """Returns the SkillView for one episode given its gamefile and
    initial observation. Stateless methods return the same view every time;
    skillrl classifies the episode's task description first; fuse routes by
    the gamefile's task type (deterministic, no classification)."""

    def __init__(self, method: str, skill: SkillView | None = None, bank: dict | None = None,
                 routed_skills: dict[str, str] | None = None):
        if method not in _METHODS:
            raise ValueError(f"Unknown method {method!r}; choose one of {_METHODS}")
        self.method = method
        self.skill = skill
        self.bank = bank
        self.routed_skills = routed_skills or {}

    def view_for(self, gamefile: str, initial_observation: str) -> SkillView:
        if self.method == "vanilla":
            return SkillView()
        if self.method in ("skillopt", "trace2skill"):
            return self.skill or SkillView()
        if self.method == "fuse":
            if not self.routed_skills:
                raise ValueError("fuse method requires a directory of routed skills")
            task_type = task_type_from_gamefile(gamefile)
            text = self.routed_skills.get(task_type)
            if text is None:
                # Unknown task type: no skill rather than a wrong skill. The
                # run summary records per-type provenance, so the gap is
                # visible after the fact instead of silently routing every
                # such episode to an arbitrary document.
                return SkillView()
            return SkillView(prefix=SKILL_KNOWLEDGE_HEADER + text)
        if self.method == "skillrl":
            if self.bank is None:
                raise ValueError("skillrl method requires a SkillBank dict")
            category = classify_alfworld_task(
                extract_task_description(initial_observation)
            )
            return SkillView(body=_render_skillrl_block(self.bank, category))
        raise AssertionError(self.method)


def _load_routed_skills(skill_dir: str | Path) -> dict[str, str]:
    """Load ``<task_type>.md`` files from a directory, keyed by task type.

    Fails fast when a known task type has no document: a silently missing file
    would quietly degrade that type to vanilla while the run still looks
    healthy, which is exactly the kind of protocol fork the summary cannot
    otherwise detect.
    """
    directory = Path(skill_dir).expanduser().resolve()
    if not directory.is_dir():
        raise FileNotFoundError(f"skill directory not found: {directory}")
    routed: dict[str, str] = {}
    for path in sorted(directory.glob("*.md")):
        routed[path.stem] = _read_text(path)
    missing = [task for task in TASKS if task not in routed]
    if missing:
        raise ValueError(
            f"skill directory {directory} is missing documents for task types: {missing}"
        )
    return routed


def _routed_provenance(skill_dir: str | Path, routed: dict[str, str]) -> dict:
    directory = Path(skill_dir).expanduser().resolve()
    per_type = {
        task_type: {
            "path": str(directory / f"{task_type}.md"),
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "chars": len(text),
        }
        for task_type, text in sorted(routed.items())
    }
    combined = hashlib.sha256(
        "".join(f"{task}:{per_type[task]['sha256']}\n" for task in sorted(per_type)).encode("utf-8")
    ).hexdigest()
    return {
        "kind": "routed_skill_dir",
        "path": str(directory),
        "per_type": per_type,
        "sha256": combined,
        "chars": sum(item["chars"] for item in per_type.values()),
    }


def skill_provenance(
    method: str,
    *,
    skill_path: str | Path | None = None,
    skillrl_bank_path: str | Path | None = None,
    skill_dir: str | Path | None = None,
) -> dict:
    """Identify the exact skill bytes a run injected.

    Recording only ``skill_path`` is not enough: a skill document is an editable
    file that later stages rewrite (Trace2Skill's consolidation regenerates it,
    and the endpoint is not deterministic, so the replacement differs). A path
    says where the skill was read from, not what was read, so a run could be
    attributed to content it never saw. The digest settles that; ``chars`` makes
    an accidental truncation visible too.
    """
    if method == "vanilla":
        return {"kind": "none"}

    if method in ("skillopt", "trace2skill"):
        path = Path(skill_path) if skill_path else _SKILLS_DIR / {
            "skillopt": "skillopt_alfworld.md",
            "trace2skill": "trace2skill_alfworld.md",
        }[method]
        text = _read_text(path)
        return {
            "kind": "markdown_skill",
            "path": str(path.expanduser().resolve()),
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "chars": len(text),
        }

    if method == "fuse":
        if skill_dir is None:
            raise ValueError("fuse method requires --skill-dir for provenance")
        routed = _load_routed_skills(skill_dir)
        return _routed_provenance(skill_dir, routed)

    if method == "skillrl":
        path = Path(skillrl_bank_path) if skillrl_bank_path else (
            _SKILLS_DIR / "skillrl_claude_style_skills.json"
        )
        text = _read_text(path)
        return {
            "kind": "skillbank_json",
            "path": str(path.expanduser().resolve()),
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "chars": len(text),
        }

    raise ValueError(f"Unknown method {method!r}; choose one of: {_METHODS}")


def load_skill_provider(
    method: str,
    *,
    skill_path: str | Path | None = None,
    skillrl_bank_path: str | Path | None = None,
    skill_dir: str | Path | None = None,
) -> SkillProvider:
    if method == "vanilla":
        return SkillProvider("vanilla")

    if method in ("skillopt", "trace2skill"):
        if skill_path is None:
            default = {
                "skillopt": _SKILLS_DIR / "skillopt_alfworld.md",
                "trace2skill": _SKILLS_DIR / "trace2skill_alfworld.md",
            }[method]
            skill_path = default
        text = _read_text(skill_path)
        prefix = SKILL_KNOWLEDGE_HEADER + text
        return SkillProvider(method, skill=SkillView(prefix=prefix))

    if method == "fuse":
        if skill_dir is None:
            raise ValueError("fuse method requires --skill-dir")
        return SkillProvider("fuse", routed_skills=_load_routed_skills(skill_dir))

    if method == "skillrl":
        if skillrl_bank_path is None:
            skillrl_bank_path = _SKILLS_DIR / "skillrl_claude_style_skills.json"
        bank = json.loads(_read_text(skillrl_bank_path))
        return SkillProvider("skillrl", bank=bank)

    raise ValueError(f"Unknown method {method!r}")
