from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from functools import wraps
from pathlib import Path
from typing import Any

import yaml

# TextWorld's cached PDDL grammar/parser has process-global mutable state.
# Serialize local environment operations, but never hold this lock during LLM calls.
_TEXTWORLD_LOCK = threading.RLock()


def _environment_operation(fn):
    @wraps(fn)
    def locked(*args, **kwargs):
        with _TEXTWORLD_LOCK:
            return fn(*args, **kwargs)
    return locked

SPLIT_TO_ALFWORLD = {
    "train": "train",
    "valid_seen": "eval_in_distribution",
    "valid_unseen": "eval_out_of_distribution",
}


def split_for_gamefile(gamefile: str) -> str:
    """Infer the benchmark split encoded in an ALFWorld game-file path."""
    normalized = str(gamefile).replace("\\", "/")
    for split in SPLIT_TO_ALFWORLD:
        if f"/{split}/" in normalized or normalized.endswith(f"/{split}"):
            return split
    # Older manifests sometimes omit the split directory.  Seen is the least
    # surprising default and matches the historical verifier behavior.
    return "valid_seen"


def episode_step_budget(config: dict[str, Any]) -> int:
    """Read the step budget ALFWorld itself will register for this config.

    ``alfred_tw_env.py`` picks the budget from ``rl.training`` or
    ``dagger.training`` according to ``general.training_method`` and passes it
    to ``textworld.gym.register_games(max_episode_steps=...)``. Mirroring that
    choice is what keeps the harness's own step cap in agreement with the
    environment's; reading a hard-coded key here would recreate the drift this
    function exists to prevent.
    """
    general = config.get("general") or {}
    method = general.get("training_method")
    section = "rl" if method == "dqn" else "dagger" if method == "dagger" else None
    if section is None:
        raise ValueError(
            f"config declares training_method={method!r}; expected 'dqn' or 'dagger'"
        )
    try:
        return int(config[section]["training"]["max_nb_steps_per_episode"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(
            f"config is missing {section}.training.max_nb_steps_per_episode"
        ) from exc


def official_split_counts(data_root: str | None = None) -> dict[str, int]:
    """Count the game files ALFWorld itself ships for each split directory."""
    root = Path(data_root or os.environ.get("ALFWORLD_DATA", "")) / "json_2.1.1"
    counts: dict[str, int] = {}
    if not root.is_dir():
        return counts
    for split in ("train", "valid_seen", "valid_unseen", "valid_train"):
        directory = root / split
        if directory.is_dir():
            counts[split] = sum(1 for _ in directory.rglob("game.tw-pddl"))
    return counts


def split_manifest_provenance(
    items: list[dict],
    split: str,
    *,
    data_root: str | None = None,
) -> dict:
    """Check a manifest belongs to ``split`` and describe its coverage.

    Every cross-method comparison rests on both runs covering the same
    episodes, so a manifest drawn from a different split must fail loudly
    instead of producing a plausible-looking summary. The returned dict is
    what gets recorded in ``summary.json`` / ``provenance.json``, because
    released manifests are subsets of the official splits (SkillOpt's
    ``alfworld_path_split`` is 39/18/134 against 3553/140/134) and a subsample
    is otherwise invisible after the fact.
    """
    claimed: dict[str, int] = {}
    for item in items:
        found = split_for_gamefile(item["gamefile"])
        claimed[found] = claimed.get(found, 0) + 1
    if set(claimed) != {split}:
        detail = ", ".join(f"{k}={v}" for k, v in sorted(claimed.items()))
        raise ValueError(
            f"--split {split} does not match the manifest: it contains "
            f"{{{detail}}}. Refusing to run, because the resulting numbers "
            "would not be comparable with another run over the same split."
        )

    official = official_split_counts(data_root)
    official_n = official.get(split)
    return {
        "split": split,
        "manifest_episodes": len(items),
        "official_episodes": official_n,
        "covers_official_split": (
            None if official_n is None else len(items) == official_n
        ),
        "official_split_counts": official,
    }


@dataclass(frozen=True)
class Observation:
    text: str
    admissible_commands: tuple[str, ...]
    game_file: str | None
    won: bool


@dataclass(frozen=True)
class StepResult:
    observation: Observation
    reward: float
    done: bool
    won: bool
    info: dict[str, Any]


def split_to_train_eval(split: str) -> str:
    try:
        return SPLIT_TO_ALFWORLD[split]
    except KeyError as exc:
        choices = ", ".join(SPLIT_TO_ALFWORLD)
        raise ValueError(f"Unknown split {split!r}; choose one of: {choices}") from exc


def _first(value: Any, default: Any = None) -> Any:
    if isinstance(value, list | tuple):
        return value[0] if value else default
    try:
        if getattr(value, "ndim", 0) > 0:
            return value[0]
    except (IndexError, TypeError):
        return default
    return value if value is not None else default


def _as_bool(value: Any) -> bool:
    return bool(_first(value, False))


def _as_game_file(value: Any) -> str | None:
    game_file = _first(value)
    return str(game_file) if game_file else None


class AlfworldTextEnv:
    """Single-process adapter around ALFWorld's ``AlfredTWEnv``."""

    def __init__(
        self,
        config_path: str | Path = "configs/textworld.yaml",
        split: str = "valid_seen",
        seed: int = 42,
        gamefiles: list[str] | None = None,
    ) -> None:
        self.config_path = Path(config_path).resolve()
        self.split = split
        self.seed = seed
        self.gamefiles = list(gamefiles) if gamefiles else None
        #: Step budget the environment itself registers. The runner's own loop
        #: cap must agree with this, or an episode is truncated by a different
        #: protocol than the one the env enforces.
        self.step_budget: int = 0
        self._env: Any = None
        self._base_env: Any = None
        self._build()

    @_environment_operation
    def _build(self) -> None:
        with self.config_path.open(encoding="utf-8") as config_file:
            config = yaml.safe_load(config_file)

        data_root = os.environ.get("ALFWORLD_DATA")
        if not data_root:
            raise RuntimeError(
                "ALFWORLD_DATA is not set. Set it to the directory containing "
                "json_2.1.1/ and logic/."
            )
        os.environ["ALFWORLD_DATA"] = str(Path(data_root).expanduser().resolve())

        self.step_budget = episode_step_budget(config)

        from alfworld.agents.environment import get_environment

        train_eval = split_to_train_eval(self.split)
        env_type = config["env"]["type"]
        self._base_env = get_environment(env_type)(config, train_eval=train_eval)
        if self.gamefiles:
            # AlfredTWEnv.init_env registers exactly base_env.game_files, so
            # overriding it pins the episode order to the requested gamefiles.
            self._base_env.game_files = [self._resolve_gamefile(g) for g in self.gamefiles]
            self._base_env.num_games = len(self._base_env.game_files)
        self._env = self._base_env.init_env(batch_size=1)
        # Must happen here, on the constructed env. This previously sat at the
        # end of _resolve_gamefile, after a return and inside a staticmethod,
        # so the seed was never applied and runs were not reproducible.
        if hasattr(self._env, "seed"):
            self._env.seed(self.seed)

    @staticmethod
    def _resolve_gamefile(gamefile: str) -> str:
        # Split manifests (e.g. SkillOpt's items.json) store paths relative
        # to $ALFWORLD_DATA.
        path = Path(os.path.expanduser(os.path.expandvars(str(gamefile))))
        if not path.is_absolute() and not path.exists():
            data_root = os.environ.get("ALFWORLD_DATA", "")
            if data_root:
                candidate = Path(data_root).expanduser() / path
                if candidate.exists():
                    return str(candidate.resolve())
        return str(path.resolve())

    @staticmethod
    def _observation(text: Any, info: dict[str, Any]) -> Observation:
        commands = _first(info.get("admissible_commands"), [])
        return Observation(
            text=str(_first(text, "")),
            admissible_commands=tuple(str(command) for command in (commands or [])),
            game_file=_as_game_file(info.get("extra.gamefile")),
            won=_as_bool(info.get("won")),
        )

    @property
    def num_games(self) -> int:
        if self.gamefiles is not None:
            return len(self.gamefiles)
        return int(getattr(self._base_env, "num_games", 0) or 0)

    @_environment_operation
    def reset(self) -> Observation:
        if self._env is None:
            raise RuntimeError("Environment is closed.")
        texts, infos = self._env.reset()
        return self._observation(texts, infos)

    @_environment_operation
    def step(self, action: str) -> StepResult:
        if self._env is None:
            raise RuntimeError("Environment is closed.")
        texts, rewards, dones, infos = self._env.step([action])
        observation = self._observation(texts, infos)
        info = {key: _first(value) for key, value in infos.items()}
        return StepResult(
            observation=observation,
            reward=float(_first(rewards, 0.0)),
            done=bool(_first(dones, False)),
            won=observation.won,
            info=info,
        )

    @_environment_operation
    def close(self) -> None:
        if self._env is not None and hasattr(self._env, "close"):
            self._env.close()
        self._env = None
        self._base_env = None

    def __enter__(self) -> AlfworldTextEnv:
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        self.close()
