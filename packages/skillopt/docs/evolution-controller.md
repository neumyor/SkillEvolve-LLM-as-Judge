# Evidence-Triggered Skill Evolution (ETE)

> **SkillOpt decides *how* to evolve a skill. This fork adds a controller
> that decides *when there is enough evidence* to invoke that evolution
> process.**

Existing skill-evolution frameworks drive skill updates on a **fixed
schedule**: every `batch_size` rollouts (or every epoch), the optimizer runs
unconditionally. This treats *update frequency* as a hyperparameter and
ignores a key property of the evidence itself: **different stages of
training accumulate evidence at very different rates** — a burst of novel
systematic failures makes an update urgent, while a stable or noisy regime
makes it wasteful.

ETE makes the update decision **evidence-driven** instead of
count-driven:

- a small **observation batch** of `m` tasks is rolled out and added to an
  **evidence buffer**;
- an independent **Evolution Controller Agent** inspects the current skill,
  its own persistent **evidence state** (suspected deficiencies, supporting
  and counter evidence, unresolved uncertainty) and compact evidence cards
  for the new executions (task, outcome, score, evaluator feedback,
  trajectory excerpt);
- the controller answers exactly one question with one bit:

  ```
  (M_t, a_t) = C(S_t, M_{t-1}, e_t),    a_t ∈ { WAIT, UPDATE }
  ```

- on `WAIT` nothing happens — no reflect, no candidate, no validation;
  on `UPDATE` the **original, untouched SkillOpt optimizer** runs over
  *everything accumulated since the previous attempt* (B_t = the whole
  evidence window), and the buffer + controller state reset afterwards —
  regardless of whether the validation gate accepts or rejects the
  candidate.

One cycle:

```
evidence accumulation  →  evolution attempt  →  reset
```

Because the update window is exactly "everything since the last attempt",
a single WAIT/UPDATE decision simultaneously produces **adaptive update
frequency** *and* **adaptive evidence amount** — no fixed batch size for
the optimizer, no second agent that selects training examples.

## What changed relative to upstream SkillOpt

| Component | Status |
|---|---|
| Rollout (env adapters) | unchanged |
| Reflect (analysts, minibatching) | unchanged |
| Aggregate (hierarchical merge) | unchanged |
| Select (edit budget / ranking) | unchanged |
| Update (patch application) | unchanged |
| Validation gate + rollback | unchanged |
| Epoch-level slow update / meta skill | unchanged (zero-attempt epochs now handled) |
| **When reflect→…→gate is invoked** | **replaced by an `EvolutionPolicy`** |

The original fixed schedule is preserved byte-for-byte as
`evolution.mode: fixed` (the default): the legacy loop runs untouched, and
the extracted `_run_evolution_attempt` closure (stages ②–⑥) is shared
verbatim by both the legacy loop and the evidence-triggered loop, so
*every* scheduling strategy — baselines and ours — differs **only** in the
policy that decides WAIT/UPDATE.

## The Evolution Controller Agent

`skillopt/evolution_controller.py` implements:

| Policy | Behaviour |
|---|---|
| `ImmediatePolicy` | UPDATE after every observation batch (per-`m`-tasks schedule) |
| `FixedKPolicy` | UPDATE after every K observation batches (window = K·m tasks; `m=batch_size, K=1` reproduces the upstream schedule) |
| `EndPolicy` | WAIT during the epoch, UPDATE at the epoch boundary (per-epoch schedule) |
| `LLMEvidencePolicy` | **ours** — the Evolution Controller Agent |

All policies implement the same interface, so the trainer is identical
across baselines and our method:

```python
class EvolutionPolicy:
    def initial_state(self) -> dict: ...
    def observe(
        self,
        skill: str,                     # current skill document
        new_results: list[dict],        # new rollout results (evidence cards)
        evidence_state: dict,           # the policy's own M_{t-1}
        *,
        epoch_end: bool = False,        # epoch-boundary consult
        rollout_dir: str | None = None, # where trajectories live
        context: dict | None = None,    # bookkeeping (never load-bearing)
    ) -> EvolutionDecision:             # .action ∈ {WAIT, UPDATE}, .state, .reason
```

### Design decisions (deliberate)

