#!/usr/bin/env bash
# SearchQA paper-caliber gate comparison at K=40 (the original cadence:
# batch_size 40 x accumulation 1 => one update per 40 tasks, 10 updates).
# Only evaluation.gate_mode differs between the three conditions.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT/packages/skillopt"
CONFIG="${JUDGE_CONFIG:-$ROOT/benchmark/llm_config.local.json}"
[ -f "$CONFIG" ] || CONFIG="$ROOT/benchmark/llm_config.example.json"
JUDGE_BASE_URL="${JUDGE_BASE_URL:-$(python3 -c "import json; print(json.load(open('$CONFIG'))['searchqa-eval']['base_url'])")}" 
JUDGE_MODEL="${JUDGE_MODEL:-$(python3 -c "import json; print(json.load(open('$CONFIG'))['searchqa-eval']['model'])")}" 
JUDGE_API_KEY="${JUDGE_API_KEY:-$(python3 -c "import json; print(json.load(open('$CONFIG'))['searchqa-eval']['api_key'])")}" 
CFG="$JUDGE_BASE_URL"
KEY="$JUDGE_API_KEY"
MODEL="$JUDGE_MODEL"
export QWEN_CHAT_BASE_URL="$CFG" QWEN_CHAT_API_KEY="$KEY" QWEN_CHAT_MODEL="$MODEL"
export QWEN_CHAT_MAX_TOKENS=16384 QWEN_CHAT_TEMPERATURE=0
export PYTHONPATH="$ROOT/packages/skillopt"
SPLIT="$ROOT/packages/skillopt/data/searchqa_split"
LOGS="$ROOT/experiments/judgestudy"
PYTHON="${SKILLOPT_PYTHON:-$ROOT/packages/skillopt/.venv/bin/python}"
[ -x "$PYTHON" ] || PYTHON="$(command -v python3)"

run_one() {
  local name="$1"; shift
  local out="$LOGS/sq_k40_$name"
  rm -rf "$out"
  "$PYTHON" scripts/train.py \
    --config configs/searchqa/judge_gate.yaml \
    --cfg-options model.backend=qwen_chat model.optimizer_backend=qwen_chat model.target_backend=qwen_chat \
    --optimizer_model "$MODEL" --target_model "$MODEL" \
    --split_dir "$SPLIT" --train_size 400 --num_epochs 1 \
    --batch_size 40 --lr_scheduler constant --edit_budget 4 \
    --use_slow_update false --use_meta_skill false --eval_test true \
    --workers 48 --analyst_workers 32 --shuffle_train_items true \
    --gate_mode "$name" \
    --judge_full_validation_audit false \
    --out_root "$out" > "$LOGS/logs/sq_k40_$name.log" 2>&1
  echo "[sq_k40_$name] exit=$? at $(date +%H:%M:%S)"
}

run_one judge &
run_one greedy &
run_one rollout &
wait
echo "=== sq_k40 all three conditions finished at $(date +%H:%M:%S) ==="
