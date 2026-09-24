# ruff: noqa: E501 -- template strings are verbatim copies of the SkillRL/SkillOpt
# prompt text; reflowing them would change the prompts sent to the model.
"""Prompt protocols for the unified ALFWorld evaluation.

Templates mirror the exact protocol shared by SkillRL / SKILL0 / SkillOpt:
the agent reasons inside <think>...</think> and commits an action inside
<action>...</action>, choosing from the environment's admissible actions.

Skill injection follows each method's own convention:
  - skillopt / trace2skill: the skill document is prepended to the user
    message under a "## Skill Knowledge" header (SkillOpt rollout.py).
  - skillrl: the rendered SkillBank block is placed after the task line under
    "## Retrieved Relevant Experience" (SkillRL prompts/alfworld.py).
  - vanilla: no skill text at all.
"""
from __future__ import annotations

from dataclasses import dataclass

SYSTEM_PROMPT = "You are an expert agent operating in the ALFRED Embodied Environment."

ACTION_PROTOCOL_REMINDER = """Before answering, reason in no more than two short
sentences. Do not discuss alternative plans or repeat the task description.
Then output exactly one action from the admissible action list using this format:
<think>brief reason</think><action>one admissible action</action>
Do not output anything after </action>."""

ALFWORLD_TEMPLATE_NO_HIS = """You are an expert agent operating in the ALFRED Embodied Environment.
Your current observation is: {current_observation}
{skill_block}Your admissible actions of the current situation are: [{admissible_actions}].

{action_protocol_reminder}
"""

ALFWORLD_TEMPLATE = """You are an expert agent operating in the ALFRED Embodied Environment. Your task is to: {task_description}
{skill_block}Prior to this step, you have already taken {step_count} step(s). Below are the most recent {history_length} observations and the corresponding actions you took: {action_history}
You are now at step {current_step} and your current observation is: {current_observation}
Your admissible actions of the current situation are: [{admissible_actions}].

{action_protocol_reminder}
"""

SKILL_KNOWLEDGE_HEADER = (
    "\n\n## Skill Knowledge\n"
    "Below is a skill document with learned strategies. "
    "Use these guidelines to inform your decisions:\n\n"
)

TASK_ANCHOR = "Your task is to: "


def _skill_block(skill: SkillView | None) -> str:
    """Render the retrieved-experience slot of a template.

    Empty when there is nothing to inject, so vanilla prompts stay byte-identical
    to the templates above.
    """
    if skill is None or not skill.body:
        return ""
    return f"\n{skill.body}\n\n"


@dataclass(frozen=True)
class SkillView:
    """A skill rendered for one episode.

    ``prefix`` is prepended to every user message (skillopt/trace2skill style);
    ``body`` is embedded in the template via {skill_block} (skillrl style).
    Methods use exactly one of the two.
    """

    prefix: str = ""
    body: str = ""


def extract_task_description(initial_observation: str) -> str:
    start = initial_observation.find(TASK_ANCHOR)
    if start == -1:
        return initial_observation.strip()
    return initial_observation[start + len(TASK_ANCHOR):].strip()


def format_admissible_actions(commands) -> str:
    return "\n ".join(f"'{c}'" for c in commands if c != "help")


def build_user_prompt(
    observation: str,
    admissible_commands,
    *,
    skill: SkillView | None = None,
    task_description: str = "",
    history: list[tuple[str, str]] | None = None,
    history_length: int = 2,
) -> str:
    """Build one user message.

    ``history`` is a list of (observation, action) pairs from previous steps.
    With no history the no-history template is used, matching step 0 of the
    SkillRL/SkillOpt env managers.

    ``skill.prefix`` (skillopt/trace2skill) is prepended to the finished message;
    ``skill.body`` (skillrl) is injected through the template's ``{skill_block}``
    slot, which sits *before* the state/action block -- directly after the task
    line, as in SkillRL's own ``ALFWORLD_TEMPLATE_WITH_MEMORY``.
    """
    actions = format_admissible_actions(admissible_commands)
    history = list(history or [])
    recent = history[-history_length:] if history_length > 0 else []
    block = _skill_block(skill)
    if not recent:
        prompt = ALFWORLD_TEMPLATE_NO_HIS.format(
            current_observation=observation,
            admissible_actions=actions,
            skill_block=block,
            action_protocol_reminder=ACTION_PROTOCOL_REMINDER,
        )
    else:
        # Mirror SkillRL's own rendering (agent_system/memory/memory.py:88-97):
        # one bracketed record per step, with the observation and the action of
        # that step sharing the step's *absolute* number. The previous version
        # emitted two lines numbered from 1, so at step 40 the history read
        # "Obs 1 / Action 1" and could not be correlated with the absolute step
        # count quoted on the following line.
        start = len(history) - len(recent)
        memory = "\n".join(
            f"[Observation {start + i + 1}: '{obs}', Action {start + i + 1}: '{action}']"
            for i, (obs, action) in enumerate(recent)
        )
        prompt = ALFWORLD_TEMPLATE.format(
            task_description=task_description,
            step_count=len(history),
            history_length=len(recent),
            action_history=memory,
            current_step=len(history) + 1,
            current_observation=observation,
            admissible_actions=actions,
            skill_block=block,
            action_protocol_reminder=ACTION_PROTOCOL_REMINDER,
        )

    if skill is not None and skill.prefix:
        return skill.prefix + "\n" + prompt
    return prompt