- **The controller never decides *how*.** It does not write patches, does
  not select which buffered tasks the optimizer sees (the window is always
  *everything* buffered), and does not touch the gate. This keeps the
  experimental isolation clean: only *timing* differs between conditions.
- **No numeric thresholds.** The controller prompt contains four semantic
  judgement principles (recurring? attributable to the skill? contradicted
  by successful cases? generalizably fixable?) — there is no
  "update if failure rate > x" and no confidence number. Fixed-schedule
  baselines count observation *batches*; the LLM policy reasons over the
  *content* of the evidence.
- **Persistent semantic evidence state.** The controller maintains a short
  natural-language belief state `M_t` (hypotheses with supporting /
  counter cases and an "unresolved" note), persisted across observations
  through `evolution_state.json` — not a memory system, a few hundred
  tokens.
- **Same model as the optimizer, different agent.** The controller reuses
  the optimizer backend via `chat_optimizer` (stage
  `evolution_controller` for token accounting) with its own system prompt,
  state and responsibility — so improvements cannot be attributed to a
  stronger model. Swap the controller model later with the same
  optimizer/backend configuration knobs.
- **Reset after every attempt (accept *or* reject).** The controller judged
  the evidence "worth an attempt"; whether the candidate was good is the
  optimizer + gate's business. Keeping the buffer after a rejection would
  re-trigger immediately and conflate the two decisions.
- **Buffers are skill-homogeneous.** If the skill changes under the buffer
  (e.g. an epoch-end slow update), the buffered evidence is stale — it was
  collected under a different document — so the trainer drops it and resets
  the controller state (logged as `[evolution] skill changed since the
  buffer started`).

### The "Score Controller" ablation

`evolution.controller_view: score` strips the controller's prompt down to
per-task outcome/score rows and cumulative window counts — no skill, no
task content, no evaluator feedback, no trajectory, no semantic state. It
is still an LLM judge deciding WAIT/UPDATE, but purely over *quantities*.
If the semantic controller beats it (especially under noisy or
contradictory evidence), adaptive timing demonstrably requires reasoning
over the **content** of the evidence, not just its failure statistics —
the standard "why not a failure-rate threshold?" objection, answered
experimentally.

## Configuration

All options live under the `evolution:` config section (defaults in
`configs/_base_/default.yaml`):

```yaml
evolution:
  mode: fixed                  # fixed | immediate | fixed_k | end | controller
  observation_batch_size: 4    # m: tasks per observation batch
  fixed_k: 1                   # K: observation batches per window (fixed_k)
  controller_view: semantic    # semantic | score (controller mode)
  controller_max_observation_chars: 1200   # per-task trajectory excerpt budget
  controller_max_state_chars: 4000         # evidence-state clip
  controller_max_parse_retries: 2          # controller JSON retries → fallback WAIT
  controller_max_completion_tokens: 4096
  max_buffer_observations: 0   # safety valve: force attempt after N obs (0=off)
```

CLI equivalents: `--evolution_mode`, `--observation_batch_size`,
`--evolution_fixed_k`, `--evolution_controller_view`,
`--evolution_max_buffer_observations`, or
`--cfg-options evolution.mode=controller`.

Example config: [`configs/searchqa/controller.yaml`](../configs/searchqa/controller.yaml).

```bash
# ours (evidence-triggered)
python scripts/train.py --config configs/searchqa/controller.yaml

# fixed-K baseline over the same observation stream (40-task windows)
python scripts/train.py --config configs/searchqa/default.yaml \
    --evolution_mode fixed_k --observation_batch_size 4 --evolution_fixed_k 10

# per-epoch baseline
python scripts/train.py --config configs/searchqa/default.yaml \
    --evolution_mode end --observation_batch_size 4
```

Notes:

- **Observation frequency is fixed and fine-grained; evolution frequency is
  adaptive.** `m` only fixes how often the controller *looks*, not how
  often it updates. For the main experiments use m=1 or m=4 and add the
  small robustness ablation m ∈ {1, 4, 8}.
- **`observation_batch_size` replaces the optimizer's `batch_size`** in
  evolution modes: the optimizer's window is the whole evidence buffer, so
  no fixed batch size is imposed on it. `train.batch_size` is still used as
  the *reference cadence* when estimating the edit-budget scheduler horizon
  for `controller` mode (an estimate only — see below).
