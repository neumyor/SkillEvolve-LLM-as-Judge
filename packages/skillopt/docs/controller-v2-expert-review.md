# Controller V2 方法设计 + "为什么打不过 fixed K=80" 的机制分析

> **文档目的**：把当前方法的完整设计，以及在原论文口径 SearchQA 实验上观察到的失败原因
> 整理成可供外部专家审阅的材料。所有数字都可从 `tmp/ete_real_runs/` 下的原始产物复算，
> 复算脚本见第 10 节。
>
> **本版更正说明**：初版分析有**两处口径错误**，已在本版修正（第 4.2 节详述）：
> ① 门控增量的取数来源错了（`history.json` 存的是门控**之后**的分，导致把 +5 题读成 +0）；
> ② 我拿"最终 skill（含 slow block）"的文本去和"best skill 的回归数"配对，两者不是同
> 一个 skill。修正后，原因二从"v2 缺少冲突消解条款"改写成一个证据更强、但结论不同的机制。
>
> **诚实性声明**：每个条件 **n=1 次运行**。所有相关性（n=5）只是提示性的。
> 已用独立复现评测排除"单次评测噪声"，但因果关系未被确立。第 6 节给出可证伪设计。

---

## 1. 研究主张（要检验什么）

被检验的主张：

> skill evolution 的**更新频率**本身不应该是一个固定超参数，而应该由**语义证据的充分性**
> 自适应决定。

形式化：设 `S_t` 为 skill，`M_{t-1}` 为控制器维护的语义证据状态，`e_t` 为新观测到的执行证据。
控制器 `C` 输出

```
(M_t, a_t) = C(S_t, M_{t-1}, e_t),   a_t ∈ {WAIT, UPDATE}
```

`a_t = UPDATE` 时调用原 SkillOpt 优化器：`S_{t+1} = SkillOpt(S_t, B_t)`，
其中 `B_t` 是**上一次尝试以来累积的全部经验**。`a_t = WAIT` 时什么都不做——
不跑 reflect、不生成候选、不做验证。一个 cycle 是：

```
证据累积 → 演化尝试 → 重置
```

期望在**适应速度、稳定性、泛化、更新成本、顺序敏感性**五个维度上取得更好的权衡，
而不是在单一维度上取胜。

### 1.1 与基线的关键关系

四个策略共用同一套 trainer 循环，**只在"何时调用优化器"这一点上不同**：

| 策略 | 更新时机 |
|---|---|
| `ImmediatePolicy` | 每个观测批次后都更新 |
| `FixedKPolicy(k)` | 每 K 个观测批次更新（窗口 = K×m） |
| `EndPolicy` | 每个 epoch 末尾更新一次 |
| `LLMEvidencePolicy`（**ours, 下称 Controller v2**） | LLM 判断证据是否充分 |

原论文的固定调度是 `FixedKPolicy(k=1)` 且 `m = batch_size` 的特例。
本轮实验为消除"immediate vs fixed-K"的混淆，统一约定
**每 K 个任务 = 一次观测 = 一次更新**（`observation_batch_size = K, fixed_k = 1`），
使唯一的自变量就是 K。

内层优化器（reflect → aggregate → select → update → gate）**字节级不变**。

---

## 2. Controller V2 的完整设计

### 2.1 接口与执行流程

```python
(M_t, a_t) = policy.observe(
    skill          = S_t,          # 当前 skill 全文
    new_results    = 本批次 m 个任务的执行结果,
    evidence_state = M_{t-1},      # 上一批之后的语义证据状态
    epoch_end      = bool,
    rollout_dir    = ...,
    context        = {...},        # buffer 大小、尝试历史等
)
```

trainer 侧（`skillopt/engine/trainer.py`）：

1. 按 `m` 个任务为一批做 rollout（**只 rollout，不优化**）；
2. 每批结束后调用一次控制器 → `WAIT` 或 `UPDATE`；
3. `WAIT`：该批进入证据缓冲 `B`，循环继续；
4. `UPDATE`：以 `B` 为窗口跑完整 SkillOpt 6 阶段流水线；
5. 无论门控**接受 / 拒绝**，窗口与控制器状态都**重置**；
6. epoch 边界额外做一次 consult（`epoch_end=True`, `new_results=[]`）；
7. 观测流位置、缓冲、控制器状态、尝试日志**逐观测落盘**，支持 `--resume` 按流重放。

