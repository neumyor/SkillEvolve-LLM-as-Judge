"""GEPA adapters for the repository's SearchQA and ALFWorld protocols.

The adapters deliberately call the same in-process evaluators as the benchmark
launchers.  A GEPA candidate is one skill document (the ``skill`` component),
so the only thing that changes between baseline and JudgeGate runs is the
acceptance criterion installed by :mod:`run`.
"""
from __future__ import annotations

import json
import hashlib
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
from pathlib import Path
from typing import Any

from gepa.core.adapter import EvaluationBatch

ROOT = Path(__file__).resolve().parents[1]


def _checkpoint_final_units(evaluate):
    """Final measurements persist each unit; evolution keeps its original calls."""
    @wraps(evaluate)
    def wrapped(self, batch, candidate, capture_traces=False):
        stage = getattr(self, "usage_stage", "")
        ledger = getattr(self, "usage_ledger", None)
        if not stage.startswith("final_") or ledger is None:
            return evaluate(self, batch, candidate, capture_traces=capture_traces)
        directory = ledger.path.parent / "final_units" / stage
        directory.mkdir(parents=True, exist_ok=True)

        def unit(item):
            identity = json.dumps({"item": item, "candidate": candidate, "traces": capture_traces}, sort_keys=True)
            path = directory / (hashlib.sha256(identity.encode()).hexdigest() + ".json")
            if path.exists():
                return json.loads(path.read_text())
            result = evaluate(self, [item], candidate, capture_traces=capture_traces)
            if len(result.scores) != 1:
                raise ValueError("Final evaluation must return exactly one result per task")
            if isinstance(result.outputs[0], dict) and result.outputs[0].get("error"):
                raise RuntimeError("Final evaluation failed: " + str(result.outputs[0]["error"]))
            payload = {"score": result.scores[0], "output": result.outputs[0],
                       "trajectory": result.trajectories[0] if result.trajectories else None}
            temporary = path.with_suffix(".tmp")
            temporary.write_text(json.dumps(payload))
            os.replace(temporary, path)
            return payload

        with ThreadPoolExecutor(max_workers=max(1, self._workers)) as pool:
            rows = list(pool.map(unit, batch))
        return EvaluationBatch(outputs=[r["output"] for r in rows], scores=[r["score"] for r in rows],
                               trajectories=[r["trajectory"] for r in rows] if capture_traces else None)
    return wrapped


class _OpenAIReflectionLM:
    """OpenAI-compatible GEPA reflection callable.

    The copied GEPA source normally routes reflection through LiteLLM.  The
    benchmark environment already has the OpenAI client and uses an
    OpenAI-compatible qwen endpoint, so this keeps the experiment independent
    of an optional LiteLLM installation.
    """

    def __init__(self, *, model: str, base_url: str, api_key: str,
                 max_tokens: int = 4096, temperature: float = 0.0):
        from openai import OpenAI

        self._client = OpenAI(
            base_url=base_url or None,
            api_key=api_key or None,
            timeout=float(os.environ.get("GEPA_HTTP_TIMEOUT", "180")),
            max_retries=2,
        )
        self._model = model
        self._max_tokens = int(max_tokens)
        self._temperature = float(temperature)

    def __call__(self, prompt):
        messages = (
            [{"role": "user", "content": prompt}]
            if isinstance(prompt, str) else list(prompt)
        )
        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
        )
        if getattr(self, "usage_ledger", None):
            self.usage_ledger.record(response.usage, stage="proposal_generation", model=self._model)
        return str(response.choices[0].message.content or "")


def _text(candidate: dict[str, str]) -> str:
    if "skill" in candidate:
        return str(candidate["skill"])
    return "\n\n".join(str(value) for value in candidate.values())


def _read_json(path: str | Path) -> Any:
    data = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    if isinstance(data, dict) and "data" in data:
        return data["data"]
    return data