- **Edit-budget decay interacts with update frequency.** Decay schedulers
  (`cosine`, `linear`) assume a fixed number of steps. Under evidence-
  triggered scheduling the attempt count is unknown, so for controlled
  comparisons use `optimizer.lr_scheduler: constant` (identical edit
  budget per attempt across all scheduling conditions).
- With the default `use_slow_update: true`, the epoch-end slow update
  modifies the skill between epochs; any still-buffered evidence from the
  previous epoch is then stale and is dropped (see "skill-homogeneous
  buffers" above). Disable slow updates to let windows span epochs.

## Artifacts

| Path | Content |
|---|---|
| `evolution_decisions.jsonl` | **one line per consult** — observation index, epoch, action, reason, evidence state, buffer sizes, skill hash. This is the data source for the update-timeline figure. |
| `evolution_state.json` | crash-safe stream state: buffer manifest, controller state, pending decision, counters. Written after *every* observation and decision. |
| `observations/obs_XXXXX/` | one directory per observation: `rollout/` (per-task predictions, `results.jsonl`), `obs_results.json` (trainer snapshot), `patches/` (reflect output at attempt time) |
| `steps/step_XXXX/` | one directory per **evolution attempt** (the original layout: merged patch, ranked edits, candidate skill, selection eval, step record with the `evolution` window metadata) |
| `summary.json` → `evolution` | totals, trigger intervals (`[{step, epoch, trigger, observations, tasks, action}]`), leftover buffer |

## Resume / crash safety

- The observation stream is the unit of crash safety: state is flushed
  after every observation + decision, and rollout adapters resume their own
  per-task artifacts, so a resume never re-rolls a completed observation
  and never re-consults a decided one.
- An `UPDATE` decision is persisted *before* the attempt runs; a crash
  between the two replays the attempt deterministically on resume.
- A crash after the attempt completed but before the cycle reset is
  reconciled against `runtime_state.json` (`last_completed_step`) — the
  stale pending cycle is discarded, never double-run.

## Validation performed

- Unit tests: `tests/test_evolution_controller.py`,
  `tests/test_evolution_config.py`
- Trainer integration (real trainer, fake env, no LLM):
  `tests/test_trainer_evolution_mode.py` — window semantics, cycle reset on
  accept *and* reject, all-WAIT never invoking the optimizer, epoch-boundary
  consults, stale-buffer drops, resume (stream replay, pending-UPDATE
  execution, pending-already-completed reconciliation), fixed-mode
  equivalence with `accumulation > 1`.
- Offline end-to-end smoke (real SearchQA env + real reflect/merge/rank +
  real controller LLM calls against a mock OpenAI-compatible server):
  `scripts/dev/smoke_test_evolution.py` — all five modes plus resume.
- The full upstream test suite (1497 tests) passes unchanged; in `fixed`
  mode the trainer's behaviour and step artifacts are unchanged (the
  extracted attempt body was diffed line-by-line against the original).

## Real-run findings on ALFWorld (qwen3.6-flash-distill) — including a negative result

Three conditions were run on an **identical regime-ordered stream** (24 real
train games, `train.shuffle_train_items=false`, one task family per m=4
observation: look_at -> pick_and_place -> heat -> cool -> clean -> two_obj;
val 12 / test 12, both family-stratified). Only the WAIT/UPDATE policy differed.

| | controller (ours) | fixed_k K=3 | end |
|---|---|---|---|
| attempts | **0** | 2 | 1 |
| gate outcomes | — | reject, reject | reject |
| val baseline (S_0) | 10/12 | 11/12 | 11/12 |
| test baseline → final | 0.750 → 0.667 | 0.750 → 0.750 | 0.750 → 0.833 |
| tokens | 3.27M (controller 33k = 1.0%) | 4.08M | 3.56M |

**All three runs finished with the byte-identical skill** (sha256
`01bd29e825b8` = the initial skill, verified across `skills/` and
`best_skill.md`). Every attempt was rejected by the validation gate, so the
test-score spread is **evaluation noise on the same skill**, not a method
difference.

Why nothing was accepted — and why this setup cannot discriminate policies:

