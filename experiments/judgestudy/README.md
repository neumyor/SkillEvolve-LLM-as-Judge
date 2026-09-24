# judge-gate study artifacts

Three experiments, all on the same model (`qwen3.6-flash-distill`) with the
judge reusing the optimizer's backend.

## Layout

The assembled repository tracks source, split manifests and the study snapshot.
Virtualenvs and caches remain machine-local. Network runs read
`benchmark/llm_config.local.json` when present, or the credential-free example.
The public snapshot replaces provider URLs in historical logs and metadata with
`https://redacted.invalid/v1`; that placeholder is not a runnable endpoint.
Configure your own endpoint before reproducing a run. These artifacts use an
older protocol and are not evidence for the current four-method comparison.

| Path | What it is |
|---|---|
| `run_searchqa_K40.sh` | SkillOpt, SearchQA K=40, all three gate conditions |
| `run_alfworld.sh` | SkillOpt, ALFWorld official 39/18/134, 4 epochs, all three conditions |
| `run_searchqa_K40_v2.sh` | SearchQA with the repaired judge (`--judge_prompt_variant v2`) |
| `run_t2s_searchqa_judge.sh` | Trace2Skill, SearchQA: analyst's verifier swapped to the judge |
| `run_t2s_alfworld_judge.sh` | Trace2Skill, ALFWorld: same swap |
| `mirror_workspaces.py` | Copy existing Trace2Skill workspaces, clearing the replay verdicts |
| `eval_candidates.sh` | Evaluate every gate candidate individually on the test split |
| `analysis/audit_gates.py` | Per-decision gate audit across conditions |
| `analysis/paired.py` | Paired bootstrap CI + exact McNemar (`--id-key`/`--score-key` for ALFWorld) |

## Directory naming

| Directory | Condition |
|---|---|
| `sq_k40_rollout` / `aw_rollout` | C0: held-out regression test (the paper gate) |
| `sq_k40_judge` / `aw_judge` | C1: judge gate, prompt v1 |
| `sq_k40_judge_v2` | C1': judge gate, repaired prompt v2 |
| `sq_k40_judge_v2_deadlock` | **First v2 attempt, discarded.** The growth rule deadlocked: the SearchQA seed skill is a 104-char placeholder, so `max_growth_ratio 1.5` permitted 156 chars and every real candidate (2.2-3.1k) was rejected — forever, since nothing accepted means the baseline never grows. Fixed by `judge_min_growth_floor`. Kept as evidence that the rule needed a floor. |
| `sq_k40_greedy` / `aw_greedy` | C2: no gate (accept everything) |
| `candidates/` | One test-split evaluation per candidate skill, for every condition |
| `t2s_sq_judge/`, `t2s_aw_judge/` | Trace2Skill produced with the judge verifier |

## Gotchas found while building this

1. **A growth rule needs a floor.** See `sq_k40_judge_v2_deadlock`. Any ratio
   threshold applied to a placeholder skill is unsatisfiable.
2. **ALFWorld results use different column names.** SearchQA rows have
   `id`/`hard`; ALFWorld rows have `gamefile`/`success`. `analysis/paired.py`
   takes `--id-key gamefile --score-key success` for ALFWorld. Using the
   defaults silently compares nothing and reports 0.0000 vs 0.0000.
3. **Environment noise exceeds the effects being measured.** Same skill, same
   1400-item list, `temperature=0`: 56-83 items flip between two evaluations
   (0.7-1.4pp, one pair at p=0.023). ALFWorld: 3-4 games out of 134 (2.2-3.0pp)
   across both this study's repeated baselines and the earlier FUSE repeats.
   Compare conditions only against that band.
4. **`--test_env_num` is not a shard count.** ALFWorld selection-set rollouts
   run as 4 chunks of ~3 games; raising `max_api_workers` above ~24 does not
   help because ALFWorld's rollout is step-synchronous (a batch advances one
   step per API round), so wall time is dominated by the slowest episode.
5. **Trace2Skill judge tooling needs the endpoint in the subprocess env.**
   `judge_episode.py`/`judge_answer.py` run as their own process and read
   `TRACE2SKILL_BASE_URL` / `_MODEL` / `_API_KEY`; `run_trace2skill.py` passes
   them from its own arguments via `_judge_env`. Without that the judge reports
   "TRACE2SKILL_BASE_URL / TRACE2SKILL_MODEL are not set" and every item fails
   closed.
6. **A judge with no comparative quantity accepts everything.** Measured, not
   predicted: v1 accepted 14/14 at confidence=high. The repair (v2) is in
   `repos/SkillOptETE/skillopt/evaluation/judge_gate.py`; both prompts are kept
   there so the comparison stays reproducible.
