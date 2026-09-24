# FUSE Skill Evolution on ALFWorld — Runbook

本文件记录 SkillEvolveCPM 的 FUSE 方法在本仓库 ALFWorld 评测栈上的适配协议、
固定输入、命令与验收规则。方法原论文义与差异见文末「与原 FUSE 的映射与偏离」。

## 概念映射

| FUSE (Terminal-Bench 2) | 本适配 (ALFWorld) |
| --- | --- |
| task(instruction.md + environment/) | episode(gamefile;instruction = 初始观测) |
| 失败公开轨迹 JSONL | `--record-trajectory` 的 `trajectories/<id>.json`,导出时**剥离每步 won/done** |
| reward == 1.0 | `EpisodeResult.success == True` |
| Skill 目录挂载(`/opt/openclaw-skills`) | 单文件 Markdown 经 `## Skill Knowledge` 前缀注入(`--skill-path`) |
| 「Skill 被读取」验收 | 不适用:本 harness 由宿主强制注入;等价物 = `summary.json.skill` 的 sha256 溯源 |
| OpenClaw 会话(Harbor + Docker/E2B) | 本地工具循环会话(list_files/read_file/write_file,workspace 只读,写仅限 result/) |
| 43 SOP family(能力聚类) | **family := task_type**(6 类,确定性路由);capability 聚类仍做,作为证据组织 |
| 每 task 3 attempts、2/3 通过 | 每 episode 3 attempts(3 次独立驱动运行)、严格多数通过 |
| infrastructure_unresolved | 缺失结果行的 attempt;绝不计为 regression |

## 固定输入(2026-09-17 起)

```text
parent skill:   src/alfworld_eval/skills_docs/skillopt_alfworld.md (sha256 c8219398…,论文产物)
baseline run:   outputs/fuse_baseline_train/merged (39 局 train,skillopt,qwen3.6-flash-distill,seed 42)
会话模型:        qwen3.6-flash-distill(benchmark/llm_config.json 的 alfworld-eval 段)
执行模型:        qwen3.6-flash-distill(与基线同)
演化输出:        outputs/fuse_run/
split 纪律:      train(39) 演化与验证;valid_seen(18) 选择门;valid_unseen(134) 只做终报
```

## 阶段与命令

### 0. 基线(已完成)

```bash
.venv/bin/python scripts/run_eval_concurrent.py --method skillopt --shards 8 \
  --base-url "$ALF_ENDPOINT" --model "$ALF_MODEL" --api-key-env ALF_LLM_KEY \
  --warmup-ramp 1,2,4,8 --shard-stagger 1.5 --out-base outputs/fuse_baseline_train \
  --unified-args "--split train --items $P/train/items.json --seed 42 --record-trajectory"
```

### 1-8. 演化(`scripts/run_fuse_evolution.py`)

```bash
# 查看阶段完成状态
.venv/bin/python scripts/run_fuse_evolution.py status --out outputs/fuse_run

# 全流程(export → diagnose → tag → cluster → author → validate → accept → stage)
.venv/bin/python scripts/run_fuse_evolution.py all \
  --baseline-run outputs/fuse_baseline_train/merged \
  --parent-skill src/alfworld_eval/skills_docs/skillopt_alfworld.md \
  --out outputs/fuse_run --attempts 3 --shards 8

# 单阶段(全部幂等可续跑;--types 限定 task_type;--limit 冒烟)
.venv/bin/python scripts/run_fuse_evolution.py export   --out outputs/fuse_run …
.venv/bin/python scripts/run_fuse_evolution.py diagnose --out outputs/fuse_run …
.venv/bin/python scripts/run_fuse_evolution.py tag      --out outputs/fuse_run …
.venv/bin/python scripts/run_fuse_evolution.py cluster  --out outputs/fuse_run …
.venv/bin/python scripts/run_fuse_evolution.py author   --out outputs/fuse_run …
.venv/bin/python scripts/run_fuse_evolution.py validate --out outputs/fuse_run …
.venv/bin/python scripts/run_fuse_evolution.py accept   --out outputs/fuse_run …
.venv/bin/python scripts/run_fuse_evolution.py stage    --out outputs/fuse_run
```

产物结构:

```text
outputs/fuse_run/
  manifest.jsonl              # incident_id / outcome / task_type / gamefile / 轨迹 / 诊断
  source/<incident_id>.jsonl  # 公开轨迹(已剥 won/done)
  diagnoses/<incident_id>/{diagnosis.md, session/}
  tagging/{incidents/*/tags.json, tags.jsonl, clusters.json, clustering_session/}
  skills/<task_type>/{skill.md, session/attempt-N/}
  validations/<task_type>/attempt-{1..3}/   # 每簇每 attempt 一个完整驱动运行
  report.json                 # 每簇 status/gains/regressions + 汇总
  staged_skills/<task_type>.md  # 发布集:accepted 用 candidate,其余回退 parent
```

### 9. 选择门与终报(val / test)

```bash
# staged 系统(fuse 路由)× 3 attempts
for i in 1 2 3; do
  .venv/bin/python scripts/run_eval_concurrent.py --method fuse --shards 16 \
    --base-url "$ALF_ENDPOINT" --model "$ALF_MODEL" --api-key-env ALF_LLM_KEY \
    $([ $i -gt 1 ] && echo --skip-warmup) \
    --out-base outputs/fuse_val_gate/attempt-$i \
    --unified-args "--split valid_seen --items $P/val/items.json --seed 42"
done
# parent 基线同样 ×3(对照),test 134 局同理(--split valid_unseen --items $P/test/items.json)
# 合并比较用 scripts/compare_runs.py + 逐 episode 配对
```

