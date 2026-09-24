"""Durable request journal. Recover local execution without repeating completed API calls."""
import json
import uuid
import threading
from pathlib import Path
from rethinkskill.runtime.types import ModelOutcome
from rethinkskill.utils.serde import atomic_write_json, canonical_json_bytes, sha256_bytes
from skillopt.evaluation.usage_ledger import UsageLedger


class DurableLedger(UsageLedger):
    def __init__(self, path):
        super().__init__(path)
        self._lock = threading.Lock()
        self.seen = {e.get('event_id') for e in self.events() if e.get('event_id')}

    def record(self, usage, *, stage, model='', **metadata):
        event_id = metadata.get('event_id')
        with self._lock:
            if event_id and event_id in self.seen:
                return None
            value = super().record(usage, stage=stage, model=model, **metadata)
            if event_id:
                self.seen.add(event_id)
            self.write_replacement_summary()
        return value


class RequestJournal:
    def __init__(self, root, ledger):
        self.root = Path(root)
        self.path = self.root/'request_journal'
        self.path.mkdir(exist_ok=True)
        self.ledger = ledger
        # Recover the small write-result/write-usage crash window.
        for file in sorted(self.path.glob('attempts/*.json')):
            record = json.loads(file.read_text())
            self._record(record)

    def _record(self, record):
        self.ledger.record(record.get('usage'), stage=record['stage'], model=record['model'],
            event_id=record['event_id'], **record['metadata'])

    def call(self, key, payload, invoke, *, stage, model, reusable=lambda value: True, usage_of=None):
        binding = sha256_bytes(canonical_json_bytes({'key':key,'payload':payload}))
        cache = self.path/'cache'/f'{binding}.json'
        if cache.exists():
            record = json.loads(cache.read_text())
            if record['binding'] != binding:
                raise ValueError('Request journal binding mismatch')
            # Legacy runs may contain cached transient failures. Keep their
            # evidence, but do not replay them as a permanent answer.
            if reusable(record['value']):
                self._record(record)
                return record['value']
        pending = self.path/'pending'/f'{binding}.json'
        if pending.exists():
            lost = json.loads(pending.read_text())
            lost.update(usage=None, metadata={**lost['metadata'],'error':'interrupted_request_usage_unknown'})
            atomic_write_json(self.path/'attempts'/f"{lost['event_id']}.json", lost)
            self._record(lost)
        metadata = {'request_key':key}
        if self.ledger._replacement_component:
            metadata['replacement_component'] = self.ledger._replacement_component
        record = {'event_id':uuid.uuid4().hex,'binding':binding,'stage':stage,'model':model,'metadata':metadata}
        atomic_write_json(pending,record)
        try:
            value = invoke()
        except Exception as exc:
            record.update(usage=None, metadata={**metadata,'error':type(exc).__name__})
            atomic_write_json(self.path/'attempts'/f"{record['event_id']}.json",record)
            self._record(record)
            pending.unlink()
            raise
        usage = usage_of(value) if usage_of else value.get('usage')
        record.update(value=value, usage=usage)
        if value.get('failure'):
            record['metadata']['error'] = value['failure']
            record['metadata']['failure_class'] = value.get('failure_class')
        atomic_write_json(self.path/'attempts'/f"{record['event_id']}.json",record)
        if reusable(value):
            atomic_write_json(cache,record)
        self._record(record)
        pending.unlink()
        return value


def outcome_dict(outcome):
    return {**outcome.public(),'raw':outcome.raw}


def restore_outcome(value):
    return ModelOutcome(**value)
