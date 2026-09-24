from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .env import AlfworldTextEnv, Observation

Policy = Callable[[Observation], str]


@dataclass(frozen=True)
class EpisodeResult:
    split: str
    game_file: str | None
    success: bool
    steps: int
    invalid_actions: int
    termination_reason: str


def first_admissible_action(observation: Observation) -> str:
    if not observation.admissible_commands:
        raise RuntimeError("The environment returned no admissible commands.")
    return observation.admissible_commands[0]


def run_episode(
    env: AlfworldTextEnv,
    policy: Policy,
    max_steps: int | None = None,
) -> EpisodeResult:
    # Same single-source rule as the unified runner: follow the budget the
    # environment registered unless the caller deliberately asks for a shorter
    # smoke run.
    if max_steps is None:
        max_steps = int(getattr(env, "step_budget", 0) or 50)
    observation = env.reset()
    game_file = observation.game_file
    invalid_actions = 0

    for step in range(1, max_steps + 1):
        action = policy(observation)
        if action not in observation.admissible_commands:
            invalid_actions += 1
        result = env.step(action)
        observation = result.observation
        if result.done:
            return EpisodeResult(
                split=env.split,
                game_file=game_file,
                success=result.won,
                steps=step,
                invalid_actions=invalid_actions,
                termination_reason="success" if result.won else "environment_done",
            )

    return EpisodeResult(
        split=env.split,
        game_file=game_file,
        success=False,
        steps=max_steps,
        invalid_actions=invalid_actions,
        termination_reason="step_limit",
    )

