# ruff: noqa: E501 -- template strings are verbatim copies of SkillOpt's
# searchqa prompt text; reflowing them would change the prompts sent to the model.
"""Prompt construction for the unified single-turn SearchQA evaluation.

Verbatim port of SkillOpt's ``skillopt/envs/searchqa/rollout.py`` prompt
builders (``_build_system`` / ``_build_user``) and its
``prompts/rollout_system.md`` template. Skill documents are injected into the
system prompt's ``## Skill`` section — the same mechanism SkillOpt uses for
its own skill and for the Trace2Skill baseline.
"""
from __future__ import annotations

from searchqa_eval.data import MAX_CONTEXT_CHARS, truncate_context

ROLLOUT_SYSTEM_TEMPLATE = """You are an expert question answering agent.

{skill_section}## Task Format
You will receive a CONTEXT containing document passages and a QUESTION.
Read the context carefully and answer the question based on the information provided.

## Answer Format
Think step by step, then provide your final answer inside <answer>...</answer> tags.
Keep your answer concise — typically a few words or a short phrase.
Do not repeat the question. Do not include unnecessary explanation in the answer tags.

Example:
<answer>Abraham Lincoln</answer>
"""


def build_system_prompt(skill_content: str = "") -> str:
    """SkillOpt _build_system: skill goes into a '## Skill' section."""
    if skill_content.strip():
        skill_section = f"## Skill\n{skill_content.strip()}\n\n"
    else:
        skill_section = ""
    return ROLLOUT_SYSTEM_TEMPLATE.format(skill_section=skill_section)


def build_user_prompt(question: str, context: str, max_context_chars: int = MAX_CONTEXT_CHARS) -> str:
    """SkillOpt _build_user (single-turn, no diagnostic sections)."""
    context = truncate_context(context, max_context_chars)
    return "\n\n".join(
        [
            f"## Context\n{context}",
            f"## Question\n{question}",
        ]
    )
