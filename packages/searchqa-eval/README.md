# Unified Single-Turn SearchQA Evaluation

面向 **SkillOpt / Trace2Skill** 所用的单轮 SearchQA benchmark 的统一评测环境。
协议逐字对齐 SkillOpt 实现（`repos/pulled/SkillOpt/skillopt/envs/searchqa/`），
保证结果可直接与其论文 Table 1（GPT-5.5 direct chat: EM 87.3）校对。

## 方法矩阵

| 方法 | Skill 来源 | 注入方式 |
|------|-----------|---------|
| `vanilla` | 无 | 纯基座模型 |
| `skillopt` | `src/searchqa_eval/skills_docs/skillopt_searchqa.md`（官方发布 skill） | system prompt 的 `## Skill` 段 |
| `trace2skill` | `src/searchqa_eval/skills_docs/trace2skill_searchqa.md`（由下节全流程生成的产物；重新生成时覆盖） | 同 skillopt |

SkillRL 的 Search 评测是另一套多轮交互式检索（Search-R1 体系），不在本环境中。

## 快速开始

```bash
cd packages/searchqa-eval
uv sync                      # 安装评测依赖
uv sync --group materialize  # 如需物化数据（下载 HF 数据集）

# 1) 物化全部 split（train 400 / val 200 / test 1400，首次需联网）
uv run --group materialize python scripts/materialize_split.py --splits train val test

# 2) 冒烟测试（无需网络，mock agent）
uv run python scripts/run_unified_eval.py --method skillopt --backend mock --limit 5

# 3) 正式评测：OpenAI 兼容 API（vLLM 等）
uv run python scripts/run_unified_eval.py --method skillopt --backend api \
    --base-url http://127.0.0.1:8000/v1 --model Qwen/Qwen2.5-7B-Instruct
```

## 评测协议（对齐 SkillOpt 源码）

- **数据**：`lucadiliello/searchqa`（Jeopardy! 风格问答 + 搜索片段 context），
  SkillOpt 官方 ID 清单切分：train 400 / val 200 / **test 1400**
- **System prompt**：`You are an expert question answering agent.` + `## Skill` 段 +
  任务/答案格式说明（逐字复刻 `prompts/rollout_system.md`）
- **User prompt**：`## Context`（**6000 字符、按 `[DOC]` 边界截断**）+ `## Question`
- **答案抽取**：`<answer>...</answer>` 标签（缺失回退最后一行）
- **指标**：SQuAD 归一化后 **EM（hard）/ F1（soft）/ sub_EM**

## 输出

`outputs/unified_<method>_<时间戳>/`：
- `results.jsonl` — 逐题 `{id, em, f1, sub_em, predicted_answer, gold_answers, ...}`
- `summary.json` — 总 EM/F1/sub_EM、用量、元信息

`results.jsonl` 按 id 去重，中断后重跑同一 `--out` 目录即自动续跑。
注意：失败行也算"已完成"——整批失败（如忘配 key）后原地重跑会被跳过，
需先清空该目录再跑，详见「实跑踩过的坑」第 3 条。
`--limit N` 可先跑子集验证链路。

## Trace2Skill：rollout、skill 生成与评测全流程

Trace2Skill 从执行轨迹蒸馏 skill（**rollout → 验证式分析 → 无冲突合并**），官方未发布
SearchQA skill——正式对比必须跑本节全流程自行生成；用现成文档直接 `--method trace2skill`
评测只是可选的复现路径（见本节末尾）。管线五阶段（对齐 alfworld-eval 实现）：

1. **train rollout**：弱种子 skill（`skills_docs/trace2skill_seed_searchqa.md`）跑 train 400 题，
   `--record-response` 保留原始回复；
2. **工作区构建**：每题生成 `agent_log.md + agent_work/{input,output,gold}.json`
   （agent 视角与金标准分文件）；
3. **验证式分析**（可分片并行）：失败题由工具调用式错误分析家诊断，必须写出
   `output_fixed.json` 并让 `verify_answer`（复用 harness 同一份打分代码）报出 PASS
   才计入；成功题蒸馏成功记忆（`--analyst-mode combined`，默认）；
4. **归纳整合**：通过验证门的 failure/success memory 合并为 skill 文档；
5. **评测**：生成 skill 注入 `## Skill` 段，先 val 200（选择）再 test 1400（报告数）。

### 正式跑法（warmup + 四步，多路并发）

