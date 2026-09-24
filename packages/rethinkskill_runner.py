#!/usr/bin/env python3
"""Official RethinkSkill components with baseline or execution-free Judge validation."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'packages'), str(ROOT / 'packages/rethinkskill/src'),
                str(ROOT / 'packages/skillopt'),
                str(ROOT / 'packages/rethinkskill/integrations/alfworld/src')]
from rethinkskill_study.runner import main
if __name__ == '__main__':
    raise SystemExit(main())
