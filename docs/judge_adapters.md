# 当前 Judge 集成协议

协议标识：`direct_replacement_v3`。当前研究对象仅为 SkillOpt、GEPA、SkillGen；官方源码以工作区 `repos/pulled` 的 checkout 为准。以下说明区分原始流程与本仓库的替换点，不以论文描述代替代码。

本次核对的官方版本：SkillOpt `79124b37e9a6371e13b753f8bcd7adb1e493ade1`；GEPA `0632cdb5dcc052e690eab439e1b4a7e3e9cfe407`；SkillGen `3c4537bb12ac287ceb1b5d410b491206089fdcb7`。本仓库的 SkillOpt 源码来自既有 SkillOptETE 分支，含可配置的证据触发调度；对照时必须固定双方调度配置，不能把该分支称为完全未修改的官方实现。

## 三种方法的对应关系

| 方法 | 官方流程 | Judge 替换 |
| --- | --- | --- |
| SkillOpt | 训练执行收集问题 → 提案/修订 skill → selection 回测决定是否接受；可选慢更新门控 | 读取当前/候选 skill、补丁和已有训练证据来接受/拒绝；无初始 selection、无逐候选 selection；最终输出冻结后才测量 |
| SkillGen | baseline 轨迹 → 归纳 → 生成 skill → verification 执行候选并计算修复/退化净收益；首次通过即停止，否则继续修订 | 在 verification 执行前分支到 Judge；复用 baseline 轨迹和归纳依据；Judge 原因用于下一次修订；首次接受即停止，全拒绝则弃用，不按未知净收益选候选 |
| GEPA | 父候选训练小批量 → reflection 生成子候选 → 子候选小批量比较 → 接受者 full validation → Pareto 候选池选择父候选和最终输出 | 保留父候选执行以生成提案；跳过子候选小批量和所有搜索期 validation；共用 Judge 判接受，局部扩展的预测用于候选池 |

SkillOpt 官方慢更新中的纵向训练比较用于生成提案，仍可能执行此前 skill；它不是待验收候选的回测。普通训练也会使用已经接受的 skill。这里“无回测”约束的是为验收/排序而重新执行候选，不是禁止方法继续获取训练经验。

SkillGen 的不同实际修订轮数是首次通过停止规则的自然结果；不强制匹配轮数。按最新目标，token 比较只累计实际发生的 Judge 调用或被替代的回测执行，不比较整个运行的成本。

## 共享核心与局部差异

三个方法调用同一个 `JudgeGate`。`v3` 共享净收益判断：失败是否有修复依据、成功行为是否保留、适用边界、冲突和复杂度。不给虚构的候选执行结果，也不使用 held-out 答案。证据去重后按已有任务类型和成功/失败分组轮流选择，最多 12 张卡，每张最多 1000 字符；当前与候选各最多 12000 字符，变更依据最多 2000 字符，最近三次判断最多 1200 字符。裁判回答最多 512 token，解析失败最多重试两次。

输入限制是字符上限，不是假定字符数等于 token 数。使用头尾保留并标注遗漏；证据不足仍可能误判，须在新实验中测量。历史 `v1/v2` 保留原有 prompt 与阈值，显式版本名写入记录。添加新版本使用 `register_judge_prompt_variant`，不复制方法专用 prompt。

共有输出为 `verdict / confidence / reason`。SkillOpt、SkillGen 无需附加字段。

GEPA 唯一附加字段是 `predicted_changes`：对训练 manifest 已有的任务类型预测相对父候选的变化，值为 -1/0/+1。没有类型标签时只有 `all_tasks` 一个轴。最多 16 个类型轴，不调用另一个模型生成类型。各候选坐标由父候选预测坐标加变化构成，保留官方 Pareto 候选池机制；它是相对 seed 的累计序数预测，不是准确率，也不是“最新接受必定最好”。该近似会有沿路径累积偏差，是需要实验检验的局部适配。

