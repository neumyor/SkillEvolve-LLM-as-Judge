from pathlib import Path
from types import SimpleNamespace

import pytest


def test_skillopt_completed_episode_survives_interrupted_batch(tmp_path, monkeypatch):
    from skillopt.envs.alfworld import rollout
    calls = []
    monkeypatch.setattr(rollout, "chat_target", lambda **kwargs: (
        calls.append(kwargs["user"]) or "<think>x</think><action>look</action>", {}))

    class Env:
        def __init__(self, crash):
            self.crash, self.steps = crash, 0

        def reset(self, _):
            return {"text": ["task0", "task1"], "anchor": ["task0", "task1"]}, [
                {"extra.gamefile": "game0"}, {"extra.gamefile": "game1"}]

        def step(self, actions):
            self.steps += 1
            if self.crash and self.steps == 2:
                raise RuntimeError("interrupted")
            done = [True, not self.crash]
            return {"text": ["task0", "task1"], "anchor": ["task0", "task1"]}, [1, 1], done, [{"won": True}, {"won": True}]

    kwargs = dict(skill_content="skill", max_steps=2, out_root=str(tmp_path), result_ids=["a", "b"])
    with pytest.raises(RuntimeError, match="interrupted"):
        rollout.run_alfworld_batch(Env(True), **kwargs)
    assert (tmp_path / "predictions/a/completed.json").exists()
    calls.clear()
    result = rollout.run_alfworld_batch(Env(False), **kwargs)
    assert len(calls) == 1 and "task1" in calls[0]
    assert [r["hard"] for r in result] == [1, 1]
    calls.clear()
    assert rollout.run_alfworld_batch(Env(False), **kwargs) == result
    assert calls == []
    with pytest.raises(ValueError, match="checkpoint"):
        rollout.run_alfworld_batch(Env(False), **{**kwargs, "skill_content": "changed"})


def test_gepa_final_unit_resume_does_not_repeat_completed_calls(tmp_path):
    from benchmark_adapters import _checkpoint_final_units
    from gepa.core.adapter import EvaluationBatch

    class Adapter:
        _workers = 1
        usage_stage = "final_test_result_path"
        usage_ledger = SimpleNamespace(path=tmp_path / "usage_events.jsonl")
        fail = True
        calls = []

        @_checkpoint_final_units
        def evaluate(self, batch, candidate, capture_traces=False):
            self.calls.extend(batch)
            if batch == [2] and self.fail:
                raise RuntimeError("interrupted")
            return EvaluationBatch(outputs=batch, scores=[float(x) for x in batch], trajectories=None)

    adapter = Adapter()
    with pytest.raises(RuntimeError, match="interrupted"):
        adapter.evaluate([1, 2], {"skill": "one"})
    adapter.fail = False
    adapter.calls.clear()
    assert adapter.evaluate([1, 2], {"skill": "one"}).scores == [1, 2]
    assert adapter.calls == [2]
    adapter.calls.clear()
    adapter.evaluate([1, 2], {"skill": "two"})
    assert adapter.calls == [1, 2]
    adapter.calls.clear()
    adapter.usage_stage = "training"
    adapter.evaluate([1, 2], {"skill": "one"})
    assert adapter.calls == [1, 2]