1. **No headroom.** The initial skill already scores 11/12 on the 12-game
   val set, and the gate requires *strict* improvement, so a candidate has to
   score a perfect 12/12. Our candidates tied (0.9167) or lost (0.750).
2. **The gate signal is noise-limited at n=12.** The same initial skill on the
   same 12 val games scored 10/12 in one run and 11/12 in another. That
   one-game swing is larger than the effect we are trying to measure.
3. **The failures may not be skill-fixable here.** The dominant failure mode
   is exhausting the 50-step budget (see below). The optimizer proposed
   plausible rules — "systematic surface search", "assume separate locations",
   "skip redundant examination" — and val did not move. On this model these
   read as capability limits rather than knowledge gaps.

Two further findings worth recording:

- **The controller never triggered, even with coherent same-family evidence.**
  Observations 4/5/6 were each a single family with 2/4 successes and two
  50-step timeouts apiece, yet every consult returned WAIT ("appear isolated
  and potentially explainable by object aliasing"); its evidence state stayed
  anchored on the task type seen in observation 1. An earlier hypothesis that
  the controller merely needed same-family repetition is therefore **refuted**.
  Its demonstrated weakness is over-conservatism / state anchoring.
- **The 50-step timeouts are model behaviour, not a pipeline bug.** The
  registered eval environment (`benchmark/alfworld-eval`) — its own code path,
  same model, same skill, same 50-step cap, same `history_length=2` — fails on
  exactly the same games with exactly 50 steps each (verified on a 12-game
  overlap), and hits the cap on 24/134 (18%) of its own test games. Real
  trajectories show the agent cycling among a few locations and never covering
  the room (one episode found the target object at step 49 on a table it had
  walked past 12 times).

Implications for experiment design (all three are needed before the timing
claim can be tested at all):

1. **Create headroom**: start from a weaker/blank initial skill and/or a val
   set that reflects real difficulty (the reference uses 18 valid_seen games,
   but even that starts at 17/18 for this model).
2. **Make the stream produce a genuine shift**: multi-epoch regime composition
   (e.g. easy families in epoch 1, transform families in epoch 2, composite in
   epoch 3) so both schedules have multiple update opportunities.
3. **Recalibrate or ablate the controller**: the current principles are too
   conservative to fire on this evidence; the score-view ablation and an
   explicit "shared failure signature counts as coherent" instruction are the
   obvious next probes.

## Controller attempt memory (fix for degenerate re-triggering)

The first scaled SearchQA experiment (60-task stream with a known regime shift
at item 21; val 40 mixed, test 100 mixed) finally produced a **valid** test of
the scheduling question — and it did **not** support the claim at the time:

| | controller | fixed_k K=3 | end |
|---|---|---|---|
| attempts (accepted) | 7 (3) | 5 (2) | 1 (1) |
| first update | 28 tasks (1 obs after the shift) | 12 tasks (**in the stable phase — wasted**) | 60 tasks |
| test | 0.540 -> 0.640 | 0.510 -> 0.620 | 0.470 -> 0.600 |
| hard-subset test | 0.250 -> 0.400 | 0.217 -> 0.367 | 0.117 -> 0.333 |
| tokens | 1.89M | 1.53M | 1.01M |

All three improved the skill (gate accepted candidates, hard items +0.15..0.22),
which validated the setup, but their final quality was within the measured
same-skill evaluation noise (±3-4 test items out of 100) while the controller
cost the most.

The decision trace exposed the cause. The controller was **correct** where it
mattered (5x WAIT through the stable phase, then UPDATE one observation after
the shift, naming the real deficiency: "over-specification"), but after the
first attempt it fired at observations 8, 10, 12, 13, 14 and 15 with buffers of
1-2 observations, and 4 of its 7 attempts were rejected. Because the evidence
state and buffer reset after every attempt (by design), the controller **forgot
that it had just attacked the same deficiency and been rejected**; in a
persistent failure regime the same 4-8 task pattern again satisfied its
"sufficient evidence" bar. Adaptive timing thus degenerated into near-immediate
updating and lost the cost advantage it exists to provide.

Fix (now default, `evolution.controller_attempt_memory: true`): every consult
receives a compact history of previous attempts — how many tasks had been
consumed, what defect it targeted, and how validation judged it (with the val
score before/after) — and the system prompt gains a matching principle: if a
previous attempt already targeted the same deficiency and validation rejected
it, WAIT unless the new evidence differs materially. The buffer still resets
(the window is exactly "everything since the last attempt"), so the paper's
`B_t` definition is unchanged; only the controller's memory of *attempts*
persists. `evolution.controller_attempt_memory: false` restores the old
behaviour for a direct ablation.

## Fix verification on the multi-shift stream (v1 -> v2)

The 189-task multi-shift stream (3 × [pass30, fail33], val 100, test 400,
`qwen3.6-flash-distill`) first ran as **v1** (attempt memory only). Its
decision trace exposed three problems; three fixes were implemented and the
**same stream, same split, same seeds** was re-run as v2 (commit `28d612c`):

- **1B/2B (informed attempt memory)** — the attempt log now records what the
  optimizer *actually did* (`candidate_score` + `edits_applied` from the
  ranked edits) and the prompt renders a gate-delta line and the edits per
  prior attempt, plus mechanism-level same-family guidance. v1's memory held
  only the controller's own defect wording, so same-family re-triggers
  escaped via wording drift ("distinct from previous attempts") and the
  controller never saw *why* attempts failed.
- **3a (window de-dilution)** — zero-failure observation batches are dropped
  from attempt windows (and never reflected). v1's first trigger after each
  long stable stretch carried 73-77% success data and its candidate
  *regressed* twice (A7: 44 tasks/23% failures, 759k tokens; A9: 48 tasks,
  847k tokens — both rejected).

Measured v1 -> v2 (identical stream/seeds, only the fixes differ):

| | v1 | v2 |
|---|---|---|
| attempts (accepted / rejected) | 13 (3 / **10**) | **5 (4 / 1)** |
| longest consecutive rejections | 4 (A10-A13 in the last fail regime) | **1** |
| post-stable-shift windows | 44t/23% fail, 48t/23% fail | 8t/75%, 12t/92% (and one 52t/67% — see below) |
| first post-shift candidate | regressed (0.56 vs 0.62) -> rejected | improved (0.57 vs 0.56) -> accepted |
| val (100) | 0.50 -> 0.62 | 0.50 -> **0.64** |
| test hard (400) | 0.4425 -> 0.58 (+13.75) | 0.4325 -> 0.57 (+13.75) |
| attempt tokens | 5.79M (4.2M on rejections) | **2.79M** (0.74M) |
| total tokens | 8.00M | **5.57M (-30%)** |
| attempt wall time | 114 min | **57 min** |
| WAIT reasons citing prior attempts / mechanism | 12/36 | **27/44** |

Quality is preserved within noise (test delta identical at +13.75; val +2)
at **half the update cost** — the adaptive-timing claim now has a positive
result on this benchmark.

Two honest caveats. (1) The obs-12 escape that v1's memory failed to block
was *productive* there (+7 val); the enriched memory now blocks it
(single-point LLM A/B probe: legacy render -> UPDATE, enriched render ->
WAIT). The quality is recovered later instead (v2 A4, a clean 8-task
window, +7 val), so the fix trades early incremental gains for far fewer
wasted attempts. (2) v2's FAIL3 trigger window was 52 tasks (67% failures)
— larger than intended, because the de-dilution filter drops only
*zero-failure* batches, not *stale-failure* ones left over from an earlier
regime that accepted fixes had already addressed. That window was accepted
(+1 val), so no harm here, but the correct filter target is "failures
relevant to the current hypothesis", not "any failure".

## Main comparison on the multi-shift stream (all five conditions)

Same 189-task stream, split, seeds, config, model and gate for every row;
only the timing policy differs. `immediate` (attempt after every 4-task
observation) **is** the original SkillOpt cadence — verified equivalent to
the original fixed loop, and single-observation windows are unaffected by
de-dilution, so its window semantics are the original ones too. Designed
failure regimes: observations 8–16, 24–32, 40–48; same-skill test noise
band measured at 171–177/400 (range 6 items).

| condition | attempts (acc/rej) | worst rej. streak | triggers in stable regimes | trigger lag per fail regime (obs) | val (100) | test delta (items/400) | total tokens | attempt wall |
|---|---|---|---|---|---|---|---|---|
| immediate (= original SkillOpt) | 48 (5/43) | 22 | **24 / 48** | 0, 0, 0 | 0.61 | +37 | 15.85M | 111 min |
| fixed_k K=3 | 16 (5/11) | 5 | **8 / 16** | 1, 0, 2 | 0.62 | +45 | 8.55M | 72 min |
| end | 1 (1/0) | 0 | 1 (epoch end) | —, —, — | 0.58 | +37 | **3.07M** | 27 min |
| controller v1 (memory only) | 13 (3/10) | 9 | 0 / 13 | 1, 2, 0 | 0.62 | **+55** | 8.00M | 114 min |
| **controller v2 (this work)** | **5 (4/1)** | **1** | **0 / 5** | 1, 4, 0 | **0.64** | **+55** | 5.57M | **57 min** |

Readings:

- **v2 dominates every fixed schedule on quality** at a fraction of the
  cost: +55 vs +37 items/400 for the original cadence (18 items, 3× the
  measured noise band) at 35% of its tokens; +55 vs +45 for fixed_k at 65%
  of its tokens.
- **The Pareto frontier is {end, v2}**: end is cheapest (3.07M) but has no
  online adaptation and loses 18 items; v2 keeps the best quality at 5.57M.
- **Trigger timing matches the designed shifts in both controllers**
  (zero triggers in 19 stable observations), but v1 degenerated inside the
  failure regimes (9 consecutive rejections, 114 min of attempts for the
  same +55); the informed memory + de-diluted windows are what make
  adaptive timing *cheaper* than every alternative while keeping the best
  quality.
- Why adaptive beats the original cadence on **quality**, not just cost:
  immediate's five accepted attempts each saw a 4-task window (edits that
  fix four specific items), while v2's accepted windows were 8–52 tasks
  at 50–92% failure density (edits that target a coherent defect family —
  its single largest jump, +7 val, came from one clean 8-task window).