### 2.2 控制器的输入（提示词内容）

系统提示词（`skillopt/evolution_controller.py::_CONTROLLER_SYSTEM_PROMPT`，节选）：

```
You are an evolution timing controller for a self-evolving agent skill.
Your job is NOT to improve or rewrite the skill.
Your only job is to decide whether the accumulated execution evidence is
sufficient to justify invoking the skill optimizer now.

UPDATE when the evidence indicates a coherent, recurring, actionable
deficiency in the current skill.
WAIT when the evidence is isolated, noisy, contradictory, task-specific,
or can plausibly be explained by execution randomness rather than the skill.

Consider:
- whether multiple independent cases support the same underlying problem;
- whether similar successful cases provide counter-evidence;
- whether the problem is attributable to the skill;
- whether a generalizable skill-level correction appears possible;
- whether a previous attempt already targeted the same deficiency and
  validation rejected it — in that case WAIT unless the new evidence differs
  materially ...
```

用户消息按顺序拼装四块（`_build_user_message`）：

1. **`## Current Skill`** —— 当前 skill 全文（未截断）；
2. **`## Evidence State (from previous observations)`** —— `M_{t-1}`，即
   `hypotheses[]`（每条含 `defect` / `supporting_cases` / `counter_cases` / `assessment`）
   + `unresolved`；
3. **`## New Observations (N task executions)`** —— 本批每个任务的证据卡：
   task / outcome / score / **evaluator feedback** / **trajectory 摘录**（每卡 1200 字符）；
4. **`## Previous Evolution Attempts (this run)`**（最近 5 条）——
   ```
   - attempt {n} after {tasks} tasks (trigger: {trigger}): targeted "{defect}"
     -> validation {accept|reject} (val {before} -> {after})
     gate: candidate {cand} vs current {cur} (delta {d})
     edit: {op}: {target}      # 最多 4 条
   ...
   ```
   用于阻止**重复触发同一个已被验证拒绝的缺陷**。

输出强制为单个 JSON：`{"decision": ..., "evidence_state": {...}, "reason": ...}`。

### 2.3 明确的设计约束

- **控制器不改 skill、不选样本**——它只能回答 WAIT/UPDATE；
- **没有任何数值阈值**（没有"失败率 > x 就更新"、没有"连续 N 次失败就更新"）：
  决策是语义判断，只由提示词里的若干原则引导；
- 与优化器**同一个 LLM**（`qwen3.6-flash-distill`，thinking 默认开，temperature 0），
  但有不同的 system prompt / 状态 / 职责——是**另一个 agent，不是另一个模型**；
- 响应解析失败时重试有限次，然后**回退到 WAIT 且状态不变**；
- 窗口去稀释（de-dilution）：若窗口内存在失败批次，则**丢弃零失败观测**。

### 2.4 配置（本轮实验）

```yaml
evolution:
  mode: controller
  observation_batch_size: 10        # m = 10
  controller_view: semantic
  controller_max_observation_chars: 1200
  controller_max_state_chars: 4000
  controller_attempt_memory: true
  controller_max_completion_tokens: 4096
  max_buffer_observations: 0        # 安全阀关闭
```

其它（与原论文口径对齐）：`edit_budget=4`、minibatch 8、merge 8、
`shuffle_train_items=true`、seed 42、`use_slow_update=true`、`use_meta_skill=true`、
workers 64 / analyst_workers 32。

---

## 3. 实验装置与主结果

### 3.1 数据与口径

- 原论文 ID split 还原：`train 400 / val 200 / test 1400`；
- 阶段一（epoch 1）：5 条件各跑 1 epoch；阶段二（epoch 2）：同 5 个 `out_root` **resume** 续跑；
- 指标：test(1400) **hard accuracy，final-skill 口径**（含 epoch-2 末端 slow update 的写入）。

### 3.2 主结果表

