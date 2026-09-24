"""Tests for ordered (non-shuffled) training streams.

Evidence-triggered evolution streams a deliberate order — grouped task
families/regimes — so same-family failures arrive together and form coherent
evidence; the order-sensitivity ablation needs the same switch. The default
must stay upstream (shuffled).
"""
from __future__ import annotations

from skillopt.datasets.base import BatchSpec


class _StubLoader:
    """Minimal SplitDataLoader-shaped object exposing train_items."""

    def __init__(self, ids):
        self.train_items = [{"id": i} for i in ids]


def _plan(loader, shuffle: bool, *, steps_per_epoch=3, batch_size=2, accumulation=1, epoch=1, seed=42):
    from skillopt.datasets.base import SplitDataLoader

    return SplitDataLoader.plan_train_epoch(
        loader,  # type: ignore[arg-type]
        epoch=epoch,
        steps_per_epoch=steps_per_epoch,
        accumulation=accumulation,
        batch_size=batch_size,
        seed=seed,
        shuffle=shuffle,
    )


class TestOrderedStream:
    def test_ordered_preserves_split_order(self) -> None:
        loader = _StubLoader(["a", "b", "c", "d", "e", "f"])
        batches = _plan(loader, shuffle=False)
        ids = [item["id"] for b in batches for item in b.payload]
        assert ids == ["a", "b", "c", "d", "e", "f"], ids
        assert [b.batch_size for b in batches] == [2, 2, 2]

    def test_ordered_is_stable_across_epochs(self) -> None:
        loader = _StubLoader(["a", "b", "c", "d"])
        e1 = [i["id"] for b in _plan(loader, shuffle=False, epoch=1, steps_per_epoch=2) for i in b.payload]
        e2 = [i["id"] for b in _plan(loader, shuffle=False, epoch=2, steps_per_epoch=2) for i in b.payload]
        assert e1 == e2 == ["a", "b", "c", "d"]

    def test_shuffled_default_differs_and_covers_all(self) -> None:
        loader = _StubLoader([f"i{n}" for n in range(12)])
        ids = [i["id"] for b in _plan(loader, shuffle=True, steps_per_epoch=6) for i in b.payload]
        assert sorted(ids) == sorted(f"i{n}" for n in range(12))
        assert ids != [f"i{n}" for n in range(12)]  # extremely unlikely to be identity

    def test_batches_unchanged_by_the_switch(self) -> None:
        loader = _StubLoader([f"i{n}" for n in range(6)])
        ordered = _plan(loader, shuffle=False, steps_per_epoch=3)
        shuffled = _plan(loader, shuffle=True, steps_per_epoch=3)
        assert [b.batch_size for b in ordered] == [b.batch_size for b in shuffled] == [2, 2, 2]
        assert [b.seed for b in ordered] == [b.seed for b in shuffled]

    def test_regime_grouping_survives_into_batches(self) -> None:
        # two regimes of 4: the first two batches are all-A, the last two all-B
        loader = _StubLoader(["a1", "a2", "a3", "a4", "b1", "b2", "b3", "b4"])
        batches = _plan(loader, shuffle=False, steps_per_epoch=4)
        groups = [{"a" if i["id"][0] == "a" else "b" for i in b.payload} for b in batches]
        assert groups == [{"a"}, {"a"}, {"b"}, {"b"}], groups
