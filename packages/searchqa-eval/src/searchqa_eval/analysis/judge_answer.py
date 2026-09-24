#!/usr/bin/env python3
"""Judge a proposed SearchQA answer instead of scoring it against gold.

This is the replacement for ``verify_answer`` when the point of the experiment
is to remove the regression test. ``verify_answer`` delegates to the benchmark's
own scorer, so its PASS is the ground truth: the analyst cannot mark an item
fixed unless the fix really is correct. This module makes no such claim. It
shows an agent the question, the context the target agent saw, the answer it
gave, and the candidate correction, and asks whether the correction is right and
whether its explanation generalizes.

The report keeps the same shape the analyst loop greps for
(``Result:          PASS``/``FAIL`` plus a summary line), so
``analyst._call_tool`` can swap one for the other without the loop knowing.
``Result:`` is followed by the judge's verdict, and the report says explicitly
that the verdict is not ground truth, so nothing downstream can mistake a
judge PASS for a scored one.

Usage::

    python -m searchqa_eval.analysis.judge_answer \\
        --output_file agent_work/output_fixed.json \\
        --gold agent_work/gold.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

from searchqa_eval.analysis.report import RULE, THIN, header

#: Locates the verifier's verdict line, matching the replay verifier's "PASS".
_VERDICT_RE = re.compile(r'"verdict"\s*:\s*"(PASS|FAIL|pass|fail)"')
#: Cap on the retrieved context shown to the judge.
MAX_CONTEXT_CHARS = 6000


def _load_json(path: str) -> tuple[dict | None, str]:
    p = Path(path)
    if not p.is_file():
        return None, f"file does not exist: {path}"
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, f"not valid JSON: {exc}"
    if not isinstance(data, dict):
        return None, "JSON must be an object"
    return data, ""


def _read_candidate(path: Path) -> tuple[str, str]:
    data, error = _load_json(str(path))
    if error:
        return "", f"Candidate {error}"
    for key in ("answer", "response"):
        if key in data:
            return str(data[key]), ""
    return "", "Candidate JSON has neither an 'answer' nor a 'response' key"


JUDGE_SYSTEM_PROMPT_V1 = """You are judging a correction to a wrong answer.

You will see: the question, the retrieved context the answering agent had, the
answer it produced, and a corrected answer with the analyst's diagnosis.

You do NOT have the gold answers. Decide from the context alone:

1. **Supported?** Does the retrieved context actually contain the corrected
   answer? A correction the context does not support is a guess, and a guess
   must not be accepted — the whole point of the regression test you replace is
   to stop guesses from reaching the user.
2. **Right span?** Is the correction the entity the question asks for, at the
   right granularity? Answers that append descriptive categories, or drop a
   qualifier the question requires, are wrong even when the entity is right.
3. **Generalizable?** The diagnosis behind the correction should name a decision
   the agent got wrong (which passage it trusted, how it chose the span) and not
   merely restate the answer. If the "fix" is only the answer, it teaches
   nothing and will not transfer.

Be strict: a correction you would not bet on is a FAIL.

Answer with exactly one JSON object and nothing else:

{"verdict": "PASS" | "FAIL", "reason": "<two or three sentences naming what you checked>"}
"""

JUDGE_SYSTEM_PROMPT_V2 = JUDGE_SYSTEM_PROMPT_V1.replace(
    "Be strict: a correction you would not bet on is a FAIL.",
    "Be strict: a correction you would not bet on is a FAIL. Name the defect "
    "mechanism and one concrete falsifier; unsupported or flat corrections FAIL.",
)
JUDGE_PROMPT_VARIANTS = {"v1": JUDGE_SYSTEM_PROMPT_V1, "v2": JUDGE_SYSTEM_PROMPT_V2}


def register_judge_prompt_variant(name: str, prompt: str, *, replace: bool = False) -> None:
    """Register a named Trace2Skill judge prompt without changing the runner."""
    key = str(name or "").strip().lower()
    if not key or not str(prompt or "").strip():
        raise ValueError("judge prompt variant requires a non-empty name and prompt")
    if key in JUDGE_PROMPT_VARIANTS and not replace:
        raise ValueError(f"judge prompt variant already exists: {key}")
    JUDGE_PROMPT_VARIANTS[key] = str(prompt)


def available_judge_prompt_variants() -> tuple[str, ...]:
    return tuple(sorted(JUDGE_PROMPT_VARIANTS))


def judge_prompt_variant() -> tuple[str, str]:
    variant = os.environ.get("TRACE2SKILL_JUDGE_PROMPT_VARIANT", "v1").strip().lower()
    return variant, JUDGE_PROMPT_VARIANTS.get(variant, JUDGE_SYSTEM_PROMPT_V1)


def _build_prompt(input_record: dict, output_record: dict, gold: dict, candidate: str) -> str:
    question = str(input_record.get("question") or gold.get("question") or "")
    context = str(input_record.get("context") or "")[:MAX_CONTEXT_CHARS]
    original = output_record.get("answer") or output_record.get("response") or "(none)"
    return (
        f"## Question\n{question}\n\n"
        f"## Retrieved Context\n{context}\n\n"
        f"## Answer the Agent Produced\n{original}\n\n"
        f"## Proposed Correction\n{candidate}\n\n"
        "Decide whether this correction should be accepted. Answer with the JSON "
        "object described in your instructions and nothing else."
    )


def _call_judge(prompt: str, *, max_tokens: int, timeout: float) -> tuple[str, str]:
    """One judge call against the configured endpoint. Returns (text, error)."""
    base_url = os.environ.get("TRACE2SKILL_BASE_URL", "").strip()
    model = os.environ.get("TRACE2SKILL_MODEL", "").strip()
    api_key = os.environ.get("TRACE2SKILL_API_KEY", "").strip()
    if not base_url or not model:
        return "", "TRACE2SKILL_BASE_URL / TRACE2SKILL_MODEL are not set"
    _variant, system_prompt = judge_prompt_variant()
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.0,
        "max_tokens": max_tokens,
    }
    request = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.load(response)
    except Exception as exc:  # noqa: BLE001 — the caller degrades, never crashes
        return "", f"{type(exc).__name__}: {exc}"
    try:
        return body["choices"][0]["message"]["content"] or "", ""
    except (KeyError, IndexError, TypeError) as exc:
        return "", f"unexpected response shape: {exc}"


def parse_verdict(text: str) -> tuple[str, str, str]:
    """Return (verdict, reason, error). Verdict is "" when unparseable."""
    text = (text or "").strip()
    if not text:
        return "", "", "empty judge response"
    candidates = re.findall(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL) + [text]
    for candidate in candidates:
        start, end = candidate.find("{"), candidate.rfind("}")
        if start == -1 or end <= start:
            continue
        try:
            payload = json.loads(candidate[start:end + 1])
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        verdict = str(payload.get("verdict", "") or "").strip().upper()
        if verdict in ("PASS", "FAIL"):
            return verdict, str(payload.get("reason", "") or "").strip(), ""
    match = _VERDICT_RE.search(text)
    if match:
        return match.group(1).upper(), "", ""
    return "", "", "judge response carries no verdict"


def build_report(
    verdict: str,
    reason: str,
    error: str,
    *,
    candidate: str,
    output_file: str,
    gold: dict,
) -> tuple[bool, str, str]:
    """Render the judge report. Returns (passed, summary, text)."""
    passed = verdict == "PASS"
    if error:
        summary = f"FAIL — judge unavailable ({error}); treated as FAIL."
    elif passed:
        summary = f"PASS — judge accepted the correction: {reason or '(no reason given)'}"
    else:
        summary = f"FAIL — judge rejected the correction: {reason or '(no reason given)'}"

    fields = {
        "Candidate file": output_file,
        "Item id": str(gold.get("id", "")),
        "Verifier": "judge (no ground-truth scoring)",
    }
    lines = header("SEARCHQA ANSWER JUDGE REPORT", fields, passed, summary)
    lines.append("This verdict comes from a judging agent reading the retrieved")
    lines.append("context. No gold answer was consulted and no answer was scored.")
    lines.append("")
    lines.append(f"  Proposed correction : {candidate!r}")
    if reason:
        lines.append(f"  Judge reason        : {reason}")
    if error:
        lines.append(f"  Judge error         : {error}")
    lines.append(THIN)
    lines.append(RULE)
    return passed, summary, "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output_file", required=True,
                        help="Candidate JSON with an 'answer' or 'response' key")
    parser.add_argument("--gold", required=True,
                        help="The item record (used for id/question; answers are NOT read)")
    parser.add_argument("--max_tokens", type=int, default=1024)
    parser.add_argument("--timeout", type=float, default=120.0)
    args = parser.parse_args()

    def fail(reason: str) -> int:
        passed, _, text = build_report("", "", reason, candidate="",
                                       output_file=args.output_file, gold={})
        print(text)
        return 0 if passed else 1

    gold, error = _load_json(args.gold)
    if error:
        return fail(f"gold record {error}")

    workspace = Path(args.output_file).resolve().parent.parent
    input_record, _ = _load_json(str(workspace / "agent_work" / "input.json"))
    output_record, _ = _load_json(str(workspace / "agent_work" / "output.json"))

    candidate, candidate_error = _read_candidate(Path(args.output_file))
    if candidate_error:
        return fail(candidate_error)

    prompt = _build_prompt(input_record or {}, output_record or {}, gold, candidate)
    text, call_error = _call_judge(prompt, max_tokens=args.max_tokens, timeout=args.timeout)
    verdict, reason, verdict_error = parse_verdict(text)

    passed, _, report = build_report(
        verdict, reason, call_error or verdict_error,
        candidate=candidate, output_file=args.output_file, gold=gold,
    )
    print(report)
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
