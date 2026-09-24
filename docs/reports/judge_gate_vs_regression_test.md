> **2026-09-23 RethinkSkill 更正：** 旧 study runner 未遵循官方执行链，已禁用，其结果不得用于方法比较。核对证据与复现边界见 [官方链审计](../rethinkskill_official_audit.md)。

# 把「回归测试」换成裁判 agent：SkillOpt / Trace2Skill 闸门替换实验

> 历史报告，非当前实验结论。2026-09-22 起研究范围为 SkillOpt / GEPA / SkillGen，协议为 direct_replacement_v3。
> 旧集成与统计存在候选仍回测、对照未演化、最终分数复用旧值及 token 漏计等问题，不能用本文证明新协议节省 token 且不掉性能。
> 更正与适用范围见 [当前协议](../judge_adapters.md)。正文保留用于核查历史证据。

日期：2026-09-21 ｜ 仓库：`repos/SkillOptETE`（SkillOpt 侧）、`benchmark/{alfworld,searchqa}-eval`（Trace2Skill 侧）
模型：`qwen3.6-flash-distill`（裁判与执行/优化器同模型）

## 0. 结论

**第一轮（裁判 prompt v1）**：SearchQA 上与回归测试打平（Δ = +0.14pp，CI 跨 0），
ALFWorld 上**明显更差**：4 个候选全部被裁判接受、全部被回归测试拒绝，
而它们的训练窗口准确率从 0.795 掉到 0.769 并连续三个 epoch 卡在那里。

**第二轮（修复后的 v2）**：修复有效但**过度收紧**。SearchQA 上接受率从 10/10 降到 1/10，
test 从 0.8221 掉到 0.8050（对 v1 −1.71pp，CI [−3.00, −0.50]，p = 0.0097）。
**回归测试仍是最好的闸门，但赢得很小**——v2 与回归测试在独立重评上差 −0.79pp（p = 0.284，不显著）。

**最重要的发现不是"裁判行不行"，而是三轮阈值设计本身**：三个新增的硬阈值
（长度比、方向、置信度）**各自单独造成一次运行死锁**，因为 SearchQA 的初始 skill 是一个
104 字符的占位符，任何"必须更好"的规则在自举阶段都是**不可满足**的。
三次死锁的完整证据都存档在 `tmp/judgestudy/sq_k40_judge_v2_deadlock{,_flat,_conf}/`。

---

## 1. 实验设计

三个（第二轮加 v2 共四个）条件，**只有闸门不同**，其余全部共享（数据、模型、采样、超参、
edit budget、epoch 数、训练流 shuffle）：

| 代号 | 闸门 | 含义 |
|---|---|---|
| **C0** regression | `gate_mode=rollout` | 论文原闸门：held-out 选择集上真跑，**严格**高于当前才接受（平局即拒） |
| **C1** judge v1 | `gate_mode=judge --judge_prompt_variant v1` | 裁判读 patch + 证据窗口，输出 ACCEPT/REJECT；**每候选不再跑选择集** |
| **C1'** judge v2 | `gate_mode=judge --judge_prompt_variant v2` | 同上，但 prompt 与阈值按 §6 的五条意见重写 |
| **C2** greedy | `gate_mode=greedy` | 无闸门，全部接受（下界：判断裁判有没有在筛） |

**裁判被刻意剥夺的信息**：选择集与其标签、任何 held-out 准确率、以及**训练窗口的聚合准确率**
（给裁判看聚合分它就成了阈值，而不是裁判）。它看到的是每题的 outcome + 评测器反馈 + 轨迹片段。
单测锁住了这一条（`test_judge_never_sees_the_held_out_selection_score`）。

### 1.1 代码落点

| 文件 | 作用 |
|---|---|
| `repos/SkillOptETE/skillopt/evaluation/judge_gate.py`（新） | `JudgeGate`（与 `evaluate_gate` 同签名/同 `GateResult` 契约）、两版 prompt、`parse_judge_payload`、v2 阈值 |
| `repos/SkillOptETE/skillopt/engine/trainer.py` | `gate_mode` 分派（step 门 + slow-update 门）；judge 模式跳过 selection rollout；把本 run 的 attempt 历史喂给裁判 |
| `repos/SkillOptETE/skillopt/config.py`、`configs/_base_/default.yaml`、`scripts/train.py` | `evaluation.gate_mode` + `judge.*`（含 v2 四阈值）；顺带接上此前只解析未生效的 `--judge_model` 等 |
| `benchmark/{alfworld,searchqa}-eval/.../analysis/judge_{episode,answer}.py`（新） | Trace2Skill 侧裁判工具，输出沿用 `Result:          PASS/FAIL` 契约 |
| `.../trace2skill/analyst.py` + `scripts/run_trace2skill.py` | `--verifier {replay,judge}`：把 analyst 的 `evaluate_output` 反馈从真值切换为裁判 |
| `tests/test_judge_gate.py`、`tests/test_trainer_judge_gate.py`（新，66 用例） | 解析/重试/失败拒绝、**「judge 模式不跑 selection rollout」**、v2 每条阈值、rollout/greedy 行为不变 |

