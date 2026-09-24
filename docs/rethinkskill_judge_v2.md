# RethinkSkill：仅替换验证决策的实现

此前错误 runner 的实验仍然无效；本文件描述重建后的 `rethinkskill_study_v2`，不能据此恢复旧结果。

## 执行链与隔离边界

| 环节 | baseline | Judge | 代码与核对方式 |
|---|---|---|---|
| 数据、seed、provider、轮数、反馈 arm | 同一输入构造 | 同一输入构造 | `rethinkskill_study/runner.py`；seed 冻结前统一 rstrip；三份任务 ID 不相交 |
| 初始 validation | 官方评估 | 不执行 | baseline 计入 seed_validation；Judge 没有伪造初始分数 |
| 当前 skill 执行训练 | 官方 NativeSkillEvaluator | 同一模块 | SearchQA 原生 harness、ALFWorld 官方可选 harness |
| 反馈过滤、历史、提案与校验 | 官方 prepare_evolution_round | 同一函数 | 从官方 round 原样提取训练/提案代码；AST 比较确认内容未变 |
| 非法提案 | 官方失败语义 | 相同 | 不改成正常 noop、不启动 Judge |
| 合法 noop | 不验证候选 | 不调用 Judge | 两组都保存 flat，保留 skill |
| 候选验证 | 官方 validation 与 gate_decision | 共用 JudgeGate 的版本化 prompt | 只用旧训练证据、新旧 skill 和提案理由，无候选执行 |
| current 与 best | 官方 hard/soft 状态 | 局部 hard/soft 定性预测 | 软分救援只更新 current；必要时再与 best 比较 |
| 最终选择 | best | best | 在执行 test 之前写 selection.json，固定 hash |
| 最终 test | 官方 NativeSkillEvaluator | 同一模块 | test 只在独立 final 路径执行，不反馈训练或 gate |
| 成本 | seed_validation + candidate_validation | 所有 llm_judge 请求 | 训练、optimizer、最终 test 不进入 replacement_cost |

`run_method.py --method rethinkskill --benchmark … --mode baseline|judge` 启动两个版本，仍使用统一的 `--judge-prompt-variant` 和 `--judge-model` 接口。ALFWorld 使用工作区 `benchmark/alfworld-eval` 的 venv。`workers` 是同轮独立任务的并发上限。

## Judge 的局部输出扩展

核心提示词沿用四方法共享的 JudgeGate。RethinkSkill 额外要求 `predicted_changes: {hard: -1|0|1, soft: -1|0|1}`，用于保留官方 hard 容差、soft rescue 和 best 选择的区别。这里是**预测分类，不是实测正确率**：hard 的正负分类对应预计超过配置容差；soft 正分类对应预计超过救援阈值。

- Judge 支持净改善且 hard=1：接受 current；若 current 与 best 不同，再比较 candidate 与 best，只在预计 hard 更好时更新 best。
- hard=0 且启用 soft rescue、soft=1、Judge 支持改善：只更新 current，保留 best。
- hard=-1 或 verdict=REJECT：拒绝；其余为 flat。
- noop：没有 Judge 成本。格式错误/调用失败耗尽重试：标记 judge_invalid，不伪装成正常拒绝或完整实验。

第二次 best 比较复用已有训练证据，不执行 best 或 candidate，其 token 同样计入 Judge 成本。接受状态全部由裁判预测驱动，因此可能与官方回测结果不同；这正是待检验的变量。

## 证据和成本

Judge 读取已经落盘的训练题问题、公开任务上下文、模型回复、hard/soft 结果、失败信息；ALFWorld 还读取已执行的动作与观察轨迹。不读取候选执行结果，不读取 val/test 的答案，不将 gold 字段作为 Judge 输入。共用证据压缩器限制卡片数、单卡长度和 skill 长度，保存省略数量；完整输入输出另行落盘。

记录每次目标模型、optimizer 和 Judge 请求的实际 usage；只有验证和 Judge 请求带 replacement_component 标签。解析重试、best 比较都计费。usage 缺失保留 usage_complete=false，不能用占位的 0 汇总宣称节省。最终性能取 test 的 hard；本实现本身不能证明性能不下降。

## 独立检查

- 原样提取的官方训练/提案代码：AST 对照上游。
- 配对行为测试：在一致回复下，两组训练 RenderedTask、optimizer RenderedTask、最终 test RenderedTask 逐项相同。
- 执行计数：baseline 初始 validation、训练、候选 validation、test；Judge 训练、Judge、test。Judge evaluator 主动禁止演化阶段的 val/test 调用。
- 分支：noop、无效提案、接受、拒绝、soft rescue、best 单独比较、解析失败、重试及缺失 usage。
- 成本测试使用已知 usage，验证排除训练/optimizer/test，并完整计入两次裁判及重试。
- 审计验证 baseline 的官方证据；Judge 检查无回测、决策记录、skill 血缘；两组检查冻结选定 skill 与真实 test skill 一致。

