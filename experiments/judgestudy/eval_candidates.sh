#!/usr/bin/env bash
# Evaluate every gate candidate on the SearchQA test split, individually.
#
# Why this is the decisive experiment for prompt attribution: the aggregate
# test score of a gate condition only says where the trajectory ended up. It
# cannot say whether the judge's individual ACCEPTs were justified. Under a
# regression test that question is answered by construction (a candidate was
# only adopted if it beat the current skill on held-out data), so the adoption
# path is monotone by definition. A judge gives up that guarantee, and the only
# way to see whether it matters is to measure each accepted candidate's true
# test accuracy after the fact.
#
# Output: one run dir per candidate under $OUT/<condition>_step<NN>/.
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
export CAND_KEY="$KEY"
OUT="$ROOT/experiments/judgestudy/candidates"
PYTHON="${SEARCHQA_PYTHON:-$ROOT/packages/searchqa-eval/.venv/bin/python}"
[ -x "$PYTHON" ] || PYTHON="$(command -v python3)"
mkdir -p "$OUT"

eval_one() {
  local cond="$1" step="$2" skill="$3"
  local name="${cond}_step${step}"
  [ -f "$OUT/$name/summary.json" ] && { echo "[$name] cached"; return 0; }
  "$PYTHON" scripts/run_unified_eval.py --method skillopt --backend api \
    --base-url "$CFG" --model "$MODEL" --api-key-env CAND_KEY \
    --temperature 0 --seed 42 --max-tokens 16384 \
    --items data/searchqa_split/test/items.json --workers 24 \
    --skill "$skill" --out "$OUT/$name" > "$ROOT/experiments/judgestudy/logs/cand_$name.log" 2>&1
  echo "[$name] exit=$? $(python3 -c "
import json;d=json.load(open('$OUT/$name/summary.json'));print('em=%.4f'%d['summary']['em'])" 2>/dev/null)"
}

for cond in judge rollout greedy; do
  for step in $(seq 1 10); do
    skill=$(printf '%s/sq_k40_%s/steps/step_%04d/candidate_skill.md' "$ROOT/experiments/judgestudy" "$cond" "$step")
    [ -f "$skill" ] || continue
    eval_one "$cond" "$step" "$skill"
  done
done
echo "=== all candidate evaluations finished at $(date +%H:%M:%S) ==="