## Paper-scale comparison on the original SearchQA split (K sweep)

The original paper's data spec and calibration (train 400 / val 200 / test 1400
from the released ID split, materialized from the `lucadiliello/searchqa`
dataset; edit_budget 4 = the paper's learning_rate; minibatch 8 / merge 8;
shuffle_train_items on; seed 42; qwen3.6-flash-distill; workers 64). Five
conditions: fixed K ∈ {10, 20, 40, 80} (one observation of K tasks → one
update, i.e. the original cadence `batch_size=K × accumulation=1`), and the
Controller v2 (m=10 observations, evidence-triggered). `use_slow_update` and
`use_meta_skill` on throughout (paper calibration): both are no-ops inside
epoch 1 by design (placeholder injection / skip-first-epoch); at the epoch-2
boundary the slow update performs the real longitudinal comparison and writes
guidance into the final skill. Phase 1 = 1 epoch; phase 2 = the same five
runs resumed into epoch 2 (`num_epochs=2`, identical config).

| condition | P1 attempts | P1 tokens | P1 test | P1+2 attempts | P1+2 tokens | P1+2 test |
|---|---|---|---|---|---|---|
| K=10 | 40 | 46.1M | 0.7936 | 80 | 97.8M | 0.7921 |
| K=20 | 20 | 22.7M | 0.8093 | 40 | 45.0M | 0.8079 |
| K=40 | 10 | 19.0M | 0.8071 | 20 | 39.7M | 0.8036 |
| K=80 | 5 | 15.6M | 0.8229 | 10 | 29.5M | 0.8207 |
| Controller v2 | **5** | **13.3M** | 0.7993 | 14 | 35.5M | 0.7957 |

