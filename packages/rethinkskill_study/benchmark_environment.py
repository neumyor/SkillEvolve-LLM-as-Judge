"""Process-isolated bridge to the workspace's authoritative ALFWorld environment."""
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import selectors
import subprocess
import time

from rethinkskill_alfworld.runtime import AlfWorldState
from .local_config import benchmark_root

BENCHMARK_ROOT = benchmark_root()


def benchmark_provenance(config):
    root = BENCHMARK_ROOT
    config = Path(config).resolve()
    if not config.is_relative_to(root/'configs'):
        raise ValueError('ALFWorld config must come from benchmark/alfworld-eval/configs')
    files = [root/'src/alfworld_eval/env.py', config, root/'uv.lock', root/'pyproject.toml']
    for file in files:
        if not file.is_file():
            raise ValueError(f'Required benchmark file missing: {file}')
    python = root/'.venv/bin/python'
    if not python.is_file():
        raise ValueError(f'Required benchmark Python missing: {python}')
    return {'kind': 'workspace_benchmark_alfworld', 'ready': True,
            'root': str(root), 'python': str(python), 'config': str(config),
            'data': str(root/'.data/alfworld'),
            'environment': 'alfworld_eval.env.AlfworldTextEnv',
            'isolation': 'one child process per active episode; maximum 64',
            'files': {str(f): hashlib.sha256(f.read_bytes()).hexdigest() for f in files}}


class BenchmarkEpisode:
    def __init__(self, *, gamefile, workspace, seed, split, config, timeout=120):
        self.timeout = timeout
        self.gamefile = Path(gamefile).resolve()
        self._stdout_buffer = bytearray()
        workspace.mkdir(parents=True, exist_ok=True)
        self.log = (workspace/'benchmark_environment.log').open('w')
        env = dict(os.environ, ALFWORLD_DATA=str(BENCHMARK_ROOT/'.data/alfworld'),
                   OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1')
        # Environment workers never need model credentials or study imports.
        env.pop('PYTHONPATH', None)
        for key in list(env):
            if 'API_KEY' in key or key.endswith('LLM_KEY'):
                env.pop(key)
        try:
            self.process = subprocess.Popen(
                [str(BENCHMARK_ROOT/'.venv/bin/python'), '-u',
                 str(Path(__file__).with_name('benchmark_environment_worker.py'))],
                cwd=BENCHMARK_ROOT, env=env, stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=self.log, text=True)
            opened = self.request('open', benchmark_root=str(BENCHMARK_ROOT),
                                  config=str(config), gamefile=str(self.gamefile),
                                  workspace=str(workspace), seed=seed,
                                  split={'val': 'valid_seen', 'test': 'valid_unseen'}.get(split, split))
            self.pid = opened['pid']
            self.step_budget = opened['step_budget']
            # Stable provenance participates in task evidence, unlike transient PIDs.
            (workspace/'benchmark_environment.json').write_text(json.dumps({
                'module': opened['module'], 'python': opened['python'],
                'config': str(config), 'step_budget': self.step_budget,
                'effective_config_sha256': opened['effective_config_sha256']}, sort_keys=True)+'\n')
        except BaseException:
            self.close()
            raise

    def request(self, operation, **payload):
        self.process.stdin.write(json.dumps({'operation': operation, **payload})+'\n')
        self.process.stdin.flush()
        deadline = time.monotonic() + self.timeout
        with selectors.DefaultSelector() as selector:
            selector.register(self.process.stdout, selectors.EVENT_READ)
            while b'\n' not in self._stdout_buffer:
                remaining = deadline - time.monotonic()
                if remaining <= 0 or not selector.select(remaining):
                    raise TimeoutError(f'ALFWorld environment {operation} timed out')
                chunk = os.read(self.process.stdout.fileno(), 65536)
                if not chunk:
                    raise RuntimeError('ALFWorld environment worker exited without a response')
                self._stdout_buffer.extend(chunk)
        line, _, remaining = self._stdout_buffer.partition(b'\n')
        self._stdout_buffer = bytearray(remaining)
        value = json.loads(line.decode('utf-8'))
        if 'error' in value:
            raise RuntimeError(value['error'])
        return value['result']

    @staticmethod
    def state(observation, done=False):
        return AlfWorldState(observation['text'],
                             tuple(action for action in observation['admissible_commands'] if action != 'help'),
                             bool(done), bool(observation['won']), {})

    def reset(self):
        observation = self.request('reset')
        if Path(observation['game_file']).resolve() != self.gamefile:
            raise RuntimeError('ALFWorld reset selected a different gamefile')
        return self.state(observation)

    def step(self, action):
        value = self.request('step', action=action)
        return self.state(value['observation'], value['done'])

    def close(self):
        process = getattr(self, 'process', None)
        if process is not None:
            # EOF invokes the worker's finally block, closing TextWorld.
            if process.stdin and not process.stdin.closed:
                try:
                    process.stdin.close()
                except BrokenPipeError:
                    pass
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            if process.stdout:
                process.stdout.close()
        self.log.close()


@dataclass(frozen=True)
class BenchmarkAlfWorldFactory:
    config: Path

    def dependency_manifest(self):
        return benchmark_provenance(self.config)

    def open(self, *, gamefile, data_root, verifier_workspace, seed, split):
        if Path(data_root).resolve() != (BENCHMARK_ROOT/'.data/alfworld').resolve():
            raise ValueError('ALFWorld assets must come from the authoritative benchmark')
        return BenchmarkEpisode(gamefile=gamefile, workspace=verifier_workspace,
                                seed=seed, split=split, config=self.config)
