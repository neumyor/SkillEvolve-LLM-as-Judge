#!/usr/bin/env python3
"""Unmodified upstream CLI, separate from the unverified study/Judge adapter.

Uses upstream argument names and artifact contracts. This does not claim to be
the study comparison runner, and does not synthesize study summaries.
"""
from pathlib import Path
import sys

PACKAGE = Path(__file__).resolve().parents[1] / "packages/rethinkskill"
sys.path.insert(0, str(PACKAGE / "src"))

from rethinkskill.cli import main

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