Test = hard accuracy on the 1400-item test set, final-skill calibration
(includes the epoch-2 slow-update guidance in phase 2). Same-skill baseline
band measured across runs: 0.7621–0.7729 (range 15 items).

Honest reading — a mixed result for the adaptive-timing claim:

- **Quality differences are not resolvable on this distribution.** The
  initial skill already passes ~77% of test; every condition's final delta is
  only +0.02–0.05, and the spread between conditions (~30 items) is about
  twice the same-skill noise band (15 items). No condition is separable at
  this sample size. K=80 nominally scores highest; the controller is within
  the same band.
- **The cost ordering is clear and monotone in K**, and the controller sits
  at or near the cheap end at equal-quality: phase 1 it is the cheapest
  (13.3M, 5 updates); over two epochs it costs 35.5M — 10–62% below K=10/20/40
  but 20% above K=80 (10 updates) — with 14 updates, i.e. its per-update
  cost is the lowest of all conditions.
- **The multi-shift stream remains the discriminating experiment** for the
  quality side of the claim (regime shifts where early adaptation matters);
  the natural distribution saturates all schedules near the same ceiling and
  mainly prices them.

Two engineering findings recorded honestly:

1. **Cross-skill test-cache reuse (fixed).** The rollout resume cache
   (`results.jsonl`) is keyed by item id only. Re-running a completed
   out_root with a larger `num_epochs` re-evaluates nothing — the phase-2
   run silently returned phase-1's cached test predictions (phase-2 test
   scores equalled phase-1's, hard and soft, for every condition). Detected
   via timestamp audit; fixed by deleting the polluted `test_eval*/` caches
   and resuming (training skipped at zero cost, tests re-evaluated). The
   proper fix (key the cache by skill hash) is noted for future work.
