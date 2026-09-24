#!/usr/bin/env bash
# Trace2Skill with the judge verifier (SearchQA).
#
# The train rollout and the workspaces already exist (400 items, 96 failures),
# so only the analyst loop is re-run -- that is the layer being replaced:
# evaluate_output now consults a judging agent instead of scoring the corrected
# answer against gold. Consolidation then produces a skill from whatever the
# judge admitted, and that skill is evaluated on the full 1400-item test split
# with the existing harness.
#
# Baselines for comparison (already on disk):
#   - replay verifier  : outputs/trace2skill_searchqa/, test EM 80.86
#   - no skill         : outputs/vanilla_test/,          test EM 76.93
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT/packages/searchqa-eval"
CONFIG="${JUDGE_CONFIG:-$ROOT/benchmark/llm_config.local.json}"
[ -f "$CONFIG" ] || CONFIG="$ROOT/benchmark/llm_config.example.json"
JUDGE_BASE_URL="${JUDGE_BASE_URL:-$(python3 -c "import json; print(json.load(open('$CONFIG'))['searchqa-eval']['base_url'])")}" 
JUDGE_MODEL="${JUDGE_MODEL:-$(python3 -c "import json; print(json.load(open('$CONFIG'))['searchqa-eval']['model'])")}" 
JUDGE_API_KEY="${JUDGE_API_KEY:-$(python3 -c "import json; print(json.load(open('$CONFIG'))['searchqa-eval']['api_key'])")}" 
CFG="$JUDGE_BASE_URL"
KEY="$JUDGE_API_KEY"
MODEL="$JUDGE_MODEL"
export OPENAI_BASE_URL="$CFG" OPENAI_API_KEY="$KEY" OPENAI_MODEL="$MODEL"
export TRACE2SKILL_BASE_URL="$CFG" TRACE2SKILL_API_KEY="$KEY" TRACE2SKILL_MODEL="$MODEL"
export PYTHONPATH="$ROOT/packages/searchqa-eval/src"
LOGS="$ROOT/experiments/judgestudy"
WORK="$LOGS/t2s_sq_judge"
TRACE2SKILL_TRAIN_RUN_DIR="${TRACE2SKILL_TRAIN_RUN_DIR:-$ROOT/packages/searchqa-eval/outputs/trace2skill_searchqa/train_run}"
PYTHON="${SEARCHQA_PYTHON:-$ROOT/packages/searchqa-eval/.venv/bin/python}"
[ -x "$PYTHON" ] || PYTHON="$(command -v python3)"

COMMON="--base-url $CFG --model $MODEL --api-key $KEY \
  --train-items data/searchqa_split/train/items.json \
  --val-items data/searchqa_split/val/items.json \
  --test-items data/searchqa_split/test/items.json \
  --train-run-dir "$TRACE2SKILL_TRAIN_RUN_DIR" \
  --skip-train --work-dir $WORK --verifier judge --skip-eval"

echo "[$(date +%H:%M:%S)] analysis: 96 failures through the judge (16 shards)"
for i in $(seq 0 15); do
  "$PYTHON" scripts/run_trace2skill.py $COMMON --skip-prepare --skip-consolidate \
      --analysis-shards 16 --analysis-shard-index $i \
      > "$LOGS/logs/t2s_sq_judge_shard$i.log" 2>&1 &
done
wait
echo "[$(date +%H:%M:%S)] consolidation"
"$PYTHON" scripts/run_trace2skill.py $COMMON --skip-prepare --skip-analysis \
    > "$LOGS/logs/t2s_sq_judge_consolidate.log" 2>&1
echo "[sq_t2s_judge] exit=$? at $(date +%H:%M:%S)"
ls -la "$WORK"/*.md 2>/dev/null
