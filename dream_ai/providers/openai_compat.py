"""OpenAI-compatible hosted provider.

Works with any endpoint that exposes the OpenAI Chat Completions schema
(OpenAI, DeepSeek, DashScope compatible mode, local Ollama/LM Studio, ...).
The ``openai`` package is imported lazily so the rest of the package stays
usable offline and in tests.
"""

from __future__ import annotations

from typing import Any

from ..exceptions import ProviderError
from .base import LLMProvider


def _count(value: object) -> int | None:
    """A token count must be a non-negative integer; a bool is not one."""
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return max(0, value)


def usage_from_response(response: Any) -> dict[str, int]:
    """Read the token counts off an SDK response, tolerating an absent block.

    The OpenAI SDK returns a typed object, a compatible proxy may return a plain
    dict, and some gateways return no usage at all. All three are handled here so
    the caller only sees a mapping, possibly empty.
    """
    usage = (
        response.get("usage") if isinstance(response, dict) else getattr(response, "usage", None)
    )
    if usage is None:
        return {}

    def field(name: str) -> object:
        if isinstance(usage, dict):
            return usage.get(name)
        return getattr(usage, name, None)

    found: dict[str, int] = {}
    for source in ("prompt_tokens", "completion_tokens"):
        count = _count(field(source))
        if count is not None:
            found[source] = count

    details = field("prompt_tokens_details")
    if details is not None:
        cached = (
            details.get("cached_tokens")
            if isinstance(details, dict)
            else getattr(details, "cached_tokens", None)
        )
        count = _count(cached)
        if count:
            found["cached_tokens"] = count
    return found


class OpenAICompatProvider(LLMProvider):
    """Chat through an OpenAI-compatible HTTP API."""

    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
    ) -> None:
        self._model = model
        self._api_key = api_key
        self._base_url = base_url
        self._system_prompt = system_prompt
        self._temperature = temperature
        self._client: Any = None
        self._last_usage: dict[str, int] = {}

    @property
    def name(self) -> str:
        return f"openai-compat:{self._model}"

    @property
    def model(self) -> str:
        return self._model

    @property
    def last_usage(self) -> dict[str, int]:
        return dict(self._last_usage)

    def _ensure_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - dependency check
            raise ProviderError(
                "The 'openai' package is required for the hosted provider. "
                "Install it with: pip install -r requirements.txt"
            ) from exc

        self._client = OpenAI(api_key=self._api_key, base_url=self._base_url)
        return self._client

    def generate(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        client = self._ensure_client()
        # Cleared before the call, so a failure cannot leave the previous turn's
        # counts looking like this turn's.
        self._last_usage = {}

        payload_messages: list[dict[str, str]] = list(messages)
        if self._system_prompt and not any(m["role"] == "system" for m in payload_messages):
            payload_messages.insert(0, {"role": "system", "content": self._system_prompt})

        temperature = kwargs.get("temperature", self._temperature)
        # A budget is optional: when the caller does not ask for one, the
        # provider's own default applies and nothing is sent.
        max_tokens = kwargs.get("max_tokens")
        options: dict[str, Any] = {
            "model": self._model,
            "messages": payload_messages,
            "temperature": temperature,
        }
        if isinstance(max_tokens, int) and max_tokens > 0:
            options["max_tokens"] = max_tokens

        try:
            response = client.chat.completions.create(**options)
        except Exception as exc:  # normalise every client/network failure
            raise ProviderError(f"LLM request failed: {exc}") from exc

        # The counts belong to this call only; the agent reads them after the
        # reply, and they are the difference between a measured bill and a guess.
        self._last_usage = usage_from_response(response)

        choice = response.choices[0]
        content = choice.message.content
        if content is None:
            raise ProviderError("The provider returned an empty response.")
        return content.strip()