注意:fuse 方法的 `--skill-dir` 指向 `outputs/fuse_run/staged_skills`。

## 验收规则(与原 FUSE 一致,适配处标注)

1. episode 通过 = 3 attempts 中严格多数成功(≥2);
2. `regression` = 基线成功 → 未通过(且无缺失 attempt);
3. `gain` = 基线失败 → 通过;
4. 任一 attempt 结果行缺失 → 该 episode 记 `infrastructure_unresolved`,
   **绝不**计为 regression(原 FUSE 的 infra 分离规则);
5. 簇 `accepted` ⇔ 无 regression 且(有失败证据时 ≥1 gain;无失败证据时全员通过);
6. authoring/静态校验失败 → 带错误反馈重试一次;两次失败记 `generation_failed`;
7. 发布集只收 `accepted` 的 candidate,其余 task_type 回退 parent skill
   (比原 FUSE 更保守:原文保留 validation_failed 的 Skill)。

## 实测时间线与成本(2026-09-17,qwen3.6-flash-distill)

| 阶段 | 覆盖 | 墙钟 | 备注 |
| --- | --- | --- | --- |
| 基线(skillopt train ×1) | 39 局 | 1425s | 82.05%(32/39),7 失败,729 API 调用 |
| 会话阶段(diagnose 7 + tag 39 + cluster 1 + author 6) | 53 会话 | ~22 min | author 1 次静态重试(超字数) |
| train 验证(6 类 × 3 attempts) | 117 局 | ~34 min | 18 次驱动运行,零 infra 缺失 |
| accept + stage | - | <5s | 2 accepted / 4 validation_failed |
| val 门(staged ×3 + parent ×3) | 108 局 | ~41 min | 16/18 vs 16/18,零 gain/regression |
| test(staged ×3 + parent ×3) | 804 局 | 133 min | **staged 84.08% vs parent 81.84%(avg@3);多数门 111 vs 110;McNemar p=1.000 不显著** |

## 第二轮演化实测(2026-09-17 晚)

```bash
# 准备 round2(复制数据产物、算 round1 发布系统成绩 33/39、验证摘要、regression 局)
.venv/bin/python scripts/prepare_fuse_round2.py --round1 outputs/fuse_run --round2 outputs/fuse_run_round2
# 诊断(7 缓存 + 2 regression 局)→ author(parent = round1 staged)→ validate → accept → stage
#   详见 /tmp/fuse_round2_stages.sh 的调用形式(CLI 参数 --parent-skill-dir /
#   --extra-diagnoses / --validation-summary / --baseline-outcomes)
```

- round2 验收(vs round1 发布系统 33/39):look、pick_and_place 再次 accepted;
  cool 修复 2 个 round1 失败局但保留 1 个 regression 被无回归门拒绝;
- round2 test(vs round1 ×3):83.58% vs 84.08%(avg@3)/ 112 vs 111(多数门),
  p=1.000 不显著——两口径方向相反,即噪声量级;
- 三层终测:parent 81.84% → round1 84.08% → round2 83.58%(avg@3),
  累计 +1.74pt 在噪声带内;结论与局限见
  `docs/reports/fuse_skillevolution_adaptation.md`。

## 实测验收结果(train 验证门)

| task_type | status | 判定依据 |
| --- | --- | --- |
| look_at_obj_in_light | **accepted** | 5/5 通过,1 gain(基线失败局 3/3 转成功) |
| pick_and_place | **accepted** | 7/7 通过,零回归 |
| pick_clean | validation_failed | 有失败证据但无 gain(基线失败局仍失败) |
| pick_cool | validation_failed | 1 regression(Pan-27 局) |
| pick_heat | validation_failed | 有失败证据但无 gain |
| pick_two_obj | validation_failed | 1 regression(CD-Drawer-319 局) |

发布集(staged_skills/):look、pick_and_place 用 candidate;其余 4 类回退 parent。

## val 选择门实测

staged 16/18 vs parent 16/18(3 attempts 多数门,逐局配对):
both_pass 16 / neither 2 / gain 0 / regression 0 / infra 0。
两个 neither 局(clean、heat 各 1)两系统均未通过。单次 attempt 的波动
(83% vs 94%)在 3 次多数门下完全抹平——印证 temperature=0 不可复现的已知结论。

- **family := task_type**:原 FUSE 的 family 由能力聚类提议 + 审核产生(43 簇);
  本适配按用户决策固定为 6 个 task_type(确定性路由,skillrl 有先例),能力聚类
  仍运行,但只作为 authoring 的证据组织,不决定发布边界。
- **会话运行时**:Harbor/Docker/E2B/原生 OpenClaw → 本地 OpenAI 兼容工具循环
  (trace2skill analyst 模式)。完成契约保留(必须用 write 工具写 result 文件),
  会话产物以 transcript.jsonl + audit.json 替代 openclaw-state。
- **「Skill 被读取」判据不适用**(注入式 vs 挂载式),以 sha256 注入溯源替代。
- **split 纪律更严格**:原 TB2 实验用同一批 task 验证;本适配按本仓库
  `docs/SKILL_EVOLUTION_EXPERIMENT_EVALUATION_CN.md` 的要求分
  演化(train)/选择(val)/终报(test)三段。
- **随机性**:端点 temperature=0 不可复现(README 实测),故 3-attempt 多数门
  是必需协议而非可选。
