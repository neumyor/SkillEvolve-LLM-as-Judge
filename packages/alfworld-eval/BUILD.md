# ALFWorld 评测环境构建方案

## 1. 建设目标

第一阶段实现一个轻量、可复现、可审计的 ALFWorld 文本评测 harness：

- 只使用 `AlfredTWEnv`，不依赖 AI2-THOR、视觉检测器或 GPU。
- 同时支持 `train`、`valid_seen` 和 `valid_unseen`。
- Agent 与环境解耦，后续可接 API 模型、本地模型或固定策略。
- 每个 episode 保存完整轨迹，汇总结果可追溯到 game file。
- 所有 Python 依赖由 `uv.lock` 固定，代码和配置由独立 Git 仓库管理。

第一阶段不包含训练、RL、Ray/vLLM、多模态环境和模型权重管理。

## 2. 版本与平台策略

基础版本固定为：

| 项目 | 版本/约束 | 原因 |
| --- | --- | --- |
| Python | `3.11` | 当前 macOS arm64 可直接使用 TextWorld 预编译包 |
| ALFWorld | `0.4.2` | 固定 benchmark 主依赖，避免无意升级改变环境行为 |
| TextWorld | `1.6.2` | 显式覆盖 ALFWorld 的宽松下界，保证当前平台安装路径稳定 |
| uv | lock file | 通过 `uv.lock` 固定所有传递依赖 |

ALFWorld 0.4.2 没有声明 Python 上界，不能仅依赖解析器自动选择兼容版本。
项目因此用 `.python-version` 和 `requires-python` 把解释器收窄到 3.11。

## 3. 环境分层

### 3.1 基础层

负责安装 ALFWorld/TextWorld、加载 YAML 配置、定位数据目录和执行环境自检。

### 3.2 环境适配层

封装 ALFWorld 原生批量接口，对上层暴露稳定协议：

```python
reset(task) -> Observation
step(action) -> StepResult
close() -> None
```

`Observation` 至少包含当前文本、可选合法动作、任务描述、game file 和 task type。
`StepResult` 至少包含 observation、reward、done、won 和错误信息。

### 3.3 Agent 层

统一为：

```python
act(observation, history) -> str
```

环境层不直接依赖 OpenAI、Anthropic、vLLM 或具体 prompt 框架。模型适配器作为可选依赖
单独加入，避免基础环境因 SDK 或 GPU 栈升级而失效。

### 3.4 Runner 与记录层

Runner 负责 step budget、异常隔离、随机种子、重试边界和结果落盘。
每个 episode 输出一条 JSONL 记录，至少包含：

- `run_id`、代码提交号、`uv.lock` 摘要；
- split、seed、game file、task type；
- agent/model/prompt/skill 标识；
- 每一步 observation、action、reward、done；
- `success`、`steps`、`invalid_actions`、`termination_reason`；
- latency 和 token/cost 字段，无法获得时为 `null`。

## 4. 评测协议

默认分别报告：

- `valid_seen`：与训练分布重叠的任务类型；
- `valid_unseen`：未见任务组合/类型，单独作为 OOD 结果；
- overall success rate；
- 按六类 ALFWorld task type 的成功率；
- 平均/中位步数、超时率、非法动作率；
- bootstrap 置信区间；
- 固定 episode 清单上的 paired agent comparison。

不得把 `valid_seen` 和 `valid_unseen` 合并成唯一总分，也不得只保存聚合结果。

六类任务：

1. Pick & Place
2. Examine in Light
3. Clean & Place
4. Heat & Place
5. Cool & Place
6. Pick Two & Place

## 5. 数据与版本边界

ALFWorld 数据默认下载到 `~/.cache/alfworld`，通过 `ALFWORLD_DATA` 指向数据根目录。
数据、模型权重、运行输出均不提交 Git。

Git 中应提交：

- `pyproject.toml`、`.python-version`、`uv.lock`；
- 环境配置和 split manifest；
- prompt/skill 文档；
- runner、adapter、指标实现和测试；
- 每次正式实验的不可变配置。

Git 中不应提交：

- `json_2.1.1` 原始游戏数据；
- `.venv`；
- API key；
- 大型逐步轨迹和模型响应；
- 模型 checkpoint。

正式运行结果需要记录 Git commit，工作区有未提交修改时标记 `dirty=true`。

## 6. 预计目录结构

```text
alfworld-eval/
├── configs/
│   └── textworld.yaml
├── src/alfworld_eval/
│   ├── env.py
│   └── runner.py
├── scripts/
│   └── check_environment.py
├── tests/
├── .python-version
├── pyproject.toml
└── uv.lock
```

## 7. 实施顺序

1. **Bootstrap**：锁定依赖，完成 import、数据目录和配置自检。
2. **Single episode**：用固定合法动作策略跑通一个 episode 并保存轨迹。
3. **Dataset runner**：按显式 game file 清单运行 seen/unseen split。清单必须与
   `--split` 一致，且其相对官方 split 的覆盖率会写入 `split_provenance`：SkillOpt
   发布的 `alfworld_path_split` 是 39/18/134，对应官方 3553/140/134，只有 test 段
   完整覆盖 `valid_unseen`。报告结果时必须连带说明覆盖率与 `--limit` 后的实际局数。
4. **Metrics**：实现总体、task-type、停止原因和 paired comparison 统计。
5. **Agent adapters**：先接一个 API 模型，再按需接本地模型。
6. **Reproducibility**：加入 run manifest、commit/lock 摘要和确定性测试。
7. **Parallelism**：单进程结果稳定后，再增加受控多进程执行。

## 8. 验收条件

基础环境完成时应满足：

- `uv sync --frozen` 在干净目录可重建环境；
- 自检脚本确认 Python、包版本、配置和数据完整；
- 固定 seed 下可重复启动同一个 game file；
- 单 episode 的输入、动作、结果完整落盘；
- seen/unseen 独立运行和独立汇总；
- 单元测试不依赖网络或真实模型 API；
- README 中的命令从全新 clone 可执行。

## 9. 已知风险

- `fast-downward-textworld` 仅提供源码发行，首次安装可能需要本机编译工具。
- ALFWorld 数据下载不属于 `uv sync`，必须作为显式的第二步。
- 原生 ALFWorld 批量环境的 seed 和 game file 选择需要实测，不能假设完全确定。
- macOS 多进程默认启动方式与 Linux 不同，应先以单进程建立基线。
- 视觉环境依赖旧版 AI2-THOR，后续应放入独立 optional dependency 或单独仓库。
