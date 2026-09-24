# ALFWorld Evaluation

这是一个独立的 ALFWorld 评测环境仓库，使用 `uv` 管理 Python、依赖和锁文件，
使用 Git 管理实现与评测协议版本。

评测环境是**可复现的 TextWorld 文本评测环境**（`AlfredTWEnv`，不依赖 AI2-THOR、
视觉检测器或 GPU），已包含统一方法评测（vanilla / skillopt / trace2skill / skillrl）
与多并发批量执行（warmup + shard 并发 + 合并）。视觉环境 `AlfredThorEnv`、模型权重训练
不在范围内。

## 快速开始

```bash
export ALFWORLD_DATA="$PWD/.data/alfworld"
uv sync --frozen
uv run alfworld-download
uv run python scripts/check_environment.py
uv run python scripts/smoke_textworld.py --split valid_seen --steps 1
```

ALFWorld 数据是外部资产，不进入 Git。若数据不在默认目录：

```bash
export ALFWORLD_DATA="/absolute/path/to/alfworld"
```

目录中应至少包含：

```text
$ALFWORLD_DATA/
├── json_2.1.1/
│   ├── train/
│   ├── valid_seen/
│   └── valid_unseen/
└── logic/
    ├── alfred.pddl
    └── alfred.twl2
```

完整设计与分阶段实施方式见 [BUILD.md](BUILD.md)。

## Docker 启动注意事项

在 Docker 中运行真实 API 评测时，请注意：

- 当前镜像固定为 `linux/amd64`。Apple Silicon 主机上会通过模拟运行并显示平台警告，这是预期现象，但速度会较慢。
- 容器内请使用 `/opt/alfworld-eval/.venv/bin/python`，不要依赖可能被 login shell 覆盖的系统 `python`。
- `ALFWORLD_DATA` 必须指向包含 `json_2.1.1/` 和 `logic/` 的数据根目录。镜像默认值为 `/opt/alfworld-eval/.data/alfworld`。
- `items.json` 中的 `gamefile` 是相对于 `ALFWORLD_DATA` 的路径；`--split` 必须与清单对应，分别使用 `train`、`valid_seen` 或 `valid_unseen`。该一致性现已硬校验，不匹配会直接退出（见下文"切分口径与覆盖率"）。
- 代码修改后，调试时要挂载最新的 `src/` 和 `scripts/`；否则容器可能仍执行镜像中旧版本代码。
- `--base-url` 只填写本地配置中的 API 基础地址，程序会自动追加 `/chat/completions`。
- API key 推荐通过容器环境变量传入，并使用 `--api-key-env` 读取。不要在宿主 shell 中提前展开一个不存在的变量，否则会得到 `401 Unauthorized`。
- 不要把真实 API key 写入 README、脚本或日志。已经暴露过的 key 应立即撤销并重新生成。

本地 Docker 镜像可按以下方式构建：

```bash
docker buildx build --platform linux/amd64 \
    --build-context wheels=.wheels-cache \
    -t alfworld-eval:local --load .
```

完整的容器排障记录见 [DOCKER_TROUBLESHOOTING.md](DOCKER_TROUBLESHOOTING.md)。

## 统一方法评测（vanilla / skillopt / trace2skill / skillrl）

`src/alfworld_eval/unified/` 在同一 TextWorld 引擎与同一
`<think>...</think><action>...</action>` 协议（SkillRL/SkillOpt 共用）上，
对四种方法做横向对比评测。默认模型请求使用 `max_tokens=4096`；若首次
响应格式或动作校验失败，系统会把确定性诊断信息回传给模型，最多允许一次
修正，修正仍失败才执行安全的 `look` 回退动作。

| 方法 | Skill 来源 | 注入方式 |
|------|-----------|---------|
| `vanilla` | 无 | 纯基座模型 |
| `skillopt` | `src/alfworld_eval/skills_docs/skillopt_alfworld.md`（官方发布 skill） | 用户消息前缀（`## Skill Knowledge`） |
| `trace2skill` | `src/alfworld_eval/skills_docs/trace2skill_alfworld.md`（占位，需自行生成） | 同 skillopt |
| `skillrl` | `src/alfworld_eval/skills_docs/skillrl_claude_style_skills.json`（官方 SkillBank） | 按任务类别渲染 `## Retrieved Relevant Experience` |

本仓库的评测约定是 **同一基座模型、同一协议、只替换 skill 注入**，以便把三种方法的
差异隔离到 skill 本身。这与各论文原始配置**不同**（见下文每节"与论文的差异"）。

