import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'packages'),str(ROOT/'packages/rethinkskill/src')]
from rethinkskill_study.rate_limit import SharedRateLimiter


def test_shared_limiter_spaces_independent_clients_and_penalizes_429(tmp_path):
    path=tmp_path/'channel.json'
    clients=[SharedRateLimiter(path,600,cooldown_seconds=.1) for _ in range(3)]
    def call(client):
        client.wait()
        return time.monotonic()
    with ThreadPoolExecutor(max_workers=3) as pool:
        times=sorted(pool.map(call,clients))
    assert times[1]-times[0]>=.075
    assert times[2]-times[1]>=.075
    assert clients[0].penalize()==300
    state=json.loads(path.read_text())
    assert state['generation']==1 and state['rate']==300
    assert state['next_at']>time.time()
