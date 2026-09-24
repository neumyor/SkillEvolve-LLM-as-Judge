# ALFWorld Docker 复现与排障记录

本文总结 Trace2Skill 在本地 Docker 中进行 ALFWorld 真实 LLM 评测时遇到的容器启动、依赖、数据路径和 API 调用问题。

## 1. 环境组成

评测由以下部分组成：

- Docker 镜像：`alfworld-eval:local`
- Python：镜像内 `/opt/alfworld-eval/.venv/bin/python`
- ALFWorld 数据：`$ALFWORLD_DATA`
- 评测代码：`src/alfworld_eval/`
- 评测入口：`scripts/run_unified_eval.py`
- Trace2Skill 入口：`scripts/run_trace2skill.py`
- 样例清单：SkillOpt 仓库中的 `items.json`
- LLM：OpenAI Chat Completions 兼容接口

Trace2Skill 的真实流程分为三段：

1. 使用 train 样例收集 ALFWorld 轨迹；
2. 对轨迹进行错误分析，并生成新的 Markdown skill；
3. 将生成的 skill 注入 prompt，在 `valid_seen` 和 `valid_unseen` 上验证。

## 2. Docker 镜像构建

### Apple Silicon 平台

当前宿主机是 Apple Silicon，Docker 会显示：

```text
The requested image's platform (linux/amd64) does not match
the detected host platform (linux/arm64/v8)
```

这是因为镜像基于 `linux/amd64` 构建，在 ARM64 宿主机上通过模拟运行。该提示本身不是错误，但运行速度会比原生架构慢。

Dockerfile 已固定：

```dockerfile
FROM --platform=linux/amd64 python:3.11-slim-bookworm
```

构建时建议显式指定平台：

```bash
docker buildx build \
  --platform linux/amd64 \
  --build-context wheels=.wheels-cache \
  -t alfworld-eval:local \
  --load .
```

### 依赖下载速度

`spacy` 依赖链较大，在模拟的 `linux/amd64` 容器中下载容易超时或非常慢。当前 Dockerfile 使用以下策略：

- 使用镜像源安装 Python 和系统依赖；
- 预先准备 `.wheels-cache`；
- 在 builder 阶段离线安装 `numpy`、`spacy`、`thinc`、`blis` 等依赖；
- 再执行 `uv sync --frozen --no-dev`。

`.wheels-cache` 只作为独立 build context 使用，并且被 `.dockerignore` 排除，避免将缓存复制进最终镜像。

### 代码变更后的镜像问题

如果代码已经修改，但直接运行旧镜像，容器内仍可能使用旧版本代码。低成本调试时建议挂载最新源码：

```bash
-v "$PWD/src:/opt/alfworld-eval/src:ro"
-v "$PWD/scripts:/opt/alfworld-eval/scripts:ro"
```

正式复现时则应重新构建镜像，避免源码挂载掩盖镜像内容问题。

## 3. ALFWorld 数据配置

容器内必须设置：

```bash
ALFWORLD_DATA=/opt/alfworld-eval/.data/alfworld
```

数据根目录至少需要包含：

```text
.data/alfworld/
├── json_2.1.1/
│   ├── train/
│   ├── valid_seen/
│   └── valid_unseen/
└── logic/
    ├── alfred.pddl
    └── alfred.twl2
```

配置文件 `configs/textworld.yaml` 中的路径通过环境变量解析：

```yaml
data_path: "$ALFWORLD_DATA/json_2.1.1/train"
eval_id_data_path: "$ALFWORLD_DATA/json_2.1.1/valid_seen"
eval_ood_data_path: "$ALFWORLD_DATA/json_2.1.1/valid_unseen"
```

如果出现以下错误，通常是数据根目录没有设置或目录结构不完整：

```text
ALFWORLD_DATA is not set
```

或：

```text
No gamefiles found
```

### `items.json` 路径

SkillOpt 的样例清单保存的是相对于 `$ALFWORLD_DATA` 的路径，例如：

```text
json_2.1.1/train/look_at_obj_in_light-.../game.tw-pddl
```

因此：

