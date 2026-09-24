#!/usr/bin/env python3
"""Run a GEPA experiment with the shared JudgeGate criterion.

The JSON config names a Python factory returning kwargs accepted by
``gepa.optimize``. This keeps benchmark-specific adapters outside the runner
while giving all methods the same judge/version/full-validation switches.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT / "packages" / "skillopt", ROOT / "packages" / "gepa" / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def _load_factory(spec: str):
    module_name, sep, function_name = spec.partition(":")
    if not sep:
        raise ValueError("GEPA builder must use module:function syntax")
    return getattr(importlib.import_module(module_name), function_name)


def _evaluation_identity(items, seed, best):
    payload = json.dumps({"items": items, "seed": seed, "best": best}, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


class _OpenAIJudgeFn:
    """Adapt an OpenAI-compatible chat client to ``JudgeGate.chat_fn``."""

    def __init__(self, *, model: str, base_url: str, api_key: str):
        from openai import OpenAI

        self._client = OpenAI(
            base_url=base_url or None,
            api_key=api_key or None,
            timeout=float(os.environ.get("GEPA_HTTP_TIMEOUT", "180")),
            max_retries=2,
        )
        self._model = model

    def __call__(self, *, system: str, user: str, max_completion_tokens: int,
                 retries: int, stage: str):
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            temperature=0.0,
            max_tokens=int(max_completion_tokens),
            **({"extra_body": {"enable_thinking": False}}
               if "qwen" in self._model.lower() else {}),
        )
        usage = getattr(response, "usage", None)
        if getattr(self, "usage_ledger", None):
            self.usage_ledger.record(usage, stage=stage, model=self._model)
        return str(response.choices[0].message.content or ""), {
            "prompt_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
            "completion_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
            "model": self._model,
            "stage": stage,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="GEPA + JudgeGate runner")
    parser.add_argument("--config", required=True, help="JSON config with a builder field")
    parser.add_argument("--benchmark", choices=["searchqa", "alfworld"], default=None,
                        help="Override builder_kwargs.benchmark")
    parser.add_argument("--mode", choices=["baseline", "judge"], default="judge",
                        help="baseline uses GEPA strict improvement; judge uses JudgeGate")
    parser.add_argument("--judge-prompt-variant", default="v3")
    parser.add_argument("--judge-model", default=None,
                        help="Reserved for benchmark factories; model selection stays in the backend")
    parser.add_argument("--model", default=None,
                        help="Inference/reflection model override")
    parser.add_argument("--base-url", default=None,
                        help="OpenAI-compatible endpoint override")
    parser.add_argument("--api-key", default=None,
                        help="Endpoint key override")
    parser.add_argument("--output-dir", default=None,
                        help="Per-condition output directory")
    parser.add_argument("--full-validation-audit", action="store_true",
                        help="Legacy flag: rejected in judge mode")
    args = parser.parse_args()
    if args.model:
        os.environ["OPENAI_MODEL"] = args.model
    if args.base_url:
        os.environ["OPENAI_BASE_URL"] = args.base_url
    if args.api_key:
        os.environ["OPENAI_API_KEY"] = args.api_key
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    # The campaign-level switch is deliberately explicit. A checked-in config
    # may document the audit path/status, but it must not turn on an expensive
    # per-decision validation pass when the unified launcher uses its defaults.
    audit_enabled = bool(args.full_validation_audit)
    if args.mode == "judge" and audit_enabled:
        raise ValueError("Judge mode forbids candidate full-validation audit")
    if args.benchmark:
        config.setdefault("builder_kwargs", {})["benchmark"] = args.benchmark
    if args.model:
        config.setdefault("builder_kwargs", {}).update({
            "model": args.model,
            "reflection_model": args.model,
            "judge_model": args.judge_model or args.model,
        })
    if args.base_url:
        config.setdefault("builder_kwargs", {}).update({
            "base_url": args.base_url,
            "reflection_base_url": args.base_url,
        })
    if args.api_key:
        config.setdefault("builder_kwargs", {}).update({
            "api_key": args.api_key,
            "reflection_api_key": args.api_key,
        })
    if args.output_dir:
        output_dir = Path(args.output_dir).expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        config["result_path"] = str(output_dir / "result.json")
        config["validation_result_path"] = str(output_dir / "validation_eval.json")
        config["test_result_path"] = str(output_dir / "test_eval.json")
        config["full_validation_audit_path"] = str(output_dir / "judge_full_validation.jsonl")
        config.setdefault("builder_kwargs", {})["run_dir"] = str(output_dir / "gepa_run")
    builder_config = config.get("builder_kwargs", {})
    builder = _load_factory(str(config["builder"]))
    kwargs = dict(builder(config.get("builder_kwargs", {})))
    testset = kwargs.pop("testset", None)
    from gepa import optimize
    from gepa.strategies.acceptance import StrictImprovementAcceptance
    from gepa_judge import GEPAFullValidationAudit, make_judge_acceptance_criterion

    valset = kwargs.get("valset")
    audit_valset = list(valset or [])
    adapter = kwargs.get("adapter")
    audit = None
    if audit_enabled:
        if valset is None or adapter is None:
            raise ValueError("full validation requires builder kwargs: adapter and valset")
        audit = GEPAFullValidationAudit(
            adapter,
            audit_valset,
            audit_path=config.get("full_validation_audit_path"),
        )
    from gepa.utils.stop_condition import MaxCandidateProposalsStopper
    from judge_policy import JudgePredictionPolicy, observed_task_axes

    axes = None
    if args.mode == "judge":
        axes = observed_task_axes(list(kwargs.get("trainset") or []))
        kwargs["val_evaluation_policy"] = JudgePredictionPolicy(axes)
        kwargs["valset"] = [{"prediction_axis": axis} for axis in axes]
    else:
        kwargs["val_evaluation_policy"] = "full_eval"
        minimum = len(audit_valset) + 2 * int(kwargs.get("reflection_minibatch_size", 2))
        if kwargs.get("max_metric_calls") is not None and kwargs["max_metric_calls"] <= minimum:
            raise ValueError("GEPA baseline budget would be exhausted before its first candidate; increase max_metric_calls")
    stops = kwargs.get("stop_callbacks") or []
    if not isinstance(stops, (list, tuple)):
        stops = [stops]
    kwargs["stop_callbacks"] = list(stops) + [
        MaxCandidateProposalsStopper(int(builder_config.get("max_candidate_proposals", 8)))
    ]
    kwargs["acceptance_criterion"] = (
        make_judge_acceptance_criterion(
            prompt_variant=args.judge_prompt_variant,
            full_validation=audit,
            prediction_axes=axes,
            chat_fn=_OpenAIJudgeFn(
                model=str(args.judge_model or builder_config.get(
                    "judge_model", builder_config.get("model", os.environ.get("OPENAI_MODEL", ""))
                )),
                base_url=str(builder_config.get("base_url", os.environ.get("OPENAI_BASE_URL", ""))),
                api_key=str(builder_config.get("api_key", os.environ.get("OPENAI_API_KEY", ""))),
            ),
        )
        if args.mode == "judge"
        else StrictImprovementAcceptance()
    )
    from skillopt.evaluation.usage_ledger import UsageLedger

    ledger = UsageLedger(Path(config.get("result_path", "outputs/gepa/result.json")).with_name("usage_events.jsonl"))
    ledger.configure_replacement_cost("gepa", args.mode)
    adapter.usage_ledger = ledger
    reflection = kwargs.get("reflection_lm")
    if reflection is not None:
        reflection.usage_ledger = ledger
    if args.mode == "judge":
        kwargs["acceptance_criterion"].judge.chat_fn.usage_ledger = ledger
        kwargs["acceptance_criterion"].judge.replacement_ledger = ledger
    result = optimize(**kwargs)
    output = config.get("result_path")
    if output:
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        Path(output).write_text(json.dumps({"status": "complete", "score_source": "judge_prediction" if args.mode == "judge" else "measured_validation", "result": result.to_dict()}, indent=2) + "\n")
        Path(output).with_name("run_metadata.json").write_text(
            json.dumps({
                "mode": args.mode,
                "protocol": "direct_replacement_v3",
                "score_source": "judge_prediction" if args.mode == "judge" else "measured_validation",
                "prediction_axes": axes,
                "max_candidate_proposals": int(builder_config.get("max_candidate_proposals", 8)),
                "benchmark": args.benchmark or builder_config.get("benchmark"),
                "model": args.model or builder_config.get("model") or os.environ.get("OPENAI_MODEL"),
                "judge_model": args.judge_model or builder_config.get("judge_model"),
                "judge_prompt_variant": args.judge_prompt_variant,
                "full_validation_audit": audit_enabled,
            }, indent=2) + "\n",
            encoding="utf-8",
        )
    # Both splits are scored once after optimization. They are never passed
    # back into proposal acceptance, so these are final measurements rather
    # than the per-decision validation audit controlled above.
    adapter = kwargs.get("adapter")
    seed = kwargs.get("seed_candidate")
    best = getattr(result, "best_candidate", None)
    if adapter is None or best is None:
        raise RuntimeError("GEPA final evaluation requires adapter and best_candidate")

    def _final_eval(items, output_key: str, default_name: str) -> None:
        if not items:
            return
        adapter.usage_stage = "final_" + output_key
        target = config.get(output_key)
        if not target:
            target = str(Path(output).with_name(default_name)) if output else default_name
        target_path = Path(target)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # Final validation/test is a measurement, but it is still expensive.
        # Persist each completed chunk so a killed process resumes without
        # repeating the whole split. The final JSON format stays unchanged.
        checkpoint_path = target_path.with_suffix(".jsonl")
        identity_path = target_path.with_suffix(".identity.json")
        identity = _evaluation_identity(items, seed, best)
        if checkpoint_path.exists() and (
                not identity_path.exists() or json.loads(identity_path.read_text()) != identity):
            raise ValueError("Final checkpoint belongs to a different or unknown dataset/candidate")
        identity_path.write_text(json.dumps(identity))
        checkpoint: dict[int, dict[str, float]] = {}
        if checkpoint_path.is_file():
            for line in checkpoint_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                record = json.loads(line)
                index = int(record["index"])
                if 0 <= index < len(items):
                    checkpoint[index] = {
                        "baseline_score": float(record["baseline_score"]),
                        "best_score": float(record["best_score"]),
                    }

        chunk_size = max(1, int(os.environ.get("GEPA_FINAL_EVAL_CHUNK_SIZE", "32")))
        for start in range(0, len(items), chunk_size):
            indices = [
                index for index in range(start, min(start + chunk_size, len(items)))
                if index not in checkpoint
            ]
            if not indices:
                continue
            batch = [items[index] for index in indices]
            baseline_eval = adapter.evaluate(batch, seed, capture_traces=False)
            best_eval = adapter.evaluate(batch, best, capture_traces=False)
            if len(baseline_eval.scores) != len(indices) or len(best_eval.scores) != len(indices):
                raise RuntimeError(
                    f"final evaluation returned mismatched score count: "
                    f"expected {len(indices)}, got {len(baseline_eval.scores)} and "
                    f"{len(best_eval.scores)}"
                )
            for offset, index in enumerate(indices):
                checkpoint[index] = {
                    "baseline_score": float(baseline_eval.scores[offset]),
                    "best_score": float(best_eval.scores[offset]),
                }
            temporary = checkpoint_path.with_suffix(checkpoint_path.suffix + ".tmp")
            temporary.write_text(
                "".join(
                    json.dumps({"index": index, **checkpoint[index]}) + "\n"
                    for index in sorted(checkpoint)
                ),
                encoding="utf-8",
            )
            os.replace(temporary, checkpoint_path)

        if len(checkpoint) != len(items):
            raise RuntimeError(
                f"final evaluation incomplete: {len(checkpoint)} / {len(items)} items"
            )
        baseline_scores = [checkpoint[index]["baseline_score"] for index in range(len(items))]
        best_scores = [checkpoint[index]["best_score"] for index in range(len(items))]
        payload = {
            "items": len(items),
            "baseline_scores": baseline_scores,
            "best_scores": best_scores,
            "baseline_mean": sum(baseline_scores) / max(len(baseline_scores), 1),
            "best_mean": sum(best_scores) / max(len(best_scores), 1),
            "audit_enabled": audit_enabled,
            "evaluation_kind": "final_split_measurement",
        }
        target_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    _final_eval(audit_valset, "validation_result_path", "validation_eval.json")
    _final_eval(testset, "test_result_path", "test_eval.json")
    ledger.path.with_name("token_totals.json").write_text(json.dumps(ledger.summary(), indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
