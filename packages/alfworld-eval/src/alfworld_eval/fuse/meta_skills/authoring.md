# FUSE Skill Authoring (ALFWorld)

Author one complete skill document for one ALFWorld task-type family. The document you write is injected into every user message of future episodes of this task type under a "## Skill Knowledge" header, so it must be a self-contained, transferable operating guide — not a patch, not a changelog, and not a bundle of per-episode notes.

Read the evidence in this order:

1. `members.jsonl` — every member incident with outcome, capability tags, and summary;
2. `clusters.json` — capability clusters over all incidents (context for which capabilities this family shares);
3. `parent/skill.md` — the current baseline skill (treat as the default content to preserve);
4. `meta_skill/SKILL.md` — this file;
5. every `incidents/<id>/` — `instruction.md`, `trajectory.jsonl`, and, for failures, `diagnosis.md`. Trajectories are large: read them per file, and only as many as you need to ground each edit.

Write the complete final document to `result/skill.md` with the write tool. That file is the only required output.

## Evidence and generalization constraints

- Every `add`, `replace`, or `delete` you make relative to the parent must be supported by evidence: a specific failure trajectory or diagnosis, or a successful member's behavior worth encoding. Do not rewrite text merely for style, length, ordering, or apparent completeness.
- Successful members are positive examples: behaviors they exhibit are default preservation constraints. Do not remove a parent rule or successful behavior unless direct contradictory evidence exists.
- Separate the shared family procedure from episode-specific facts. Never write rules keyed to incident ids, gamefile paths, trial names, specific receptacle layouts, or one-off object names. Concrete objects may appear as *examples*, clearly marked as such, not as rules.
- Prefer rewriting an existing rule over appending a special case; keep the document focused and incremental relative to the parent.
- If this family has no failure evidence, encode the reusable successful SOP and its verification practice, and state what is preserved from the parent.
- If diagnosis and trajectory disagree, the trajectory is primary evidence and the diagnosis is a hypothesis to verify.

## Document requirements

- Plain Markdown, English only. No YAML frontmatter (the harness injects the raw text into the episode prompt).
- Address the agent directly ("Check each receptacle ...", "Before placing, ..."), organized by phase of the episode: understanding the task, locating objects, the type-specific transformation (heat / cool / clean / examine), carrying and placing, and verifying completion.
- Include the reusable procedure, the key decision points, common failure modes observed in the evidence, and concrete verification steps before finishing.
- Stay within the character budget stated in `protocol.json` (`max_skill_chars`); the document is re-sent in every prompt of every episode, so length is a direct cost.
- Do not mention rewards, verifiers, success rates, this pipeline, or the existence of the evidence workspaces. The document is written for an agent that only sees the environment, its task, and this text.
