"""Unified single-turn SearchQA evaluation runner.

One execution path for every method: build (system, user) prompts with the
method's skill injected, make one model call, extract the answer, score with
EM/F1/sub_EM. Batch execution mirrors SkillOpt's run_batch: ThreadPoolExecutor,
per-item result rows appended to results.jsonl, resume-aware by id.
"""
from __future__ import annotations

import json
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from pathlib import Path

from searchqa_eval.agent import Agent
from searchqa_eval.data import MAX_CONTEXT_CHARS
from searchqa_eval.evaluator import evaluate
from searchqa_eval.prompts import build_user_prompt

METHODS = ("vanilla", "skillopt", "trace2skill")


@dataclass
class ItemResult:
    id: str
    question: str
    em: float
    f1: float
    sub_em: float
    hard: int
    soft: float
    predicted_answer: str
    gold_answers: list[str]
    response: str
    agent_ok: bool
    fail_reason: str = ""
    usage: dict = field(default_factory=dict)

    def to_row(self, include_response: bool = False) -> dict:
        row = {
            "id": self.id,
            "question": self.question,
            "em": self.em,
            "f1": self.f1,
            "sub_em": self.sub_em,
            "hard": self.hard,
            "soft": self.soft,
            "predicted_answer": self.predicted_answer,
            "gold_answers": self.gold_answers,
            "agent_ok": self.agent_ok,
            "fail_reason": self.fail_reason,
        }
        # The raw response is the only record of the model's reasoning. It is
        # what a Trace2Skill-style error analyst reads to diagnose a failure,
        # and what the resume path at load time expects to find, so persist it
        # on request. Off by default to keep results.jsonl small.
        if include_response:
            row["response"] = self.response
        if self.usage:
            row["usage"] = self.usage
        return row


def process_one(
    item: dict,
    system_prompt: str,
    agent: Agent,
    *,
    max_context_chars: int = MAX_CONTEXT_CHARS,
    exec_timeout: float = 120.0,
) -> ItemResult:
    """Run + evaluate one QA item (SkillOpt process_one, single-turn)."""
    user_prompt = build_user_prompt(
        str(item["question"]),
        str(item.get("context", "")),
        max_context_chars,
    )
    started = time.time()
    try:
        response, usage = agent.respond(system_prompt, user_prompt)
        eval_result = evaluate(response, list(item.get("answers", [])))
        return ItemResult(
            id=str(item["id"]),
            question=str(item["question"]),
            em=eval_result["em"],
            f1=eval_result["f1"],
            sub_em=eval_result["sub_em"],
            hard=int(eval_result["em"]),
            soft=eval_result["f1"],
            predicted_answer=eval_result["predicted_answer"],
            gold_answers=eval_result["gold_answers"],
            response=response,
            agent_ok=True,
            usage={
                **usage,
                "latency_s": round(time.time() - started, 2),
            },
        )
    except Exception as exc:  # noqa: BLE001
        return ItemResult(
            id=str(item["id"]),
            question=str(item["question"]),
            em=0.0,
            f1=0.0,
            sub_em=0.0,
            hard=0,
            soft=0.0,
            predicted_answer="",
            gold_answers=list(item.get("answers", [])),
            response="",
            agent_ok=False,
            fail_reason=f"{type(exc).__name__}: {exc}",
            usage={"latency_s": round(time.time() - started, 2)},
        )


def _exec_timeout_of(agent: Agent, default: float) -> float:
    return float(getattr(agent, "timeout", default) or default)


