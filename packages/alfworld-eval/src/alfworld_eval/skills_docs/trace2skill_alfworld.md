# Trace2Skill — ALFWorld Skill Document (placeholder)

Trace2Skill's official repository (`repos/pulled/Trace2Skill`) only ships
released skills for spreadsheet tasks (`trace2skill-xlsx-*`); it does not
include ALFWorld skills. To evaluate Trace2Skill on ALFWorld, generate a skill
document with the Trace2Skill pipeline (distill trajectory-local lessons from
ALFWorld rollouts, then consolidate them) and place the result here as
`trace2skill_alfworld.md`, replacing this placeholder.

Injection protocol: this file's full text is prepended to every user message
under a "## Skill Knowledge" header — identical to how SkillOpt's skill
document is injected (see `repos/pulled/SkillOpt/skillopt/envs/alfworld/rollout.py`,
`_build_skill_prompt`), which is also how the SkillOpt paper ran Trace2Skill
as a baseline.

Until a real document is provided, this placeholder keeps the harness runnable
but contributes no task guidance beyond the note below.

## Task completion guidelines

- Parse the goal into ordered sub-goals: locate the object, acquire it,
  apply any required transformation (clean / heat / cool / examine), then
  deliver it to the requested receptacle.
- Only choose actions from the admissible action list provided each step.
- Track which receptacles have already been searched to avoid loops.