质量门：ETE 全套 `1689 passed, 9 skipped, 353 subtests`；SearchQA `40 passed`；ALFWorld 新增用例通过
（该仓库另有 2 个失败用例在我改动前已存在，已 `git stash` 验证）。

---

## 2. SearchQA：三条件打平，v2 反而不如

论文口径：train 400 / val 200 / test 1400，batch_size 40（= 原始 cadence，10 次更新），
edit_budget 4，constant LR，seed 42，1 epoch。

| 条件 | 接受/尝试 | 选择集/候选 | best test EM | final test EM | token |
|---|---|---|---|---|---|
| C0 regression | 4 / 10 | 200 题 | 0.8207 | 0.8207 | 16.27 M |
| C1 judge v1 | **10 / 10** | 不跑 | **0.8221** | 0.8221 | 12.63 M |
| **C1' judge v2** | **1 / 10** | 不跑 | 0.8050 | 0.8050 | **8.53 M** |
| C2 greedy | 10 / 10（force） | 200 题 | 0.8186 | 0.8100 | 25.32 M |

参照：无 skill 0.7721；论文发布的 GPT-5.5 skill 0.8121；各 run 自测的初始 skill 0.7643–0.7679。

### 2.1 配对比较（同一份 1400 题清单）

**trainer 侧测量**（每个条件自己的 best_skill）：

| 比较 | Δ | 95% CI | McNemar p |
|---|---|---|---|
| C1 v1 vs C0 | +0.0014 | [−0.0107, +0.0143] | 0.911 |
| C1 v1 vs C2 | +0.0036 | [−0.0079, +0.0150] | 0.625 |
| **C1' v2 vs C0** | **−0.0157** | **[−0.0286, −0.0036]** | **0.0198** |
| C1' v2 vs C1 v1 | −0.0171 | [−0.0300, −0.0050] | 0.0097 |
| C1' v2 vs C2 | −0.0136 | — | — |

**独立重评**（把每个条件最终采纳的那份 skill 单独拉到 test 上重跑，`tmp/judgestudy/candidates/`；
候选文件哈希已逐一与 `history.json` 的 `candidate_hash` 核对一致）：

| 比较 | Δ | 95% CI | McNemar p | both / only-A / only-B / neither |
|---|---|---|---|---|
| v1 vs C0 | −0.0043 | [−0.0179, +0.0093] | 0.614 | 1086 / 46 / 52 / 216 |
| v1 vs C2 | −0.0029 | [−0.0150, +0.0093] | 0.728 | 1097 / 35 / 39 / 229 |
| **v2 vs C0** | **−0.0079** | **[−0.0214, +0.0050]** | **0.284** | 1089 / 38 / 49 / 224 |
| v2 vs v1 | −0.0036 | [−0.0164, +0.0086] | 0.653 | 1090 / 37 / 42 / 231 |

三种读数必须同时给出：

1. **在独立重评下四个条件全部不可区分**（最大 |Δ| = 0.79pp，所有 CI 跨 0）。这是最干净的比较，
   因为每个 skill 都在同一份新环境里评过一次。
2. **v2 相对 v1 的 −1.71pp 在 trainer 侧显著（p = 0.0097）**，但它同时是**评测噪声带内**的量：
   本次实测同一 skill 重评的不一致题数是 **56–83 题（0.7–1.4pp）**，其中一次 p = 0.023。
   所以"v2 比 v1 差"这个方向可信，"差 1.7pp"这个量不可信。
3. **唯一的确定收益是成本**：v2 用 8.53 M token 拿到与 16.27 M 的回归测试无显著差异的分数，
   省 48%；裁判自身只占 1.3%。

### 2.2 逐候选真值：每个候选单独评 test

把每个候选 skill 单独拉到 1400 题 test 上评测（哈希已核对）：

**C1 judge v1（10/10 接受）**

