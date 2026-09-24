#!/usr/bin/env python3
"""Fast repository audit for the assembled judge-gate study."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "packages/skillopt/skillopt/evaluation/judge_gate.py",
    "packages/skillopt/tests/test_judge_gate.py",
    "packages/skillopt/tests/test_trainer_judge_gate.py",
    "packages/searchqa-eval/src/searchqa_eval/analysis/judge_answer.py",
    "packages/alfworld-eval/src/alfworld_eval/analysis/judge_episode.py",
    "experiments/judgestudy/analysis/audit_gates.py",
    "experiments/judgestudy/analysis/paired.py",
    "docs/reports/judge_gate_vs_regression_test.md",
)
SECRET_RE = re.compile(
    r"(?:JUDGE_API_KEY|OPENAI_API_KEY|QWEN_CHAT_API_KEY|TRACE2SKILL_API_KEY)"
    r"\s*[:=]\s*['\"]?sk-[A-Za-z0-9]+|"
    r"['\"]api_key['\"]\s*:\s*['\"]sk-[A-Za-z0-9]+"
)
SKIP_DIRS = {".git", ".venv", ".venv-alfworld", ".uv-cache", ".uv-cache-sandbox",
             ".pytest_cache", ".ruff_cache", "outputs", ".data"}


def main() -> int:
    errors: list[str] = []
    for rel in REQUIRED:
        if not (ROOT / rel).is_file():
            errors.append(f"missing required file: {rel}")

    json_count = jsonl_count = 0
    for path in ROOT.rglob("*"):
        if (
            not path.is_file()
            or SKIP_DIRS.intersection(path.parts)
            or path.name == "llm_config.local.json"
        ):
            continue
        if path.suffix == ".json":
            json_count += 1
            try:
                json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"invalid JSON {path.relative_to(ROOT)}: {exc}")
        elif path.suffix == ".jsonl":
            jsonl_count += 1
            try:
                for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                    if line.strip():
                        json.loads(line)
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"invalid JSONL {path.relative_to(ROOT)}:{line_no}: {exc}")

        if path.suffix in {".json", ".jsonl", ".py", ".sh", ".md", ".yaml", ".yml"}:
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if SECRET_RE.search(text):
                errors.append(f"possible credential in {path.relative_to(ROOT)}")

    if errors:
        print("repository audit: FAIL")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print(f"repository audit: OK ({json_count} JSON, {jsonl_count} JSONL files checked)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