```bash
cd packages/searchqa-eval
BASE="$SEARCHQA_BASE_URL"; MODEL="$SEARCHQA_MODEL"   # 见 benchmark/llm_config.local.json
export T2S_KEY=sk-...            # warmup 与直评命令经 --api-key-env 读这个环境变量

# 0) warmup：冷启动的并发请求会被网关 429，先逐级压测确定可用并发（实测 64 全绿）
uv run python scripts/warmup_endpoint.py --base-url $BASE --model $MODEL \
    --api-key-env T2S_KEY --ramp 1,2,4,8,16,32,64 --out outputs/warmup.json

# 1) rollout + 工作区：种子 skill 跑 train 400 题（64 workers，约 1 分钟）
uv run python scripts/run_trace2skill.py --base-url $BASE --model $MODEL \
    --api-key $T2S_KEY --workers 64 \
    --skip-analysis --skip-consolidate --skip-eval --work-dir outputs/trace2skill_searchqa

# 2) 验证式分析（最慢环节，分片并行）：32 进程各分析 400/32 题（约 6 分钟）
mkdir -p outputs/trace2skill_searchqa/logs
for i in $(seq 0 31); do
  uv run python scripts/run_trace2skill.py --base-url $BASE --model $MODEL \
    --api-key $T2S_KEY \
    --skip-train --skip-prepare --skip-consolidate --skip-eval \
    --analysis-shards 32 --analysis-shard-index $i \
    --work-dir outputs/trace2skill_searchqa \
    > outputs/trace2skill_searchqa/logs/shard_$i.log 2>&1 &
  sleep 0.5                       # 错峰启动
done; wait

# 3+4) 归纳 + 评测：合并记忆为 skill，随后 val 200 + test 1400（约 4 分钟）
uv run python scripts/run_trace2skill.py --base-url $BASE --model $MODEL \
    --api-key $T2S_KEY --workers 64 \
    --skip-train --skip-prepare --skip-analysis --work-dir outputs/trace2skill_searchqa
```

产物在 `outputs/trace2skill_searchqa/`：`train_run/`（rollout）、`analysis_workspaces/`
（逐题工作区 + `analyst_transcript.json`）、`analysis_summary.json`（验证门统计）、
`trace2skill_searchqa.md`（生成 skill）、`val_run/` 与 `test_run/`（正式评测）。
生成满意后把它复制到 `src/searchqa_eval/skills_docs/trace2skill_searchqa.md`
（本仓库已装入一版 qwen3.6-flash-distill 的产物）。注意 `run_trace2skill.py` 不带
skip 旗标也能一条命令跑完，但分析阶段是单进程串行，400 题会很慢——正式跑按上面分阶段。

无端点接线自检：`uv run python scripts/run_trace2skill.py --backend mock --limit 5
--skip-analysis --skip-eval`（mock rollout + 回退整合，不发任何 LLM 请求）。

### 实测参考（qwen3.6-flash-distill，64 并发）

warmup ~40 s（1→64 每级 429 率 0，中位延迟 ~2 s）；rollout 400 题 ~40 s（seed EM 0.760）；
分析 32 shard ~6 min（**验证门 96/96 全过** + 304 条成功分析 → 1,086 条记忆）；归纳 ~30 s
（→ 3,498 字符 skill）；val+test ~3 min。全程零 429、零 API 失败。test 1400 题配对结果：
vanilla 0.7693 / seed 0.7879 / **生成 0.8086 EM**（vs vanilla +3.93，McNemar p≈2e-07；
vs seed +2.07，p≈3e-03）。

### SkillOpt 官方 skill 实测（warmup 至 100 并发）

`--method skillopt`（`skills_docs/skillopt_searchqa.md`，sha256 与上游 `ckpt/searchqa/gpt5.5_skill.md`
一致）：warmup 1→100 每级 429 率 0 后，val 200 @64 workers 28 s、test 1400 @**100 workers** 4 m 51 s，
零 agent 失败。test 1400：**EM 0.8121** / F1 0.8907 / sub_EM 0.9229（vs vanilla +4.29，McNemar
p≈2.6e-09；vs T2S 生成 skill +0.36，p≈0.66 打平）。与论文 Table 1 的对比及口径差异见
`docs/reports/searchqa_qwen36_skillopt_eval.md`。

### 实跑踩过的坑（检查与修复方案）

1. **不 warmup 直接开高并发 → 网关 429**。修复：先跑 `scripts/warmup_endpoint.py`
   （自 alfworld 移植）逐级压测；探活阶段 401/404 会立即失败退出，坏 key/错模型名
   在第一步就暴露，而不是 1400 题逐题发现。
2. **`--api-key-env` 只是环境变量名**：忘了 `export` 时没有任何前置报错，整批题
   全部 `agent_failed`（EM=0、usage 全 0）。检查：任何跑完的 run 先看 `summary.json`
   的 `agent_failed` 是否为 0，非 0 先查配置再怀疑模型。
3. **整批失败后原地重跑会被"续跑"跳过**：`results.jsonl` 按 id 去重续跑，失败行也算
   已完成，同目录重跑会秒完成并复用失败结果。修复：`rm outputs/<run>/results.jsonl
   outputs/<run>/summary.json` 后重跑，或换 `--out` 新目录。坑 2+3 会连环出现：
   忘 key → 全失败 → 重跑"秒完成"但分数仍为 0。

### 可选快速路径：直接用已生成的 skill 复现

```bash
uv run python scripts/run_unified_eval.py --method trace2skill --backend api \
    --base-url $BASE --model $MODEL --api-key-env T2S_KEY --workers 64 \
    --items data/searchqa_split/test/items.json --out outputs/unified_trace2skill_test
```

这只复现已安装的文档；换模型/换种子重新生成 skill 时必须跑全流程并用新产物覆盖
`skills_docs/trace2skill_searchqa.md`，否则评测的是旧文档。

## 已知限制

- Trace2Skill 官方未发布 SearchQA skill；`skills_docs/trace2skill_searchqa.md` 为本环境
  管线生成物，重新生成时按上节流程覆盖。
- 材料化脚本依赖 HuggingFace 网络访问；离线环境可自备 `items.json`
  （字段：`id, question, context, answers`）。
