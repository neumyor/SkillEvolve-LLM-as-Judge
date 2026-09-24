"""Agent backends for the unified ALFWorld evaluation.

``api``      any OpenAI-compatible chat endpoint (vLLM, OpenAI, Azure proxy...).
             This is how frozen-base-model methods (vanilla/skillopt/trace2skill)
             run, and also how a SkillRL fine-tuned checkpoint is served for eval.
``mock``     deterministic agent that always picks the first admissible action.
             Used for engine smoke tests; no network required.
``random``   uniform over admissible actions (sanity lower bound).
"""
from __future__ import annotations

import json
import os
import random as _random
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Protocol

from .prompts import SYSTEM_PROMPT

FALLBACK_RESPONSE = "<think>empty model response</think><action>look</action>"
#: ``finish_reason`` reported when the completion hit ``max_tokens``.
FINISH_LENGTH = "length"
#: Statuses worth retrying: server-side faults and rate limiting. Anything else
#: (400/401/404/422...) is a request problem that a retry cannot fix.
RETRYABLE_STATUS = frozenset({408, 409, 425, 429, 500, 502, 503, 504, 529})


_PROTOCOL_TAG_RE = re.compile(r"</?(think|action|search|answer|information)\s*>", re.IGNORECASE)


def _neutralize_protocol_tags(text: str) -> str:
    """Defuse protocol tags so reasoning text cannot be mistaken for an action.

    ``<action>`` becomes ``[action]``. The think block is only ever checked for
    *presence*, never parsed, so squaring off its brackets costs nothing — while
    leaving the words intact keeps the trace readable for error analysis.
    """
    return _PROTOCOL_TAG_RE.sub(lambda m: f"[{m.group(0)[1:-1]}]", text)


def _restore_think_block(content: str, reasoning: str) -> str:
    """Re-attach a reasoning model's separate CoT field as a ``<think>`` block.

    Reasoning models (MiniCPM5, DeepSeek-R1, ...) return chain-of-thought in a
    sibling ``reasoning_content`` field rather than inline. The `<think>` block
    the protocol asks for is therefore split across two fields: ``content``
    begins mid-thought and often carries only the orphaned ``</think>``. Left
    alone, `runner.project_action` sees no opening tag and marks every step
    invalid — including steps whose ``<action>`` parsed and executed fine.

    The CoT is neutralized before being re-attached. `project_action` extracts
    the *first* ``<action>`` in the string, and this model rehearses the output
    format while thinking (measured: 4 steps in 100), so splicing raw reasoning
    in front of the real action makes the parser read the rehearsal instead —
    executing `look` where the model had committed to `inventory`.
    """
    if not reasoning or "<think>" in content:
        return content
    # A spilled CoT tail arrives ahead of content's orphaned closing tag; it is
    # reasoning, so it belongs inside the think block rather than in the part
    # the action is parsed from.
    #
    # Split on the *last* closing tag, not the first: this model quotes the
    # protocol while reasoning ("enclosed within <think></think> tags"), so an
    # earlier tag can sit inside the CoT. Splitting there leaves reasoning in
    # the action half, and the parser reads prose instead of the action. The
    # action half never contains the tag, so the final one is the true boundary.
    if "</think>" in content:
        spilled, action_part = content.rsplit("</think>", 1)
        reasoning = reasoning + spilled
    else:
        action_part = content
    return f"<think>{_neutralize_protocol_tags(reasoning)}</think>{action_part}"


_ADMISSIBLE_RE = re.compile(
    r"admissible actions of the current situation are:\s*\[(.*?)\]",
    re.DOTALL | re.IGNORECASE,
)


def extract_admissible_commands(user_prompt: str) -> list[str]:
    """Read the admissible-action list out of a rendered user prompt.

    Anchored on the list's own label rather than on the first ``[``. Skill
    documents are injected around the template, so a ``[`` appearing inside a
    skill (a markdown link, a bracketed example) would otherwise be mistaken for
    the action list -- and the policy would silently degrade to ``look`` for
    every step while the run still looked healthy.
    """
    match = _ADMISSIBLE_RE.search(user_prompt)
    return re.findall(r"'([^']+)'", match.group(1)) if match else []


class Agent(Protocol):
    name: str

    def respond(self, user_prompt: str) -> tuple[str, dict]:
        """Return (raw_model_response, usage_dict)."""
        ...


@dataclass
class UsageAccumulator:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    api_calls: int = 0
    api_errors: int = 0

    def add(self, usage: dict) -> None:
        self.prompt_tokens += int(usage.get("prompt_tokens", 0) or 0)
        self.completion_tokens += int(usage.get("completion_tokens", 0) or 0)
        self.api_calls += 1

    def to_dict(self) -> dict:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "api_calls": self.api_calls,
            "api_errors": self.api_errors,
        }

    def delta_since(self, previous: dict) -> dict:
        """Usage added since an earlier ``to_dict()`` snapshot.

        A run reuses one agent for every episode, so this accumulator is
        cumulative. Recording ``to_dict()`` per episode (as the runner used to)
        stored a running total for every episode, and ``summarize()`` then added
        those totals together: a 3-episode 50-step mock run reported 300 api
        calls for 150 real requests, scaling quadratically with episode count.
        """
        current = self.to_dict()
        return {
            key: current[key] - int(previous.get(key, 0) or 0) for key in current
        }


