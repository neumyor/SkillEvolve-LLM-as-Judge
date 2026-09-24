"""JSON pipe server; one benchmark-owned ALFWorld environment per process."""
import contextlib
import dataclasses
import hashlib
import json
import os
from pathlib import Path
import sys

import yaml


def main():
    # Keep the protocol stream separate from ALFWorld's diagnostic stdout.
    protocol = sys.stdout
    env = None
    with contextlib.redirect_stdout(sys.stderr):
        try:
            for line in sys.stdin:
                request = json.loads(line)
                try:
                    operation = request['operation']
                    if operation == 'open':
                        root = Path(request['benchmark_root']).resolve()
                        sys.path.insert(0, str(root/'src'))
                        from alfworld_eval import env as module
                        if Path(module.__file__).resolve() != root/'src/alfworld_eval/env.py':
                            raise RuntimeError('Unexpected ALFWorld environment module')
                        os.environ['ALFWORLD_DATA'] = str(root/'.data/alfworld')
                        gamefile = Path(request['gamefile']).resolve()
                        workspace = Path(request['workspace']).resolve()
                        with Path(request['config']).open() as source:
                            config = yaml.safe_load(source)
                        for key in ('data_path', 'eval_id_data_path', 'eval_ood_data_path'):
                            config['dataset'][key] = str(gamefile.parent)
                        config['logic']['domain'] = str(workspace/'logic/alfred.pddl')
                        config['logic']['grammar'] = str(workspace/'logic/alfred.twl2')
                        effective_config = workspace/'benchmark_effective_config.yaml'
                        effective_config.write_text(yaml.safe_dump(config, sort_keys=True))
                        env = module.AlfworldTextEnv(
                            config_path=effective_config, split=request['split'],
                            seed=request['seed'], gamefiles=[str(gamefile)])
                        result = {'pid': os.getpid(), 'module': module.__file__,
                                  'python': sys.executable, 'step_budget': env.step_budget,
                                  'effective_config_sha256': hashlib.sha256(effective_config.read_bytes()).hexdigest()}
                    elif operation == 'reset':
                        result = dataclasses.asdict(env.reset())
                    elif operation == 'step':
                        state = env.step(request['action'])
                        result = {'observation': dataclasses.asdict(state.observation),
                                  'done': state.done, 'won': state.won}
                    elif operation == 'close':
                        result = None
                    else:
                        raise ValueError('Unknown environment operation')
                    protocol.write(json.dumps({'result': result})+'\n')
                    protocol.flush()
                    if operation == 'close':
                        break
                except Exception as exc:
                    protocol.write(json.dumps({'error': f'{type(exc).__name__}: {exc}'})+'\n')
                    protocol.flush()
                    break
        finally:
            if env is not None:
                env.close()


if __name__ == '__main__':
    main()