def run_batch(
    items: list[dict],
    system_prompt: str,
    agent: Agent,
    *,
    out_dir: str | Path,
    workers: int = 24,
    max_context_chars: int = MAX_CONTEXT_CHARS,
    exec_timeout: float = 120.0,
    on_progress=None,
    record_response: bool = False,
    failed_retries: int = 1,
) -> list[ItemResult]:
    """Parallel execution with resume support and bounded failed-item retries.

    Failed rows are deliberately re-queued on resume. A transient endpoint
    timeout must not become permanent training evidence merely because the
    first process wrote a placeholder row before the request recovered.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    results_path = out / "results.jsonl"

    done: dict[str, ItemResult] = {}
    if results_path.exists():
        with results_path.open(encoding="utf-8") as f:
            for line in f:
                try:
                    row = json.loads(line)
                    done[str(row["id"])] = ItemResult(
                        id=str(row["id"]),
                        question=str(row.get("question", "")),
                        em=row.get("em", 0.0),
                        f1=row.get("f1", 0.0),
                        sub_em=row.get("sub_em", 0.0),
                        hard=int(row.get("hard", 0)),
                        soft=row.get("soft", 0.0),
                        predicted_answer=str(row.get("predicted_answer", "")),
                        gold_answers=list(row.get("gold_answers", [])),
                        response=str(row.get("response", "")),
                        agent_ok=bool(row.get("agent_ok", False)),
                        fail_reason=str(row.get("fail_reason", "")),
                        usage=row.get("usage", {}),
                    )
                except (json.JSONDecodeError, KeyError):
                    continue

    # Successful rows are final. Failed rows are eligible for a bounded retry,
    # including rows written by an earlier interrupted run.
    pending = [
        it for it in items
        if str(it["id"]) not in done or not done[str(it["id"])].agent_ok
    ]
    results = [done[str(it["id"])] for it in items if str(it["id"]) in done]
    if not pending:
        return results

    per_call_timeout = _exec_timeout_of(agent, exec_timeout)
    # Remove failed placeholders from the in-memory result set while retrying;
    # the final list contains exactly one row per item.
    results = [result for result in results if result.agent_ok]
    total = len(items)
    completed = len(results)
    attempts = {str(it["id"]): 0 for it in pending}

    with results_path.open("a", encoding="utf-8") as outf:
        executor = ThreadPoolExecutor(max_workers=workers)
        try:
            futures = {
                executor.submit(
                    process_one,
                    item,
                    system_prompt,
                    agent,
                    max_context_chars=max_context_chars,
                    exec_timeout=per_call_timeout,
                ): item
                for item in pending
            }
            outstanding = set(futures)
            while outstanding:
                finished, _ = wait(outstanding, timeout=5, return_when=FIRST_COMPLETED)
                for fut in finished:
                    outstanding.remove(fut)
                    item = futures[fut]
                    result = fut.result()
                    item_id = str(item["id"])
                    if not result.agent_ok and attempts[item_id] < max(0, int(failed_retries)):
                        attempts[item_id] += 1
                        retry = executor.submit(
                            process_one,
                            item,
                            system_prompt,
                            agent,
                            max_context_chars=max_context_chars,
                            exec_timeout=per_call_timeout,
                        )
                        futures[retry] = item
                        outstanding.add(retry)
                        continue

                    results.append(result)
                    completed += 1
                    row = result.to_row(record_response)
                    outf.write(json.dumps(row, ensure_ascii=False) + "\n")
                    outf.flush()
                    if on_progress:
                        on_progress(completed, total, result)
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    # During execution rows are appended for crash recovery. Compact them at
    # completion so a recovered failed item has one authoritative row and the
    # campaign's duplicate-id audit remains meaningful.
    by_id = {result.id: result for result in results}
    ordered = [by_id[str(item["id"])] for item in items if str(item["id"]) in by_id]
    include_response = record_response or any(result.response for result in ordered)
    compact_path = results_path.with_suffix(results_path.suffix + ".tmp")
    with compact_path.open("w", encoding="utf-8") as outf:
        for result in ordered:
            outf.write(json.dumps(result.to_row(include_response), ensure_ascii=False) + "\n")
    compact_path.replace(results_path)
    return ordered


def summarize(results: list[ItemResult]) -> dict:
    n = len(results)
    scored = [r for r in results if r.agent_ok]
    total_usage = {
        key: sum(r.usage.get(key, 0) for r in results if r.usage)
        for key in ("prompt_tokens", "completion_tokens", "api_calls", "api_errors")
    }
    return {
        "n_items": n,
        "agent_ok": len(scored),
        "agent_failed": n - len(scored),
        "em": round(sum(r.em for r in scored) / len(scored), 4) if scored else 0.0,
        "f1": round(sum(r.f1 for r in scored) / len(scored), 4) if scored else 0.0,
        "sub_em": round(sum(r.sub_em for r in scored) / len(scored), 4) if scored else 0.0,
        "usage": total_usage,
    }


def save_results(out_dir: str | Path, summary: dict, meta: dict) -> None:
    out = Path(out_dir)
    with (out / "summary.json").open("w", encoding="utf-8") as f:
        json.dump({**meta, "summary": summary}, f, indent=2, ensure_ascii=False)
