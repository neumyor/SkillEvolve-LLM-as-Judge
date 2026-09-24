# SearchQA 实验诊断信息清单（Controller v2 vs fixed K）

> 位置基准：本地实验目录（例如 `$ETE_RUNS_ROOT`）；具体路径由运行者配置。
> 本文只列**实际存在**的文件，并标注每个文件能回答什么问题、有什么坑。
> 总占用约 **1.2 GB**，其中 `steps/` 与 `test_eval*/` 的 rollout 轨迹占绝大部分。

---

## 0. 一张图：数据在哪里

```
tmp/ete_real_runs/
├── ps_{k10,k20,k40,k80,v2}/        ← 五个条件的完整 run（主数据，427M/208M/165M/119M/156M）
│   ├── config.json                 ← 该 run 的确切配置（可复算"条件是否真的是这个条件"）
│   ├── summary.json                ← 顶层汇总：test 分数、token、evolution 全账本
│   ├── history.json                ← 每次尝试一行（1717 行/条件）
│   ├── evolution_decisions.jsonl   ← 控制器的每次决策 + 理由全文 + 证据状态
│   ├── evolution_state.json        ← 跑完时的持久化状态（buffer、attempt_log、trigger_intervals）
│   ├── runtime_state.json          ← resume 用（9 行）
│   ├── best_skill.md               ← val 上最好的 skill
│   ├── skills/skill_vNNNN.md       ← 每个 skill 版本
│   ├── observations/obs_NNNNN/     ← 每个观测批次：3 类文件（见 §3）
│   ├── steps/step_NNNN/            ← 每次尝试（= 一次演化）：7 类文件（见 §4）
│   ├── selection_eval_baseline/    ← init skill 在 200 题 val 上的评测
│   ├── final_selection_eval/       ← 最终 skill 在 200 题 val 上的评测
│   ├── test_eval_baseline/         ← init skill 在 1400 题 test 上
│   ├── test_eval/                  ← best skill 在 1400 题 test 上
│   ├── test_eval_final/            ← final skill 在 1400 题 test 上
│   ├── slow_update/epoch_0N/       ← epoch 级 slow update（§6）
│   └── meta_skill/epoch_0N/        ← epoch 级 meta skill（§6）
├── ps_*.log                        ← 阶段一（epoch 1）完整 stdout
├── ps_*_ep2.log                    ← 阶段二（epoch 2）+ 测试重评，**两段**（§7）
├── repl_best/                      ← 独立复现：v2 ep1/best、k80 best/final
├── repl_rule/                      ← 独立复现：v2 step1/step2/final（规则翻转检验）
├── rr_*.log / repl_*.log           ← 上述复现的 stdout
└── 脚本与图表（§8）
```

---

## 1. 每个条件的顶层状态文件

### 1.1 `summary.json`（20K，583 行）—— 最该先看的文件

| 键 | 内容 |
|---|---|
| `config` | 该 run 的完整生效配置（backend / model / seed / 各超参） |
| `tokens` | ⚠️ **只是最后一个进程**的统计，**不可直接用**（见 §7） |
| `evolution.mode` / `policy` / `observation_batch_size` | 调度身份（`fixed_k` / `controller`） |
| `evolution.total_decisions` / `total_attempts` | 决策数与尝试数（可与 jsonl 行数对账） |
| `evolution.trigger_intervals[]` | **每个窗口的完整账本**：`observations`、`tasks`、`attempt_observations`、`attempt_tasks`、`dropped_zero_failure_observations`、`action` |
| `evolution.attempt_log[]` | 每次尝试：`tasks_consumed`、`val_before`/`val_after`、`candidate_score`、`edits_applied[]`（op + target 摘要） |
| `evolution.leftover_buffer_observations` / `_tasks` | 跑完时仍留在 buffer 里的证据（v2 = 6 obs / 60 tasks） |
| `baseline_test_hard` / `test_hard` / `final_test_hard` | 三个 test 口径的分数 |
| `best_step` | val 最优的 step 号 |

> **用途**：算"每个窗口多大 / 有多少证据被丢弃 / 每次尝试的 val 变化 / test 三口径"。
> `trigger_intervals` 是复算 §4.1 的 470 vs 800 的唯一权威来源。

### 1.2 `history.json`（48K，1717 行）—— 每次尝试的详细记录

