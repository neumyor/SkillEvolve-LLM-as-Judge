"""Agent backends for the unified SearchQA evaluation.

``api``    any OpenAI-compatible chat endpoint (vLLM, OpenAI, ...). The
           single-turn protocol means one call per item.
``mock``   canned response for pipeline smoke tests (no network).
``random`` picks a random token as the answer (sanity lower bound).
"""
from __future__ import annotations

import json
import re
import random as _random
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Protocol



_PROTOCOL_TAG_RE = re.compile(r"</?(think|action|search|answer|information)\s*>", re.IGNORECASE)


def _neutralize_protocol_tags(text: str) -> str:
    """Defuse protocol tags so reasoning text cannot be mistaken for an action.

    ``<search>`` becomes ``[search]``. The think block is only ever checked for
    *presence*, never parsed, so squaring off its brackets costs nothing — while
    leaving the words intact keeps the trace readable for error analysis.
    """
    return _PROTOCOL_TAG_RE.sub(lambda m: f"[{m.group(0)[1:-1]}]", text)


def _restore_think_block(content: str, reasoning: str) -> str:
    """Re-attach a reasoning model's separate CoT field as a ``<think>`` block.

    Reasoning models (MiniCPM5, DeepSeek-R1, ...) return chain-of-thought in a
    sibling ``reasoning_content`` field, so ``content`` begins mid-thought and
    often carries only the orphaned ``</think>``. Dropping the field entirely
    loses the reasoning the protocol asks for; splicing it back in raw is worse,
    because a CoT that rehearses the output format would be parsed as the action.
    Neutralizing first gives back the shape a non-reasoning model would emit.
    """
    if not reasoning or "<think>" in content:
        return content
    # Split on the *last* closing tag, not the first: a model that quotes the
    # protocol while reasoning ("enclosed within <think></think> tags") leaves an
    # earlier tag inside the CoT. Splitting there puts reasoning in the action
    # half and the parser reads prose. The action half never contains the tag.
    if "</think>" in content:
        spilled, action_part = content.rsplit("</think>", 1)
        reasoning = reasoning + spilled
    else:
        action_part = content
    return f"<think>{_neutralize_protocol_tags(reasoning)}</think>{action_part}"

class Agent(Protocol):
    name: str

    def respond(self, system: str, user: str) -> tuple[str, dict]:
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


@dataclass
class OpenAIChatAgent:
    base_url: str
    model: str
    api_key: str = ""
    temperature: float = 0.0
    max_tokens: int = 16384
    timeout: float = 120.0
    retries: int = 3
    name: str = "api"
    seed: int | None = None
    usage: UsageAccumulator = field(default_factory=UsageAccumulator)

    def respond(self, system: str, user: str) -> tuple[str, dict]:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
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
        for _ in range(self.retries):
            try:
                request = urllib.request.Request(
                    self.base_url.rstrip("/") + "/chat/completions",
                    data=json.dumps(payload).encode("utf-8"),
                    headers=headers,
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    body = json.loads(response.read().decode("utf-8"))
                message = body["choices"][0]["message"]
                text = _restore_think_block(
                    (message.get("content") or "").strip(),
                    (message.get("reasoning_content") or "").strip(),
                )
                usage = body.get("usage") or {}
                self.usage.add(usage)
                return text, usage
            except (urllib.error.URLError, KeyError, TimeoutError, OSError) as exc:
                last_error = exc
                self.usage.api_errors += 1
        raise RuntimeError(f"API agent failed after {self.retries} retries: {last_error}")


@dataclass
class MockAgent:
    """Returns a fixed-format response so the eval pipeline is testable."""

    name: str = "mock"
    usage: UsageAccumulator = field(default_factory=UsageAccumulator)

    def respond(self, system: str, user: str) -> tuple[str, dict]:
        # Echo the question's first word as the answer — enough to exercise
        # extraction + scoring end to end.
        lines = user.splitlines()
        question = ""
        for i, line in enumerate(lines):
            if line.startswith("## Question"):
                question = lines[i + 1].strip() if i + 1 < len(lines) else ""
                break
        tokens = [t for t in question.replace("?", "").split() if t]
        answer = tokens[0] if tokens else "nothing"
        self.usage.add({})
        return f"Thinking briefly. <answer>{answer}</answer>", {}


@dataclass
class RandomAgent:
    name: str = "random"
    seed: int = 0
    usage: UsageAccumulator = field(default_factory=UsageAccumulator)

    def __post_init__(self) -> None:
        self._rng = _random.Random(self.seed)

    def respond(self, system: str, user: str) -> tuple[str, dict]:
        word = self._rng.choice("alpha beta gamma delta epsilon".split())
        self.usage.add({})
        return f"<answer>{word}</answer>", {}


def build_agent(
    backend: str,
    *,
    base_url: str = "",
    model: str = "",
    api_key: str = "",
    temperature: float = 0.0,
    max_tokens: int = 16384,
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
            seed=seed,
        )
    if backend == "mock":
        return MockAgent()
    if backend == "random":
        return RandomAgent(seed=seed)
    raise ValueError(f"Unknown backend {backend!r}; choose api/mock/random")
