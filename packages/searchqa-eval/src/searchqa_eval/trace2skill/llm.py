"""Small OpenAI-compatible client used by the Trace2Skill pipeline.

The benchmark intentionally does not depend on the OpenAI SDK.  This client
uses only the Python standard library and supports the chat-completions subset
needed by the analyst and consolidation stages, including tool calls.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

#: Statuses worth retrying: server-side faults and rate limiting.
RETRYABLE_STATUS = frozenset({408, 409, 425, 429, 500, 502, 503, 504, 529})


@dataclass
class ChatResponse:
    content: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    usage: dict[str, int] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class OpenAICompatibleClient:
    base_url: str
    model: str
    api_key: str = ""
    temperature: float = 0.0
    max_tokens: int = 4096
    timeout: float = 180.0
    retries: int = 5
    retry_backoff: float = 2.0

    def complete(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> ChatResponse:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature if temperature is None else temperature,
            "max_tokens": self.max_tokens if max_tokens is None else max_tokens,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        request = urllib.request.Request(
            self.base_url.rstrip("/") + "/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers=self._headers(),
            method="POST",
        )
        last_error: Exception | None = None
        for attempt in range(max(1, self.retries)):
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    body = json.loads(response.read().decode("utf-8"))
                choice = body["choices"][0]
                message = choice.get("message") or {}
                tool_calls = message.get("tool_calls") or []
                return ChatResponse(
                    content=(message.get("content") or "").strip(),
                    tool_calls=list(tool_calls),
                    usage=body.get("usage") or {},
                    raw=body,
                )
            except urllib.error.HTTPError as exc:
                # HTTPError subclasses URLError, so it must be caught first.
                last_error = exc
                if exc.code not in RETRYABLE_STATUS:
                    raise RuntimeError(
                        f"Chat completion rejected: HTTP {exc.code} {exc.reason}"
                    ) from exc
                self._backoff(attempt)
            except (
                urllib.error.URLError,
                TimeoutError,
                OSError,
                KeyError,
                json.JSONDecodeError,
            ) as exc:
                last_error = exc
                self._backoff(attempt)
        raise RuntimeError(
            f"Chat completion failed after {max(1, self.retries)} attempt(s): {last_error}"
        )

    def _backoff(self, attempt: int) -> None:
        """Wait before the next attempt, so a transient fault can clear."""
        if attempt + 1 >= max(1, self.retries):
            return
        delay = self.retry_backoff * (2**attempt)
        time.sleep(delay)

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers


def client_from_env(
    *,
    base_url: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    **kwargs: Any,
) -> OpenAICompatibleClient:
    """Build a client using explicit values first, then standard env vars."""
    resolved_model = model or os.environ.get("OPENAI_MODEL", "")
    if not resolved_model:
        raise ValueError("model is required (--model or OPENAI_MODEL)")
    return OpenAICompatibleClient(
        base_url=base_url or os.environ.get("OPENAI_BASE_URL", "http://127.0.0.1:8000/v1"),
        model=resolved_model,
        api_key=api_key if api_key is not None else os.environ.get("OPENAI_API_KEY", "EMPTY"),
        **kwargs,
    )
