# FUSE Diagnostic (ALFWorld)

Treat every usable failed public trajectory as an opportunity to evolve the current reusable skill document. Read the public inputs in this order: `instruction.md`, `current/trajectory.jsonl`, and `current/skill.md` (the skill that was injected into every prompt of this episode). Do not infer facts from hidden tests, rewards, verifier output, or files that are not in the workspace.

Write a Markdown diagnosis to `result/diagnosis.md` with the write tool. Its first non-empty line must be exactly one of:

```text
Decision: evolve
Decision: no_change
Decision: inconclusive
```

## Completion Contract

The host reads only `result/diagnosis.md`; text in a final assistant reply is discarded. Before ending the session, use the `write_file` tool to save the complete diagnosis at that exact path. Do not merely say that you will write it. A session that does not create this file is incomplete.

The remaining Markdown is free-form. Use the following method and include the headings that materially help explain the decision.

## Method

1. Reconstruct the public task contract: the task description in `instruction.md` (after "Your task is to:"), the room and receptacle layout it implies, the 50-step budget, and the action protocol (reason in ```...```, commit one admissible action in `<action>...</action>` each step).
2. Find candidate errors. An error needs both a **wrong commitment** (a non-hedged plan, claim, or binding action) and a **violated reference** visible at that point — the admissible action list, the environment feedback, or the task description. Quote both. Do not treat reasonable exploration (opening containers to find an object) or a first guess made before contrary evidence was available as an error.
3. For each serious candidate, state its phase (`plan`, `reason`, `act`, `observe`, or `verify`) and reference source (`task`, `history`, `intra-step`, or `environment`). Group repetitions, retries, and downstream symptoms that violate the same concrete object into one error chain.
4. Trace the chain: was it cleanly repaired, repaired only after costly wasted effort, still active in the terminal state, or unrelated to the final failure? The earliest local error is not automatically the root cause.
5. Select the earliest decisive origin among terminal-relevant candidates. Ask: with a correct decision at this step, would the trajectory plausibly have returned to success? Do not select a later step that only repeats or exposes an earlier mistake.
6. Make an **operational skill attribution**. Attribute the failure to the focused, reusable skill-document change that could most plausibly prevent, detect, recover from, or limit the observed error, even when the public trajectory does not prove the skill caused the failure. Classify the intervention as a wrong rule, missing safeguard, bad template, wrong trigger, conflicting rules, or a new reusable procedure. This is a counterfactual improvement hypothesis for candidate generation, not a claim of observed causal responsibility.
7. Separate outcome reasoning into `Observed Contract` (what the environment and task description establish), `Derived Invariants` (e.g. an object must be *heated* before it is placed; examine-then-use; navigate by checking receptacles one at a time), `Unverified Hypotheses`, and a `Public Validation Plan` (how a corrected trajectory would verify each invariant).
8. Before recommending a skill edit, apply a generality test: name another plausible episode class of the same task type that could benefit, mark this as an unverified transfer hypothesis, prefer rewriting an existing rule over appending a special case, and keep the proposed change focused. Only claim regression safety when public passing evidence exists.

For every usable failed trajectory, use `Decision: evolve`. Emitting `Decision: no_change` for a usable failed trajectory is a protocol failure. The diagnosis must state the observed evidence separately from the operational attribution, then give a focused candidate-change brief. Do not use `Decision: no_change` because the failure was caused by the environment, an inadmissible action that the harness corrected, or because the current skill is empty or generic. An empty or generic skill is an evolvable skill: attribute the failure to its missing reusable procedure, safeguard, trigger, or verification rule and propose that addition. Use `Decision: inconclusive` only when the public inputs are missing, malformed, internally unusable, or the session cannot complete; it is not an abstention option for uncertainty about real-world causality.

Suggested outline:

```markdown
Decision: evolve

# Failure Summary
# Critical Error
# Error Lifecycle
# Observed Evidence
# Operational Skill Attribution
# Outcome Hypotheses
# Transfer Hypothesis
# Evolution Brief
```