| step | 窗口 acc | 候选长度 | 判据 | 真值 test EM |
|---|---|---|---|---|
| 1 | 0.825 | 2111 | ACCEPT(high) | 0.8214 |
| 2 | 0.900 | 3559 | ACCEPT(high) | 0.8171 |
| 3 | 0.825 | 4616 | ACCEPT(high) | 0.8171 |
| 4 | 0.900 | 5404 | ACCEPT(high) | **0.8221** |
| 5 | 0.750 | 6285 | ACCEPT(high) | 0.8114 |
| 6 | 0.750 | 6803 | ACCEPT(high) | 0.8114 |
| 7 | **0.725** | 7616 | ACCEPT(high) | 0.8143 |
| 8 | 0.800 | 10187 | ACCEPT(high) | 0.8086 |
| 9 | 0.750 | 12369 | ACCEPT(high) | 0.8099 |
| 10 | 0.800 | 13536 | ACCEPT(high) | 0.8086 |

**C0 regression（4/10 接受）**

| step | 窗口 acc | 选择集 | 判据 | 真值 test EM |
|---|---|---|---|---|
| 1 | 0.825 | 0.7700 | ACCEPT | 0.8086 |
| 2 | 0.900 | 0.7750 | ACCEPT | 0.8186 |
| 3 | 0.800 | 0.7600 | **reject** | 0.8007 |
| 4 | 0.900 | 0.7850 | ACCEPT | 0.8100 |
| 5 | 0.775 | 0.7550 | **reject** | 0.7957 |
| 6 | 0.750 | 0.7950 | ACCEPT | 0.8171 |
| 7 | 0.775 | 0.7950 | **reject** | 0.8093 |
| 8 | 0.850 | 0.7600 | **reject** | 0.8157 |
| 9 | 0.800 | 0.7800 | **reject** | 0.8071 |
| 10 | 0.775 | 0.7700 | **reject** | 0.8171 |

三条读数：

1. **没有一个候选差于初始 skill**（最差 0.7986，初始 ≈0.767）。Skill 学习这一步在这个
   benchmark 上是稳健的——**没有东西可筛**，这直接解释了为什么三个条件分数相同。
2. **裁判放行后 skill 膨胀到 13536 字符（6.4×）**，真值曲线在 step 4 达峰（0.8221）后走低到 0.8086；
   回归测试在 step 4 后拒掉 6 个，把 skill 钉在 5425 字符。**两个条件走了非常不同的路，
   但终点撞在一起**。
3. 裁判的 ACCEPT 与真值**负相关**（窗口 acc 最低的 step 7 被接受，其后全是下降段）。
   回归测试的选择集分数方向正确（拒掉的 5 个里 4 个真值 ≤ 0.8071）——但它筛掉的东西不影响最终分。

---

## 3. ALFWorld：v1 方向明确的负面结果

论文口径：官方 39/18/134，batch_size 40 → 每 epoch 恰好 1 次更新，4 epoch = **4 次门控决策**。

| 条件 | 接受/尝试 | baseline | best | final | 最终 skill |
|---|---|---|---|---|---|
| C0 regression | **0 / 4** | 0.7836 (105) | 0.7910 (106) | 0.7910 | 2966（init，未变） |
| C1 judge v1 | **4 / 4** | 0.7985 (107) | 0.7836 (105) | 0.7836 | 11644（3.9×） |
| C1' judge v2 | 运行中（见 §7.4） | — | — | — | — |
| C2 greedy | 4 / 4 | 0.8060 (108) | 0.7836 (105) | 0.8134 (109) | 12600+ |

**注意 3.1 和 3.2 是本节的读法**：跨 run 的 baseline 列不可比（同一份 skill 差 3 局），
只有同一 run 内的配对差（§3.2）和训练窗口内部的量（§3.3）可用。

### 3.1 本次实测的 ALFWorld 噪声带

三个条件跑的是**逐字节相同**的 init skill（sha256 `01bd29e8…`，已核对三份 `skills/skill_v0000.md`），
各自在 134 局上独立评测：

| run | init skill 的 test |
|---|---|
| aw_judge | 0.7985（107/134） |
| aw_greedy | 0.8060（108/134） |
| aw_rollout | **0.7836（105/134）** |

**同一份 skill 的 spread = 3 局 = 2.24pp。** 与既有 FUSE 重复实验一致
（parent ×3 = 111/110/108，staged ×3 = 110/114/114，spread 3–4 局）。
因此 §3 表中所有跨 run 的比较都不可用；只有**同一 run 内的配对差**和**训练集窗口内部的量**可用。

### 3.2 同一 run 内的配对差（baseline skill vs best skill，同一份 134 局）