- `items.json` 可以挂载到容器内任意位置；
- 清单中的 `gamefile` 必须相对于容器内的 `$ALFWORLD_DATA` 能够解析；
- `--split train`、`--split valid_seen`、`--split valid_unseen` 必须与清单中的游戏目录一致。

常用清单：

```text
repos/pulled/SkillOpt/data/alfworld_path_split/train/items.json
repos/pulled/SkillOpt/data/alfworld_path_split/val/items.json
repos/pulled/SkillOpt/data/alfworld_path_split/test/items.json
```

其中：

- `train/items.json` 对应 `train`；
- `val/items.json` 对应 `valid_seen`；
- `test/items.json` 对应 `valid_unseen`。

## 4. Python 解释器问题

### `sh -lc` 可能切换到系统 Python

容器默认环境中 `PATH` 包含：

```text
/opt/alfworld-eval/.venv/bin
```

但使用 login shell 后，`PATH` 可能被重置，导致实际调用系统 Python，并出现：

```text
ModuleNotFoundError: No module named 'yaml'
```

推荐始终使用绝对路径：

```bash
/opt/alfworld-eval/.venv/bin/python scripts/run_trace2skill.py ...
```

不要仅依赖：

```bash
python scripts/run_trace2skill.py
```

## 5. 真实 API 调用配置

当前评测代码使用 OpenAI Chat Completions 兼容接口。配置示例：

```text
Base URL: value from local endpoint configuration
Model: deepseek-v4.1-flash
```

代码会自动拼接：

```text
/chat/completions
```

因此 `--base-url` 应填写到 `/v1`，不要直接填写完整的 `/chat/completions` 地址。

### API key 传递

推荐使用环境变量：

```bash
docker run --rm \
  -e TRACE2SKILL_API_KEY="$TRACE2SKILL_API_KEY" \
  ...
```

容器内由脚本读取：

```bash
--api-key-env TRACE2SKILL_API_KEY
```

或者在容器命令中显式读取变量：

```bash
sh -lc '/opt/alfworld-eval/.venv/bin/python \
  /opt/alfworld-eval/scripts/run_trace2skill.py \
  --api-key "$TRACE2SKILL_API_KEY" ...'
```

### API key 传递时的常见错误

#### 宿主 shell 提前展开变量

如果命令中的变量在宿主 shell 中展开，而宿主机没有该变量，容器最终收到的就是空字符串，服务端会返回：

```text
401 Unauthorized
缺少访问秘钥
```

需要让变量在容器内展开，或直接使用 `--api-key-env`。

#### JSON 和 shell 引号冲突

使用 `curl` 时，嵌套引号、通配符和 shell 展开容易导致请求体被破坏。排查 API 连通性时，优先使用 Python `urllib` 构造 JSON 请求，避免 shell 引号问题。

最小验证只应检查：

1. 容器内 key 是否为空；
2. 请求是否返回 `HTTP 200`；
3. 返回体是否包含 `choices[0].message`。

不要在日志中打印完整 key。当前使用过的 key 曾经在对话和命令中暴露，应立即撤销并重新生成。

## 6. Trace2Skill 小规模真实测试

推荐先使用少量样例，避免直接消耗完整数据集。下面的命令使用：

- 3 条 train 样例生成 skill；
- 3 条 valid_seen 样例验证；
- 3 条 valid_unseen 样例验证；
- 每局最多 8 个环境步；
- `max_tokens=4096`；
- 温度为 0；
- 每个环境步最多一次非法输出修正。

示例：

