#!/usr/bin/env bash
# Trace2Skill with the judge verifier (ALFWorld).
#
# The 39 train trajectories and their workspaces already exist (28 successes,
# 11 failures), so only the analyst loop is re-run: evaluate_output now asks a
# judging agent whether the repair is justified, instead of replaying the
# sequence in TextWorld. Consolidation then builds a skill from whatever the
# judge admitted, and that skill is evaluated on the full 134-game
# valid_unseen split with the existing harness.
#
# Baselines for comparison (already on disk):
#   - replay verifier : outputs/t2s_full/, valid_unseen 66.42%
#   - SkillOpt skill  : outputs/final_skillopt_test/, valid_unseen 82.09%
#
# The 11 failure workspaces are analysed here. The 12-way shard trick used for
# SearchQA is unnecessary at this size (11 items), so the analyst runs serially.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT/packages/alfworld-eval"
ALFWORLD_DATA="${ALFWORLD_DATA:-$ROOT/packages/alfworld-eval/.data/alfworld}"
export ALFWORLD_DATA
CONFIG="${JUDGE_CONFIG:-$ROOT/benchmark/llm_config.local.json}"
[ -f "$CONFIG" ] || CONFIG="$ROOT/benchmark/llm_config.example.json"
JUDGE_BASE_URL="${JUDGE_BASE_URL:-$(python3 -c "import json; print(json.load(open('$CONFIG'))['alfworld-eval']['base_url'])")}" 
JUDGE_MODEL="${JUDGE_MODEL:-$(python3 -c "import json; print(json.load(open('$CONFIG'))['alfworld-eval']['model'])")}" 
JUDGE_API_KEY="${JUDGE_API_KEY:-$(python3 -c "import json; print(json.load(open('$CONFIG'))['alfworld-eval']['api_key'])")}" 
CFG="$JUDGE_BASE_URL"
KEY="$JUDGE_API_KEY"
MODEL="$JUDGE_MODEL"
export OPENAI_BASE_URL="$CFG" OPENAI_API_KEY="$KEY" OPENAI_MODEL="$MODEL"
export TRACE2SKILL_BASE_URL="$CFG" TRACE2SKILL_API_KEY="$KEY" TRACE2SKILL_MODEL="$MODEL"
LOGS="$ROOT/experiments/judgestudy"
WORK="$LOGS/t2s_aw_judge"
P="$ROOT/packages/skillopt/data/alfworld_path_split"
TRACE2SKILL_TRAIN_RUN_DIR="${TRACE2SKILL_TRAIN_RUN_DIR:-$ROOT/packages/alfworld-eval/outputs/full_t2s_train/merged}"
PYTHON="${ALFWORLD_PYTHON:-$ROOT/packages/alfworld-eval/.venv/bin/python}"
[ -x "$PYTHON" ] || PYTHON="$(command -v python3)"

COMMON="--base-url $CFG --model $MODEL --api-key $KEY \
  --train-items $P/train/items.json \
  --selection-items $P/val/items.json \
  --test-items $P/test/items.json \
  --train-run-dir "$TRACE2SKILL_TRAIN_RUN_DIR" \
  --skip-train --work-dir $WORK --verifier judge --skip-eval"

echo "[$(date +%H:%M:%S)] analysis: 11 failed episodes through the judge"
"$PYTHON" scripts/run_trace2skill.py $COMMON --skip-prepare --skip-consolidate \
    > "$LOGS/logs/t2s_aw_judge_analysis.log" 2>&1
echo "[$(date +%H:%M:%S)] consolidation (exit $?)"
"$PYTHON" scripts/run_trace2skill.py $COMMON --skip-prepare --skip-analysis \
    > "$LOGS/logs/t2s_aw_judge_consolidate.log" 2>&1
echo "[t2s_aw_judge] exit=$? at $(date +%H:%M:%S)"
ls -la "$WORK"/*.md 2>/dev/null