2. Baseline test re-evaluation per condition is redundant (~4.6M tokens x5
   for the same init skill) but doubles as the noise-band measurement.

Artifacts: `tmp/ete_real_runs/ps_{k10,k20,k40,k80,v2}/`,
`paper_scale_k_sweep.png`, `paper_scale_rows.json`, analysis in
`tmp/ete_real_runs/analyze_paper_scale.py`.

### Why the controller trails K=80: attempt-level diagnosis

The 2.5pp gap between Controller v2 (0.7957) and K=80 (0.8207) is real, not
evaluation noise — established two ways:

- **Noise calibration.** The same byte-identical init skill was re-evaluated
  on the same 1400 items in all five runs. Pairwise discordance: 59–82 items,
  mean 68.8 (4.9pp), max signed asymmetry 15 items. The v2/K80 signed
  asymmetry is 58 vs 23 = 35 items, above that ceiling.
- **Independent replication.** Both best-on-val skills re-evaluated in fresh
  out_roots (no cache): v2 0.7907 → 0.7929, K=80 0.8200 → 0.8243. The gap
  reproduces (2.93pp → 3.14pp).

Decomposition of the net gain over the init skill (same 1400 items, best-on-val
skills, so the epoch-2 slow block is excluded):

| condition | fixed (init wrong → right) | regressed (init right → wrong) | net |
|---|---|---|---|
| K=80 | 110 / 333 (33.0%) | 29 / 1067 (2.7%) | +81 |
| Controller v2 | 75 / 333 (22.5%) | 35 / 1067 (3.3%) | +40 |

K=80 leads on **both** terms: it repairs half again as many initial failures and
regresses fewer. The controller's deficit is mostly *under-repair*, not damage.

Four mechanism-level causes, in order of evidence strength:

1. **Thin evidence windows (strongest).** The controller's UPDATE windows
   averaged 34 tasks (14 attempts, 470 tasks total) against K=80's fixed 80.
   Four attempts ran on a single 10-task observation, one on 20. Window size is
   the only strong predictor of test accuracy across the five conditions
   (Pearson **+0.771**; inner-skill length −0.571, accepts −0.469, gate calls
   −0.374). Per-edit evidence support: 3.7 tasks/edit and 0.83 failures/edit for
   v2, versus 8.0 and 1.72 for K=80 — v2's evidence density sits between K=20 and
   K=40. Attempts built on 10-task windows were accepted at +1 val item.
2. **The validation gate cannot discriminate at this val size (strongest,
   newly quantified).** The 200-item val set has a 5.9-item standard error, and
   two independent evaluations of the *same* skill differ by 10.8 items on
   average (measured: 8–15 items). Across all five conditions, **26 of 27
   acceptances moved val by less than that noise band** — the only exception is
   K=20's first attempt at +17. The gate is therefore effectively not filtering;
   the controller simply exposes it to more, more varied, and smaller-window
   candidates (14 submissions, 5 of them ≤20-task, vs K=80's 10 submissions of
   80 tasks each).