```bash
docker run --rm \
  --name trace2skill-real-smoke \
  -e TRACE2SKILL_API_KEY="$TRACE2SKILL_API_KEY" \
  -v "$PWD/src:/opt/alfworld-eval/src:ro" \
  -v "$PWD/scripts:/opt/alfworld-eval/scripts:ro" \
  -v "$PWD/outputs/trace2skill_real:/opt/alfworld-eval/outputs/trace2skill_real:rw" \
  -v "$PWD/../../repos/pulled/SkillOpt/data/alfworld_path_split/train/items.json:/opt/alfworld-eval/train_items.json:ro" \
  -v "$PWD/../../repos/pulled/SkillOpt/data/alfworld_path_split/val/items.json:/opt/alfworld-eval/val_items.json:ro" \
  -v "$PWD/../../repos/pulled/SkillOpt/data/alfworld_path_split/test/items.json:/opt/alfworld-eval/test_items.json:ro" \
  alfworld-eval:local \
  /opt/alfworld-eval/.venv/bin/python \
  /opt/alfworld-eval/scripts/run_trace2skill.py \
  --base-url "$ALF_ENDPOINT" \
  --model deepseek-v4.1-flash \
  --api-key-env TRACE2SKILL_API_KEY \
  --temperature 0 \
  --max-tokens 4096 \
  --seed 42 \
  --max-steps 8 \
  --history-length 2 \
  --train-items /opt/alfworld-eval/train_items.json \
  --selection-items /opt/alfworld-eval/val_items.json \
  --test-items /opt/alfworld-eval/test_items.json \
  --work-dir /opt/alfworld-eval/outputs/trace2skill_real \
  --analyst-mode combined \
  --max-analyst-turns 6 \
  --limit 3
```

注意：如果使用 `--api-key-env`，API key 必须已经存在于容器环境中。不要同时把未展开的宿主机变量传给脚本。

## 7. 校验和一次修正机制

每个环境步的流程如下：

1. 调用模型；
2. 校验 `<think>...</think><action>...</action>`；
3. 校验 action 是否在当前 admissible action 列表中；
4. 如果失败，生成确定性诊断信息；
5. 将诊断和 admissible action 列表回传模型；
6. 最多允许一次修正；
7. 修正成功才执行修正动作；
8. 修正失败执行安全回退 `look`。

修正请求不会推进 ALFWorld 环境，因此：

```text
环境步数 != API 调用次数
```

如果模型频繁输出非法格式，API 调用数会明显高于环境步数。

结果中的关键统计字段：

- `invalid_requests`：首次模型请求非法的次数；
- `correction_attempts`：实际发起修正请求的次数；
- `correction_successes`：修正后通过校验的次数；
- `uncorrected_invalid_requests`：修正后仍失败的次数；
- `invalid_action_rate`：首次非法请求相对于环境步数的比例；
- `uncorrected_invalid_request_rate`：修正仍失败相对于环境步数的比例。

## 8. 输出文件

Trace2Skill 流程通常生成：

```text
<work-dir>/
├── train_run/
│   ├── results.jsonl
│   ├── summary.json
│   └── trajectories/
├── analysis_workspaces/
│   └── <episode>/
│       ├── agent_log.md
│       ├── analysis_report.md
│       └── evaluate_passed.flag
├── trace2skill_alfworld.md
├── selection_run/
│   ├── results.jsonl
│   └── summary.json
└── test_run/
    ├── results.jsonl
    └── summary.json
```

重点检查：

- `trace2skill_alfworld.md` 是否成功生成；
- `train_run/summary.json` 中是否记录了 train 轨迹；
- `selection_run/summary.json` 是否对应 `valid_seen`；
- `test_run/summary.json` 是否对应 `valid_unseen`；
- trajectory 中的 `initial_model_response`、`diagnostic`、`correction_response` 和 `correction_diagnostic`。

## 9. 推荐排查顺序

遇到运行失败时，按以下顺序检查：

1. `docker image inspect alfworld-eval:local`，确认镜像存在；
2. 确认容器内使用 `/opt/alfworld-eval/.venv/bin/python`；
3. 确认 `ALFWORLD_DATA` 指向包含 `json_2.1.1` 和 `logic` 的目录；
4. 确认 `items.json` 已挂载，且 gamefile 能在 `$ALFWORLD_DATA` 下找到；
5. 单独验证 API 返回 `HTTP 200`；
6. 确认 `--base-url` 没有重复 `/chat/completions`；
7. 确认 API key 没有被宿主 shell 提前展开为空；
8. 确认源码挂载的是最新版本；
9. 先运行 1 条样例，再扩大到 3 条；
10. 最后检查 `summary.json` 和 trajectory，而不是只看终端最后一行。
