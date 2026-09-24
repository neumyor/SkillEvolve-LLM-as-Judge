# SkillEvolve: LLM as Judge

Can an LLM judge replace the expensive re-execution used to accept or reject a proposed skill, while using fewer tokens and preserving final task performance? This repository tests that question on **SkillOpt, GEPA, SkillGen, and RethinkSkill** with **SearchQA** and **ALFWorld**. It contains the method adapters, shared judge, benchmark harnesses, paired-run tools, audits, and historical evidence.

The intervention is narrow: both arms use the same method-specific training, feedback, and proposal path. The `baseline` arm keeps the method's original candidate-verification decision; the `judge` arm makes that decision from the proposed change and **already collected training evidence**, without executing the candidate on verification tasks. After selection is frozen, an independent test run measures performance in both arms. Test results never feed back into acceptance. Per-candidate full-validation audit is off in judge mode.

This is an experimental implementation, not a claim that judging is cheaper or equally accurate. Only completed, audited paired runs with complete usage records support a token-savings estimate. Earlier experiments that used different replacement boundaries or failed audits are retained for diagnosis and must not be pooled with the current protocol.

## What is replaced

| Method | Original acceptance path | Judge path |
| --- | --- | --- |
| SkillOpt | Selection rollouts, including initial and enabled slow-update selection gates | Judge reads the current and candidate skills, patch, and existing training attempts; no selection rollout for acceptance |
| GEPA | Candidate minibatch comparison and search-time validation after a proposal | Judge replaces those decisions; a local `predicted_changes` field supplies the candidate-pool ordering that GEPA needs |
| SkillGen | Verification executes the proposed skill and scores repairs versus regressions | Judge uses the already collected baseline traces and proposal; the original refinement/stop behavior remains |
| RethinkSkill | Seed and candidate validation inform its hard/soft gate and best-skill choice | Judge predicts the local hard/soft decision from existing training feedback; no candidate validation execution |

Method-specific training executions required to **create** a proposal remain. Judge decisions are predictions, not measured validation scores. The shared prompt, evidence selection, parsing, retry budget, and version registry live in [`packages/skillopt/skillopt/evaluation/`](packages/skillopt/skillopt/evaluation/); method-specific output fields stay in their adapters. `v3` is the current default; `v1` and `v2` remain available for explicitly labeled historical comparisons. See the [adapter protocol](docs/judge_adapters.md) and [RethinkSkill execution-chain audit](docs/rethinkskill_judge_v2.md) for the exact boundaries.

## Repository layout

| Path | Purpose |
| --- | --- |
| [`scripts/run_method.py`](scripts/run_method.py) | Common `--method`, `--mode`, model, judge-version, and output interface |
| [`packages/skillopt`](packages/skillopt), [`packages/gepa`](packages/gepa), [`packages/skillgen`](packages/skillgen), [`packages/rethinkskill`](packages/rethinkskill) | Method implementations and local adaptations |
| [`packages/rethinkskill_study`](packages/rethinkskill_study) | RethinkSkill benchmark binding, durable request journal, and run audit |
| [`packages/searchqa-eval`](packages/searchqa-eval), [`packages/alfworld-eval`](packages/alfworld-eval) | Benchmark harnesses and data interfaces |
| [`configs`](configs) | GEPA and SkillGen run configurations; SkillOpt configs are under its package |
| [`scripts/check_rethinkskill_pair.py`](scripts/check_rethinkskill_pair.py), [`scripts/run_rethinkskill_full.py`](scripts/run_rethinkskill_full.py) | Four-arm RethinkSkill preflight and gated full-run supervisor |
| [`scripts/compare_replacement_tokens.py`](scripts/compare_replacement_tokens.py) | Cost comparison for an audited baseline/Judge pair |
| [`experiments/judgestudy`](experiments/judgestudy), [`docs/reports`](docs/reports) | Historical artifacts and reports; read their protocol and validity notes before using numbers |

The four source packages are separate Python projects with different dependencies. The checkout also contains local experiment directories; **a directory name is not evidence that its run completed or passed audit**. Trace2Skill source and old results remain for historical reference, but it is not one of the four methods exposed by the current common runner.

## Prerequisites

- Python environments for the selected method and benchmark. The launcher uses `packages/skillopt/.venv` for SearchQA, method-specific ALFWorld environments, and the configured **external** ALFWorld benchmark's `.venv` for RethinkSkill. Install each package's dependencies in its own environment before running it.
- SearchQA and ALFWorld split manifests under `packages/skillopt/data/`. RethinkSkill on ALFWorld requires the separate `benchmark/alfworld-eval` checkout with `src/alfworld_eval/env.py`, `configs/rethinkskill_official.yaml`, `pyproject.toml`, `uv.lock`, `.venv/bin/python`, and game data in `.data/alfworld/`. The data root must contain `json_2.1.1/` and `logic/`. See the [environment correction](docs/alfworld_environment_correction.md).
- An OpenAI-compatible inference endpoint, model, and credentials. A models-list response alone is not a service health check: send a real generation request before a costly run.

Copy [`benchmark/llm_config.example.json`](benchmark/llm_config.example.json) to the Git-ignored `benchmark/llm_config.local.json`, then fill these fields:

