"""Static validation of a candidate skill document (FUSE stage-7 gate).

Ports the original FUSE static checks (frontmatter/name/description/unsafe
paths/placeholders) to this harness's single-file, prompt-injected skill
format, and adds the constraints that only exist here:

* the document is re-sent in every episode prompt, so a hard character budget
  is part of the protocol (the released SkillOpt document is ~13k chars);
* the episode protocol rejects non-English responses, and a skill containing
  CJK text would coach the model toward them;
* incident ids, gamefile paths and trial names are evaluation artifacts; a
*reward/verifier* vocabulary would break the trust boundary (the skill must
  read as an operating guide, not as benchmark meta-commentary).
"""
from __future__ import annotations

import re

# The released SkillOpt ALFWorld skill is 13,179 chars; allow headroom but keep
# the prompt-cost in the same order of magnitude.
DEFAULT_MAX_CHARS = 16_000
DEFAULT_MIN_CHARS = 400

CJK_RE = re.compile(r"[\u3000-\u303f\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff00-\uffef]")
TRIAL_RE = re.compile(r"trial[_-]?T?\d{6,}", re.IGNORECASE)
GAMEFILE_RE = re.compile(r"json_2\.1\.1|\.tw-pddl|gamefile|game_file", re.IGNORECASE)
# "reward"/"verifier" are benchmark vocabulary; plain "verify" is legitimate
# skill language and must not trip this check.
BENCHMARK_META_RE = re.compile(r"\brewards?\b|\bverifier\b|\bbenchmark\b|\bskillbank\b", re.IGNORECASE)
PLACEHOLDER_RE = re.compile(r"TODO|TBD|FIXME|<insert|placeholder text", re.IGNORECASE)


def check_candidate_skill(
    text: str,
    *,
    max_chars: int = DEFAULT_MAX_CHARS,
    min_chars: int = DEFAULT_MIN_CHARS,
) -> list[str]:
    """Return the list of static violations (empty list = passes)."""
    errors: list[str] = []
    stripped = str(text or "").strip()
    if not stripped:
        return ["skill document is empty"]
    if len(stripped) < min_chars:
        errors.append(
            f"skill document is too short ({len(stripped)} < {min_chars} chars); "
            "a transferable operating guide cannot be this small"
        )
    if len(stripped) > max_chars:
        errors.append(
            f"skill document exceeds the budget ({len(stripped)} > {max_chars} chars); "
            "it is re-sent in every episode prompt"
        )
    if CJK_RE.search(stripped):
        errors.append("skill document contains CJK characters; the episode protocol is English-only")
    if TRIAL_RE.search(stripped):
        errors.append("skill document references trial/incident ids (evaluation artifacts)")
    if GAMEFILE_RE.search(stripped):
        errors.append("skill document references gamefile paths (evaluation artifacts)")
    if BENCHMARK_META_RE.search(stripped):
        errors.append(
            "skill document uses benchmark meta vocabulary (reward/verifier/benchmark); "
            "it must read as an operating guide"
        )
    if PLACEHOLDER_RE.search(stripped):
        errors.append("skill document contains placeholder markers")
    return errors