每次尝试一个对象，含：

- `step` / `epoch` / `step_in_epoch`
- `timing`：`rollout_s` / `reflect_s` / `aggregate_s` / `select_s` / `update_s` / `evaluate_s`
- `tokens`：按阶段拆（`rollout` / `analyst` / `merge` / `ranking` / `evolution_controller`，各含 `calls`/`prompt_tokens`/`completion_tokens`）
- `evolution.window_tasks` / `obs_indices` / `dropped_zero_failure_*` / `controller_reason`
- `rollout_hard` / `rollout_soft` / `rollout_n`（**窗口内**的成功率——算"窗口内失败数"用这个）
- `n_patches` / `n_failure_patches` / `n_success_patches`
- `n_edits_merged` / `n_edits_ranked` / `edit_budget`
- `support_counts[]`（每条编辑的证据支持数）
- `candidate_hash` / `candidate_skill_len` / `skill_len`
- `edit_apply_summary`（total/applied/skipped/errors）
- `selection_hard` / `selection_soft` / `candidate_gate_score` / `action` / `current_score` / `best_score` / `best_step` / `current_origin` / `best_origin`
- `wall_time_s`

> ⚠️ **最大的坑**：`action`、`current_score`、`best_score` 是**门控执行之后**的结果。
> 因此 `current_score` 在 accept 的条目里**已经等于** `candidate_gate_score`。
> **不要用 history.json 相减算"这次 accept 涨了多少"** —— 会得到恒为 0 的错误结论
> （我上一版分析就栽在这里，把 v2 step1 的 +5 题读成了 +0）。
> **正确来源是 log 的 `[6/6 EVALUATE]` 行**（§7.3），那里有真正的 `prev best` / `current`。

### 1.3 `evolution_decisions.jsonl`（212K，82 行）—— 控制器视角的完整轨迹

每行一次决策，字段：

- `global_obs_index` / `epoch` / `obs_in_epoch` / `epoch_end`
- `policy` / `action`（`WAIT` / `UPDATE`）
- **`reason`** —— 控制器给出的完整理由段落（诊断"它看到了什么、为什么不动手"直接读这个）
- **`evidence_state`** —— 控制器的语义记忆 `M_t`：
  `hypotheses[]`（`defect` / `supporting_cases[]` / `counter_cases[]` / `assessment`）+ `unresolved`
- `n_new` / `buffer_observations` / `buffer_tasks`
- **`skill_hash`** —— 该观测所用 skill 版本的 sha256 前 16 位
- `meta`：`view` / `parse_attempts` / `trigger`

> **这是诊断控制器行为的主文件**。epoch-1 那 22 次连续 WAIT 的理由、以及
> "它在 epoch-2 反复指出过扩写"的证据，全部在这里。
>
> **`skill_hash` 的一个必须知道的用法**：`observations/obs_NNNNN/` 目录里
> **不记录**该观测用的是哪个 skill 版本。要建立
> 「观测 → skill 版本」的映射，必须用 `skill_hash` 去匹配
> `skills/skill_vNNNN.md` 的 sha256[:16]。
> 已实测：**5 个条件中 4 个全部可映射；v2 有 1 个 hash（`396433aeef59a2ee`）只存在于
> `steps/step_0005/candidate_skill.md`**（因为 epoch-1 末的 slow update 在写盘前改了它），
> 这类 hash 需要同时搜 `steps/*/candidate_skill.md`。

### 1.4 `evolution_state.json`（20K，560 行）—— 跑完时的持久化快照

顶层键：`mode` / `policy` / `observation_batch_size` / `global_obs_index` / `epoch` /
`obs_in_epoch` / `last_epoch_end_decided` / **`buffer[]`** / **`buffer_skill_hash`** /
`evidence_state` / `pending_decision` / `total_decisions` / `total_attempts` /
**`trigger_intervals`** / **`attempt_log`**

`buffer[]` 每条的字段：`obs_index` / `epoch` / `obs_in_epoch` / `batch_seed` / `n_envs` /
`dir` / `hard` / `soft` / `ids[]`（该批次的任务 id 列表）。

> **用途**：`buffer_skill_hash` 是复现"epoch 边界把 22 个观测整批作废"的关键——
> 它等于 `skill_v0008` 的 hash，而 epoch-1 用的是 `skill_v0005`，
> 两者差异正是 slow update 注入的 placeholder。
> `buffer[].ids` 可用于检查"哪些任务被 rollout 过但从未进入任何窗口"。

