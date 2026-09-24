# RethinkSkill failure and recovery policy

This policy applies to the baseline and Judge arms on SearchQA and ALFWorld.
The frozen train/validation/test selections, official training and optimizer,
gate semantics, and final best-skill test remain unchanged. Failed tasks are
never removed from a denominator or silently scored zero.

| Failure | Current pass | Next pass |
| --- | --- | --- |
| HTTP 408/409/425/429/5xx, timeout, transport error, malformed provider envelope | Record the failed task and unknown usage if the provider supplied none; official evaluation is invalid | Retry that request; replay successful requests from the durable journal |
| ALFWorld process/open/step error or parallel task exception | Record the task as invalid; continue already submitted siblings | Recreate the isolated episode, replay successful model steps, retry the interrupted boundary |
| Judge transport error or incomplete decision JSON | Charge every attempt; Judge evolution is invalid after its bounded local attempts | Retry the decision with the same training evidence; invalid replies are not cached |
| Optimizer output that violates the official strict JSON schema | Keep the official invalid-proposal result for this pass; do not interpret fences or repair the text | Repeat the identical optimizer request in the next bounded pass; malformed replies are not cached |
| HTTP 4xx outside the transient set, optimizer contract error, changed inputs/source | Stop without final-test selection | No automatic retry; inspect the cause |
| Completed run with failed evidence audit, hash mismatch, missing proof, or score inconsistency | Quarantine the run | No automatic retry or result-table entry |
| Missing summary after a non-signal child exit | Mark the pass incomplete | Recover within the same finite pass budget |
| Child terminated by signal | Preserve all artifacts and request attempts | Do not restart automatically in the same supervisor; an explicit relaunch may recover |

The full supervisor permits three passes per setting by default. Passes wait
15 then 30 seconds plus a stable 0-3 second per-setting offset. Worker ceilings
halve on each recovery pass. The default ALFWorld ceiling is 8 (configurable
up to 64); SearchQA starts at 64. All four settings share a conservative
24-request-per-minute channel limiter. A 429 halves its rate, with a minimum
of four per minute, and imposes a 60-second cooldown across all settings.
Only the worker count may decrease on resume. Successful model requests are keyed by the exact rendered
task, skill, attachments, executor manifest, timeout, and workspace position.
They are reused when the official artifact tree is reconstructed. A failed
request is never treated as a cached answer. A request interrupted between send
and durable response is recorded with unknown token usage.

`<campaign>/<setting>.status.json` records the recovery pass, worker count,
failure category, audit errors, and pending task IDs. `completion.json` is the
four-setting terminal status. `replacement_cost.json` includes all known
replacement-request tokens, including failed attempts, and retains
`usage_complete=false` when a provider omitted usage. Savings must not be
claimed as exact in that case.

Relaunch the same supervisor command with the same root, preflight, model, and
recovery policy after an interrupted process. The supervisor follows its child
PID and the per-run output lock; it will not start a second writer while that
child is alive. A run that exhausted its pass budget remains invalid. Raising
the budget requires a newly registered campaign, not silent extra attempts.

Old campaigns whose implementation hashes differ from the current code cannot
be resumed in place. Keep them as failed evidence. A new full campaign requires
fresh four-arm real-API preflight with the current source and a 50-step ALFWorld
budget, followed by the preregistered input/control and audit checks.