| 条件 | 尝试次数 | 窗口/次 | 窗口合计 | 窗口内失败 | 写入编辑 | accept | test(1400) | 总 tokens |
|---|---|---|---|---|---|---|---|---|
| K=10 | 80 | 10 | 800 | 163 | 352 | 10 | 0.7921 | 97.8M |
| K=20 | 40 | 20 | 800 | 159 | 217 | 4 | 0.8079 | 45.0M |
| K=40 | 20 | 40 | 800 | 167 | 161 | 6 | 0.8036 | 39.7M |
| **K=80** | **10** | **80** | **800** | **172** | **100** | **2** | **0.8207** | **29.5M** |
| **Controller v2** | **14** | **34** | **470** | **105** | **127** | **5** | **0.7957** | **35.5M** |

> **token 口径**：表中数字 = 该条件所有 run 日志段之和（阶段一 + 阶段二 + 测试重评段）。
> 阶段二续跑时因 resume 缓存以 task id 为键而**漏付**了 test 评测成本，重评段正是补上这笔。
> 若只看阶段一 + 阶段二（漏付口径）：K=10 85.5M / K=20 36.5M / K=40 29.0M /
> K=80 21.2M / v2 29.6M —— **排序与相对关系完全不变**。

同一 init skill 在 test 上的基线带：0.7621–0.7729（15 题极差）。

### 3.3 差距是真实的（已排除单次评测噪声）

5 次独立运行里评测的是**逐字节相同**的 init skill、**同一 1400 题**，据此标定噪声：

- 同 skill 两两不一致：59–82 题（均值 68.8 = 4.9pp），**最大有符号不对称 15 题**；
- v2 vs K=80 的有符号不对称 = 58 vs 23 = **35 题 > 15 题噪声上界**；
- **独立复现**（两个 best-on-val skill 在全新 `out_root` 重评，无缓存复用）：
  - v2: 0.7907 → **0.7929**
  - K=80: 0.8200 → **0.8243**
  - 差距 2.93pp → **3.14pp**，复现且量级一致（配对不对称 44 题 > 噪声上界）。

### 3.4 收益分解

| 参考口径 | k10 | k20 | k40 | **k80** | **v2** |
|---|---|---|---|---|---|
| A：各条件自带 baseline | +36 | +41 | +56 | **+77** | +40 |
| B：统一用同一 baseline | +51 | +54 | +70 | **+81** | +40 |

**两种口径排序一致：K=80 净收益最高，v2 居中（高于 K=10/20/40 的水平，但显著低于 K=80）。**

### 3.5 slow block（epoch-2 末端写入）的独立复现效应

用全新 rollout 评测同条件的 best → final：

| 条件 | best | final（含 slow） | 效应 |
|---|---|---|---|
| K=80 | 0.8243 | 0.8179 | **−0.64pp** |
| v2 | 0.7929 | 0.7850 | **−0.79pp** |

**slow block 在两个条件上都是轻度有害的，因此它不解释 v2 < K=80 的差距。**
差距来自内层 skill 本身。

---

## 4. 四条机制原因

### 4.1 原因一：证据窗口太薄（**证据最强的一条**）

**现象：窗口大小是唯一的强预测因子。**

| 条件 | 每次窗口平均 | 每条编辑背后的任务数 | 每条编辑背后的失败样本 | test |
|---|---|---|---|---|
| K=10 | 10 | 2.27 | 0.46 | 0.7986 |
| K=20 | 20 | 3.69 | 0.73 | 0.8007 |
| K=40 | 40 | 4.97 | 1.04 | 0.8121 |
| **K=80** | **80** | **8.00** | **1.72** | **0.8200** |
| **v2** | **34** | **3.70** | **0.83** | **0.7907** |

五个预测因子与 test(best) 的相关性（n=5，仅提示性）：

| 预测因子 | Pearson |
|---|---|
| **窗口大小** | **+0.771** |
| inner skill 字符数 | −0.571 |
| accept 次数 | −0.469 |
| 写入编辑总条数 | −0.391 |
| 门控调用次数 | −0.374 |

