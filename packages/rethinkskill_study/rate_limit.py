"""Cross-process request pacing for one shared model-channel quota."""
import fcntl
import json
import os
from pathlib import Path
import time

from rethinkskill.utils.serde import atomic_write_json


class SharedRateLimiter:
    def __init__(self, path, requests_per_minute, *, cooldown_seconds=60):
        self.path=Path(path)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.lock_path=self.path.with_suffix(self.path.suffix+'.lock')
        self.initial_rate=requests_per_minute
        self.cooldown_seconds=cooldown_seconds
        if not 1 <= requests_per_minute <= 600:
            raise ValueError('requests_per_minute must be in [1, 600]')

    @classmethod
    def from_environment(cls):
        path=os.environ.get('RETHINKSKILL_RATE_LIMIT_FILE')
        if not path:
            return None
        return cls(path,int(os.environ['RETHINKSKILL_MAX_REQUESTS_PER_MINUTE']))

    def _locked(self, operation):
        with self.lock_path.open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            state=json.loads(self.path.read_text()) if self.path.is_file() else {
                'schema':'rethinkskill_rate_limit_v1','rate':self.initial_rate,
                'next_at':0.0,'generation':0}
            result=operation(state)
            atomic_write_json(self.path,state)
            return result

    def wait(self):
        while True:
            def reserve(state):
                now=time.time()
                slot=max(now,state['next_at'])
                state['next_at']=slot+60/state['rate']
                return slot,state['generation']
            slot,generation=self._locked(reserve)
            delay=slot-time.time()
            if delay>0:
                time.sleep(delay)
            current=self._locked(lambda state:state['generation'])
            if current==generation:
                return

    def penalize(self):
        def cool(state):
            state['rate']=max(4,state['rate']//2)
            state['next_at']=max(state['next_at'],time.time()+self.cooldown_seconds)
            state['generation']+=1
            return state['rate']
        return self._locked(cool)
