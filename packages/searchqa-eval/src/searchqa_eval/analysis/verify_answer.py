#!/usr/bin/env python3
"""Verify a proposed SearchQA answer against the gold answers.

This is the SearchQA analogue of Trace2Skill's ``analysis/evaluate_output.py``.

The candidate artifact is an answer rather than a workbook, so "comparing
cells" becomes "scoring the answer". Crucially the scoring is delegated to
``searchqa_eval.evaluator`` — the exact code the eval harness uses — so the
analyst's notion of correctness cannot drift from the benchmark's. A verifier
with its own private scoring rule would let the analyst validate fixes that the
harness would still mark wrong.

Candidate file format (JSON)::

    {"id": "...", "answer": "Risky Business"}

``response`` is accepted in place of ``answer`` and is run through the same
``<answer>...</answer>`` extraction the harness applies to raw model output.

Ground truth format (JSON)::

    {"id": "...", "answers": ["Risky Business"], "question": "...", "context": "..."}

Usage::

    python -m searchqa_eval.analysis.verify_answer \\
        --output_file agent_work/output_fixed.json \\
        --ground_truth agent_work/gold.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from searchqa_eval.analysis.report import RULE, THIN, header
from searchqa_eval.evaluator import evaluate, extract_answer, normalize_answer

# The harness reports EM/F1/sub_EM; a task counts as solved when EM is 1.0.
# sub_EM is reported too because it is what distinguishes a near-miss (right
# entity, wrong surface form) from a genuinely wrong answer.
PASS_METRIC = "em"


def _load_json(path: str, label: str) -> tuple[dict | None, str]:
    p = Path(path)
    if not p.is_file():
        return None, f"{label} file does not exist: {path}"
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, f"{label} file is not valid JSON: {exc}"
    if not isinstance(data, dict):
        return None, f"{label} JSON must be an object"
    return data, ""


def load_candidate(path: str) -> tuple[str, str]:
    """Read the candidate answer. Returns (answer_text, error)."""
    data, error = _load_json(path, "Candidate")
    if error:
        return "", error
    if "answer" in data:
        return str(data["answer"]), ""
    if "response" in data:
        # Raw model output — apply the harness's own extraction.
        return extract_answer(str(data["response"])), ""
    return "", "Candidate JSON has neither an 'answer' nor a 'response' key"


def load_gold(path: str) -> tuple[dict, str]:
    """Read the gold record. Returns (record, error)."""
    data, error = _load_json(path, "Ground truth")
    if error:
        return {}, error
    answers = data.get("answers")
    if answers is None:
        return {}, "Ground truth JSON has no 'answers' key"
    if not isinstance(answers, list) or not answers:
        return {}, "'answers' must be a non-empty list"
    return data, ""


def build_report(answer: str, gold: dict, output_file: str,
                 ground_truth: str) -> tuple[bool, str, str]:
    """Render the verification report. Returns (passed, summary, text)."""
    gold_answers = [str(a) for a in gold["answers"]]
    # evaluate() re-runs extraction; passing the already-extracted answer is
    # idempotent because text without tags falls through to itself.
    scores = evaluate(answer, gold_answers)
    passed = scores[PASS_METRIC] == 1.0

    if passed:
        summary = "PASS — answer matches the ground truth (EM = 1.0)."
    elif scores["sub_em"] == 1.0:
        summary = (
            f"FAIL — EM = 0.0 but sub_EM = 1.0: the answer overlaps the gold "
            f"answer but does not match it exactly (F1 = {scores['f1']:.3f})."
        )
    elif scores["f1"] > 0.0:
        summary = (
            f"FAIL — EM = 0.0, partial token overlap only "
            f"(F1 = {scores['f1']:.3f})."
        )
    else:
        summary = "FAIL — EM = 0.0, no token overlap with any gold answer."

    fields = {
        "Candidate file": output_file,
        "Ground truth": ground_truth,
    }
    if gold.get("id"):
        fields["Item id"] = str(gold["id"])
    if gold.get("question"):
        fields["Question"] = str(gold["question"])

    lines = header("SEARCHQA ANSWER VERIFICATION REPORT", fields, passed, summary)

    lines.append("Scores:")
    lines.append(f"  EM     : {scores['em']:.1f}")
    lines.append(f"  F1     : {scores['f1']:.4f}")
    lines.append(f"  sub_EM : {scores['sub_em']:.1f}")
    lines.append("")
    lines.append("Answer comparison:")
    lines.append(f"  Predicted (raw)        : {scores['predicted_answer']!r}")
    lines.append(f"  Predicted (normalized) : {normalize_answer(scores['predicted_answer'])!r}")
    lines.append("  Gold answers:")
    for g in gold_answers:
        mark = "==" if normalize_answer(g) == normalize_answer(scores["predicted_answer"]) else "!="
        lines.append(f"    [{mark}] {g!r}  -> normalized {normalize_answer(g)!r}")

    if not passed:
        lines.append("")
        lines.append("Hint: the harness scores EM after the normalization shown above")
        lines.append("(lowercase, punctuation stripped, articles removed, whitespace")
        lines.append("collapsed). A near-miss on sub_EM usually means extra words were")
        lines.append("included in the answer span rather than a wrong entity.")

    lines.append(THIN)
    lines.append(RULE)
    return passed, summary, "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify a SearchQA answer against the gold answers."
    )
    parser.add_argument("--output_file", required=True,
                        help="Candidate JSON with an 'answer' or 'response' key")
    parser.add_argument("--ground_truth", required=True,
                        help="Gold JSON with an 'answers' list")
    args = parser.parse_args()

    def fail(msg: str) -> int:
        print(RULE)
        print("SEARCHQA ANSWER VERIFICATION REPORT")
        print(RULE)
        print("Result:          FAIL")
        print(f"Summary:         {msg}")
        print(RULE)
        return 1

    gold, error = load_gold(args.ground_truth)
    if error:
        return fail(error)

    answer, error = load_candidate(args.output_file)
    if error:
        return fail(error)

    passed, _, text = build_report(answer, gold, args.output_file, args.ground_truth)
    print(text)
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