**窗口大小是唯一接近线性的正因子**；v2 的证据密度（3.70 任务/编辑、0.83 失败/编辑）
几乎正好落在 K=20 与 K=40 之间——而**它的 test 分数（0.7907）也落在 K=10 与 K=20 之间**，
比按证据密度应有的位置还要低。

v2 的 14 次尝试窗口序列：
`60, 10, 30, 50, 10, 30, 30, 30, 40, 20, 10, 110, 30, 10`

**其中 4 次只有 10 个任务**（step 2/5/11/14），1 次 20 个（step 10）。
K=80 的 10 次窗口**全部恰好 80 个任务**。

**为什么这直接伤害质量**：内层 reflect 阶段据以归纳"缺陷"的证据只有 2 个失败样本、
却要写 4–6 条通用规则。step 2 就是这样：10 个任务、2 个失败、写了 4 条编辑。

### 4.2 原因二：小窗口让一条**有害规则通过了门控**（**本版重写**）

#### 4.2.1 先撤回初版的分析

初版写的是"v2 缺少冲突消解条款、而 K=20/40/80 有"，这是**错的**：

1. **配对错误**：回归数取自 `test_eval`（= **best** skill 的评测），而"有无冲突条款"取自
   `skills/skill_v{last}`（= **final** skill，且含 slow block）——不是同一个 skill。
2. **修正后**：K=80 的 `Override Brevity Rules When Conflicted` 位于
   **epoch-2 的 slow block 内部**（第 4991 字符起，而 slow block 从 3687 字符开始），
   它的 **inner skill 里根本没有这条**。K=80 的 inner skill（3687 字符）是全场最简洁的之一。

#### 4.2.2 修正后的真相：同一条规则，两个条件，相反的命运

一条具体的规则——"保留完整正式名称/头衔"（如 `Drake` → `Sir Francis Drake`）——
被**两个条件都提出过**，因为它们都反复观察到同一类失败：

| 观测到的失败 | 次数（v2 / k80） |
|---|---|
| `Pelican` → `Brown pelican` | 2 / 2 |
| `China` → `(The People's Republic of) China` | 2 / 2 |
| `Isaac Newton` → `Sir Isaac Newton` | 2 / 2 |
| `Superior` → `Lake Superior` | 2 / 2 |
| `Drake` / `Francis Drake` → `Sir Francis Drake` | 2 / 1 |

**但两个条件的结局完全相反：**

| 条件 | step | 窗口 | 支持失败数 | 门控结果 | val 变化 |
|---|---|---|---|---|---|
| **K=80** | 3 | 80 | **16** | **reject** | 0.78 → 0.755 |
| **K=80** | 6 | 80 | 8 | **reject** | 0.795 → 0.750 |
| **K=80** | 7 | 80 | 16 | **reject** | 0.795 → 0.775 |
| **K=80** | 10 | 80 | 6 | **reject** | 0.795 → 0.775 |
| **Controller v2** | 2 | **10** | **2** | **accept_new_best** | 0.760 → 0.760（+1 题） |

K=80 的大窗口把这条规则写得更"证据充分"（16 个支持样本），**依然被 200 题门控连续拒绝
4 次**，于是它的 skill 保持简洁。v2 用 **10 个任务、2 个支持失败样本**提出同一条规则，
**一次就通过了门控**，从此 inner skill 里多了一条与既有规则矛盾的条款：

```
- Exact Match Priority: ... Do not expand abbreviations, add titles, middle
  initials, or prepend/append names unless explicitly stated.
- Trivia/Quiz Format: ... If the clue implies a full formal name or title
  present in the context, preserve it rather than defaulting to a surname.
```

**这是本方法最清晰的失效路径：控制器的小窗口不仅让"证据不足就动手"，
还让一条在固定 K 下会被稳定拒绝的有害规则溜进了 skill。**

#### 4.2.3 但要诚实：这条规则本身不是差距的主因

我做了决定性检验——在全新 rollout 上评测规则翻转前后的两个 skill：

| skill | test(1400) |
|---|---|
| v2 step1（**规则翻转前**） | 0.7914 |
| v2 step2（**规则翻转后**） | 0.7957 |

