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
) -> tuple[str, dict[str, str], dict]:
    """Return ``(url, headers, payload)`` for a streaming request."""
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