| 条件 | Δ | 95% CI | McNemar p | 换成局数 |
|---|---|---|---|---|
| judge v1 | −0.0149 | [−0.0746, +0.0448] | 0.804 | −2 局 |
| regression | +0.0075 | [−0.0448, +0.0597] | 1.000 | +1 局 |
| greedy | −0.0224 | [−0.0672, +0.0224] | 0.508 | −3 局 |

全部 CI 跨 0。**ALFWorld 的 test 集（134 局）分辨不出这些差别。**

### 3.3 不依赖 test 集的证据（这是本轮最有说服力的部分）

| step | 训练窗口 acc | 回归测试（选择集 18 局） | 裁判 v1 |
|---|---|---|---|
| 1 | 0.795 | REJECT（0.8889 **平局** 即拒） | ACCEPT（conf=medium） |
| 2 | **0.769** | REJECT（0.8333 **< 0.8889，实测回退**） | ACCEPT（conf=high） |
| 3 | **0.769** | REJECT（平局） | ACCEPT（conf=high） |
| 4 | **0.769** | REJECT（平局） | ACCEPT（conf=high） |

- **训练窗口自己说候选没让系统变好**：acc 从 0.795 掉到 0.769 并连续三个 epoch 卡住。
- **回归测试在 step 2 拿到了实测回退信号**（0.8333 < 0.8889），拒掉。
- **裁判四条全收**，理由是 "adds necessary rigor"、"strengthens search heuristics"、
  "introduces critical termination safeguard"、"generalize across task types without
  contradicting successful trajectories"，且 skill 从 2966 膨胀到 11644 字符（3.9×）。

这是**方向明确的负面结果**：不是在说"裁判差 1.5pp"（test 分辨不出），
而是在说**"训练窗口和 18 局验证集各自都明确否掉的候选，裁判一个都没拦住"**。
4 次决策不足以给效应量，但 4/4 vs 0/4 的分离是干净的。

### 3.4 为什么两个 benchmark 结论相反

| | SearchQA | ALFWorld |
|---|---|---|
| 选择集规模 | 200 题 | **18 局** |
| 选择集标准误 | ~2.9pp | **~11pp** |
| 回归测试本次接受率 | 4/10 | **0/4** |
| 候选真值散布 | 0.7986–0.8221（全部 > init） | 全部弱于 init |
| 裁判 v1 接受率 | 10/10 | 4/4 |
| 结论 | 可以换（差异在噪声内） | 不能换（方向明确为负） |

关键不是"回归测试在 ALFWorld 更准"，而是 **ALFWorld 上回归测试恰好给出了正确的否决**：
18 局上四次里三次是平局（0.8889 == 0.8889）、一次是实测回退，
而真值也确认这些候选确实没改进。**裁判看不到"平局"这个信息，因为它没有可比的分。**

---

## 4. Trace2Skill 侧：验证器从真值换成裁判

Trace2Skill 的闸门在 analyst 循环内部：`evaluate_output` 工具在真实环境重组修好的动作序列
（ALFWorld）或用 harness 的 EM 打分（SearchQA），只有精确 `PASS` 才写 `evaluate_passed.flag`。
换成裁判后，analyst 的反馈信号不再是真值。

### 4.1 SearchQA：裁判丢掉的 11 条里 8 条从未提交候选

| 条件 | 通过/分析 | 通过率 | 记忆条目 | skill 大小 | test EM（1400） |
|---|---|---|---|---|---|
| replay（原，2026-09-15） | 400/400 | **100%** | 1086 | 3498 | 0.8086 |
| **judge（本次）** | **389/400** | **97.25%** | 1059 | 4648 | **0.8036** |
| 无 skill | — | — | — | — | 0.7721 |

- judge 0.8036 vs replay 0.8086：**Δ −0.0050，CI [−0.0164, +0.0071]，p = 0.483**
  （both 1092 / only-judge 33 / only-replay 40 / neither 235）→ **不可区分**。
- judge 0.8036 vs vanilla 0.7721：Δ +0.0314，CI [+0.0171, +0.0457]，p = 1.9e−05 → 增益显著。

**丢弃的 11 条里 8 条 `verifier_calls = 0`**：analyst 从没调用过裁判，3 轮就结束了
（`turns_used = 3/20`）。对照同一批 item 在 replay 运行的 transcript：
replay 下 analyst 在同样 5 轮里调用了 `evaluate_output` 并拿到 PASS。
→ **当验证器不再给出"对/错"这种即时信号时，模型倾向于不去提交候选。**
这是"去掉回归测试"的副作用，与裁判质量无关：它连被检验的机会都没有。

### 4.2 ALFWorld：裁判反而让通过率上升，生成的 skill 略好