配对结果：step2 相对 step1 **净 +6 题**（34 对 / 28 错），**在噪声带 ±15 题之内**。

**所以：这条规则既没有显著伤害，也没有显著帮助。它不能解释 2.4pp 的差距。**
它是个**症状**（说明小窗口能让坏规则通过门控），不是**病因**。

各条件 best skill 的过扩写回归占比（修正配对后）：

| 条件 | best inner 含"求简短"族 | 含"求完整"族 | 过扩写/回归 |
|---|---|---|---|
| K=10 | 5 | 0 | 9/36 = 25% |
| K=20 | 5 | 0 | 7/45 = 16% |
| K=40 | 3 | 0 | 4/27 = 15% |
| **K=80** | 3 | 0 | 5/26 = 19% |
| **v2** | 6 | 1 | **10/35 = 29%** |

**v2 是唯一同时含两个矛盾规则族的条件**，其过扩写回归占比也最高。
但 n=1，且上述决定性检验显示单条规则的影响在噪声内——**此条只能作为提示，不能作为结论。**

### 4.3 原因三：41% 的证据被丢弃（fixed-K 的丢弃是 0）

以**任务**为单位（避免观测批次大小不同的混淆）：

| 条件 | 流出的任务 | 真正进入优化器窗口 | 占比 |
|---|---|---|---|
| K=10 / 20 / 40 / **K=80** | 800 | **800** | **100%** |
| **Controller v2** | 800 | **470** | **59%** |

v2 的 330 个被丢弃任务，逐项来源（可由 `summary.json["evolution"]` 复算）：

| 来源 | 数量 | 原因 |
|---|---|---|
| **epoch-1 边界作废** | **220 任务（22 观测）** | epoch-1 末端 slow update 注入 placeholder → skill hash 变化 → "证据属于旧 skill 版本" → 整个 buffer 作废 |
| 去稀释丢弃 | 50 任务（5 个零失败观测） | 设计行为：窗口内有失败批次时丢弃全成功批次 |
| run 结束时仍在 buffer | 60 任务（6 观测） | epoch-2 结束后没有下一次尝试 |

**这不是 bug，是设计**：homogeneous-skill buffer 是正确性要求。但在 **train 池只有 400 个
任务**的规模下，代价极其昂贵。

**最大的一笔浪费来自"控制器的谨慎 + reset 语义"的叠加**：epoch-1 的最后一次尝试在 obs 18，
之后控制器**连续 22 次 WAIT**（`evolution_decisions.jsonl` 里 obs19–40 的理由几乎全是
"重复的过扩写模式，已在既有假设中记录"），这 22 个观测（220 个任务）在 epoch-2 一开始被
整体作废——**它们从未被任何优化器看过**。

**另一个对比**：v2 在 epoch-2 用 9 次尝试重看了 310 个任务（train 池只有 400 个），
即**同一个池被反复、重叠地重看**；K=80 用 5 次尝试、每次不重叠地看满 80 个任务。
**v2 既看得更少（470 < 800）、又更重复。**

### 4.4 原因四：门控在 v2 的候选上基本无法分辨好坏

**这是本版用正确口径重算后最刺眼的发现。**

先看 val 集的判别力：200 题的 val 集标准误 ≈ 5.9 题；**同一个 skill** 的两次独立评测
平均相差 **10.8 题**（实测：5 个 run 的 baseline 两两不一致 8–15 题）。
门控判据是 `cand_score > current_score`（严格大于），即 **+1 题就算改进**。

**把全部 5 个条件的 27 次 accept 的 val 增量列出来：**

| 条件 | 每次 accept 的 val 增量（题） |
|---|---|
| K=10 | 1, 2, 1, 1, 2, 1, 2, 1, 1, 1 |
| K=20 | **17**, 1, 2, 1 |
| K=40 | 6, 2, 2, 3, 1, 3 |
| K=80 | 9, 3 |
| v2 | 5, 1, 1, 1, 2 |

> **27 次"接受"中，只有 1 次（K=20 step1 的 +17 题）超过了 val 噪声带。
> 其余 26 次（96%）都落在"同一个 skill 重测就能产生"的抖动范围内。**