@dataclass
class OpenAIChatAgent:
    base_url: str
    model: str
    api_key: str = ""
    temperature: float = 0.0
    max_tokens: int = 4096
    timeout: float = 120.0
    #: Total attempts. A live pipeline run died on an intermittent HTTP 500 that
    #: three immediate retries all landed inside; five attempts with backoff
    #: span ~30s, which rides out a gateway blip.
    retries: int = 5
    name: str = "api"
    seed: int | None = None
    retry_backoff: float = 2.0
    usage: UsageAccumulator = field(default_factory=UsageAccumulator)
    #: ``finish_reason`` of the most recent completion, so the runner can tell a
    #: protocol violation from output cut off at ``max_tokens``.
    last_finish_reason: str | None = None
    truncated_responses: int = 0

    def respond(self, user_prompt: str) -> tuple[str, dict]:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
        if self.seed is not None:
            payload["seed"] = self.seed
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        last_error: Exception | None = None
        for attempt in range(self.retries):
            try:
                request = urllib.request.Request(
                    self.base_url.rstrip("/") + "/chat/completions",
                    data=json.dumps(payload).encode("utf-8"),
                    headers=headers,
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    body = json.loads(response.read().decode("utf-8"))
                choice = body["choices"][0]
                message = choice["message"]
                self.last_finish_reason = choice.get("finish_reason")
                if self.last_finish_reason == FINISH_LENGTH:
                    self.truncated_responses += 1
                text = _restore_think_block(
                    (message.get("content") or "").strip(),
                    (message.get("reasoning_content") or "").strip(),
                )
                usage = body.get("usage") or {}
                self.usage.add(usage)
                if not text:
                    return FALLBACK_RESPONSE, usage
                return text, usage
            except urllib.error.HTTPError as exc:
                # HTTPError subclasses URLError, so it must be caught first.
                last_error = exc
                self.usage.api_errors += 1
                if exc.code not in RETRYABLE_STATUS:
                    # A 400/401/404 is a request problem (bad key, bad model
                    # name, malformed payload). Retrying it only delays the
                    # diagnosis, so fail fast and say which status came back.
                    raise RuntimeError(
                        f"API request rejected: HTTP {exc.code} {exc.reason}"
                    ) from exc
                self._backoff(attempt)
            except (urllib.error.URLError, KeyError, TimeoutError, OSError) as exc:
                last_error = exc
                self.usage.api_errors += 1
                self._backoff(attempt)
        raise RuntimeError(
            f"API agent failed after {self.retries} attempts: {last_error!r}"
        )

    def _backoff(self, attempt: int) -> None:
        """Wait before the next attempt, so a transient fault can clear."""
        if attempt + 1 >= self.retries:
            return
        delay = self.retry_backoff * (2**attempt)
        # Jitter keeps several episodes retrying out of lockstep.
        time.sleep(delay + _random.uniform(0, delay / 4))


@dataclass
class MockAgent:
    """Picks the first admissible action; requires the prompt to embed them."""

    name: str = "mock"
    seed: int = 0
    usage: UsageAccumulator = field(default_factory=UsageAccumulator)

    def respond(self, user_prompt: str) -> tuple[str, dict]:
        # The prompt may contain a skill document with quoted examples before
        # the admissible-action list. Restrict extraction to that list so the
        # deterministic smoke backend always emits a real environment action.
        commands = extract_admissible_commands(user_prompt)
        action = commands[0] if commands else "look"
        self.usage.add({})
        return f"<think>mock: choose first admissible action</think><action>{action}</action>", {}


@dataclass
class RandomAgent:
    """Uniformly samples an admissible action from the embedded action list."""

    name: str = "random"
    seed: int = 0
    usage: UsageAccumulator = field(default_factory=UsageAccumulator)

    def __post_init__(self) -> None:
        self._rng = _random.Random(self.seed)

    def respond(self, user_prompt: str) -> tuple[str, dict]:
        commands = extract_admissible_commands(user_prompt)
        action = self._rng.choice(commands) if commands else "look"
        self.usage.add({})
        return f"<think>random policy</think><action>{action}</action>", {}


def build_agent(
    backend: str,
    *,
    base_url: str = "",
    model: str = "",
    api_key: str = "",
    temperature: float = 0.0,
    max_tokens: int = 4096,
    seed: int = 0,
) -> Agent:
    if backend == "api":
        if not base_url or not model:
            raise ValueError("--base-url and --model are required for --backend api")
        return OpenAIChatAgent(
            base_url=base_url,
            model=model,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=float(os.environ.get("TRACE2SKILL_HTTP_TIMEOUT", "120")),
            retries=int(os.environ.get("TRACE2SKILL_HTTP_RETRIES", "5")),
            seed=seed,
        )
    if backend == "mock":
        return MockAgent(seed=seed)
    if backend == "random":
        return RandomAgent(seed=seed)
    raise ValueError(f"Unknown backend {backend!r}; choose api/mock/random")