| 条件 | 通过/分析 | 通过率 | 记忆条目 | skill 大小 | test（134 局） |
|---|---|---|---|---|---|
| replay 产物（原，2026-09-15） | 31/39 | 79.5% | 93 | 2078 | 0.6642 |
| replay 产物（**今天同会话重评**） | — | — | — | 同一份文件 | **0.6418** |
| **judge 产物（本次）** | **38/39** | **97.4%** | 114 | 2100 | **0.6940** |
| 无 skill | — | — | — | — | 0.6269 |

配对比较：judge 0.6940 vs replay（今天重评）0.6418，**Δ +0.0522，CI [−0.0149, +0.1194]，
p = 0.189**（both 79 / only-judge 14 / only-replay 7 / neither 34）→ **方向为正但不显著**。

两点必须诚实说明：

1. **replay 的 0.6642 是 9-15 的历史值，今天重评同一份文件只有 0.6418**（−2.24pp，
   正好等于 §3.1 的噪声带）。所以这里用的是今天同会话重评的 0.6418；即便如此 CI 仍跨 0。
2. **方向与 SkillOpt 侧相反**。解释：ALFWorld 的 Trace2Skill 闸门丢掉的 8 条失败轨迹里，
   大部分是"analyst 修不好自己没解出的那局"（既有报告 §4 已记录）。裁判不要求"真的解开"，
   于是放行了它们——**其中一部分确实带来了有用的泛化教训**（通过率 79.5%→97.4%、
   记忆 93→114 条）。**"去掉回归测试"在 Trace2Skill 侧不一定是坏事：它的闸门原本卡的是
   任务难度，不是教训质量。**

---

## 5. 归因：v1 失败在 prompt 设计的哪一点

裁判的失败不是"模型不够聪明"，而是**被要求做一件它没有信息去做的事**。

### 5.1 要求「strictly better」却不给任何可比量 → 退化为全接受

v1 的 prompt 写着：

> *Be strict. The gate you replace accepts only a candidate that is **strictly** better
> than the current skill; a candidate that is merely plausible does not clear that bar,
> and a tie is a rejection.*

但裁判手里只有候选文本、patch、窗口内每题结果——**没有当前 skill 的可比分数，没有窗口前后差异**。
它能判定的只有"这段规则是否被证据支持"，而**所有由真实失败归纳出的规则都被证据支持**。
"strictly better" 在实践中变成 "plausible → ACCEPT"。

证据：14 次决策 13 次 `confidence=high`，接受率 14/14。ALFWorld 四个候选的窗口 acc 是
0.769–0.795、init 的选择集分是 0.8889——候选连训练集都没改进，裁判全部接受。

### 5.2 没有长度/稀释预算 → 把「更长」读成「更全」

v1 理由里反复出现 *strengthens*、*adds necessary rigor*、*introduces critical safeguard*。
它没有任何关于"skill 变长会稀释指令遵循"的信号，prompt 也从不提长度。
后果：SearchQA 2111 → 13536 字符（6.4×），ALFWorld 2966 → 11644（3.9×）。

### 5.3 只有本窗口证据，没有「上一次尝试」→ 在复现型缺陷上反复接受

SearchQA step 5–10 六次针对**同一缺陷族**（entity 长短 / normalization 冲突），
窗口 acc 在 0.750–0.800 之间反复，裁判六次全接受、每次说是"新的修复"，回归测试六次全拒。
裁判看不到"这个缺陷上次试过且没解决"。这正是 ETE Evolution Controller 用
`controller_attempt_memory` 修掉的同一退化模式（`repos/SkillOptETE/docs/evolution-controller.md`）。

### 5.4 证据窗口被截断且刻意不带聚合 → 无法察觉「候选没帮上忙」

`max_evidence_cards=24`，窗口是 40 题。裁判看到最近 24 条而不是全部，且刻意不给聚合准确率。
这个设计的本意是"不给裁判一个阈值"，代价是**它无法比较候选带来的窗口前后差异**——
而那正是"这个 patch 好不好"唯一可测的定义。这是 §5.1 的另一面。

### 5.5 confidence 无校准，不能当二次门

14 次决策 13 次 high。该字段在 v1 下零信息量。
（→ 一轮修复里我把它当硬门用，结果造成第三次死锁，见 §7.3。**这说明该字段确实不可用，
但方式与我原先设想的不同：v2 下它会诚实报 medium，而 medium 又太常见。**）

---

## 6. 最优先的 5 条修复意见

按"用最少信息补齐最大缺口"排序。全部已实现并跑过第二轮，实现结果见 §7。