这意味着**整个门控机制在这套 val 规模下近乎失效**——包括 fixed-K 条件。
v2 的问题在于它**暴露给这个失效门控的次数和多样性更高**：

- v2 提交 **14 次**候选，其中 **5 次窗口 ≤ 20 任务**；K=80 只提交 10 次、每次都 80 任务；
- 小窗口 → 候选更"随机" → 在噪声门控下更容易被接受。

**已在同 run 内配对验证的一次误接受**（全新 rollout 复现）：

| skill | 来源 | 复现 test |
|---|---|---|
| step 5（epoch-1 末，即 v2 的 epoch-1 best） | `repl_best/v2_ep1` | **0.8000** |
| step 8（epoch-2 中，被门控以 **+2 题** val 接受为 new best） | `repl_best/v2_best` | 0.7929 |

配对：step 8 相对 step 5 —— **24 题变好、34 题变差，净 −10 题**。
门控用 +2 题的噪声接受了它，test 上净亏 10 题。

---

## 5. 把四条原因串成一句话

> 控制器的**判断**基本是对的（它准确、反复地指出了过扩写缺陷），
> 但它把"语义上连贯的 2–3 个失败案例"当成了"统计上充分的证据"，
> 于是在 10–40 个任务的小窗口上频繁动手；
> 而**下游的门控在这套 val 规模下根本分辨不出好坏（27 次接受里 26 次在噪声内）**，
> 于是小窗口既产生了质量更差的候选、
> 又让一条在 K=80 下被稳定拒绝 4 次的有害规则一次通过；
> 同时 41% 的证据被丢弃（epoch 边界作废 + 去稀释 + 结束遗留），
> 最终它比 K=80 少看了 330 个任务的证据、写了 27 条更多规则、准确率低 2.5pp（final 口径）、3.1pp（best 口径，独立复现）。

**最重要的结论（与初版相同，且本版证据更强）：**

**该方法的失效点不在"何时更新"的判断逻辑本身，而在"证据充分性"缺乏统计意义上的
量级校准（无阈值这一设计约束的直接后果），以及它把决策权交给了一个分辨率不足的门控。**

初版把重心放在"编辑空间只会追加规则"上，本版**下调**该因素：决定性检验显示单条规则
翻转的影响在噪声内（+6 题），因此"更新动作缺乏消解冲突能力"是**次要**因素。

---

## 6. 可证伪的实验设计（请专家重点看这一节）

以下实验成本可控（单条件 30–120 分钟）。**实验 A/D 是当前最值得先做的两个。**

### 实验 A：消除"窗口太薄"（对原因 1，**最高优先级**）
- 把 `m` 从 10 提到 **20 / 40**，其余不变。
- **预测**：若原因 1 成立，v2@m=40 的 test 应显著上升并接近 K=80；控制器触发次数下降。
- **反向预测**：若 m 提上去后 v2 仍落后，说明问题不在窗口大小。
- **为什么优先级最高**：窗口大小是唯一与 test 强相关的因子（Pearson **+0.771**），
  且它是四个原因中唯一能通过**单参数改动**直接检验的。

### 实验 D：修门控（对原因 4，**与 A 同等优先级**）
- 27 次 accept 里 26 次在噪声内 → 门控实际上没有在筛选。
- 改法：判据改为"必须超过噪声带"（如 +2~3 题）、或 k 折重复评测取均值、
  或把 val 从 200 提到 500+。
- **预测**：v2 的 accept 从 5 次降到 2–3 次，test 净收益上升；**所有 fixed-K 条件也会同时受益**。
- ⚠️ 这会同时改变所有条件，必须作为**独立变量**单独报告，不能与 A 混跑。

### 实验 B：消除"证据丢弃"（对原因 3）
- 在 slow update 注入 placeholder 时**保留下 buffer**（placeholder 不改变 skill 的语义行为），
  或打开 `max_buffer_observations`（例如 20）做安全阀。
- **预测**：v2 的有效证据量从 470 → 接近 800。