GEPA 上游内部字段仍名为 `val_subscores`，但结果文件、状态索引、轨迹与 metadata 标明 `score_source=judge_prediction`，不能当作实测 validation。原始 `eval_after` 为 None，实际 candidate/full-validation 执行计数为零。当前 Judge 只支持默认 reflective mutation + AllImprovements；请求 merge 或基于实测小批量排序的其他选择策略会报错。

## 最终测量与预算

输出选定后才执行 validation/test；最终测量不能改变输出。SkillOpt Judge 不再复用旧 selection 分数，未测时为 null。SkillGen 不生成虚假的 repair/regression/net_gain，Judge 历史的 net_gain 为 null。

GEPA 保留官方 metric-call 停止条件，并通过官方 MaxCandidateProposalsStopper 给双方同样的最大提案轮数（默认 8），防止零回测成本导致无限运行。SearchQA / ALFWorld 的配置预算分别为 2000 / 300，均允许 baseline 在完整 seed validation 后继续提案。两组按各自停止条件运行，不要求实际轮数相同。

## 当前 Token 口径

只比较 `replacement_cost.json` 中的两类成本：

| 方法 | baseline 计入的重新做题 | Judge 计入 |
| --- | --- | --- |
| SkillOpt | 初始化 selection、候选 selection、启用门控的慢更新 selection | LLM Judge 调用 |
| GEPA | seed validation、候选小批量、接受后的 full validation | LLM Judge 调用，含其局部预测输出 |
| SkillGen | verification 的 effectiveness 执行与必要结果评分 | LLM Judge 调用 |

初始化 selection/validation 也被当前 Judge 路径移除，因此计入 baseline，并通过 `seed_validation` 单独列出。GEPA 父候选训练执行、SkillGen baseline 轨迹采集、提案生成、案例分析、修订建议、最终 validation/test 均不计入。

原始 `usage_events.jsonl` 在实际执行边界添加 `replacement_component` 标签；线程池里的执行也继承该边界，不能靠模糊的模型名或 `rollout` 名字归类。仅汇总带标签的输入、输出和合计 token。缓存命中没有新调用，不补算理论成本；恢复后从逐次记录累加。

`scripts/compare_replacement_tokens.py --baseline <run> --judge <run>` 输出节省数量和比例，比例分母固定为 baseline 回测 token；不挑选最有利的轮次，也不强制实际轮数相同。负值表示 Judge 更贵。相关调用缺失 usage 时不生成节省率；旧日志缺少标签时拒绝直接续作新统计。原有全程 token 日志可用于排查，但不参与本次比较。

恢复必须使用同一模式和 Judge 版本。旧协议输出不能直接续跑为新协议；请用新的输出目录。历史 campaign 已停用。当前仅完成离线行为验证，尚未完成真实模型小样本、服务健康检查和完整实验预检。

## 历史结果撤回说明

- 旧 SkillGen Judge 是 verification 后附加判断，不回答直接替换问题。
- 旧 GEPA Judge 保留候选小批量；部分 baseline 初始化即耗尽预算，没有真正演化。
- 旧 SkillOpt Judge 的最终 selection 数字可能是初始值，不能作为最终性能。
- 旧“约 100 倍门控 token 节省”混淆全部 rollout 与门控开销，撤回。
- SkillGen 旧 token 汇总可能仅覆盖最后一个恢复进程且遗漏最终评估，不能用来比较完整运行成本。

保留历史原始文件和报告用于核查，不将其标作新协议的实验结论。

## RethinkSkill

The official source is vendored under `packages/rethinkskill/src/rethinkskill`.
`packages/rethinkskill_runner.py` binds its normal feedback-conditioned loop to
the repository's SearchQA and ALFWorld adapters. In `baseline`, the seed and
candidate are evaluated on the validation split for acceptance. In `judge`,
training trajectories are still collected for proposal context, but candidate
validation is skipped and `JudgeGate` is the only acceptance decision. The
frozen candidate is evaluated on test once after evolution. Replacement costs
are therefore `seed_validation`/`candidate_validation` versus `llm_judge` only.