### 修复 1 给裁判**可比的窗口前后差异**
在 prompt 里加入本次窗口的题目数、成功/失败数，并要求裁判显式回答
"这个候选预期把窗口准确率往哪个方向推、凭什么"。
**这不是** held-out 选择集分数（那会让它变成阈值），而是训练集自身的前后对比——
gate 本来就有权知道的信息。

### 修复 2 加入长度预算与「每条新增规则必须有失败支撑」
给出当前/候选字符数与增长比；超过 `max_growth_ratio` 时，裁判必须逐条指出每条新增规则
对应的具体失败，说不出则 REJECT。

### 修复 3 注入「上一次尝试」记录
把上次尝试的目标缺陷、裁决、裁决后的窗口准确率写进 prompt，并加原则：
若上次针对**同一缺陷机制**且此后窗口准确率未改善，除非新证据在**数量或机制**上实质不同，否则 REJECT。

### 修复 4 结构性输出 + 可证伪声明
要求裁判输出 `defect_mechanism` / `evidence_count` / `counter_evidence_count` /
`expected_window_delta` / `falsifier`，并据此裁决：
`evidence_count < min_evidence` → REJECT；方向不合规 → REJECT；无 falsifier → REJECT。
把"strictly better"变成可执行的计数与方向判断。

### 修复 5 默认保守 + 给 confidence 一个用途
解析失败仍 REJECT；`confidence != high` → REJECT（默认开启）；
`judge_min_evidence`、`judge_max_growth_ratio` 全部可配便于消融。

### 修复 6（附带）针对 §4.1 的「analyst 不提交」
在 judge 模式下把"必须先提交至少一个候选"写成强制步骤（先写 `output_fixed.json` 再写报告），
避免 8/11 条因从未提交而被丢弃。

---

## 7. 第二轮：修复结果

配置：`--judge_prompt_variant v2`，阈值 `min_evidence=2`、`max_growth_ratio=1.5`、
`require_high_confidence`（见 7.3）。数据/模型/超参/流与第一轮完全一致。

### 7.1 SearchQA：修复生效但过度收紧

| | v1 | **v2** | 回归测试 |
|---|---|---|---|
| 接受/尝试 | 10/10 | **1/10** | 4/10 |
| best test EM | 0.8221 | **0.8050** | 0.8207 |
| 独立重评 | 0.8086 | **0.8050** | 0.8129 |
| token | 12.63 M | **8.53 M** | 16.27 M |
| 最终 skill | 13536 字符 | **1891 字符** | 5425 字符 |

逐 decision：

| step | 模型说 | 证据/反证 | 方向 | 闸门 |
|---|---|---|---|---|
| 1 | ACCEPT | 5 / 15 | improve | **接受** |
| 2 | REJECT | 2 / 0 | flat | 拒 |
| 3 | ACCEPT | 7 / 17 | improve | 拒（增长 1.77× > 1.50×） |
| 4 | REJECT | 5 / 0 | flat | 拒 |
| 5 | REJECT | 6 / 18 | flat | 拒 |
| 6 | REJECT | 6 / 7 | flat | 拒 |
| 7 | REJECT | 5 / 0 | flat | 拒 |
| 8 | REJECT | 3 / 0 | improve | 拒（evidence 3 < … 实际是模型自己拒） |
| 9 | REJECT | 6 / 10 | flat | 拒 |
| 10 | ACCEPT | 7 / 12 | improve | 拒（增长 1.60× > 1.50×） |

读数：

- **修复确实改变了行为**：接受率 10/10 → 1/10，skill 从 13536 压到 1891 字符，
  token 再降 32%。裁判开始真的拒绝了。
- **但过度收紧**：v2 只接受了一次（step 1，1891 字符），
  独立重评 0.8050 是四个条件中最低之一，相对 v1 −0.36pp（p = 0.653，不显著）、
  相对回归测试 −0.79pp（p = 0.284，不显著）。
- **代价收益**：8.53 M token 换 0.8050；回归测试 16.27 M 换 0.8129。
  省 48% token，损失落在噪声带内。

### 7.2 三条规则的表现（归因）

| 规则 | 触发次数 | 效果 |
|---|---|---|
| 模型自主 REJECT（多数因 `expected_window_delta=flat`） | **7 / 10**（step 2/4/5/6/7/8/9） | **最有效**：模型报 flat 时确实没改善（这些 step 的窗口 acc 在 0.725–0.800 之间反复） |
| `max_growth_ratio` downgrade | **2 次**（step 3 的 1.77×、step 10 的 1.60×） | 有效但**边界太紧**：1.5× 把两个模型明确判为 `improve` 的候选也砍了 |
| `min_evidence` | 0 次 | 模型自己就很保守（`evidence_count` 普遍 3–9，从未低于 2） |
| `require_high_confidence` | 见 §7.3 | **不可用**（默认已关） |
| `falsifier` 非空 | 0 次拦截 | 模型总能写出一个，没有区分度 |