### 实验 C：验证"同一条规则两种命运"是否可复现（对原因 2）
- 现在只有 n=1。**把 5 个条件各重跑 3 个 seed**，检查：
  (a) "保留全名"规则是否总在 v2 的小窗口下被接受、在 K=80 的大窗口下被拒绝；
  (b) 该规则接受后 test 是否变化（本次测到 +6 题，在噪声内）。
- **预测**：若 (a) 可复现而 (b) 仍不可测，则原因 2 是**症状而非病因**，应从结论中剔除。

### 实验 E：验证"窗口大小 vs test"的相关性（当前最强的一条）
- 已有 5 个点给出 +0.771。**在 K=5 / 15 / 30 / 60 上补 4 个点**，
  看曲线是否单调、是否在某个 K 之后饱和。
- **预测**：若曲线在 K≈40–80 之间饱和，说明 v2 只要把 m 提到 40 即可接近最优；
  若持续上升，说明 K 本身（而非"自适应"）就是主要变量，主张需要重新表述。

---

## 7. 需要专家判断的四个开放问题

1. **"无阈值"是否是个错误的设计约束？**
   当前方法刻意不含任何数值阈值（为了让主张表述为"语义判断"）。
   但原因 1 显示：控制器无法区分"2 个高度相似的失败"与"16 个多样化的失败"——
   而后者恰好是 K=80 能稳定拒绝坏规则的**唯一原因**。
   是否应该允许**有界的**量级信息（如把窗口任务数、独立失败数作为输入的一部分），
   同时仍不设硬阈值？

2. **当前实验设计能否真正区分"自适应调度"与"K 的选择"？**
   如果实验 E 显示 window size 与 test 是单调关系，那么"自适应"的价值可能只体现在
   **它是否稳定地停在最优 K 附近**，而不是"自适应"本身。
   如何设计实验才能把这两者分开？

3. **门控的分辨率不足是"环境缺陷"还是"方法缺陷"？**
   200 题 val 在 EM 精度 ~0.78 下只有 5.9 题标准误。如果把 val 扩到 1400，
   门控会变好——但那样 token 成本会翻数倍。
   在"门控必须便宜"的前提下，调度算法应当如何补偿门控的噪声？
   （例如：小窗口时**提高**接受门槛，大窗口时才用默认门槛。）

4. **cycle reset 的语义在"证据稀缺"场景下是否应当放宽？**
   当前保证窗口内 skill 同质（正确性），代价是 41% 的证据浪费。
   是否存在"证据可以跨 skill 版本、但标注版本"的表示方式？

---

## 8. 数据可靠性审计（5 个 run 全部通过）

| 检查项 | 结果 |
|---|---|
| 重复执行同一观测（两进程混流事故特征） | 0 处 |
| `[OBS n]` 起止配对（started == done） | 全部配对 |
| 观测产物数量 == 期望（400/K × 2 epoch） | 全部相符 |
| 每个观测的 `results.jsonl` 条数 == m | 全部相符 |
| `history.json` 尝试数 == `summary.evolution.total_attempts` | 全部相符 |
| `evolution_decisions.jsonl` 行数 == `total_decisions` | 全部相符 |
| `trigger_intervals.attempt_tasks` == 各 `step_record.window_tasks` 之和 | 全部相符 |
| 重复 candidate（同一 skill 被评测两次） | 0 处 |

### 8.1 两处必须说明的口径陷阱（初版分析在此出错）

1. **`history.json` 的 `current_score` 是门控*之后*的值**，不是尝试前的值。
   因此"accept 到底涨了多少"必须从 **log 的 `[6/6 EVALUATE]` 行**取：
   ```
   [6/6 EVALUATE] ACCEPT (new best) hard=0.7550 > prev best 0.7300
   ```
   初版用 `history.json` 相减，把 v2 step1 的 **+5 题**读成了 **+0 题**，
   并由此得出了错误的"全部 accept 都是 0.000"结论。
2. **回归数对应的是 best skill，就必须用 best skill 的文本**去解释它，
   不能用 final skill（含 slow block）的文本。初版的"冲突消解条款"分析即栽在这里。

### 8.2 token 口径

