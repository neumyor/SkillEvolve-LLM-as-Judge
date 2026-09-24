#!/usr/bin/env bash
# ALFWorld paper-caliber gate comparison: official 39/18/134 split.
# batch_size 40 over 39 train games => exactly one update per epoch, so with
# 4 epochs there are 4 gate decisions per condition -- a small number, which is
# itself the finding (the ALFWorld gate sees very few candidates).
# Only evaluation.gate_mode differs between conditions.
#
# Each condition runs its own full train + all three test evaluations
# (baseline / best / final) on valid_unseen=134, which is what makes the
# scores comparable to the existing SkillOpt ALFWorld number (82.09%).
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT/packages/skillopt"
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
export QWEN_CHAT_BASE_URL="$CFG" QWEN_CHAT_API_KEY="$KEY" QWEN_CHAT_MODEL="$MODEL"
export QWEN_CHAT_MAX_TOKENS=16384 QWEN_CHAT_TEMPERATURE=0
export PYTHONPATH="$ROOT/packages/skillopt"
LOGS="$ROOT/experiments/judgestudy"
PYTHON="${SKILLOPT_PYTHON:-$ROOT/packages/skillopt/.venv-alfworld/bin/python}"
[ -x "$PYTHON" ] || PYTHON="$(command -v python3)"

run_one() {
  local name="$1"; shift
  local out="$LOGS/aw_$name"
  rm -rf "$out"
  "$PYTHON" scripts/train.py \
    --config configs/alfworld/judge_gate.yaml \
    --cfg-options model.backend=qwen_chat model.optimizer_backend=qwen_chat model.target_backend=qwen_chat \
    --optimizer_model "$MODEL" --target_model "$MODEL" \
    --split_dir data/alfworld_path_split --train_size 39 --num_epochs 4 \
    --batch_size 40 --lr_scheduler constant --edit_budget 4 \
    --use_slow_update false --use_meta_skill false --eval_test true \
    --workers 12 --max_api_workers 12 --analyst_workers 8 \
    --gate_mode "$name" \
    --judge_full_validation_audit false \
    --out_root "$out" > "$LOGS/logs/aw_$name.log" 2>&1
  echo "[aw_$name] exit=$? at $(date +%H:%M:%S)"
}

run_one judge &
run_one greedy &
run_one rollout &
wait
echo "=== aw all three conditions finished at $(date +%H:%M:%S) ==="
