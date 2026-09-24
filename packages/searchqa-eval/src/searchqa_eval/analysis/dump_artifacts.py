#!/usr/bin/env python3
"""Build Trace2Skill error-analysis workspaces from a SearchQA eval run.

This is the SearchQA analogue of ``setup_analysis_dir`` in Trace2Skill's
``analysis/run_error_analysis.py``. It turns harness output into the directory
layout the error analyst expects::

    {output_dir}/{item_id}/
        agent_log.md          # the episode rendered as a readable transcript
        agent_work/
            input.json        # question + retrieved context (what the agent saw)
            output.json       # the agent's answer  (candidate under test)
            gold.json         # the gold answers    (ground truth)

The split between ``input.json`` and ``gold.json`` matters: the analyst is
instructed to reason strictly from what the target agent could see, and the
gold file exists only so the verifier can be run. Keeping them in separate
files makes that boundary explicit rather than relying on the prompt alone.

Requires the run to have been produced with ``--record-response``; without it
``results.jsonl`` carries no reasoning trace and the analyst can only see the
final answer.

Usage::

    python -m searchqa_eval.analysis.dump_artifacts \\
        --run-dir outputs/unified_vanilla_20260911_104744 \\
        --items data/searchqa_split/test/items.json \\
        --output-dir analysis_workspaces \\
        --failures-only
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load_rows(run_dir: Path) -> list[dict]:
    path = run_dir / "results.jsonl"
    if not path.is_file():
        raise SystemExit(f"No results.jsonl in {run_dir}")
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_items(items_path: Path) -> dict[str, dict]:
    data = json.loads(items_path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("data") or list(data.values())
    return {str(it["id"]): it for it in data}


def render_log(row: dict, item: dict) -> str:
    """Render the episode as a transcript the analyst can read."""
    lines = [
        f"# SearchQA Episode — {row.get('id', '?')}",
        "",
        "## Task (first user message)",
        "",
        "Answer the question using the retrieved context. Put the final answer "
        "inside <answer>...</answer> tags.",
        "",
        "### Question",
        "",
        str(row.get("question") or item.get("question", "")),
        "",
        "### Retrieved context",
        "",
        "```",
        str(item.get("context", "(context unavailable — item not found in items.json)")),
        "```",
        "",
        "## Agent response",
        "",
    ]
    response = row.get("response")
    if response:
        lines += ["```", str(response), "```"]
    else:
        lines += [
            "_(raw response not recorded — re-run the eval with "
            "`--record-response` to capture the model's reasoning)_",
            "",
            f"Extracted answer: `{row.get('predicted_answer', '')}`",
        ]
    lines += [
        "",
        "## Outcome",
        "",
        # Explicit marker the pipeline greps for to route the workspace to the
        # error analyst (FAILURE) or the success analyst (SUCCESS); mirrors the
        # ALFWorld agent_log convention.
        f"Outcome: {'SUCCESS' if float(row.get('em') or 0.0) >= 1.0 else 'FAILURE'}",
        "",
        f"- EM: {row.get('em')}",
        f"- F1: {row.get('f1')}",
        f"- sub_EM: {row.get('sub_em')}",
        f"- agent_ok: {row.get('agent_ok')}",
    ]
    if row.get("fail_reason"):
        lines.append(f"- fail_reason: {row['fail_reason']}")
    return "\n".join(lines) + "\n"


def setup_analysis_dir(output_dir: Path, row: dict, item: dict) -> Path:
    item_id = str(row["id"])
    analysis_dir = output_dir / item_id
    agent_work = analysis_dir / "agent_work"
    agent_work.mkdir(parents=True, exist_ok=True)

    (analysis_dir / "agent_log.md").write_text(render_log(row, item), encoding="utf-8")

    (agent_work / "input.json").write_text(json.dumps({
        "id": item_id,
        "question": row.get("question") or item.get("question", ""),
        "context": item.get("context", ""),
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    output_payload = {"id": item_id, "answer": row.get("predicted_answer", "")}
    if row.get("response"):
        output_payload["response"] = row["response"]
    (agent_work / "output.json").write_text(
        json.dumps(output_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    (agent_work / "gold.json").write_text(json.dumps({
        "id": item_id,
        "question": row.get("question") or item.get("question", ""),
        "answers": row.get("gold_answers") or item.get("answers", []),
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    return analysis_dir


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path,
                        help="Eval output dir containing results.jsonl")
    parser.add_argument("--items", required=True, type=Path,
                        help="items.json used for the run (supplies the context)")
    parser.add_argument("--output-dir", required=True, type=Path,
                        help="Where to write the per-item analysis workspaces")
    parser.add_argument("--failures-only", action="store_true",
                        help="Only dump items with EM < 1.0 (the error-analyst input)")
    parser.add_argument("--successes-only", action="store_true",
                        help="Only dump items with EM == 1.0 (the success-analyst input)")
    parser.add_argument("--limit", type=int, default=0, help="Cap the number dumped (0 = all)")
    args = parser.parse_args()

    if args.failures_only and args.successes_only:
        raise SystemExit("--failures-only and --successes-only are mutually exclusive")

    rows = load_rows(args.run_dir)
    items = load_items(args.items)

    selected = []
    for row in rows:
        em = float(row.get("em") or 0.0)
        if args.failures_only and em >= 1.0:
            continue
        if args.successes_only and em < 1.0:
            continue
        selected.append(row)
    if args.limit:
        selected = selected[:args.limit]

    missing_context = 0
    missing_response = 0
    for row in selected:
        item = items.get(str(row["id"]), {})
        if not item.get("context"):
            missing_context += 1
        if not row.get("response"):
            missing_response += 1
        setup_analysis_dir(args.output_dir, row, item)

    print(f"Wrote {len(selected)} analysis workspace(s) to {args.output_dir}")
    if missing_context:
        print(f"  WARNING: {missing_context} item(s) had no context "
              f"(id not found in {args.items})")
    if missing_response:
        print(f"  WARNING: {missing_response} item(s) had no recorded response; "
              "re-run the eval with --record-response for full analyst input")
    return 0


if __name__ == "__main__":
    sys.exit(main())