`summary.json` 的 `tokens` 字段只是**最后一个进程**的统计，**不可直接使用**。
本文档的 token = 阶段一 log + 阶段二 log + 重评段（跨进程累加）。

### 8.3 阶段一（仅 epoch 1）结果

| 条件 | tokens | test(1400) |
|---|---|---|
| K=10 | 46.1M | 0.7936 |
| K=20 | 22.7M | 0.8093 |
| K=40 | 19.0M | 0.8071 |
| **K=80** | 15.6M | **0.8229** |
| **Controller v2** | **13.3M** | 0.7993 |

单 epoch 下 v2 是**最省的**（比 K=80 少 15%），但准确率低 2.4pp。
**v2 在两个 epoch 都比 K=80 更"勤快"（5+9=14 次 vs 5+5=10 次），但每一次的收益都更小。**

---

## 9. 独立复现评测汇总（全新 out_root，同 1400 题）

| skill | 来源 | test | soft |
|---|---|---|---|
| v2 step1（规则翻转前） | `repl_rule/v2_step1` | 0.7914 | 0.8698 |
| v2 step2（规则翻转后） | `repl_rule/v2_step2` | 0.7957 | 0.8728 |
| v2 ep1 / step5 | `repl_best/v2_ep1` | **0.8000** | 0.8765 |
| v2 best / step8 | `repl_best/v2_best` | 0.7929 | 0.8716 |
| v2 final（含 slow） | `repl_rule/v2_final` | 0.7850 | 0.8660 |
| k80 best / step5 | `repl_best/k80_best` | **0.8243** | 0.8928 |
| k80 final（含 slow） | `repl_best/k80_final` | 0.8179 | 0.8893 |

同 init skill、同 1400 题、5 次独立评测的**评测噪声**：两两不一致 59–82 题（均值 68.8），
最大有符号不对称 **15 题**。

**在已评测的 v2 skill 中，最好的是 epoch-1 的 step5（0.8000）**，而 K=80 的 step5 是 0.8243。
两者配对对比：**K=80 对而 v2 错 71 题，v2 对而 K=80 错 37 题，不对称 34 题 > 噪声上界 15 题**。
**即使用 v2 全程最好的 skill 去比，差距依然是真实的**，且 note：
v2 的 epoch-1 skill 反而好于它 epoch-2 的 skill（0.8000 vs 0.7929）——
**第二个 epoch 对它是有害的。**

---

## 10. 原始产物索引

| 路径 | 内容 |
|---|---|
| `tmp/ete_real_runs/ps_{k10,k20,k40,k80,v2}/` | 5 个条件的完整 run 产物 |
| `.../history.json` | 每次尝试的记录（⚠️ `current_score` 是门控后的值） |
| `.../evolution_decisions.jsonl` | 控制器的每一次 WAIT/UPDATE + 理由全文 |
| `.../steps/step_*/ranked_edits.json` | 每次尝试实际写入的编辑（op + target + support_count） |
| `.../steps/step_*/step_record.json` | 窗口构成（obs_indices / window_tasks / 去稀释丢弃数） |
| `.../skills/skill_v*.md` | 每个 skill 版本（含被拒绝后的回滚状态） |
| `tmp/ete_real_runs/repl_best/` | 独立复现：v2 ep1/best、k80 best/final（全新 rollout） |
| `tmp/ete_real_runs/repl_rule/` | 独立复现：v2 step1/step2（规则翻转检验）、v2 final |
| `tmp/ete_real_runs/paper_scale_k_sweep.png` | 主图（双纵轴：tokens / test hard） |
| `tmp/ete_real_runs/FINAL_NUMBERS.txt` | 本文档全部数字的机械提取结果 |
| `tmp/ete_real_runs/replicate_v2_vs_k80.sh` | 差距复现脚本 |
| `tmp/ete_real_runs/replicate_rule_flip.sh` | 规则翻转检验脚本 |
| `repos/SkillOptETE/skillopt/evolution_controller.py` | 控制器实现（914 行） |
| `repos/SkillOptETE/docs/evolution-controller.md` | 方法文档与全部实验结果 |