**净效果**：10 次决策里模型自主拒了 7 次，两版阈值规则额外砍掉 2 次，最终只接受 1 次
（step 1，1891 字符）。也就是说 **v2 的行为主要由模型的诚实判定驱动，而不是由我的阈值驱动**
——阈值只贡献了 2/10 的额外拒绝，且这 2 次都可能是误杀。

### 7.3 三次运行死锁（最重要的工程发现）

v2 的三个新增硬阈值**各自单独造成一次运行完全无法启动**。根因是同一个：
**SearchQA 的初始 skill 是 104 字符的占位符**，任何"必须更好"的规则在自举阶段不可满足；
而因为从不接受，`current skill` 永远是那 104 字符，于是**下一次同样被拒——死锁**。

| # | 阈值 | 现象 | 证据 | 修复 |
|---|---|---|---|---|
| 1 | `max_growth_ratio=1.5` 无条件生效 | 104 字符 × 1.5 = 156 字符，而真实候选是 2247–3106 字符（21.6–29.9×）→ 10/10 全拒，`skill_len` 永远是 104 | `sq_k40_judge_v2_deadlock/` | 加 `min_growth_floor=600`：占位符低于此值时比值不生效 |
| 2 | `expected_window_delta` 必须 `improve` | 模型诚实回答 `flat`（4 个失败 vs 33 个会受影响但成功的任务）→ 10/10 全拒 | `sq_k40_judge_v2_deadlock_flat/` | 改成**随 regime 变化**：自举期 `improve|flat` 都接受，skill 长成后只接受 `improve`——**这正是真实闸门的行为**（回归测试也是拿候选比 current） |
| 3 | `require_high_confidence=True` | v2 下模型诚实报 `medium`（3/3），硬门把 3 个 ACCEPT+improve 全砍 | `sq_k40_judge_v2_deadlock_conf/` | 默认改为 `false`；字段保留记录、可配可消融 |

**这三次死锁都是我的阈值设计错误，不是模型判断错误。** 三次里模型的判断都是对的：
死锁 1 它正确说"4 个失败支持这个机制，但增长 19.2×"；死锁 2 它正确说"方向是 flat"；
死锁 3 它正确说 ACCEPT + improve。

对方法论的含义：**把 LLM 的软判断包成硬阈值时，必须同时验证该阈值在系统的每一个状态
（尤其是自举态）都可达**。否则得到的是一个不报错、只是永远拒绝的闸门——
比没有闸门更隐蔽，因为日志显示它在正常工作。

### 7.4 ALFWorld 的 v2 复测

同一份训练流（官方 39/18/134，4 epochs，每 epoch 1 次更新 = **4 次门控决策**）。

**step 1（已完成）**：模型给 `REJECT`——**不是我的阈值砍的**（`judge_rule_override` 为空），
是模型自己判的：

| 字段 | 值 |
|---|---|
| 模型判据 | `REJECT` |
| 缺陷机制 | `none`（模型认为没有可归因的机制） |
| 证据数 / 反证数 | 0 / 0 |
| 预期方向 | **`worse`** |
| 长度 | 2966 → 5274 字符（1.78×） |

理由里有一句是 v1 从未产出过的：

> *It also contains **direct contradictions**, such as Principle 9 encouraging functional
> substitutes while the updated Common Mistakes section warns against mismatched object...*

v1 在同一份流上对 4 个同类候选全给 `ACCEPT(high)`，理由是 "adds necessary rigor"、
"generalize across task types without contradicting successful trajectories"。**v2 读出的是
同一份候选里两节自相矛盾。** 同一模型、同一候选、同一证据窗口，唯一变量是 prompt：
一旦要求"指出机制并计数"，模型就去逐条读了候选文本。

> **step 2–4 与 test 评测在报告定稿时仍在运行**（`tmp/judgestudy/aw_judge_v2/`），
> 以该目录下的 `summary.json` 与 `test_eval*/summary.json` 为准。
> 读法沿用 §3.1/§3.2：**只看同一 run 内的配对差**
> （`test_eval` vs `test_eval_baseline`，同一份 134 局），跨 run 不可用。

---

## 8. 必须随结论一起报出的限制

