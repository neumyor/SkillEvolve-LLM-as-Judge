"""Append-only usage events, including retries and work repeated after resume."""
from __future__ import annotations

import fcntl
import json
import os
from contextlib import contextmanager
from pathlib import Path


REPLACEMENT_COMPONENTS = {"llm_judge", "seed_validation", "candidate_validation",
                          "candidate_minibatch", "verification_execution"}


class UsageLedger:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._replacement_component = None
        self._replacement_metadata = None

    def configure_replacement_cost(self, method, mode):
        """Declare the narrow comparison contract before starting any calls."""
        metadata = {"schema": "replacement_cost_v1", "method": method, "mode": mode}
        target = self.path.with_name("replacement_cost.json")
        if target.exists():
            previous = json.loads(target.read_text())
            if any(previous.get(k) != v for k, v in metadata.items()):
                raise ValueError("Cannot change replacement-cost method/mode on resume")
        elif self.events():
            raise ValueError("Legacy usage lacks replacement-cost labels; use a fresh output directory")
        self._replacement_metadata = metadata
        self.write_replacement_summary()

    @contextmanager
    def capture_replacement(self, component):
        """A synchronous phase includes its joined workers, so labels are shared.

        The runner must finish this phase (including workers) before starting
        another. No per-thread context propagation is needed by evaluator pools.
        """
        if component not in REPLACEMENT_COMPONENTS:
            raise ValueError(f"Unknown replacement-cost component: {component}")
        previous = self._replacement_component
        self._replacement_component = component
        try:
            yield
        except BaseException:
            self.record(None, stage=component, error="phase_did_not_complete")
            raise
        finally:
            self._replacement_component = previous
            self.write_replacement_summary()

    def record(self, usage, *, stage, model="", **metadata):
        if usage is not None and not isinstance(usage, dict):
            usage = {k: getattr(usage, k, None) for k in
                     ("prompt_tokens", "completion_tokens", "total_tokens")}
        usage = usage or {}
        complete = usage.get("usage_complete", True) and all(
            usage.get(k) is not None for k in ("prompt_tokens", "completion_tokens"))
        event = {"stage": stage, "model": model, "usage_complete": complete, **metadata,
                 "prompt_tokens": int(usage.get("prompt_tokens", 0) or 0),
                 "completion_tokens": int(usage.get("completion_tokens", 0) or 0)}
        if self._replacement_component is not None:
            event["replacement_component"] = self._replacement_component
        event["total_tokens"] = int(usage.get("total_tokens") or
                                    event["prompt_tokens"] + event["completion_tokens"])
        with self.path.open("a", encoding="utf-8") as out:
            fcntl.flock(out, fcntl.LOCK_EX)
            out.write(json.dumps(event, ensure_ascii=False) + "\n")
            out.flush()
            os.fsync(out.fileno())
        return event

    def replacement_summary(self):
        rows = [r for r in self.events() if r.get("replacement_component") in REPLACEMENT_COMPONENTS]
        def total(items):
            return {**{k: sum(r[k] for r in items) for k in
                       ("prompt_tokens", "completion_tokens", "total_tokens")},
                    "usage_complete": all(r["usage_complete"] for r in items)}
        return {**(self._replacement_metadata or {}), "usage_events_path": str(self.path.resolve()), **total(rows),
                "components": {c: total([r for r in rows if r["replacement_component"] == c])
                               for c in sorted({r["replacement_component"] for r in rows})}}

    def write_replacement_summary(self):
        if self._replacement_metadata is None:
            return
        target = self.path.with_name("replacement_cost.json")
        temporary = target.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(self.replacement_summary(), indent=2) + "\n")
        os.replace(temporary, target)

    def summary(self):
        rows = self.events()
        totals = {k: sum(r[k] for r in rows) for k in
                  ("prompt_tokens", "completion_tokens", "total_tokens")}
        return {**totals, "events": len(rows),
                "usage_complete": bool(rows) and all(r["usage_complete"] for r in rows),
                "stages": {stage: sum(r["total_tokens"] for r in rows if r["stage"] == stage)
                           for stage in sorted({r["stage"] for r in rows})}}

    def events(self):
        if not self.path.exists():
            return []
        with self.path.open(encoding="utf-8") as source:
            fcntl.flock(source, fcntl.LOCK_SH)
            return [json.loads(line) for line in source]