class SearchQAGEPAAdapter:
    """GEPA adapter backed by ``searchqa_eval.runner.process_one``."""

    # Use GEPA's default reflective proposer.  The explicit attribute is part
    # of GEPA's adapter contract; omitting it makes the engine treat a real
    # adapter as malformed only when the first mutation is attempted.
    propose_new_texts = None

    def __init__(self, *, base_url: str = "", model: str = "", api_key: str = "",
                 backend: str = "api", workers: int = 1, seed: int = 42,
                 max_tokens: int = 16384, max_context_chars: int = 6000):
        source = ROOT / "searchqa-eval" / "src"
        if str(source) not in sys.path:
            sys.path.insert(0, str(source))
        from searchqa_eval.agent import build_agent
        self._build_agent = build_agent
        self._base_url, self._model, self._api_key = base_url, model, api_key
        self._backend, self._workers, self._seed = backend, workers, seed
        self._max_tokens, self._max_context_chars = max_tokens, max_context_chars

    @_checkpoint_final_units
    def evaluate(self, batch, candidate, capture_traces=False):
        from searchqa_eval.prompts import build_system_prompt
        from searchqa_eval.runner import process_one
        system = build_system_prompt(_text(candidate))

        def _evaluate_one(item):
            # Keep one client/usage accumulator per worker. The endpoint is
            # stateless, while sharing an agent across threads would race its
            # usage counters and obscure campaign cost accounting.
            agent = self._build_agent(
                self._backend, base_url=self._base_url, model=self._model,
                api_key=self._api_key, temperature=0.0, max_tokens=self._max_tokens,
                seed=self._seed,
            )
            row = process_one(item, system, agent, max_context_chars=self._max_context_chars)
            if getattr(self, "usage_ledger", None):
                self.usage_ledger.record(row.usage, stage=getattr(self, "usage_stage", "evolution_execution"),
                                         model=self._model, item_id=str(row.id),
                                         agent_ok=row.agent_ok, fail_reason=row.fail_reason,
                                         score=float(row.em))
            return row

        if self._workers <= 1 or len(batch) <= 1:
            rows = [_evaluate_one(item) for item in batch]
        else:
            with ThreadPoolExecutor(max_workers=self._workers) as executor:
                rows = list(executor.map(_evaluate_one, batch))
        outputs = [row.response for row in rows]
        scores = [float(row.em) for row in rows]
        traces = None
        if capture_traces:
            traces = [{
                "id": row.id,
                "question": row.question,
                "task_type": item.get("task_type", "all_tasks"),
                "task_input": {"question": row.question, "context": str(item.get("context", ""))[:self._max_context_chars]},
                "response": row.response,
                "predicted_answer": row.predicted_answer,
                "gold_answers": row.gold_answers,
                "score": row.em,
            } for row, item in zip(rows, batch, strict=True)]
        return EvaluationBatch(outputs=outputs, scores=scores, trajectories=traces)

    def make_reflective_dataset(self, candidate, eval_batch, components_to_update):
        traces = eval_batch.trajectories or []
        records = [{
            "Inputs": trace.get("question", ""),
            "Generated Outputs": trace.get("response", ""),
            "Feedback": f"EM score: {trace.get('score', 0)}",
        } for trace in traces]
        return {component: records for component in components_to_update}


