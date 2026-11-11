"""Wire formats for the three provider families.

Everything here is a pure function of its arguments: build a request, or turn one
SSE chunk into ``(kind, text)``. No network, no settings - which is what makes the
formats testable without a key.
"""

from __future__ import annotations

import json
from urllib.parse import quote

from .providers import Provider

ANTHROPIC_VERSION = "2023-06-01"


def build_request(
    provider: Provider,
    *,
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    temperature: float,
    max_tokens: int,
    top_p: float | None = None,
    presence_penalty: float | None = None,
    include_usage: bool = True,
) -> tuple[str, dict[str, str], dict]:
    """Return ``(url, headers, payload)`` for a streaming request.

    Sampling knobs are optional and provider-specific: OpenAI-compatible endpoints
    take both, Anthropic takes ``top_p`` only, Gemini spells it ``topP`` inside
    ``generationConfig``.
    """
    if provider.kind == "anthropic":
        system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
        chat = [m for m in messages if m["role"] != "system"]
        payload = {
            "model": model,
            "messages": chat,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }
        if system:
            payload["system"] = system
        if top_p is not None:
            payload["top_p"] = top_p
        headers = {
            "x-api-key": api_key,
            "anthropic-version": ANTHROPIC_VERSION,
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        }
        return f"{provider.base_url.rstrip('/')}/v1/messages", headers, payload

    if provider.kind == "google":
        contents = [
            {
                "role": "model" if m["role"] == "assistant" else "user",
                "parts": [{"text": m["content"]}],
            }
            for m in messages
            if m["role"] != "system"
        ]
        system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
        payload: dict = {
            "contents": contents,
            "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
        }
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        if top_p is not None:
            payload["generationConfig"]["topP"] = top_p
        url = (
            f"{provider.base_url.rstrip('/')}/models/{quote(model, safe='')}"
            f":streamGenerateContent?alt=sse&key={quote(api_key, safe='')}"
        )
        return url, {"Content-Type": "application/json"}, payload

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }
    if include_usage:
        # The final SSE chunk then carries a top-level `usage` object. Without
        # this field most vendors simply never send token counts on a stream.
        payload["stream_options"] = {"include_usage": True}
    if top_p is not None:
        payload["top_p"] = top_p
    if presence_penalty is not None:
        payload["presence_penalty"] = presence_penalty
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    return f"{provider.base_url.rstrip('/')}/chat/completions", headers, payload


def parse_chunk(kind: str, event: str, data: str) -> list[tuple[str, str]]:
    """Turn one SSE event into zero or more ``(content|reasoning, text)`` items."""
    if not data or data == "[DONE]":
        return []
    try:
        chunk = json.loads(data)
    except ValueError:
        return []
    if not isinstance(chunk, dict):
        return []

    if kind == "anthropic":
        if event != "content_block_delta":
            return []
        delta = chunk.get("delta") or {}
        if delta.get("type") == "thinking_delta" and delta.get("thinking"):
            return [("reasoning", delta["thinking"])]
        if delta.get("type") == "text_delta" and delta.get("text"):
            return [("content", delta["text"])]
        return []

    if kind == "google":
        items: list[tuple[str, str]] = []
        for candidate in chunk.get("candidates") or []:
            for part in (candidate.get("content") or {}).get("parts") or []:
                text = part.get("text")
                if text:
                    items.append(("reasoning" if part.get("thought") else "content", text))
        return items

    error = chunk.get("error")
    if error:
        message = error.get("message") if isinstance(error, dict) else str(error)
        raise ValueError(message or "模型服务返回错误")

    choices = chunk.get("choices") or []
    if not choices:
        return []
    delta = choices[0].get("delta") or {}
    items = []
    if isinstance(delta.get("reasoning_content"), str) and delta["reasoning_content"]:
        items.append(("reasoning", delta["reasoning_content"]))
    if isinstance(delta.get("content"), str) and delta["content"]:
        items.append(("content", delta["content"]))
    return items


def _count(value: object) -> int | None:
    """Token counts are non-negative numbers; a bool is not a count."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return max(0, int(value))


def usage_from_chunk(kind: str, data: str) -> dict[str, int] | None:
    """Normalise whatever token counts a provider put in one SSE chunk.

    Three shapes are in the wild:

    * OpenAI-compatible: a final ``usage`` object in the last chunk;
    * Anthropic: ``message_start.message.usage`` for input, then a cumulative
      ``message_delta.usage`` for output;
    * Gemini: ``usageMetadata`` with camel-cased names, often repeated.

    Only the keys actually present are returned, so a caller can accumulate
    across chunks without mistaking a missing value for a zero.
    """
    if not data or data == "[DONE]":
        return None
    try:
        chunk = json.loads(data)
    except ValueError:
        return None
    if not isinstance(chunk, dict):
        return None

    if kind == "anthropic":
        usage = chunk.get("usage") or {}
        if chunk.get("type") == "message_start":
            usage = (chunk.get("message") or {}).get("usage") or {}
        if not isinstance(usage, dict):
            return None
        found: dict[str, int] = {}
        for source, target in (
            ("input_tokens", "prompt_tokens"),
            ("output_tokens", "completion_tokens"),
        ):
            count = _count(usage.get(source))
            if count is not None:
                found[target] = count
        return found or None

    if kind == "google":
        meta = chunk.get("usageMetadata") or {}
        if not isinstance(meta, dict):
            return None
        found = {}
        for source, target in (
            ("promptTokenCount", "prompt_tokens"),
            ("candidatesTokenCount", "completion_tokens"),
        ):
            count = _count(meta.get(source))
            if count is not None:
                found[target] = count
        return found or None

    usage = chunk.get("usage") or {}
    if not isinstance(usage, dict):
        return None
    found = {}
    for source, target in (
        ("prompt_tokens", "prompt_tokens"),
        ("completion_tokens", "completion_tokens"),
    ):
        count = _count(usage.get(source))
        if count is not None:
            found[target] = count
    return found or None