> **要跑一次完整评测，直接看
> [复现操作手册](#复现操作手册skillopt-与-trace2skill-端到端)**：SkillOpt 直接评测；
> **Trace2Skill 是"先训练（步骤 3）再测试（步骤 4）"两段式，每次复现都要自己训一份 skill**。
> 手册给出按顺序执行的命令、每步的验收标准、实测预算表与踩坑清单。
> 下面各节是方法背景与上游口径差异，不是操作顺序。

通用调用形式：

```bash
export ALFWORLD_DATA="$PWD/.data/alfworld"
# 从仓库根目录的 benchmark/llm_config.local.json 读取本机配置
export ALF_ENDPOINT="$(python3 -c 'import json;print(json.load(open("../../benchmark/llm_config.local.json"))["alfworld-eval"]["base_url"])')"
export ALF_MODEL="$(python3 -c 'import json;print(json.load(open("../../benchmark/llm_config.local.json"))["alfworld-eval"]["model"])')"
export ALF_LLM_KEY="$(python3 -c 'import json;print(json.load(open("../../benchmark/llm_config.local.json"))["alfworld-eval"]["api_key"])')"

uv run python scripts/run_unified_eval.py \
    --method <vanilla|skillopt|trace2skill|skillrl> \
    --backend api --base-url "$ALF_ENDPOINT" --model "$ALF_MODEL" \
    --api-key-env ALF_LLM_KEY \
    --split <train|valid_seen|valid_unseen> --items <manifest> --limit 3
```

`--skill-path` 覆盖 skillopt/trace2skill 的 Markdown skill，`--skillrl-bank-path`
覆盖 skillrl 的 SkillBank JSON（**两者不可混用**：给 skillrl 传 `--skill-path`
不会生效）。

输出写入 `outputs/unified_<method>_<时间戳>/`：`results.jsonl`（逐局）、
`summary.json`（6 类子任务成功率、整体成功率、平均步数、非法动作率、token 用量、
`split_provenance`）、`--record-trajectory` 额外保存逐步交互。

`summary.json` 的 `skill` 字段记录**实际注入的 skill 文档**的路径、`sha256` 与字符数。
只记路径是不够的：skill 文档是可被后续步骤改写的文件（Trace2Skill 的归纳会重写它，且端点不确定——
同一批 memory 重跑会得到另一份文档），路径只能说明"从哪读的"，不能说明"读到了哪一版"，
分数就可能被归因到它从没见过的内容上。旧的运行没有这个字段，可用
`sha256sum <skill>` 对照运行目录下手工钉的摘要文件。

### 多并发评测（warmup + shard 并发 + 合并）

`run_unified_eval.py` 是单进程单局串行的（`AlfredTWEnv` 以 `batch_size=1` 构建），
所以并发粒度是**进程**：N 个进程各自带 `--num-shards N --shard-index i`，把同一份
items.json 切成互不重叠的条带，跑完再合并。三个脚本把这件事包成一条命令：

| 脚本 | 作用 |
|---|---|
| `scripts/warmup_endpoint.py` | 先单发探活（401/404 直接退出），再按 `--ramp` 逐级压测，报告每级 429 率与中位延迟，给出可用的最大并发 |
| `scripts/run_eval_concurrent.py` | warmup → 按测得的并发起 N 个 shard（带启动错峰）→ 全部结束后调 `merge_shards.py` 合并 |
| `scripts/sample_manifest.py` | 按六类任务分层抽样，供小规模测试使用 |

```bash
uv run python scripts/run_eval_concurrent.py --method skillopt --shards auto \
    --base-url "$ALF_ENDPOINT" --model "$ALF_MODEL" --api-key-env ALF_LLM_KEY \
    --warmup-ramp 1,2,4,8,16 --shard-stagger 1.0 \
    --out-base outputs/final_skillopt \
    --unified-args "--split valid_unseen --items .../test/items.json --seed 42 --record-trajectory"
```

要点：

- **必须 warmup**：网关对冷启动的并发请求返回 429。agent 自己会退避重试（5 次，
  `2^i` 加抖动），但整批 shard 同时冷启动会把开头几分钟耗在重试上。warmup 先打几发
  单请求、再逐级升并发，实测各级 429 率；`--shards auto` 取最高干净档位。实测该端点
  在 c=1..32 均无 429（报告见各运行目录下的 `warmup.json`）。
- warmup 发的是短请求，衡量的是**请求速率**容忍度，不等于长 prompt/长输出下的吞吐；
  想更保守就显式给 `--shards`（超过 warmup 实测值时会给出警告）。
- 每个 shard 写到 `shard<i>of<N>/`，日志在 `logs/shard<i>of<N>.log`（driver 会设
  `PYTHONUNBUFFERED=1`，否则逐局进度会卡在缓冲区里看不见）。合并前
  `merge_shards.py` 会校验各 shard 覆盖同一语料（`corpus_fingerprint`）、无重叠、
  无缺失；不齐时可 `--allow-incomplete`，或直接重跑——每局都有断点续跑。
- 有 shard 失败不会被静默吞掉：driver 报出失败编号并以非 0 退出，且**不合并**。
- 小规模测试不要直接 `--limit`：SkillOpt 清单按任务类型聚集（`test` 前 6 条全是
  `look_at_obj_in_light` 且同属一个 trial 目录），只截前 N 条会把单一任务类型的
  成功率当成整体成绩。用 `sample_manifest.py --per-type K` 分层抽样。

#### 端点并行（一个 shard 用多台服务）

`--base-url` 接受**逗号分隔的列表**。每个 shard 会为列表里每个端点各建一个 agent，
按 episode 轮转使用，因此 N 个 shard 能把负载摊到多台服务上，而**不需要改动切分逻辑**
（各 shard 仍是同一份语料的一个条带，`merge_shards.py` 的校验照旧成立）。

```bash
uv run python scripts/run_eval_concurrent.py --method skillopt --shards 8 \
    --base-url "http://127.0.0.1:8004/v1,http://127.0.0.1:8005/v1,http://127.0.0.1:8006/v1" \
    ...
```

要点：

- 单端点（不带逗号）时行为与以前完全一致：只有一个 agent，没有轮转。
- 每个 shard 的起始端点是 `(shard_index + seed) % len(urls)`，相邻 shard 从不同端点
  起步，此后逐 episode 轮转。
- `--shards auto` 的 warmup 会**逐个端点**探活，取各端点干净并发档位的**最小值**
  （整体吞吐由最冷的端点决定），各端点报告分别写到 `warmup_<i>.json`。
- 该列表会记进 `run_meta.json` 的 `base_urls`。

**实测（本地 vLLM，18 局 `valid_seen`，全部 0 API 错误）**：

| 配置 | 墙钟 | 说明 |
|---|---|---|
| 1 端点 × 4 shard | 96s | 434 次调用 |
| 4 端点 × 4 shard | 115s | 470 次调用；4 个端点计数器分别 +189/+157/+97/+62，**分发已验证覆盖全部端点** |
| 4 端点 × 8 shard | 85s | 469 次调用 |

**结论：端点并行是有效的（流量确实摊到了多台服务），但它不是这个 workload 的加速杠杆。**
瓶颈是 **prompt token 总量**：ALFWorld 每局都要把完整历史反复喂回去，18 局约产生 1.5M
prompt tokens（约 17k token/s 的量级），而每局内部是单进程串行的。因此要更快应该先加
**shard 数**（进程级并行，受 CPU 与端点数量约束）；加端点只在「shard 数已经超过单台服务
吞吐」时才有收益。要显著加速，应考虑**压缩历史长度**而不是继续堆服务。

这些计时**不含 warmup**（`--skip-warmup`）；对真实网关跑时 warmup 是必需的，
且端点越多 warmup 总耗时越长。

Trace2Skill 的**生成**阶段同样可并发（分析器是逐个 workspace 串行跑的，是最慢的
一段）：先跑一次 `--skip-analysis --skip-consolidate` 只建 workspace，再起 N 个进程
`--skip-prepare --skip-consolidate --analysis-shards N --analysis-shard-index i`
各分析自己那一片，最后单独一次调用做归纳（不加 `--skip-analysis/--skip-consolidate`）。

### 方法一：SkillOpt
**上游复现材料（本仓库可直接使用）**

| 材料 | 上游路径 | 作用 |
|---|---|---|
| 论文 skill 产物 | `ckpt/alfworld/gpt5.5_skill.md` | 论文 Table 1 中 GPT-5.5 优化后的 skill |
| 环境配置 | `configs/alfworld/default.yaml` | `max_steps: 50`、`split_mode: split_dir` |
| 切分清单 | `data/alfworld_path_split/{train,val,test}` | 39/18/134，**唯一可直接当 `--split_dir` 用**的清单 |
| 只评不训入口 | `scripts/eval_only.py` | 用给定 skill 评一个 split |
| 重训入口 | `scripts/train.py` / `scripts/run_alfworld.sh`（**只有训练，无评测模式**） | 自己训一份 skill |

上游**没有印出过 ALFWorld 的评测命令行**：`README.md` 全文不含 ALFWorld；
`ckpt/README.md` 只给了 SearchQA 的例子，并说"替换 benchmark、config、skill
路径和 `--split_dir` 即可评其余五个"。按该替换规则，ALFWorld 等价命令是：

```bash
python scripts/eval_only.py \
  --config configs/alfworld/default.yaml \
  --skill ckpt/alfworld/gpt5.5_skill.md \
  --split valid_unseen \
  --target_model gpt-5.5
```

（`configs/alfworld/default.yaml` 已含 `split_dir: data/alfworld_path_split`，
故 `--split_dir` 可省。`--split` 默认 `all`，会依次跑 train + valid_seen +
valid_unseen 共 **191** 局；`valid_unseen` 单独为 **134** 局。）

**在本仓库评测 SkillOpt**（`skillopt_alfworld.md` 与上游 `ckpt/alfworld/gpt5.5_skill.md`
SHA-256 相同，`c8219398...`，即所用的就是论文产物本身）：

```bash
uv run python scripts/run_unified_eval.py --method skillopt --backend api \
    --base-url "$ALF_ENDPOINT" --model "$ALF_MODEL" --api-key-env ALF_LLM_KEY \
    --split valid_unseen \
    --items ../../skillopt/data/alfworld_path_split/test/items.json
```

**与论文的差异（必须说明）**

- 论文数值来自 `gpt-5.5`（Azure OpenAI）。上游 `eval_only.py` 的 `--backend`
  可选值里**没有通用 OpenAI 兼容后端**，但它支持
  `--target_backend openai_compatible`（或
  `--cfg-options model.target_backend=openai_compatible`）配合环境变量
  `OPENAI_COMPATIBLE_BASE_URL` / `_API_KEY` / `_MODEL`——见上游
  `docs/guide/new-backend.md`。因此换端点复现时，**不应用本仓库的分数与论文直接对比**。
- 仓库内的 skill 是用 `optimizer.slow_update_gate_with_selection: true` 产出的；
  上游 `main` 现在默认 `false`。用当前默认重训会得到**不同的** `best_skill.md`。
- skill 文档末尾带 `SLOW_UPDATE` 段，这是刻意的纵向指导，不是格式错误。
- **上游不训练权重，也没有权重可下**：`ckpt/` 下 6 个文件全是 Markdown skill 文档
  （ALFWorld 那个 13,179 字节），全仓库没有任何 `.pt/.safetensors/.bin`。
  "可训练的状态"就是 skill 文档本身（`skill_init: .../skills/initial.md`）。
  所以 SkillOpt 与 SkillRL 的复现形态**根本不同**：前者是"冻结模型 + 换 skill"，
  后者是"换权重 + 换提示"。
- **采样参数不同**：上游 rollout 用 `temperature: 0.4`、
  `max_completion_tokens: 16384`；本仓库默认 `--temperature 0` 和
  `--max-tokens 4096`。要贴论文口径需显式传参（尤其推理模型输出很长，
  `--max-tokens` 太小会截断——见下文「推理模型与 `--max-tokens`」）。
- 重训一轮 = 4 个 epoch × 39 局（`batch_size: 40` → `steps_per_epoch = 1`），
  selection 固定 `valid_seen`（18 局），test 固定 `valid_unseen`（134 局）。

### 方法二：SkillRL

**上游复现材料**

| 材料 | 上游位置 | 作用 |
|---|---|---|
| SFT 权重 | `https://huggingface.co/Jianwen/Alfworld-7B-SFT` | 论文的 SFT 起点 |
| RL 权重 | `https://huggingface.co/Jianwen/Alfworld-7B-RL` | 论文的最终模型 |
| SkillBank | `memory_data/alfworld/claude_style_skills.json` | 分层技能库 |
| SFT 数据 | `https://huggingface.co/Jianwen/SkillRL-SFT-Data` | 复现 SFT |

上游官方命令（`README.md`）：

```bash
export MODEL_PATH=YOUR_SFT_CKPT      # 或 Jianwen/Alfworld-7B-RL
bash examples/grpo_trainer/run_alfworld_skills.sh
```

**本仓库只复现"SkillBank 提示"这一半。** SkillRL 的完整方法 = 微调权重 **+** SkillBank
提示；权重不在本仓库内（也没有随仓库分发）。我们的
`skillrl_claude_style_skills.json` 与上游
`memory_data/alfworld/claude_style_skills.json` SHA-256 相同（`e8a953be...`），
所以**提示侧是保真的，权重侧缺失**。

要用上权重，把 checkpoint 用 vLLM / SGLang 等起成 OpenAI 兼容服务，
再把 `--base-url` / `--model` 指过去，`--method` 保持 `skillrl`：

```bash
# 另一终端：vllm serve Jianwen/Alfworld-7B-RL --port 8000
uv run python scripts/run_unified_eval.py --method skillrl --backend api \
    --base-url http://127.0.0.1:8000/v1 --model Jianwen/Alfworld-7B-RL \
    --split valid_unseen \
    --items ../../skillopt/data/alfworld_path_split/test/items.json
```

**与论文的差异（必须说明）**

- 上游**没有独立评测脚本**：评测发生在 RL trainer 的验证循环里
  （`trainer.test_freq`），skill 脚本的 `val_data_size=64`、基线脚本为 `128`；
  默认 split 是 `eval_in_distribution`（= `valid_seen`，140 局）。本仓库用
  SkillOpt 的 134 局 `valid_unseen` 清单以保证跨方法同集，**这不等于 SkillRL 的评测口径**。
- **首步注入差异**：上游 `ALFWORLD_TEMPLATE_WITH_MEMORY` 只从第 2 步开始生效
  （`env_manager.py` 中 `... and not init`），即**每局第一步没有 skill 块**；
  本仓库的 `NO_HIS` 模板同样带 `{skill_block}`，因此首步也注入了 skill。这是有意的
  统一化，但与原仓库不一致。
- 历史块格式（`[Observation N: '...', Action N: '...']`）已与上游
  `agent_system/memory/memory.py:94` 对齐。
- 上游的 SkillBank JSON 实际有 **4** 个顶层键（多一个 `metadata`），其 README
  写"three top-level keys"已过时；本仓库的渲染只用到前三个。

#### 在远程服务器上跑通（2026-09-15 全程实测）

复现前请将权重放在 `$CHECKPOINT_ROOT`（下载脚本与全部坑见仓库根
`REMOTE_SERVER.md`，量化数据见 `docs/reports/skillrl_alfworld_protocol_and_serving.md`）。
在本机私有环境中设置 `CHECKPOINT_ROOT`、`SKILLRL_ROOT`（SkillRL checkout）、
`SKILLRL_SHIM`（其 Python import shim）和 `VLLM_PYTHON`（vLLM 环境的 Python）；
不要将这些机器路径写回仓库。

**1. 起服务**（两个可同时驻留，各占一张 A800 约 41 GB，启动约 2 分钟）：

```bash
# SFT：标准 HF 权重，--model 必须指到 checkpoint-140 子目录
CUDA_VISIBLE_DEVICES=7 "$VLLM_PYTHON" -m vllm.entrypoints.openai.api_server \
  --model "$CHECKPOINT_ROOT/Alfworld-7B-SFT/checkpoint-140" \
  --served-model-name alfworld-sft --port 8001 --tensor-parallel-size 1 \
  --gpu-memory-utilization 0.50

# RL：上游发的是 verl FSDP 分片，不能直接 serve。先合并（约 1 分钟）再起：
cd "$SKILLRL_ROOT"
PYTHONPATH="$SKILLRL_SHIM" \
  "$VLLM_PYTHON" -u scripts/model_merger.py merge --backend fsdp \
  --local_dir "$CHECKPOINT_ROOT/Alfworld-7B-RL/actor" \
  --target_dir "$CHECKPOINT_ROOT/Alfworld-7B-RL-hf"

CUDA_VISIBLE_DEVICES=6 "$VLLM_PYTHON" -m vllm.entrypoints.openai.api_server \
  --model "$CHECKPOINT_ROOT/Alfworld-7B-RL-hf" \
  --served-model-name alfworld-rl --port 8002 --tensor-parallel-size 1 \
  --gpu-memory-utilization 0.50
```

三个坑（照旧命令必死）：merger **必须带 `merge` 子命令**，且 **`PYTHONPATH` 必须指向
`$SKILLRL_SHIM`**（`python scripts/xxx.py` 时 import 不到仓库根的 `verl/`）；服务必须
`setsid nohup ... > log 2>&1 < /dev/null &` 起，否则 ssh 一断就死；`--dtype` 不用加。

**2. 跑评测，必须在服务器上跑**（Mac→服务器单程 RTT ~100 ms，harness 的 urllib 每个
请求新建 TCP 连接，从本机跑每步白吃 ~0.2 s）。服务器上的 harness 要先与本地同步
（`tar czf - src configs scripts pyproject.toml | ssh ... 'tar xzf - -C $H'`，曾出现服务器副本过期导致 ImportError）：

```bash
H=packages/alfworld-eval
cd $H && export ALFWORLD_DATA=$H/.data/alfworld PYTHONPATH=$H/src ALF_LLM_KEY=dummy
# 本地 vLLM 无鉴权，但 warmup 强制要 key，export 一个假值即可

.venv/bin/python scripts/run_eval_concurrent.py --method skillrl --shards 16 \
  --base-url http://127.0.0.1:8002/v1 --model alfworld-rl --api-key-env ALF_LLM_KEY \
  --out-base outputs/skillrl_rl \
  --unified-args "--split valid_unseen \
    --items ../../skillopt/data/alfworld_path_split/test/items.json --seed 42"
# 结果在 outputs/skillrl_rl/merged/summary.json（warmup → 16 shard → 自动 merge）
```

**3. 预期结果与注意**（实测）：

- 134 局 × 16 shards 实测 **359 s**；32 shards 只快 21% 但每步慢 47%，取 16–24 即可，
  **单副本够用**（16 路时 p50 仅 0.56 s，服务侧还有约 2× 余量）。
- `invalid_request_rate ≈ 0.27/步` 是这套 ckpt + 技能块的**固有行为**（不注入技能
  时为 0）：实测缩小技能块 / 换上游模板 / 换上游指令三种修复**全部更差**，不要修，
  如实报告即可。
- temperature=0 在批处理下**不可复现**（同一批 128 局，16/32 shards 给出 0.680/0.703）：
  复现时固定 `--shards`，或多次运行取误差棒。
- **正式结果**（134/134 局 valid_unseen，16 shards，seed 42，2026-09-15，
  `outputs/final_skillrl_test/merged/summary.json` 与 `outputs/final_skillrl_sft_test/`）：

  | | 总体 | Pick(24) | Pick2(17) | Clean(31) | Heat(23) | Cool(21) | Look(18) |
  |---|---|---|---|---|---|---|---|
  | RL 权重（=SkillRL 本体） | **0.679**（91/134，23.3 步/局） | 0.625 | 0.529 | 0.645 | 0.696 | 0.857 | 0.722 |
  | SFT 权重（RL 起点，仅参考） | 0.134（18/134，44.4 步/局） | 0.250 | 0.118 | 0.097 | 0.000 | 0.191 | 0.167 |

  这是「RL 权重 + 发布版 44 条静态 SkillBank」的结果，与论文 89.9%（valid_seen +
  训练后 100 条库）**不可比**，差异清单见上文。SFT ckpt 在本协议下
  `invalid_request_rate=0.42`、平均 44 步/局，说明未经 RL 的起点在本协议下基本不可用，
  其 0.134 **不对应论文中的任何一行**。
- **归因**（2×2 对照：同权重同协议，只换 split × 是否注入技能，`outputs/final_vanilla_rl_*`
  与 `final_skillrl_val`）：技能在推理期 **+11.2pt**（unseen）/ **+14.3pt**（seen），
  与论文主张的 +12.3pt 同向同量级；split 差 **+12.8pt**；在 valid_seen 上我们的
  0.807 与论文 89.9 在统计上不可区分（若论文 n=64），且协议干净的局成功 0.879–0.886
  ≈ 论文水平。完整分解见 `docs/reports/skillrl_alfworld_protocol_and_serving.md` §6。
- 小规模试跑**不要用 `--limit`**：`items.json` 按任务类型分组，前缀只覆盖 2–3 类任务；
  用 `scripts/sample_manifest.py` 分层抽样。

### 方法三：Trace2Skill

**上游仓库没有 ALFWorld**（全仓库检索 `alfworld` 零命中，`released_skills/` 只有
SpreadsheetBench 的 `xlsx`），所以本仓库按上游流程的结构把它移植过来——这正是
`scripts/run_trace2skill.py` 做的事。

上游流程（SpreadsheetBench 版，供对照）：

```
① run_spreadsheetbench.py --agent cli_skill_preloaded   用种子 skill 跑轨迹
  → ② evaluate_with_official.py                          评测
  → ③ analyze_results.py                                 结果/日志配对
  → ④ analysis/run_{error,success}_analysis*.py          错误分析（ReAct+工具）/ 成功分析
  → ⑤ parse_{error,success}_analysis_outputs.py          解析成 JSON
  → ⑥ skill_evolver/run_parallel_skill_evolution.py      演化（MAP→REDUCE→TRANSLATION→APPLY→VERIFY）
  → ⑦ 用演化后的 skill 重跑 ① ②
```

三个坑：**③ 是必需的**（它把日志改名成 `*_SUCCEED.md`/`*_FAILED.md`，后续脚本只认这种
文件名）；**④ 的验证是关键闸门**（错误分析要**修好**产出、让比较器打印 `Result: PASS`
并写出 `evaluate_passed.flag`，该条失败才会被蒸馏进 skill，**没通过的一律丢弃**）；
**上游自身缺文件**（`data/spreadsheetbench_verified/`、`config/llm_api.json`、
`skills/skill-creator/scripts/quick_validate.py` 都不在仓库内，照抄命令会失败）。
演化的效果可量化：种子 `xlsx-35B/SKILL.md` 89 行 → 演化后 481 行并长出 13 个
`references/*.md`，即上游产物是**会"长大"的 skill 目录**。

> **移植保真度**：本仓库保留了上游"轨迹 → 结果配对 → 带验证器的分析 → 归纳"的结构与
> 那道 `evaluate_passed.flag` 闸门，但产物是**单份 Markdown**，不长出 `references/`。
> 复现的是流程与判据，不是"skill 目录"这一载体形态。

**本仓库的移植：两阶段（训练 → 测试）**。冒烟形态如下（`--limit 3`、串行、几分钟），
**正式复现的并发流程、闸门验收与预算见 [复现操作手册](#复现操作手册skillopt-与-trace2skill-端到端) 步骤 3~4**：

```bash
uv run python scripts/run_trace2skill.py \
    --base-url "$ALF_ENDPOINT" --model "$ALF_MODEL" --api-key "$ALF_LLM_KEY" \
    --train-items .../train/items.json --selection-items .../val/items.json \
    --test-items .../test/items.json --limit 3 --work-dir outputs/trace2skill_run
# 产出：trace2skill_alfworld.md（训练出的 skill）、provenance.json（覆盖率）、
#       analysis_summary.json（闸门通过率）、analysis_workspaces/*/{analysis_report.md,analyst_transcript.json}
```

`run_trace2skill.py` 用 `--api-key`（不是 `--api-key-env`），并**自己**驱动最后的评测
（`--skip-eval` 只做训练）；`--skip-train/--skip-prepare/--skip-analysis/--skip-consolidate`
用于复用已有产物。

**当前状态**：仓库内 `skills_docs/trace2skill_alfworld.md` 是**占位文档**，直接跑
`--method trace2skill` 只会注入它，**不构成 Trace2Skill 的评测**，必须先训练出真 skill。
两个与判据有关的机制：

- 每条错误分析都落 `analysis_workspaces/<episode>/analyst_transcript.json`（`outcome` 含
  `verified/verifier_calls/turns_used`），否则"没调验证器"与"调了多次都不通过"无法区分；
- 验证器的可采纳动作列表按"与失败动作的词元重合度"排序。ALFWorld 按语法拒绝动作
  （`put kettle 1 in cabinet 1` vs 可采纳的 `move kettle 1 to cabinet 1`），按环境顺序截断
  会把唯一能用的那条截掉——实测同一条失败轨迹：改前 30 轮不通过，改后 16 轮通过。

历史实测（`--limit 3`，`MiniCPM5-2B-0822`）：分析器 0/3 通过验证、0 条 memory、skill 退化成
seed 副本——**小模型会静默退化，`verified_rate` 就是判据**。

### 三种方法复现成功与否的判据

| 检查项 | SkillOpt | SkillRL | Trace2Skill |
|---|---|---|---|
| 注入内容非空 | `## Skill Knowledge` 在提示词中 | `## Retrieved Relevant Experience` 在提示词中 | 同 skillopt |
| 使用的是论文/上游产物 | skill 与 `ckpt/alfworld/gpt5.5_skill.md` 同哈希 | SkillBank 与上游同哈希（**权重另需自备**） | **需自己生成**，无官方产物 |
| 上游原始口径 | `gpt-5.5`，`eval_only.py` | 微调权重 + SkillBank，`valid_seen` 64 局/次 | SpreadsheetBench（ALFWorld 属移植） |
| summary 中应检查 | `split_provenance`、`max_steps`、`skill.sha256` | 同上 + `model` 是否为你服务的 ckpt | 同上 + `provenance.json` 的 `effective_episodes`、`analysis_summary.json` 的 `verified_rate` |

**任何跨方法对比都必须同时报出**：基座模型与端点、`--split` 与清单覆盖率（只有 `test`
是 134/134 完整）、采样参数与步数上限（50）、以及注入 skill 的 sha256 与体量。
**Trace2Skill 还要报训练侧**：训练清单条数（默认 39 局，官方 3553 局的子集）、种子 skill、
`verified_rate`、memory 条数——缺了它，"Trace2Skill 66%"无法回答"这是在多少条验证过的
经验上训出来的"，也就无法与他人的 Trace2Skill 并列。

### 切分口径与覆盖率（跨方法对比前必读）

`--items` 指向的清单必须与 `--split` 一致，否则**直接报错退出**（以前会静默跑通）。
清单条数与官方 split 的关系会写入 `summary.json` 的 `split_provenance`：

| 清单 | `--split` | 条数 | 官方 `json_2.1.1` | 是否完整覆盖 |
| --- | --- | --- | --- | --- |
| `alfworld_path_split/train/items.json` | `train` | 39 | 3553 | 否 |
| `alfworld_path_split/val/items.json` | `valid_seen` | 18 | 140 | 否 |
| `alfworld_path_split/test/items.json` | `valid_unseen` | 134 | 134 | **是** |

也就是说：**test 段与官方 `valid_unseen` 逐文件相同**，而 train/val 段是
SkillOpt 发布的**子集**。任何"训练用了多少数据"的说法都要连带报出该覆盖率，
单纯写"train split"会把 39 与 3553 混为一谈。`--limit` 之后实际生效的局数也会
记入 `split_provenance.effective_episodes`。

### 步数上限只有一个来源

episode 截断点属于评测协议，因此取自 `configs/textworld.yaml` 的
`max_nb_steps_per_episode`（= 50），这正是 ALFWorld 注册环境时使用的同一个值。
`--max-steps` 的默认值随之确定；**显式传入与配置不一致的值会报错**，而不是让
协议静默分叉。生效值及其来源写入 `summary.json` 的 `max_steps` /
`max_steps_source`。若要做短步数的冒烟测试，请另建一份降低了该键的 config，
不要用 `--max-steps` 覆盖。

### 使用 `benchmark/llm_config.local.json` 的端点

```bash
export ALF_LLM_KEY="$(python3 -c 'import json;print(json.load(open("../../benchmark/llm_config.local.json"))["alfworld-eval"]["api_key"])')"
uv run python scripts/run_unified_eval.py --method skillopt --backend api \
    --base-url "$ALF_ENDPOINT" --model "$ALF_MODEL" \
    --api-key-env ALF_LLM_KEY --seed 42 --limit 3 --record-trajectory
```

### 推理模型与 `--max-tokens`

`deepseek-v4.1-flash` 这类推理模型把思维链放在 `reasoning_content`，与
`content` 共用同一份 completion 预算。实测中它们会在 `max_tokens=4096` 内用尽
预算，返回一个以 `</think>` 结尾、完全没有 `<action>` 的超长思考块（约 16k 字符）。
此时：

- 该步记为非法请求，`summary.json` 的 `corrections.truncated_responses` 会计数；
- 诊断信息会说明是"输出被截断"，修正请求也会要求"至多一句话"再给动作。

修正请求要求简短后，实测 trace2skill 未修正的非法请求从 2 降到 0、总步数从 27
降到 18。若仍频繁截断，请调大 `--max-tokens`。

### 可复现性注意

`--seed` 会写入 API 请求体（`temperature=0` 时一并发送），但端点是否真正遵循
该字段取决于服务实现。实测同一 `--seed 42` 的两次 skillopt 运行选中的是同一批
episode、同一顺序，但其中一个 episode 分别走了 10 步和 5 步，说明该端点并未按
seed 保证确定性。若需要严格可复现的基线，应先确认端点对 `seed` 的支持。

## 复现操作手册：SkillOpt 与 Trace2Skill 端到端

**SkillOpt 直接评测；Trace2Skill 每次复现都要先训练一份 skill，再用它测试**
（它没有官方 ALFWorld 产物）。括号里的数字是 2026-09-15 在 `qwen3.6-flash-distill`
上的实测值，可用来判断自己的复现是否跑偏；`uv run` 若因缓存目录权限失败，换成
`.venv/bin/python` 等价。

### 0. 环境与 warmup

先按上文「通用调用形式」导出 `ALFWORLD_DATA`、`ALF_ENDPOINT`、`ALF_MODEL`、`ALF_LLM_KEY`
并设 `P=../../skillopt/data/alfworld_path_split`，然后：

```bash
uv run python scripts/check_environment.py
uv run python scripts/run_unified_eval.py --method vanilla --backend mock --limit 2 --out outputs/_envcheck
uv run python scripts/warmup_endpoint.py --base-url "$ALF_ENDPOINT" --model "$ALF_MODEL" \
    --api-key-env ALF_LLM_KEY --ramp 1,2,4,8,16,32 --per-level 2 --out outputs/warmup.json
```

前两条不花 API 额度（2 局约 4 s），先把引擎问题排掉。warmup 退出码 **2** = key/模型错
（不要继续），**1** = 没有干净的并发档位（调低 `--shards`）；实测该端点 c=1..32 全 0 次 429。
warmup 为什么必须、`--shards auto` 与合并校验的机制见上文「多并发评测」。

### 1. 小规模验证（分层抽样）

```bash
uv run python scripts/sample_manifest.py --items $P/test/items.json --per-type 2 \
    --out outputs/_smoke/manifests/test_2per.json          # 六类任务各 2 局
uv run python scripts/run_eval_concurrent.py --method skillopt --shards 4 \
    --base-url "$ALF_ENDPOINT" --model "$ALF_MODEL" --api-key-env ALF_LLM_KEY \
    --warmup-ramp 1,2,4 --shard-stagger 1.0 --out-base outputs/smoke_skillopt \
    --unified-args "--split valid_unseen --items outputs/_smoke/manifests/test_2per.json \
                    --seed 42 --record-trajectory"
```

验收：12 局覆盖六类任务，`uncorrected_invalid_requests = 0`、`truncated_responses = 0`
（实测 11/12 成功、6 次非法请求全部被一次修正救回）。不要用 `--limit` 代替分层抽样。

### 2. SkillOpt 评测

```bash
# valid_seen 18 局（SkillOpt 发布清单，18/140，非完整切分）
uv run python scripts/run_eval_concurrent.py --method skillopt --shards 16 \
    --base-url "$ALF_ENDPOINT" --model "$ALF_MODEL" --api-key-env ALF_LLM_KEY \
    --warmup-ramp 1,2,4,8,16,32 --shard-stagger 1.0 --out-base outputs/final_skillopt_val \
    --unified-args "--split valid_seen --items $P/val/items.json --seed 42 --record-trajectory"

# valid_unseen 134 局（test 清单 = 官方 valid_unseen 全量）：同上，改 --shards 32、
# --out-base outputs/final_skillopt_test、--split valid_unseen --items $P/test/items.json
```

SkillOpt 用的就是仓库里的论文产物（`c8219398…`），**没有训练步骤**；正式评测不要加 `--limit`。
两个 split 可并行（实测 297 s / 1111 s，与另一个 32 shard 运行并行也没出现失败浪潮）。

### 3. 训练 Trace2Skill 的 skill

```bash
T2S_TRAIN=outputs/t2s_train                      # 训练轨迹运行目录
T2S_WORK=outputs/t2s_work                        # 训练工作目录（产出 skill 在这里）
T2S_SEED=src/alfworld_eval/skills_docs/trace2skill_seed_alfworld.md   # 种子 skill
T2S_SKILL=$T2S_WORK/trace2skill_alfworld.md      # 训练产物，步骤 4 注入它
```

- **训练集**默认 SkillOpt 发布的 `train/items.json`（39 局，官方 3553 局的子集，报告要写明
  这个覆盖率）。想训更多就自建同格式清单（`gamefile` 写相对 `$ALFWORLD_DATA` 或绝对路径
  都可以）；`--use-full-split` 不能并发分片。缩小训练集（`--limit`）后必须重训。
- **基座模型必须与测试阶段相同**：skill 是该模型自己的经验，换模型要重训。

```bash
# 3a 跑训练轨迹（必须 --record-trajectory，必须给 --skill-path）
uv run python scripts/run_eval_concurrent.py --method trace2skill --shards 8 \
    --base-url "$ALF_ENDPOINT" --model "$ALF_MODEL" --api-key-env ALF_LLM_KEY \
    --warmup-ramp 1,2,4,8 --shard-stagger 1.5 --out-base "$T2S_TRAIN" \
    --unified-args "--split train --items $P/train/items.json --seed 42 --record-trajectory \
                    --skill-path $T2S_SEED"

# 公共参数：注意是 --api-key（不是 --api-key-env）
T2S="--base-url $ALF_ENDPOINT --model $ALF_MODEL --api-key $ALF_LLM_KEY \
     --train-items $P/train/items.json --selection-items $P/val/items.json \
     --test-items $P/test/items.json --work-dir $T2S_WORK \
     --train-run-dir $T2S_TRAIN/merged --skip-train --skip-eval"

# 3b 建 workspace（单进程，39 局约 2.5 min：每局要开一次环境取初始观测）
uv run python scripts/run_trace2skill.py $T2S --skip-analysis --skip-consolidate

# 3c 并发分析（失败轨迹最多 20 轮工具调用，是最慢的一段，实测 22 min）
for i in $(seq 0 11); do
  uv run python scripts/run_trace2skill.py $T2S --skip-prepare --skip-consolidate \
      --analysis-shards 12 --analysis-shard-index $i > $T2S_WORK/analysis_shard$i.log 2>&1 &
done; wait

# 3d 归纳，产出本次训练的 skill；随后记下哈希
uv run python scripts/run_trace2skill.py $T2S --skip-prepare --skip-analysis
sha256sum "$T2S_SKILL"
```

**闸门验收**：`$T2S_WORK/analysis_summary.json` 的 `verified_rate` 就是这次训练的可信度
（实测 31/39 = 0.7949；`discarded_episodes` 列出被丢弃的 8 条）。偏低时不要进入步骤 4，
先看 `analysis_workspaces/<episode>/analyst_transcript.json` 的 `outcome`：
`verifier_calls = 0` = 分析器没调验证器（检查该 workspace 是否缺轨迹）；
多次调用仍 `verified=false` = 修不动（提高 `--max-analyst-turns`，默认 20，重跑该片，
或接受丢弃——这正是闸门语义）。

超参只有三个需要动：`--analysis-shards`（正式训练 8~12）、`--max-analyst-turns`
（`verified_rate` 偏低且 transcript 显示多次调用才提高）、`--analyst-mode`
（默认 `combined` 成功也分析；改 `error` 更贴上游，但高成功率模型上几乎无事可做——
实测种子 skill 在 39 局上解出 28 局）。

### 4. 测试（用本次训练出的 skill 评测）

注入的必须是步骤 3 训出的那份：`--skill-path "$T2S_SKILL"`。指向别的文档测的就是那份文档，
不是本次训练的结果；漏掉它就退回占位文档，结果不构成 Trace2Skill 评测。训练与测试要成套，
重训过（3d）旧分数即作废。

```bash
# valid_unseen 134 局
uv run python scripts/run_eval_concurrent.py --method trace2skill --shards 32 \
    --base-url "$ALF_ENDPOINT" --model "$ALF_MODEL" --api-key-env ALF_LLM_KEY \
    --warmup-ramp 1,2,4,8,16,32 --shard-stagger 1.0 --out-base outputs/final_t2s_test \
    --unified-args "--split valid_unseen --items $P/test/items.json --seed 42 --record-trajectory \
                    --skill-path $T2S_SKILL"

# valid_seen 18 局：同上，改 --shards 16、--out-base outputs/final_t2s_val、
# --split valid_seen --items $P/val/items.json

# 核对注入的确实是 3d 记下的那份
python3 -c "import json;print(json.load(open('outputs/final_t2s_test/merged/summary.json'))['skill'])"
```

### 5. 配对比较

```bash
uv run python scripts/compare_runs.py outputs/final_skillopt_test/merged \
    outputs/final_t2s_test/merged --label-a skillopt --label-b trace2skill \
    --out outputs/comparison_valid_unseen.json
```

两个 run 必须覆盖同一份清单，否则脚本拒绝。结论用**整体**配对检验（差值 CI + McNemar p）；
单任务类型每类只有 17~31 局，只用来看差距在哪。

### 6. 验收与排期

| 检查 | 期望 |
|---|---|
| `run_meta.json` | `failed_shards` 为空；`shards` 与 warmup 实测相符 |
| `merged/summary.json` | `n_episodes` = 清单条数；`split_provenance`；`max_steps=50`；`uncorrected_invalid_requests=0`；`usage.api_errors` < 1% |
| `merged/summary.json.skill` | `sha256` = 步骤 3d 记下的那份（旧运行看 `evaluated_skill.json`） |
| `merged/trajectories/` | 每局一个文件（下一次训练与失败分析要用） |
| 训练侧 `$T2S_WORK/analysis_summary.json` | `verified_rate`、`discarded_episodes`、`memory_items` |
| 训练侧 `$T2S_WORK/provenance.json` | 训练/选择/测试三段清单与覆盖率 |

任何一项不通过都用**原命令重跑**（逐局断点续跑），不要手工改产物。

| 阶段 | 覆盖 | 并发 | 墙钟 | API 调用 | prompt / completion tokens |
|---|---|---|---|---|---|
| 训练轨迹（3a） | 39 | 8 | 16.5 min | 936 | 0.77 M / 0.52 M |
| workspace（3b） | 39 | 1 | 2.6 min | 0 | — |
| 训练分析（3c） | 39 | 12 | 22 min | 每条失败轨迹 ≤ 20 轮工具调用 | — |
| SkillOpt valid_seen | 18 | 16 | 297 s | 228 | 0.78 M / 0.13 M |
| SkillOpt valid_unseen | 134 | 32 | 1110 s | 2,422 | 8.20 M / 1.71 M |
| Trace2Skill valid_seen | 18 | 16 | 551 s | 389 | 0.37 M / 0.23 M |
| Trace2Skill valid_unseen | 134 | 32 | 1720 s | 3,444 | 3.11 M / 2.09 M |

排期三条：**墙钟由最长那一局决定**（撞 50 步上限的局要十几分钟），所以 134 局/32 shard
仍要 18~29 min；并发升高时单次调用延迟同步上升，16→32 还值得、再往上收益递减；
Trace2Skill 的时间大头在**训练**（3a+3b+3c ≈ 41 min），测试只要 29 min。
顺带一条预算事实：SkillOpt 的 prompt token 高约 8 倍（13 KB skill 每次调用都要重发）。

### 7. 踩坑

| 症状 | 原因 | 处理 |
|---|---|---|
| 一开并发就大量 429 | 冷启动 | 先 warmup，或用 `--shards auto` |
| 小规模结果只有一类任务 | `--limit` 取清单前 N 条，而清单按任务类型聚集 | 用 `sample_manifest.py --per-type K` |
| `analyst ... max_turns exceeded`、`items=0` | 分析器没修好或没调验证器 | 看 `analyst_transcript.json` |
| Trace2Skill 分数异常低、skill ≈1.4 KB | 漏了 `--skill-path`，注入的是占位文档 | 查 `summary.json.skill` |
| 同一批 memory 重训得到不同 skill | 归纳是 LLM 调用，端点不确定 | 用哈希对齐；训练→测试成套复现 |
| `merge_shards.py` 报 "shard looks incomplete" | 某个 shard 中途死了 | 原命令重跑，或 `--allow-incomplete` |
| 有的局跑了十几分钟 | 撞上 50 步上限 | 正常，它也是墙钟的下界来源 |
| 想用 `--max-steps` 缩短冒烟 | 步数上限是评测协议的一部分 | 另建降了该键的 config |

本手册实测对应的完整结果（SkillOpt `valid_unseen` 82.09% vs Trace2Skill 66.42%，配对差值
+15.67 点、95% CI +8.21~+23.13、McNemar p = 4.9e-05）与全部 caveat 见
`docs/reports/alfworld_qwen36_skillopt_vs_trace2skill.md`；与论文数值的对照（含 Qwen 两行）
与逐条差异判定见 `docs/ALFWorld_reproduction_report.md`（均在仓库根 `docs/` 下）。