### 1.5 `runtime_state.json`（9 行）

`last_completed_step` / `current_skill_path` / `current_score` / `current_origin` /
`best_skill_path` / …。**resume 依赖它**；诊断时用来看"最终 current 是哪个 skill、
它的 origin 是 `step_000N` 还是 `slow_update_epoch_0N`"。

---

## 2. `skills/skill_vNNNN.md` —— 每个 skill 版本

- 命名：`skill_v0000.md` = init（104 字符），之后每完成一次尝试写一个版本
  （无论接受/拒绝，**拒绝后写回的是回滚后的 current**，所以会出现连续多版内容相同）。
- 版本数：k10 **81** / k20 **41** / k40 **21** / k80 **11** / v2 **15**。
- 文件可能包含 `<!-- SLOW_UPDATE_START --> ... <!-- SLOW_UPDATE_END -->` 段
  （epoch ≥2 写完 slow update 之后）。
  **做"skill 文本 vs 表现"的分析时必须先切掉这段**，否则会把 slow block 的内容
  误当成 inner skill 的规则（我上一版分析的第二个错误就栽在这里）。
- `best_skill.md` = val 最优的那个 skill（独立一份）。

> ⚠️ **版本号 ≠ 一次尝试**：v2 有 14 次尝试但 15 个版本文件（v0000 是 init）。
> k80 有 10 次尝试、11 个版本。数量关系是 `版本数 = 尝试数 + 1`，
> 但**中间会出现内容完全相同的连续版本**（拒绝回滚），
> 所以不能用"版本文件内容变化"来判断"有没有发生尝试"。

---

## 3. `observations/obs_NNNNN/` —— 每个观测批次（诊断的最底层原始数据）

| 文件 | 内容 |
|---|---|
| `rollout/results.jsonl` | **该批次每个任务一行**：`id`/`question`/`em`/`f1`/`sub_em`/`hard`/`soft`/`predicted_answer`/`gold_answers`/`response`/`fail_reason`/`agent_ok`/`n_turns` |
| `rollout/predictions/<task_id>/` | 每个任务 3 个文件：`conversation.json`（完整轨迹）、`target_system_prompt.txt`、`target_user_prompt.txt` |
| `obs_results.json` | 与 `results.jsonl` 同构的 list（10/20/40/80 条） |
| `patches/minibatch_fail_NNN.json` | 每个失败 minibatch 一个：`batch_size` / **`failure_summary[]`**（`failure_type` / `count` / `description`）/ `patch`（reflect 产物）/ `source_type` |
| `patches/minibatch_succ_NNN.json` | 成功 minibatch 的对照 patch |

**规模**：文件数随 K 线性变化——k10/v2 每观测 **34** 个文件，k20 **65**，k40 **128**，k80 **253**。

**每个条件的观测数与总任务数完全一致**：

| 条件 | 观测目录数 | 任务总数 | `conversation.json` 总数 |
|---|---|---|---|
| k10 | 80 | 800 | 800 |
| k20 | 40 | 800 | 800 |
| k40 | 20 | 800 | 800 |
| k80 | 10 | 800 | 800 |
| v2 | 80 | 800 | 800 |

> **用途**：
> - 算"窗口内失败数"（用 `results.jsonl` 的 `hard`）；
> - 复现"同类失败出现了几次"（我用来做规则翻转检验的那类分析）；
> - **`patches/*/failure_summary[].failure_type` 是被很少使用但很有价值的标签**——
>   已实测各条件的分布：
>   k10 `rule_missing=58, rule_wrong=20, rule_ignored=18, answer_format=15`；
>   k80 `rule_wrong=19, rule_missing=17, answer_format=11, rule_ignored=10`；
>   v2 `rule_missing=35, rule_ignored=12, rule_wrong=10, answer_format=8`。
>   **v2 的 `rule_missing` 占比显著偏高（53% vs k80 的 26%）**，
>   而 k80 更多是 `rule_wrong`——这条线索目前还没有被写进任何分析，值得单独挖。
> - `target_system_prompt.txt` 可用来**逐字确认该观测实际喂给模型的是哪个 skill 文本**
>   （已实测：把某个 skill 版本文件内容 `in` 这个 prompt，能唯一定位版本）。

