> 后续实现更新：已新增共享官方训练/提案的 Judge v2，见 [当前执行链说明](rethinkskill_judge_v2.md)。下文保留此前审计结论；其中“HTTP 500 记为普通失败继续”是历史要求，当前实现已恢复官方无效判定。旧实验仍无效。

# RethinkSkill 官方执行链核对（2026-09-23）

## 判定与范围

此前 `packages/rethinkskill_runner.py` 不是官方执行链的复现，已禁用；campaign 审计明确拒绝该方法旧产物。此前 baseline/Judge 的性能与节省 token 数字不得用于 RethinkSkill 方法结论。原始实验记录保留，不删除、不补造。

本次建立的是可直接运行的官方 baseline 入口及可复查的行为验证。**这不等于 Judge 对比集成已经修好，也不等于复现论文数值。** 四方法统一对比仍需修复 RethinkSkill 的局部 gate 扩展、成本记录和恢复机制。

上游：`https://github.com/HKUST-KnowComp/rethinkskill`，commit `8252445918ebebebce7adf9be843c90841e66810`（1.1.0）。完整 Git 跟踪文件已补齐到 `packages/rethinkskill/`，含 LICENSE、protocol、测试、可选 ALFWorld 包。`UPSTREAM.json` 逐文件记录上游 hash 和明确的本地补丁。

## 逐步核对

| 官方步骤 | 官方位置 | 旧 study runner 的偏差 | 当前验证 |
|---|---|---|---|
| 注册 provider、harness、optimizer，冻结分离的训练/验证输入 | `cli/commands.py::native_evolution_command` | 仅导入配置类型，未执行官方链 | 官方 CLI 入口；输入 hash、任务 ID、能力和 provider 清单 |
| 对初始 skill 做 validation | `evolution/loop.py::execute_evolution` | 用 GEPA adapter 做近似评估 | 官方 `NativeSkillEvaluator` |
| 每轮用当前 skill 做训练题 | `execute_evolution_round` | 同样训练但 prompt、执行器和反馈结构不同 | 原生 SearchQA harness；ALFWorld 官方可选 harness |
| 按 normal/fail_only/success_only 过滤反馈，加入真实历史 | `filter_feedback`、`OptimizationContext` | 手写截断轨迹，不提供官方上下文 | 行为测试检查过滤与第二轮历史 |
| 提出 add/delete/replace/noop | `ModelSkillOptimizer`、`render_model_optimizer_task` | 自写 prompt，非法 JSON 被改成正常 noop | 官方渲染、解析、调用次数约束；非法提案终止测试 |
| noop 不回测，skill 必须逐字节不变 | `ProposalOutcome.validate`、`execute_evolution_round` | noop 仍回测，甚至可能接受 | 断言只有初始验证和训练两次执行 |
| 非 noop 才回测候选，再按 hard dead band/soft rescue 决策 | `gate_decision` | 只比较 `candidate > current` | 接受、拒绝、容差、soft rescue 分支测试 |
| 维护 current 与 best 两条状态 | `execute_evolution_round` | 接受即把两者一起覆盖 | soft rescue 只更新 current；回归候选不改 best |
| 每轮证据、最终 receipt 和离线重放审计 | `finalize_evolution_artifacts`、`validate_run_evidence` | 自制 summary，无官方证据校验 | 测试真实落盘后用官方审计重放 |

官方演化阶段输出 `final_current` 和 `best`，不自动替研究者执行最终 test。后续 study 最终评测必须预先固定选择哪个 skill；不能把最后 current 默认为官方 best。Judge 没有实测 validation 分数，也不能伪造分数填进官方 baseline receipt。

## 两个 benchmark 的执行差异

- SearchQA：官方 `SearchQAHarness` 渲染 context/question，要求 `<answer>...</answer>`，官方 verifier 计算 hard/soft。原 study 使用的 GEPA SearchQA adapter 不是这一调用链。
- ALFWorld：官方 `rethinkskill_alfworld` 包使用 ALFWorld 0.4.2，要求 `<think>` 与 `<action>`，以真实环境的 `won` 为准。游戏材料放在 verifier workspace，与模型 workspace 隔离。已经安装可选包并执行官方真实环境测试。
- protocol JSON 指定 10 轮，SearchQA dead band=.01、soft rescue=.02；ALFWorld dead band=.02、无 soft rescue。官方 CLI 自身默认 3 轮、dead band=.01、无 soft rescue，**不会自动应用 protocol JSON**。旧 study 的 4 轮和统一 gate 都不能冒称官方 protocol。
- 官方 protocol 的 ALFWorld train/validation/test=40/140/134；study 使用39/18/134。SearchQA protocol train=40，study train=400。使用 study 数据、seed、模型是显式实验条件调整，不是官方数值复现。