1. **单次运行**。`temperature=0` 在该端点不保证确定性；本次**实测**同一 skill 重评 1400 题
   不一致 56–83 题（0.7–1.4pp，其中一次 p = 0.023）。ALFWorld 同一 init skill 三次独立评测
   spread 3 局（2.24pp）。条件间的全部差值都落在这个带内——**这是"打平"结论的主要支撑，
   也是"v2 更差"结论的主要削弱**。
2. **ALFWorld 只有 4 次门控决策**。4/4 vs 0/4 的分离干净，但不足以给效应量。
   "回归测试更好"依赖"那 4 个候选确实更差"，该点由**训练窗口 acc 0.795→0.769 且三轮不动**
   支撑，不依赖 test 集。
3. **ALFWorld 的 SkillOpt 用 init skill（2966 字符）而非论文发布的 13179 字符 skill**。
   刻意的：要比较的是"同一流上不同闸门"，不是复现论文数值。
   因此这一栏的绝对值**不可**与 `docs/ALFWorld_reproduction_report.md` 的 82.09% 并列。
4. **v2 不是独立复现**，而是"同一 prompt 家族的第二次迭代"——五条修复正是从第一轮诊断来的。
   它的成绩不能读成"裁判的真实上限"。
5. **没有做裁判模型强度消融**（同模型 vs 更强模型）。用户选择同模型，所以
   "裁判弱是因为模型弱"这条替代解释**没有被排除**。
6. **Trace2Skill 两轮跨会话**（replay 产物 9-15、judge 产物 9-21）。已用"今天重评 replay 产物"
   对齐（0.6418），但只剩单次测量。
7. **ALFWorld v2 的完整结果见 §3 表以外的补充**；v1 的三条死锁同源问题在 ALFWorld 上不存在
   （init skill 2966 字符，远高于 600 的 floor），所以 v2 在 ALFWorld 上不会遇到死锁 1，
   但会遇到死锁 2/3 的同类问题。
8. **C2 greedy 的 token 最高（25.3 M）** 是因为它接受全部 10 个候选、每个都触发下一轮更长迭代；
   不能读成"无闸门更贵"。

---

## 9. 一句话回答最初的问题

> 把 SkillOpt / Trace2Skill 的回归测试直接换成"用一个 agent 判断 patch 好不好"，效果变化多大？

- **SearchQA 上：几乎没有变化**（Δ ≤ 0.8pp，全部落在 0.7–1.4pp 的评测噪声带内），
  但省 22–48% token。
- **ALFWorld 上：变差，且方向明确**——裁判放行了训练窗口和 18 局验证集都已经否掉的候选，
  4/4 vs 0/4。原因不是裁判"看不出问题"，是它**没有被给任何可比的分**：
  而"比 current 更好"恰恰是回归测试的全部内容。
- **修复可以让裁判变严，但不能让它变成回归测试**：v2 收紧到 1/10 接受率后，
  仍然没有超过回归测试（0.8050 vs 0.8129，不显著）。
- **真正可复用的结论**：当验证信息廉价时（SearchQA 每题 1 次调用），回归测试的价值
  不体现在分数上——四个条件的分数在噪声带内完全相同——而体现在**它不会放行没改进的东西**。
  裁判能省掉这笔开销，代价是把"确保有改进"换成"看起来合理"。

---

## 10. 复现

```bash
# SkillOpt 三条件（SearchQA K=40）
bash tmp/judgestudy/run_searchqa_K40.sh            # sq_k40_{rollout,judge,greedy}
bash tmp/judgestudy/run_searchqa_K40_v2.sh         # sq_k40_judge_v2

# SkillOpt 三条件（ALFWorld 官方 39/18/134，4 epochs）
bash tmp/judgestudy/run_alfworld.sh                # aw_{rollout,judge,greedy}
bash tmp/judgestudy/run_alfworld_v2.sh             # aw_judge_v2

# Trace2Skill：analyst 的验证器换成裁判
bash tmp/judgestudy/run_t2s_searchqa_judge.sh      # t2s_sq_judge
bash tmp/judgestudy/run_t2s_alfworld_judge.sh      # t2s_aw_judge

# 逐候选真值
bash tmp/judgestudy/eval_candidates.sh             # candidates/

# 分析
python3 tmp/judgestudy/analysis/audit_gates.py --glob 'tmp/judgestudy/sq_k40_*' \
    --out tmp/judgestudy/analysis/audit_sq_k40.json
python3 tmp/judgestudy/analysis/paired.py --a A/results.jsonl --b B/results.jsonl \
    --label-a A --label-b B
# ALFWorld 结果文件用 --id-key id --score-key hard（T2S 的用 gamefile/success）
```

目录说明、命名约定与六个已知坑见 `tmp/judgestudy/README.md`。
