# ALFWorld Environment Correction

The RethinkSkill ALFWorld experiments are stopped at the user's request.
The previous runs used the vendored installed-ALFWorld factory and are not
results for the newly required workspace benchmark environment. Do not resume
them under the corrected environment or pool their scores with new runs.

## Authoritative Environment

The required repository is the workspace-root `benchmark/alfworld-eval`,
not `repos/JudgeGateStudy/packages/alfworld-eval` and not a directory under
`repos/JudgeGateStudy/benchmark`.

The corrected adapter uses its `.venv/bin/python`, `.data/alfworld`,
`configs/rethinkskill_official.yaml`, and `src/alfworld_eval/env.py::AlfworldTextEnv`.
The config matches the official RethinkSkill DAgger settings. For each episode,
the worker points the dataset and logic fields at that task's verifier assets,
matching the official factory's effective configuration. The bridge also removes
`help` from admissible actions, as the official RethinkSkill adapter does.
Module location, interpreter, configuration, dependency lock and source hashes
are persisted. Missing files or a different data root are errors, with no
fallback to the vendored environment. Old environment runs cannot resume.

RethinkSkill still owns training, feedback filtering, proposal, action protocol
and gate decisions. This adapter does not call the benchmark's unified agent
or introduce its one-shot action correction/fallback rules. Environment reset,
step, observations and success flags are owned by the workspace benchmark.
Both arms share this same boundary. Judge evolution still executes no validation.

## Concurrency

The benchmark's `scripts/run_eval_concurrent.py` uses process-level shards;
its `AlfredTWEnv(batch_size=1)` is never shared between threads.
The RethinkSkill bridge follows that isolation boundary with a dedicated
environment subprocess for every active episode. Parent task workers retain
model calls and token journals; environment subprocesses receive no model keys.
Each episode's actions are sequential. Closing an episode joins its exact PID.

The full launcher now defaults to a maximum of 64 ALFWorld task workers.
Actual occupancy is bounded by the selected task count: at most 39 training,
18 validation, and 64 final-test episodes. Aggregate request load across both
arms can exceed 64; the endpoint must be checked before another full run.
Two-process correctness checks do not certify endpoint throughput at 64.

Environment workers return structured failures on exceptions or pipe timeouts;
the parent does not convert an environment crash into success. Target and
optimizer requests are attempted once, as in the official provider. HTTP 500,
timeouts and transport errors invalidate the native evaluation. Ordered final
results and receipts remain in the native evaluator.

## Verification

Run the real-environment tests with the authoritative benchmark Python and
`RETHINKSKILL_ALFWORLD_ASSET_ROOT` pointing at its `.data/alfworld`.
The tests compare identical action sequences in serial and concurrent processes,
and compare one real episode against the official environment adapter. They
exercise both study arms and verify native audit, token accounting, environment
provenance and process cleanup without API costs.

No full ALFWorld experiment is restarted by this correction.