class ALFWorldGEPAAdapter:
    """GEPA adapter backed by the shared single-episode ALFWorld runner."""

    propose_new_texts = None

    def __init__(self, *, config_path: str, split: str = "valid_seen",
                 base_url: str = "", model: str = "", api_key: str = "",
                 backend: str = "api", workers: int = 1, seed: int = 42,
                 max_tokens: int = 4096,
                 history_length: int = 2, max_steps: int | None = None):
        source = ROOT / "alfworld-eval" / "src"
        if str(source) not in sys.path:
            sys.path.insert(0, str(source))
        from alfworld_eval.env import AlfworldTextEnv
        from alfworld_eval.unified.agent import build_agent
        from alfworld_eval.unified.runner import run_unified_episode
        from alfworld_eval.unified.skills import SkillProvider, SkillView
        self._Env, self._build_agent = AlfworldTextEnv, build_agent
        self._run_episode = run_unified_episode
        self._SkillProvider, self._SkillView = SkillProvider, SkillView
        self._config_path, self._split = config_path, split
        self._base_url, self._model, self._api_key = base_url, model, api_key
        self._backend, self._workers, self._seed = backend, max(1, int(workers)), seed
        self._max_tokens = max_tokens
        self._history_length, self._max_steps = history_length, max_steps

    @_checkpoint_final_units
    def evaluate(self, batch, candidate, capture_traces=False):
        skill = _text(candidate)
        def _evaluate_one(item):
            gamefile = str(item["gamefile"] if isinstance(item, dict) else item)
            env = self._Env(config_path=self._config_path, split=self._split,
                            seed=self._seed, gamefiles=[gamefile])
            try:
                agent = self._build_agent(
                    self._backend, base_url=self._base_url, model=self._model,
                    api_key=self._api_key, temperature=0.0,
                    max_tokens=self._max_tokens, seed=self._seed,
                )
                provider = self._SkillProvider(
                    "skillopt", skill=self._SkillView(prefix=skill) if skill else self._SkillView()
                )
                result = self._run_episode(
                    env, agent, provider, max_steps=self._max_steps,
                    history_length=self._history_length, record_trajectory=capture_traces,
                )
                if getattr(self, "usage_ledger", None):
                    self.usage_ledger.record(result.usage, stage=getattr(self, "usage_stage", "evolution_execution"),
                                             model=self._model, item_id=gamefile)
                output = {"success": bool(result.success), "steps": result.steps}
                trace = {
                    "gamefile": gamefile,
                    "task_type": item.get("task_type", "all_tasks") if isinstance(item, dict) else "all_tasks",
                    "task": result.initial_observation,
                    "success": bool(result.success),
                    "steps": result.steps,
                    "trajectory": result.trajectory,
                } if capture_traces else None
                return float(result.success), output, trace
            except Exception as exc:  # noqa: BLE001 - isolate one bad episode
                if getattr(self, "usage_ledger", None):
                    self.usage_ledger.record(None, stage=getattr(self, "usage_stage", "evolution_execution"),
                                             model=self._model, item_id=gamefile, error=type(exc).__name__)
                return 0.0, {"success": False, "steps": 0, "error": str(exc)}, (
                    {"gamefile": gamefile, "success": False, "steps": 0,
                     "trajectory": [], "error": str(exc)} if capture_traces else None
                )
            finally:
                if hasattr(env, "close"):
                    env.close()

        if self._workers <= 1 or len(batch) <= 1:
            rows = [_evaluate_one(item) for item in batch]
        else:
            with ThreadPoolExecutor(max_workers=self._workers) as executor:
                rows = list(executor.map(_evaluate_one, batch))
        return EvaluationBatch(
            outputs=[row[1] for row in rows],
            scores=[row[0] for row in rows],
            trajectories=[row[2] for row in rows] if capture_traces else None,
        )

    def make_reflective_dataset(self, candidate, eval_batch, components_to_update):
        records = [{
            "Inputs": trace.get("gamefile", ""),
            "Generated Outputs": json.dumps(trace.get("trajectory", []), ensure_ascii=False),
            "Feedback": f"Success: {trace.get('success', False)}; steps: {trace.get('steps', 0)}",
        } for trace in (eval_batch.trajectories or [])]
        return {component: records for component in components_to_update}


def _load_skill(path: str | None) -> str:
    return Path(path).expanduser().read_text(encoding="utf-8") if path else ""