---

## 4. `steps/step_NNNN/` —— 每次演化尝试（一次 UPDATE）

每个目录 7 类文件：

| 文件 | 内容 |
|---|---|
| **`step_record.json`** | **最全的单次尝试记录**。见下方字段表 |
| **`ranked_edits.json`** | select 阶段的产物：`reasoning` + `edits[]`，每条含 `op` / `target` / `content` / `support_count` / `source_type` |
| `merged_patch.json` | aggregate 阶段合并后的 patch（与 ranked_edits 同构） |
| `edit_apply_report.json` | update 阶段每条编辑的应用结果：`op` / `target` / `content_preview` / `status`（`applied_replace` 等）/ `index` |
| `candidate_skill.md` | 本次尝试产生的候选 skill（**接受前**） |
| `trajectory_digest.json` | `step` / `action` / `n_total` / `n_fail` / `failure_patterns[]`（`pattern` / `count` / `task_ids`） |
| `selection_eval/` | 候选 skill 在 **200 题 val** 上的评测：`results.jsonl` + `predictions/`（**601 个文件**，约 3.4M/step） |

**`step_record.json` 的字段**（已实测 v2 step2）：

```
step, epoch, step_in_epoch
timing.{rollout_s, reflect_s, aggregate_s, select_s, update_s, evaluate_s}
tokens.{analyst, evolution_controller, merge, rollout}.{calls, prompt_tokens, completion_tokens}
evolution.{mode, policy, trigger, controller_reason, n_observations, window_tasks,
           obs_indices[], dropped_zero_failure_observations, dropped_zero_failure_tasks}
rollout_hard, rollout_soft, rollout_n
accumulation_batches[].{batch_idx, batch_seed, n_envs, hard, soft,
                        n_failure_patches, n_success_patches}
n_patches, n_failure_patches, n_success_patches
n_edits_merged, n_edits_ranked, edit_budget, lr_control_mode, support_counts[]
candidate_hash, candidate_skill_len, edit_apply_summary.{total, applied, skipped, errors}
selection_hard, selection_soft, gate_metric, candidate_gate_score
action, current_score, best_score, best_step, current_origin, best_origin
skill_len, wall_time_s
```

> **用途**：
> - `evolution.window_tasks` + `obs_indices` → **权威的窗口构成**（比 summary 更细）；
> - `ranked_edits.json` 的 `op`/`support_count` → 复算"编辑空间的操作类型分布"
>   （实测 5 条件合计 618 条：`replace` 304 / `insert_after` 245 / `append` 69 / **`delete` 0**）；
> - **`evolution.controller_reason` 也在这里存了一份**（便于按 step 对齐控制器意图）；
> - `selection_eval/` 是复现"门控为什么接受/拒绝"的唯一途径（可对同一候选重算分数）。

> ⚠️ **`steps/` 是占用大头**：k10 因为 80 次尝试累积到 **323M**（占该 run 75%），
> k80 只有 32M。做磁盘清理时不要误删（这是唯一的门控原始证据）。

---

## 5. 评测目录（三个口径 × 两个 split）

| 目录 | skill | split | 大小 | 用途 |
|---|---|---|---|---|
| `selection_eval_baseline/` | init | val 200 | 3.4M | val 基线；**同时是噪声带的测量材料**（5 个 run 同一 skill） |
| `final_selection_eval/` | final | val 200 | 3.4M | val 终值 |
| `test_eval_baseline/` | init | test 1400 | 19M | test 基线（三口径对比的锚） |
| `test_eval/` | **best** | test 1400 | 24–30M | "best skill"口径 |
| `test_eval_final/` | **final** | test 1400 | 24–30M | "final skill"口径（含 slow block） |
| `steps/*/selection_eval/` | 每个候选 | val 200 | 各 3.4M | 门控判据来源 |

每个目录结构一致：`results.jsonl`（逐题）+ `predictions/<id>/{conversation.json,target_*.txt}`；
顶层三个另有 `summary.json`（`overall.hard_acc`）。

> **交叉诊断的用法**：`test_eval_baseline` 在 5 个条件里评的是**逐字节相同**的 init skill，
> 因此它的两两不一致（8–15 题）就是**评测噪声的实测值**，
> 这是判断任何差距是否真实的基准。（另可用 `selection_eval_baseline/` 得到 val 上的噪声：
> 两两 8–15 题、均值 10.8 题。）