```bash
cp benchmark/llm_config.example.json benchmark/llm_config.local.json
```

| Field | Required value |
| --- | --- |
| `alfworld_benchmark_root` | Absolute path to the external `benchmark/alfworld-eval` checkout; a path relative to this repository also works |
| `default.base_url`, `default.model` | OpenAI-compatible API base URL and model for the general campaign |
| `searchqa-eval` and `alfworld-eval` sections | Endpoint, model, and API key for each benchmark; paired runs must use the same section within a benchmark |
| `api_key` | Your own key; it is never versioned. `OPENAI_API_KEY` may be used instead when supported by the launcher |

The example contains no working endpoint, key, or machine path. `ALFWORLD_BENCHMARK_ROOT` can override the configured benchmark root for a particular process. Keep the override identical for a paired run and its resume. Direct `run_method.py` calls can also receive `--model` and `--base-url` explicitly; use environment variables for credentials so they do not appear in shell history.

Run commands from the repository root. First inspect the resolved command without sending model requests:

```bash
python scripts/run_method.py --method skillopt --benchmark searchqa --mode judge \
  --config packages/skillopt/configs/searchqa/judge_gate.yaml \
  --model YOUR_MODEL --base-url YOUR_ENDPOINT --output-dir outputs/skillopt_judge \
  --dry-run
```

Use the same frozen input selection, model settings, seed, and method budget for each baseline/Judge pair. Change only `--mode` and its output directory. Examples of the four entry points follow; add `--dry-run` for the first invocation of each configuration.

```bash
python scripts/run_method.py --method skillopt --benchmark searchqa --mode baseline \
  --config packages/skillopt/configs/searchqa/judge_gate.yaml --output-dir outputs/skillopt_baseline
python scripts/run_method.py --method gepa --benchmark searchqa --mode judge \
  --config configs/gepa/searchqa.json --output-dir outputs/gepa_judge
python scripts/run_method.py --method skillgen --benchmark searchqa --mode judge \
  --skillgen-config configs/skillgen/qwen_campaign.yaml --output-dir outputs/skillgen_judge
python scripts/run_method.py --method rethinkskill --benchmark searchqa --mode judge \
  --model YOUR_MODEL --base-url YOUR_ENDPOINT --output-dir outputs/rethinkskill_judge
```

Pass method-specific flags after `--`; use `--judge-prompt-variant v3` and optionally `--judge-model MODEL` to pin a judge version/model. The common runner defaults to `judge`, so always pass `--mode` explicitly in paired experiments. Do not use `--full-validation-audit` in judge mode: the runner rejects it. The examples show the interface, not a preregistered paired campaign; each method's complete data and budget settings must be frozen in its run plan.

For the current RethinkSkill campaign, use [`scripts/check_rethinkskill_pair.py`](scripts/check_rethinkskill_pair.py) on two train cases plus one validation and test case per benchmark, inspect all four `*.status.json` files and `verification.json`, then use [`scripts/run_rethinkskill_full.py`](scripts/run_rethinkskill_full.py) with the **same model, channel limit, and passing preflight root**. The full supervisor refuses missing audits, changed source, and mismatched paired inputs. Both tools support bounded recovery; see the [failure and resume policy](docs/rethinkskill_recovery.md). Do not start a full or expensive run until the [repository rules](AGENTS.md) and their referenced parent-workspace preflight checklist pass.

## Measures and audit

The primary performance comparison uses paired final-test task outcomes from frozen outputs. The cost comparison includes **only** baseline model tokens spent on the re-executions being replaced and judge-model tokens spent on decisions. Training, proposal generation, analysis, and final test are outside that cost measure. The arms may make different numbers of proposals because their acceptance decisions can differ; do not force equal actual rounds or interpret this as whole-run token savings.

Each run writes `replacement_cost.json` and individual `usage_events.jsonl` events. Compare a completed, matching pair with:

```bash
python scripts/compare_replacement_tokens.py \
  --baseline outputs/skillopt_baseline --judge outputs/skillopt_judge \
  --output outputs/skillopt_token_comparison.json
```

The report separates prompt and completion tokens and computes `(baseline - judge) / baseline`. Retries with known usage count; cached responses do not create new charges. If the provider omits usage or a request was interrupted after send, `usage_complete=false` and exact savings are **unknown**, not zero. Runs with failed tasks, missing summaries, duplicate work, or audit inconsistencies are invalid for performance comparisons. Preserve their artifacts, repair the cause, and resume only under the same registered inputs and source.

Offline checks, which do not call a model:

```bash
PYTHONPATH=packages/skillopt:packages/gepa/src:packages/gepa:packages/skillgen \
  packages/skillopt/.venv/bin/python -m pytest \
  tests packages/skillopt/tests/test_judge_gate.py \
  packages/skillopt/tests/test_judge_adapters.py \
  packages/skillopt/tests/test_trainer_judge_gate.py -q
```

The [historical report](docs/reports/judge_gate_vs_regression_test.md) documents earlier experiments, including negative findings and failed runs. Its older protocols and withdrawn comparisons do not establish the current four-method claim.