## 本次发现的上游问题

1. **离线审计命名遮蔽 bug。** `evidence/evolution.py::replay_evolution_rounds` 将 `gate_state` 作为状态变量，又当解析函数调用，触发 `TypeError: 'GateState' object is not callable`。本地补丁只将解析函数改名 `parse_gate_state`，不改变执行或 gate；补丁保存于 `packages/rethinkskill/patches/0001-fix-evidence-state-shadowing.patch`。未修改 `repos/pulled/rethinkskill`。
2. **noop 严格字节契约和失败计数限制。** 首轮真实 API 冒烟在两个 benchmark 上均得到 noop，但模型漏掉 seed 末尾换行。官方拒绝提案，且 `_optimizer_boundary` 将校验异常折叠成 `optimizer_invalid`、call accounting unknown。原始 `EXECUTION.json` 仍保存已完成的一次请求。本次不放宽官方校验，也不伪造“零调用”；行为测试固定覆盖该失败。后续计费必须从逐请求证据汇总，不能使用此异常 receipt 的 0 次当作真实成本。

## 复核命令与证据

从 study 仓库根目录：

```sh
PYTHONPATH=packages/skillopt packages/skillopt/.venv/bin/python -m pytest -q \
  tests/test_rethinkskill_official_chain.py tests/test_rethinkskill_integration.py tests/test_direct_campaign.py

packages/skillopt/.venv/bin/python scripts/run_rethinkskill_official.py --help

# 新目录；每个 benchmark 只有一个 train、一个 validation、一轮，无 Judge。
packages/skillopt/.venv/bin/python scripts/check_rethinkskill_official_live.py \
  --root experiments/NEW_CHECK/searchqa --benchmark searchqa --canonicalize-seed
packages/skillopt/.venv/bin/python scripts/check_rethinkskill_official_live.py \
  --root experiments/NEW_CHECK/alfworld --benchmark alfworld --canonicalize-seed
```

`--canonicalize-seed` 是明确记录的输入变体：冻结前去除 seed 末尾空白；不修补模型输出。没有该选项时保留 seed 原始字节。凭据只通过环境变量交给官方 provider，不写入命令参数。全部检查产物在 `experiments/rethinkskill_official_check_20260923/`，每次单独保存 preflight、执行输出、receipt、逐题和 optimizer 原始输出；失败记录也保留。

## 后续完整对比的必要条件

- baseline 直接复用本次验证的官方链；Judge 只局部替换初始/候选 validation 依赖，保留训练、optimizer、noop 和错误语义，并采用诚实的独立 Judge 证据契约。
- 共享 Judge 的 system/user 完整送入模型，诊断落盘，解析失败不能当作正常拒绝并通过烟测。
- baseline/Judge 共用冻结的模型、seed、任务、停止规则和最终选择规则；Judge 无候选回测、无默认 full validation audit。
- 原版官方对基础设施失败停止，用户要求 HTTP 500 记为普通失败并继续：这是必须显式实现和测试的 study 偏离，不能静默宣称是官方行为。
- 官方当前只允许新输出目录，没有 resume；完整实验前仍须加入可审计恢复、逐请求 token 累计和限流策略，不能把本次一轮测试直接扩到长实验。

## 本次最终验证结果

- 官方原始仓库测试：158 passed，1 skipped（首次未指定 ALFWorld 数据路径），另有 77 个 subtests 通过。
- 修复审计 bug 后的本地官方副本：在 ALFWorld 环境及真实 corpus 下 158 passed，1 skipped（发布检查要求独立 Git 文件清单）；真实 ALFWorld 环境用例未跳过。
- 新增行为验证及 study/campaign 相关测试：18 passed。覆盖源码 hash、官方 native loop、官方 optimizer/feedback、noop、非法 JSON、字节不一致 noop、接受/拒绝、current/best 分离、soft rescue、旧入口和旧结果禁用。
- 真实 API：原始 seed 的 SearchQA/ALFWorld 两次均在非法 noop 处失败并保留；明确去除 seed 末尾空白后，两个 benchmark 都完成一轮官方执行及 `validate-run`。两次成功 live run 均为合法 noop，所以没有候选 validation；非 noop 的验证/接受/拒绝分支由固定回复的完整 native 链路测试覆盖，不能冒称 live 候选门也已实测。
- 机器可读证据汇总：`experiments/rethinkskill_official_check_20260923/verification_summary.json`。没有启动完整实验，没有生成新的 Judge 对比结论。
