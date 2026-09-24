# FUSE Capability Tagging (ALFWorld)

Tag the atomic capabilities an ALFWorld episode's *task* requires, from its public evidence. Read `instruction.md` (the episode's initial observation with the task description) and `current/trajectory.jsonl` (the agent's step-by-step reasoning, actions, admissible action lists, and environment feedback). When `diagnosis.md` is present you may read it, but tags describe the task, not one run's failure.

Write the result to `result/tags.json` with the write tool, in this exact shape:

```json
{
  "schema_version": 1,
  "incident_id": "<the incident id from protocol.json>",
  "outcome": "<success or failure, from protocol.json>",
  "capability_tags": ["..."],
  "capability_summary": "..."
}
```

## Completion Contract

The host reads only `result/tags.json`; a final reply is not a delivery. Use the `write_file` tool before ending. `incident_id` and `outcome` must be copied from `protocol.json` verbatim. The host validates the JSON and rejects payloads whose tags are empty or whose summary is missing.

## Tagging rules

- Tag the capabilities the task contract requires, not the events of this trajectory. Success and failure episodes of the same task must be able to receive the same tags.
- Each tag expresses one atomic capability: something with an independently constructible input, an execution goal, and a completion criterion. Examples of the right grain: "locate a target object by systematically checking receptacles", "heat an object with the correct appliance (microwave)", "verify the carried object matches the task target before placing it".
- Do not merge an ordered procedure, parallel requirements, or a local repair into one tag; split them.
- Tags must be stated as concrete actions with observable results. A state, a resource, or a context alone is not a capability.
- Causal stories, specific object names from this episode, receptacle names, room names, step numbers, and commands are explanation material only — never tags.
- The number of tags is decided by what the task requires; do not pad or truncate.

`capability_summary` is one or two sentences describing what completing this task's deliverable requires, in transferable terms.