def build_benchmark(config: dict[str, Any]) -> dict[str, Any]:
    """Build ``gepa.optimize`` kwargs from a compact JSON config.

    ``benchmark`` is ``searchqa`` or ``alfworld``. The returned ``valset`` is
    always the complete configured validation split. ``testset`` stays outside
    GEPA's search and is scored once at the end by ``run.py``; the optional
    per-decision JudgeGate audit remains disabled unless explicitly requested.
    """
    benchmark = str(config.get("benchmark", "searchqa")).lower()
    root = Path(config.get("root", ROOT)).expanduser()
    seed_skill = _load_skill(config.get("seed_skill"))
    if benchmark == "searchqa":
        data_root = Path(config.get("data_root", root / "searchqa-eval/data/searchqa_split"))
        train = _read_json(config.get("train_items", data_root / "train/items.json"))
        val = _read_json(config.get("val_items", data_root / "val/items.json"))
        test = _read_json(config.get("test_items", data_root / "test/items.json"))
        adapter = SearchQAGEPAAdapter(
            base_url=config.get("base_url", os.environ.get("OPENAI_BASE_URL", "")),
            model=config.get("model", os.environ.get("OPENAI_MODEL", "")),
            api_key=config.get("api_key", os.environ.get("OPENAI_API_KEY", "")),
            backend=config.get("backend", "api"), workers=int(config.get("workers", 1)),
            seed=int(config.get("seed", 42)), max_tokens=int(config.get("max_tokens", 16384)),
        )
    elif benchmark == "alfworld":
        data_root = Path(config.get("data_root", root / "skillopt/data/alfworld_path_split"))
        train = _read_json(config.get("train_items", data_root / "train/items.json"))
        val = _read_json(config.get("val_items", data_root / "val/items.json"))
        test = _read_json(config.get("test_items", data_root / "test/items.json"))
        adapter = ALFWorldGEPAAdapter(
            config_path=str(config.get("env_config", root / "alfworld-eval/configs/textworld.yaml")),
            split="valid_seen",
            base_url=config.get("base_url", os.environ.get("OPENAI_BASE_URL", "")),
            model=config.get("model", os.environ.get("OPENAI_MODEL", "")),
            api_key=config.get("api_key", os.environ.get("OPENAI_API_KEY", "")),
            backend=config.get("backend", "api"), workers=int(config.get("workers", 1)),
            seed=int(config.get("seed", 42)),
            max_tokens=int(config.get("max_tokens", 4096)),
            max_steps=config.get("max_steps"),
        )
    else:
        raise ValueError(f"unsupported GEPA benchmark: {benchmark}")

    kwargs: dict[str, Any] = {
        "seed_candidate": {"skill": seed_skill},
        "trainset": train,
        "valset": val,
        # ``gepa.optimize`` has no test_set argument. The runner removes this
        # private builder value and performs the final held-out pass after
        # optimization, outside the JudgeGate acceptance loop.
        "testset": test,
        "adapter": adapter,
        "max_metric_calls": int(config.get("max_metric_calls", 20)),
        "skip_perfect_score": bool(config.get("skip_perfect_score", True)),
        "run_dir": config.get("run_dir"),
        "seed": int(config.get("seed", 42)),
        "reflection_minibatch_size": int(config.get("reflection_minibatch_size", 2)),
    }
    reflection_model = config.get("reflection_model", os.environ.get("OPENAI_MODEL", ""))
    if config.get("backend", "api") == "mock":
        def mock_proposer(candidate, reflective_dataset, components_to_update, **_):
            return {name: str(candidate[name]) + "\nBe concise and verify the observed evidence."
                    for name in components_to_update}
        kwargs["custom_candidate_proposer"] = mock_proposer
    elif reflection_model:
        kwargs["reflection_lm"] = _OpenAIReflectionLM(
            model=str(reflection_model),
            base_url=str(config.get("reflection_base_url", os.environ.get("OPENAI_BASE_URL", ""))),
            api_key=str(config.get("reflection_api_key", os.environ.get("OPENAI_API_KEY", ""))),
            max_tokens=int(config.get("reflection_max_tokens", 4096)),
            temperature=float(config.get("reflection_temperature", 0.0)),
        )
    else:
        raise ValueError("GEPA requires reflection_model or backend=mock")
    return kwargs


__all__ = ["SearchQAGEPAAdapter", "ALFWorldGEPAAdapter", "build_benchmark"]