3. **Evidence discarded by cycle reset.** 330 of the 800 streamed tasks (41%)
   were rolled out but never used as evidence: 220 tasks (22 observations)
   invalidated at the epoch-1 boundary when the slow update's placeholder changed
   the skill hash, 50 tasks dropped by window de-dilution, 60 tasks still in the
   buffer at run end. K=80 discards nothing. The epoch-1 loss is the largest
   single waste: after the last epoch-1 attempt the controller issued 22
   consecutive WAITs (obs 19–40, all reasoning "the same over-specification
   pattern is already tracked"), and all 220 tasks were then thrown away.
4. **A harmful rule that K=80 rejected four times slipped through v2's gate once.**
   This *replaces* an earlier, wrong claim in a previous revision of this
   section. The earlier version said v2 lacked a conflict-resolution clause
   present in K=20/40/80; that was a base-rate error — the clause it cited
   (`Override Brevity Rules When Conflicted`) lives in K=80's epoch-2 **slow
   block** (char 4991, slow block starts at 3687), not in its inner skill, and
   the regression counts had been paired against the *best* skill while the text
   was read from the *final* skill. Corrected, the real finding is sharper:

   Both conditions observed the same failure family (`Pelican`→`Brown pelican`,
   `China`→`The People's Republic of China`, `Isaac Newton`→`Sir Isaac Newton`,
   `Superior`→`Lake Superior`, `Drake`→`Sir Francis Drake`) and both proposed the
   same fix — "preserve the full formal name/title". K=80 proposed it four times
   with 80-task windows and 6–16 supporting failures (steps 3, 6, 7, 10) and the
   gate **rejected every one**, so its skill stayed concise. v2 proposed it once
   (step 2) with a **10-task window and 2 supporting failures** and the gate
   **accepted it as new best**, leaving its inner skill carrying two contradictory
   rule families (`Exact Match Priority`: "do not expand abbreviations, add
   titles..."; `Trivia/Quiz Format`: "preserve it rather than defaulting to a
   surname").

   Honest caveat established by a dedicated fresh-rollout test
   (`replicate_rule_flip.sh`): evaluating v2's step-1 skill (before the flip,
   0.7914) against its step-2 skill (after it, 0.7957) gives a paired net **+6
   items** — inside the ±15 noise band. So this rule is a *symptom* of the small
   window letting a gate-rejected rule through, **not** a demonstrated cause of
   the 2.5pp gap. It is retained here as a mechanism, not as a quantitative
   explanation.

Honest scope of this diagnosis: n = 1 run per condition, so causes 1–4 are
consistent patterns, not established causal claims. Reproduced by fresh-rollout
re-evaluation: the gap itself is real (v2 best-evaluated skill 0.8000 vs K=80's
0.8243, paired asymmetry 34 items > the 15-item noise ceiling), and v2's epoch-2
trajectory is net *harmful* to it (0.8000 → 0.7929 → 0.7850 with the slow block).
The clean way to test the causes is a re-run with a larger `m` (20–40), a gate
threshold above the val noise band, and — only if a repeated-seed test confirms
cause 4 — a conflict-resolution clause forced into the controller's edit space.

Artifacts for this diagnosis: `tmp/ete_real_runs/repl_best/` (independent
re-evaluations), `replicate_v2_vs_k80.sh`, plus the per-attempt
`evolution_decisions.jsonl` and `steps/step_*/{ranked_edits,step_record}.json`.

## Relation to the validation gate (FAQ)

The SkillOpt validation gate is a **post-update** decision ("accept this
candidate?"). The Evolution Controller is a **pre-update** decision ("is
there enough evidence to bother generating a candidate?"). They are
orthogonal and composed: the controller reduces *needless* evolution
attempts; the gate still guards every candidate that is actually produced.

## Paper mapping

- Method: `M_t, a_t = C(S_t, M_{t-1}, e_t)` with `a_t ∈ {WAIT, UPDATE}`;
  on UPDATE, `S_{t+1} = SkillOpt(S_t, B_t)` where `B_t` is everything
  accumulated since the previous attempt.
- Update-timeline figure: `evolution_decisions.jsonl` (per-observation
  online scores + actions) and `summary.json["evolution"]["trigger_intervals"]`.
- Suggested main comparison on ALFWorld: stream the six task-type regimes
  (pick/place → heat/cool/clean → mixed) and show the controller WAITing
  through stable regimes and UPDATEing shortly after a new systematic
  failure regime appears, versus fixed schedules that update on the clock.