---

## 6. `slow_update/` 与 `meta_skill/`

```
slow_update/epoch_01/slow_result.json          ← epoch 1：placeholder（no-op）
slow_update/epoch_02/
    ├── slow_result.json                       ← 真实的纵向比较结果（含完整 reasoning）
    ├── comparison_pairs.json                  ← 采样的 20 个训练任务
    ├── rollout_prev/                          ← 用「上一个 skill」在这些任务上的 rollout
    └── candidate_skill.md                     ← slow update 产生的候选
meta_skill/epoch_01/  meta_skill/epoch_02/     ← meta skill 产物
```

> **用途**：
> - `slow_result.json` 的 `reasoning` 是**诊断 epoch-2 退化原因的一手材料**——
>   v2 的那份明确写着 "aggressive over-stripping ... 'Sir Francis Drake' ... dropping
>   honorifics"，即 slow update **自己**也识别出了与 v2 的 `Exact Match Priority`
>   直接冲突的问题，并写入了相反的指令；
> - `rollout_prev/results.jsonl` 可复算"prev skill vs current skill"在同一批任务上的差异。

---

## 7. 日志（`ps_*.log` / `ps_*_ep2.log`）

### 7.1 分段结构（**必须知道**）

| 文件 | 段数 | 内容 |
|---|---|---|
| `ps_<cond>.log` | 1 段 | 阶段一（epoch 1），末尾一个 `total tokens:` |
| `ps_<cond>_ep2.log` | **2 段** | ① 阶段二（epoch 2）；② **测试重评段**（因缓存污染而补跑） |

每段以 `total tokens: N (prompt=… completion=… calls=…)` 结束。
**跨进程累加 token 必须把全部段的数字相加**，`summary.json` 的 `tokens` 只有最后一段。

### 7.2 可 grep 的关键锚点（已实测计数，v2 为例）

| 模式 | v2 命中 | 用途 |
|---|---|---|
| `\[OBS N\] epoch` | 80 | 观测开始 |
| `\[OBS N done\]` | 80 | 观测结束（**起止配对**用于完整性审计） |
| `\[6/6 EVALUATE\]` | 28 | **门控判据的唯一可信来源**（见 §7.3） |
| `dropping .* stale` | 1 | **epoch 边界作废 buffer 的那一行**（v2 为 "dropping 22 stale observation(s)"） |
| `de-diluted` | 4 | 去稀释丢弃 |
| `total tokens:` | 3 | token 分段 |
| `SLOW UPDATE` / `META SKILL` | 6 / 5 | epoch 级机制执行 |
| `resumed` | 6 | resume 生效点（确认没有重跑） |

### 7.3 `[6/6 EVALUATE]` 行 —— 门控的真实判据

```
[6/6 EVALUATE] ACCEPT (new best) hard=0.7550 > prev best 0.7300
[6/6 EVALUATE] REJECT            hard=0.7600 <= current=0.7650
```

> **这是唯一能算"这次 accept 涨了多少"的地方**。全 5 条件共 164 次门控
> （k10 80 / k20 40 / k40 20 / k80 10 / v2 14），其中 27 次 accept。
> 已从这个来源算出：**27 次 accept 中只有 1 次（k20 step1 的 +17 题）
> 超出 val 噪声带（均值 10.8 题）**，其余 26 次都在噪声内。

### 7.4 驱动脚本的 stdout

`ps_driver.log` / `ps_ep2_driver.log` / `ps_ep2fix_driver.log` 只有几行 exit code 与时间戳，
确认阶段一 21:59→02:12、阶段二与重评的完成时刻。**无诊断价值，但可证明没有中途重启。**

---

## 8. 脚本、图表与复现产物

