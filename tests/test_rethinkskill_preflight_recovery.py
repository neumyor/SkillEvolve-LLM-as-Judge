import json
import sys
from pathlib import Path
from threading import Lock

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import check_rethinkskill_pair as preflight


def test_preflight_retries_transient_failure_with_lower_concurrency(tmp_path, monkeypatch):
    seen={}
    lock=Lock()

    class Child:
        def __init__(self, command, **kwargs):
            self.out=Path(command[command.index('--output-dir')+1])
            self.workers=int(command[command.index('--workers')+1])
            self.pid=12345
            with lock:
                seen.setdefault(self.out.name,[]).append(self.workers)
                self.attempt=len(seen[self.out.name])

        def wait(self):
            self.out.mkdir(parents=True,exist_ok=True)
            if self.attempt==1:
                (self.out/'summary.json').write_text(json.dumps({
                    'status':'invalid','failure_class':'target_timeout'}))
                return 1
            rounds=self.out/'runs/evolution/rounds'
            rounds.mkdir(parents=True,exist_ok=True)
            (rounds/'round_0001.json').write_text(json.dumps({'operation':'replace'}))
            (self.out/'summary.json').write_text(json.dumps({'status':'completed'}))
            return 0

    def classify(out,code):
        if json.loads((out/'summary.json').read_text())['status']=='completed':
            return 'completed','',[]
        return 'retryable','target_timeout',[]

    monkeypatch.setattr(preflight.subprocess,'Popen',Child)
    monkeypatch.setattr(preflight,'classify_run',classify)
    monkeypatch.setattr(preflight,'pending_tasks',lambda out:[])
    monkeypatch.setattr(preflight.time,'sleep',lambda seconds:None)
    root=tmp_path/'preflight'
    argv=['check_rethinkskill_pair.py','--root',str(root),'--benchmark','searchqa',
          '--max-recovery-passes','2','--recovery-backoff-seconds','0','--workers','2']
    monkeypatch.setattr(sys,'argv',argv)
    assert preflight.main()==0
    assert seen=={'searchqa_baseline':[2,1],'searchqa_judge':[2,1]}
    verification=json.loads((root/'verification.json').read_text())
    assert all(row['status']=='passed' and row['attempts']==2 for row in verification.values())
    monkeypatch.setattr(sys,'argv',argv+['--resume'])
    assert preflight.main()==0
    assert seen=={'searchqa_baseline':[2,1],'searchqa_judge':[2,1]}
