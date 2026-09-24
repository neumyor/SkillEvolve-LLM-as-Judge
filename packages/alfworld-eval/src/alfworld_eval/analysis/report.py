"""Shared PASS/FAIL report formatting for Trace2Skill-style verifiers.

Trace2Skill's error analyst validates its diagnosis by running a verifier tool
and looking for a PASS verdict. The tool wrapper
(``repos/pulled/Trace2Skill/analysis/error_analysis_agent.py::create_evaluate_tool``)
detects success with the regex ``^Result:\\s+PASS\\b`` over the verifier's
stdout, and the runner treats a non-zero exit code as failure.

Any verifier ported to a new environment must therefore keep three things
identical to ``analysis/evaluate_output.py``:

1. a line ``Result:          PASS`` / ``Result:          FAIL``;
2. exit code 0 on pass, 1 on fail;
3. rich enough diagnostics that the analyst can locate the defect.

This module holds the parts of that contract that are environment-independent.
"""
from __future__ import annotations

RULE = "=" * 70
THIN = "-" * 70

PASS_LINE = "Result:          PASS"
FAIL_LINE = "Result:          FAIL"


def header(title: str, fields: dict[str, str], passed: bool, summary: str) -> list[str]:
    """Render the report preamble, including the contract-critical Result line."""
    lines = [RULE, title, RULE]
    width = max((len(k) for k in fields), default=0)
    for key, value in fields.items():
        lines.append(f"{key + ':':<{width + 2}} {value}")
    lines.append(PASS_LINE if passed else FAIL_LINE)
    lines.append(f"Summary:         {summary}")
    lines.append(THIN)
    return lines


def fmt_value(v: object) -> str:
    """Format a value for display, disambiguating empty/None and showing type."""
    if v is None:
        return "None (empty)"
    if isinstance(v, str):
        return f'"{v}" (str)'
    return f"{v} ({type(v).__name__})"