| 路径 | 内容 |
|---|---|
| `run_searchqa_paper_scale.sh` | **阶段一的完整命令**（可复算"配置是否真的是论文口径"，注释里写明了全部对齐项） |
| `run_searchqa_paper_scale_ep2.sh` | 阶段二（`--num_epochs 2` resume） |
| `fix_paper_scale_ep2_tests.sh` | 测试重评（删污染缓存后零训练成本 resume） |
| `analyze_paper_scale.py` | 主结果分析（输出 `paper_scale_rows.json` 与主图） |
| `paper_scale_rows.json` | 主图的数据（10 行 = 5 条件 × 2 phase，含 test/test_best/tokens/attempts） |
| `paper_scale_k_sweep.png` | 主图（双纵轴：tokens / test hard，横轴 K） |
| `replicate_v2_vs_k80.sh` | 差距复现（4 个 skill × 全新 rollout） |
| `replicate_rule_flip.sh` | 规则翻转检验（v2 step1 vs step2 vs final） |
| `repl_best/{v2_ep1,v2_best,k80_best,k80_final}/` | 上述复现的产物（各含 `eval_summary.json` + `results.jsonl` + `predictions/`） |
| `repl_rule/{v2_step1,v2_step2,v2_final}/` | 同上 |
| `FINAL_NUMBERS.txt` | 本文档全部数字的机械提取结果（可重跑核对） |
| `warmup_concurrency.py` | 并发预热（为什么选 workers=64） |
| `analyze_v2_fixes.py` / `probe_v1_decisions_ab.py` | v1 与修复主题分析（**v1 时代产物**，不是 v2 paper-scale） |

---

## 9. 数据（在 repo 内，不在 tmp）

| 路径 | 内容 |
|---|---|
| `repos/SkillOptETE/data/searchqa_id_split/` | 原论文 ID 清单（`train`/`val`/`test/items.json` + `split_manifest.json`，400/200/1400，只有 id） |
| `repos/SkillOptETE/data/searchqa_split/` | **实际可运行的数据**：`train/items.json`(1.6M, 400 条) / `val`(0.8M, 200) / `test`(5.6M, 1400)，字段 `id`/`question`/`context`/`answers` |
| `repos/SkillOptETE/scripts/materialize_searchqa.py` | 从 ID 清单还原可运行 split 的脚本 |
| `repos/SkillOptETE/configs/searchqa/default.yaml` | 基座配置（`train_size 400`, `batch_size 40`, `learning_rate 4`, minibatch 8, merge 8） |
| `benchmark/llm_config.json` → `searchqa-eval` | endpoint / model（`qwen3.6-flash-distill`）；api_key 不在此文档记录 |

---

## 10. 各条件共有 vs 独有的关键量（速查）

| 量 | k10 | k20 | k40 | k80 | v2 |
|---|---|---|---|---|---|
| 观测目录 / 任务 | 80 / 800 | 40 / 800 | 20 / 800 | 10 / 800 | 80 / 800 |
| 尝试数（`history.json` 行数） | 80 | 40 | 20 | 10 | 14 |
| 窗口任务合计 | 800 | 800 | 800 | 800 | **470** |
| 窗口内失败合计 | 163 | 159 | 167 | 172 | 105 |
| 写入编辑合计 | 352 | 217 | 161 | 100 | 127 |
| 门控次数 / accept | 80 / 10 | 40 / 4 | 20 / 6 | 10 / 2 | 14 / 5 |
| skill 版本文件数 | 81 | 41 | 21 | 11 | 15 |
| `steps/` 占用 | 323M | 123M | 71M | 32M | 55M |
| `evolution_decisions.jsonl` 行数 | 80 | 40 | 20 | 10 | 82 |

> ⚠️ **只有 v2 的决策行数（82）= 观测数（80）+ 2 个 epoch 边界 consult**；
> fixed-K 条件的决策只记在 `trigger_intervals` 里，`evolution_decisions.jsonl`
> 行数等于尝试数（没有 WAIT 决策，因为 fixed_k 不产生 WAIT）。

---

## 11. 三条最容易踩的坑（总结）

1. **`history.json` 的 `current_score` / `best_score` / `action` 是门控之后的值**。
   要算门控增量，只能读 log 的 `[6/6 EVALUATE]` 行。用 history 相减会得到恒为 0。
2. **skill 文本必须先切掉 `<!-- SLOW_UPDATE_START -->…<!-- SLOW_UPDATE_END -->`**，
   且**回归数（来自 `test_eval`，best skill）只能配 best skill 的文本**——
   拿 final skill 的文本去解释 best skill 的回归是配对错误。
3. **token 必须跨进程累加**（阶段一 log + 阶段二 log 的**两段**），
   `summary.json` 的 `tokens` 只有最后一段，直接使用会低估。
