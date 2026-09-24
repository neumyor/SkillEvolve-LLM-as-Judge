#!/usr/bin/env python3
"""Bounded official-chain reproduction check, not a Judge comparison.

One training item, one validation item, one round, upstream native harnesses.
No credential values appear in argv or saved manifests. Fresh root required.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True, type=Path)
    parser.add_argument('--benchmark', required=True, choices=['searchqa', 'alfworld'])
    parser.add_argument('--model')
    parser.add_argument('--base-url')
    parser.add_argument('--canonicalize-seed', action='store_true',
                        help='Explicit input variant: strip trailing whitespace before freezing the seed')
    args = parser.parse_args()
    root = args.root.resolve()
    root.mkdir(parents=True, exist_ok=False)
    (root / 'pyproject.toml').write_text('# Official-chain smoke workspace\n')
    benchmark = args.benchmark
    config = json.loads((ROOT / 'benchmark/llm_config.local.json').read_text())
    section = config.get(f'{benchmark}-eval', config.get('default', {}))
    args.model = args.model or section.get('model')
    args.base_url = args.base_url or section.get('base_url')
    if not args.model or not args.base_url:
        raise ValueError(f'Missing {benchmark} model or endpoint in local configuration')
    env = dict(os.environ)
    env['RETHINKSKILL_CHECK_API_KEY'] = os.environ.get('OPENAI_API_KEY') or section['api_key']
    env['RETHINKSKILL_ALFWORLD_ASSET_ROOT'] = str(ROOT / 'packages/alfworld-eval/.data/alfworld')
    env.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', TOKENIZERS_PARALLELISM='false')
    split_dir = 'searchqa_split' if benchmark == 'searchqa' else 'alfworld_path_split'
    for split in ('train', 'val'):
        rows = json.loads((ROOT / 'packages/skillopt/data' / split_dir / split / 'items.json').read_text())
        folder = root / 'dataset' / split
        folder.mkdir(parents=True)
        (folder / 'items.json').write_text(json.dumps(rows[:1], ensure_ascii=False, indent=2))
    skill = ROOT / 'packages/skillopt/skillopt/envs' / benchmark / 'skills/initial.md'
    (root / 'seed.md').write_text(skill.read_text().rstrip() if args.canonicalize_seed else skill.read_text())
    python = ROOT / ('packages/alfworld-eval/.venv/bin/python' if benchmark == 'alfworld' else 'packages/skillopt/.venv/bin/python')
    prefix = [str(python), str(ROOT / 'scripts/run_rethinkskill_official.py'), '--repository', str(root)]
    if benchmark == 'alfworld':
        prefix += ['--load-harness-plugins']
    options = ['--benchmark', benchmark, '--dataset', str(root / 'dataset'),
        '--skill', str(root / 'seed.md'), '--out-root', str(root / 'runs/evolution'),
        '--train-limit', '1', '--validation-limit', '1', '--rounds', '1', '--timeout-seconds', '120',
        '--hard-dead-band', '.01' if benchmark == 'searchqa' else '.02']
    if benchmark == 'searchqa':
        options += ['--soft-rescue-delta', '.02']
    else:
        options += ['--asset-root', env['RETHINKSKILL_ALFWORLD_ASSET_ROOT']]
    for role in ('target', 'optimizer'):
        options += [f'--{role}-transport', 'openai-compatible', f'--{role}-model', args.model,
                    f'--{role}-api-base-url', args.base_url, f'--{role}-api-key-env', 'RETHINKSKILL_CHECK_API_KEY',
                    f'--{role}-reasoning-effort', '']
    (root / 'commands.json').write_text(json.dumps({'prefix': prefix, 'options': options,
        'canonicalize_seed': args.canonicalize_seed,
        'scope': 'official baseline chain only; local study seed and tiny splits; not a performance result'}, indent=2))
    commands = [('preflight', prefix + ['native-evolution-preflight'] + options),
                ('evolution', prefix + ['native-evolve'] + options + ['--authorize-model-calls']),
                ('audit', prefix + ['validate-run', str(root / 'runs/evolution')])]
    status = {}
    for label, command in commands:
        with (root / f'{label}.stdout.json').open('w') as output, (root / f'{label}.stderr.log').open('w') as error:
            completed = subprocess.run(command, env=env, stdout=output, stderr=error)
        status[label] = completed.returncode
        (root / 'check_status.json').write_text(json.dumps(status, indent=2))
        print(f'{benchmark} {label}: exit={completed.returncode}', flush=True)
        if completed.returncode:
            return completed.returncode
    return 0


if __name__ == '__main__':
    sys.exit(main())