运行行为测试：

```sh
PYTHONPATH=packages/skillopt packages/skillopt/.venv/bin/python -m pytest -q \
  tests/test_rethinkskill_study.py tests/test_rethinkskill_official_chain.py \
  tests/test_rethinkskill_integration.py tests/test_direct_campaign.py
```

真实小样本脚本：`scripts/check_rethinkskill_pair.py --root <新目录>`。两题训练、一题 validation、一题 test、一轮；ALFWorld 冒烟明确使用官方 harness 的 max_steps=1 参数，两组相同，正式默认仍为 50；要求真的出现非 noop 候选，否则不将“全 noop”冒烟视为验证 gate 成功。此脚本不启动完整实验。

## 尚不等于完整研究结论

本次最终验证：官方测试 158 passed、1 skipped（发布 Git 清单）；study 与共享 Judge 相关测试 88 passed；真实 ALFWorld 环境的两组完整链路行为测试 1 passed。

四个真实 API 有界冒烟均通过，且全部是非 noop 候选：SearchQA baseline=add/flat、Judge=add/accept_new_best；ALFWorld baseline=replace/flat、Judge=replace/accept_new_best。两组输入数据、seed、模型与轮数等条件、实现源码 hash 一致；两组最终 test 均完成；Judge 解析均成功；replacement usage 均完整。这里只检查链路与计量，不从一题 test 推断性能或报告节省比例。

机器可读逐环节证据：`experiments/rethinkskill_pair_v2_bounded_20260923/chain_verification.json`。其中 baseline 的演化调用严格为 val→train→val，Judge 为 train；最终 test 在单独目录中。更早的 SearchQA 超时与中止的 50 步 ALFWorld 冒烟均保留于 `experiments/rethinkskill_pair_v2_20260923/`，不混入成功记录。

这些检查验证代码干预范围与计量，不证明模型判断正确。正式结论仍需完整独立 test、重复运行和预先固定的性能非劣界限。旧实验不可混入。

## 完整实验运行保障（2026-09-23）

新增 `--resume`：逐次模型请求保存结果与 usage，中断后重建官方执行产物并复用已落盘响应，不重复请求。源码、参数、种子和数据变更会拒绝恢复；完成后的恢复先审计再直接退出。调用已发出但响应未持久化的中断窗口记为未知成本，不能伪造零费用。

当前对齐官方失败语义：HTTP 500、超时、传输错误均保留原始失败并使本轮 native evaluation 无效，不当作零分训练反馈；optimizer 错误仍使提案失败。目标和 optimizer 请求只尝试一次，已发出的请求仍逐次记账。旧实验采用的零分继续和重试规则已废止，不可与当前运行混用。

`scripts/run_rethinkskill_full.py` 在四组真实 API 冒烟通过且源码、配对输入与控制量核对后运行四组完整条件。完整数据、种子、比较指标与源码哈希预先保存在 plan.json；10 轮，ALFWorld 50 步；同轮独立任务的并发上限为 64，四组可同时运行。日志和 supervisor 状态位于各 run 目录外；逐请求、按任务顺序逐题、逐轮落盘，完成后先审计。可恢复故障按预注册的有限轮次和退避策略续跑，成功请求复用；证据审计错误和永久失败停止并保留现场。分类规则见 `docs/rethinkskill_recovery.md`。


## 评估轮内并发（2026-09-24）

新增 `--workers 1..64`。它只并发同一评估轮内彼此独立的 task；结果写入、evidence 和 receipt 汇总仍按原始 task 顺序执行。SearchQA 每题独立；ALFWorld 并发不同 episode，单个 episode 内动作交互仍串行。

ALFWorld 的线程共享环境版本已被真实冒烟否定。按用户要求，现改为工作区根目录 `benchmark/alfworld-eval` 的 Python、配置、数据和 `AlfworldTextEnv`，每个活跃 episode 独立环境子进程。完整实验保持停止。来源、协议边界与验证见 [环境修正说明](alfworld_environment_correction.md)。

并发 task 的失败都会落盘并进入统一调用计数；本轮失败使该条件无效，不进入性能对比。已同时开始的 sibling task 可能完成，因此失败运行的实际请求数可能多于官方串行执行；有效运行的逐题输入、输出顺序及评分语义保持一致。optimizer、Judge 和演化轮次仍串行；最终 test 的独立 episode 可同轮并发。
