"""Tests for the evolution config section — YAML inheritance and flattening.

The ``evolution:`` section must behave exactly like the other structured
sections: inherit through ``_base_``, flatten onto the trainer's flat keys,
survive ``--cfg-options`` overrides, and default to the untouched original
schedule (``mode: fixed``) so existing configs are unaffected.
"""
from __future__ import annotations

import os
import textwrap

import pytest
import yaml

from skillopt.config import (
    _FLATTEN_MAP,
    flatten_config,
    is_structured,
    load_config,
    apply_overrides,
)


BASE_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "configs", "_base_", "default.yaml",
)


def _write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(textwrap.dedent(text), encoding="utf-8")
    return str(path)


# ── Base defaults ────────────────────────────────────────────────────────────


class TestBaseDefaults:
    def test_base_defines_evolution_section(self) -> None:
        cfg = load_config(BASE_CONFIG_PATH)
        assert is_structured(cfg)
        evo = cfg["evolution"]
        assert evo["mode"] == "fixed"
        assert evo["observation_batch_size"] == 4
        assert evo["fixed_k"] == 1
        assert evo["controller_view"] == "semantic"
        assert evo["max_buffer_observations"] == 0

    def test_flatten_maps_every_evolution_key(self) -> None:
        flat = flatten_config(load_config(BASE_CONFIG_PATH))
        assert flat["evolution_mode"] == "fixed"
        assert flat["observation_batch_size"] == 4
        assert flat["evolution_fixed_k"] == 1
        assert flat["evolution_controller_view"] == "semantic"
        assert flat["evolution_max_buffer_observations"] == 0

    def test_every_documented_evolution_key_is_mapped(self) -> None:
        """A key present in the base evolution section but missing from
        _FLATTEN_MAP would be silently dropped by flatten_config."""
        base = yaml.safe_load(open(BASE_CONFIG_PATH, encoding="utf-8"))
        for key in base["evolution"]:
            assert f"evolution.{key}" in _FLATTEN_MAP, (
                f"evolution.{key} is defined in the base config but has no "
                f"flatten mapping — it would be dropped"
            )


# ── Inheritance + overrides ──────────────────────────────────────────────────


class TestEvolutionConfigInheritance:
    def test_child_override_wins(self, tmp_path) -> None:
        path = _write(
            tmp_path,
            "child.yaml",
            f"""
            _base_: {BASE_CONFIG_PATH}
            evolution:
              mode: controller
              observation_batch_size: 8
            """,
        )
        cfg = load_config(path)
        assert cfg["evolution"]["mode"] == "controller"
        assert cfg["evolution"]["observation_batch_size"] == 8
        # untouched keys inherit
        assert cfg["evolution"]["controller_view"] == "semantic"

    def test_cfg_options_override(self, tmp_path) -> None:
        path = _write(
            tmp_path,
            "child.yaml",
            f"""
            _base_: {BASE_CONFIG_PATH}
            evolution:
              mode: controller
            """,
        )
        cfg = load_config(path, overrides=["evolution.mode=fixed_k", "evolution.fixed_k=5"])
        assert cfg["evolution"]["mode"] == "fixed_k"
        assert cfg["evolution"]["fixed_k"] == 5

    def test_apply_overrides_dotted(self) -> None:
        cfg = load_config(BASE_CONFIG_PATH)
        apply_overrides(cfg, ["evolution.mode=controller"])
        assert cfg["evolution"]["mode"] == "controller"

    def test_flat_config_without_evolution_stays_flat(self, tmp_path) -> None:
        path = _write(
            tmp_path,
            "flat.yaml",
            """
            env: searchqa
            batch_size: 8
            num_epochs: 1
            out_root: /tmp/x
            """,
        )
        cfg = load_config(path)
        assert not is_structured(cfg)
        assert "evolution_mode" not in cfg  # legacy flat config untouched

    def test_evolution_section_makes_config_structured(self, tmp_path) -> None:
        path = _write(
            tmp_path,
            "evo_only.yaml",
            """
            env: searchqa
            batch_size: 8
            num_epochs: 1
            out_root: /tmp/x
            evolution:
              mode: controller
            """,
        )
        cfg = load_config(path)
        assert is_structured(cfg)
        flat = flatten_config(cfg)
        assert flat["evolution_mode"] == "controller"
        assert flat["batch_size"] == 8
