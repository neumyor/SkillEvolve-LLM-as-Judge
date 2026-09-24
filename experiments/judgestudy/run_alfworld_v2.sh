#!/usr/bin/env bash
# ALFWorld with the repaired judge (prompt variant v2), same stream as
# tmp/judgestudy/run_alfworld.sh so the v1/v2 comparison is apples-to-apples.
#
# Round 1 (v1) on this stream: the judge accepted 4/4 candidates whose own train
# window had dropped 0.795 -> 0.769, including one that measurably regressed on
# the held-out 18-game selection set (0.8333 < 0.8889). The regression test
# rejected all four.
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

rm -rf "$LOGS/aw_judge_v2"
"$PYTHON" scripts/train.py \
  --config configs/alfworld/judge_gate.yaml \
  --cfg-options model.backend=qwen_chat model.optimizer_backend=qwen_chat model.target_backend=qwen_chat \
  --optimizer_model "$MODEL" --target_model "$MODEL" \
  --split_dir data/alfworld_path_split --train_size 39 --num_epochs 4 \
  --batch_size 40 --lr_scheduler constant --edit_budget 4 \
  --use_slow_update false --use_meta_skill false --eval_test true \
  --workers 12 --max_api_workers 12 --analyst_workers 8 \
  --gate_mode judge --judge_prompt_variant v2 \
  --judge_full_validation_audit false \
  --out_root "$LOGS/aw_judge_v2" > "$LOGS/logs/aw_judge_v2.log" 2>&1
echo "[aw_judge_v2] exit=$? at $(date +%H:%M:%S)"
