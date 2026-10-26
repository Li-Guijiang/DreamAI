"""Streaming client for any OpenAI-compatible chat-completions endpoint.

Keeping this layer dependency-free (httpx only) means the web service can talk
to DeepSeek, OpenAI, DashScope compatible mode, Moonshot, local vLLM/Ollama and
so on, just by changing ``DREAMAI_BASE_URL``.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx

logger = logging.getLogger("dreamai.llm")

_client: httpx.AsyncClient | None = None

_STATUS_HINTS = {
    400: "请求格式有误，请调整输入后重试。",
    401: "API Key 无效或已过期，请在服务端 .env 中更新 DREAMAI_API_KEY。",
    402: "模型账户余额不足，请先在服务商控制台充值。",
    403: "当前 API Key 没有访问该模型的权限。",
    404: "模型接口地址不正确，请检查 DREAMAI_BASE_URL。",
    429: "请求过于频繁，请稍后再试。",
    500: "模型服务内部错误，请稍后重试。",
    502: "模型服务暂时不可用，请稍后重试。",
    503: "模型服务繁忙，请稍后重试。",
    504: "模型服务响应超时，请稍后重试。",
}


class LLMError(Exception):
    """A normalized, user-facing upstream error."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=15.0, read=240.0, write=30.0, pool=15.0),
            limits=httpx.Limits(max_connections=32, max_keepalive_connections=16),
            follow_redirects=True,
        )
    return _client


async def close_client() -> None:
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None


def endpoint(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    return f"{base}/chat/completions"


def _extract_error(status: int, body: bytes) -> str:
    detail = ""
    try:
        payload = json.loads(body.decode("utf-8", "replace"))
        error = payload.get("error") if isinstance(payload, dict) else None
        if isinstance(error, dict):
            detail = str(error.get("message") or "")
        elif isinstance(error, str):
            detail = error
        if not detail and isinstance(payload, dict):
            detail = str(payload.get("message") or "")
    except (ValueError, UnicodeDecodeError):
        detail = body.decode("utf-8", "replace")[:200]

    hint = _STATUS_HINTS.get(status, "模型服务返回了错误，请稍后重试。")
    detail = " ".join(detail.split())[:160]
    return f"{hint}（HTTP {status}）" + (f" 详情：{detail}" if detail else "")


async def stream_completion(
    *,
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> AsyncIterator[tuple[str, str]]:
    """Yield ``(kind, text)`` where kind is ``content`` or ``reasoning``."""
    payload: dict[str, Any] = {
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
        "User-Agent": "DreamAI-Web/1.0 (+https://liguijiang.com)",
    }

    client = get_client()
    try:
        async with client.stream(
            "POST", endpoint(base_url), headers=headers, json=payload
        ) as response:
            if response.status_code != 200:
                body = await response.aread()
                logger.warning("upstream %s: %s", response.status_code, body[:300])
                raise LLMError(_extract_error(response.status_code, body), response.status_code)

            async for line in response.aiter_lines():
                if not line:
                    continue
                if line.startswith(":"):  # comment / keep-alive
                    continue
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if not data or data == "[DONE]":
                    if data == "[DONE]":
                        break
                    continue
                try:
                    chunk = json.loads(data)
                except ValueError:
                    continue
                if isinstance(chunk, dict) and chunk.get("error"):
                    message = chunk["error"]
                    if isinstance(message, dict):
                        message = message.get("message", "模型服务返回错误")
                    raise LLMError(str(message))

                choices = chunk.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}
                reasoning = delta.get("reasoning_content")
                if isinstance(reasoning, str) and reasoning:
                    yield "reasoning", reasoning
                content = delta.get("content")
                if isinstance(content, str) and content:
                    yield "content", content
    except LLMError:
        raise
    except httpx.TimeoutException as exc:
        raise LLMError("模型响应超时，请稍后重试或缩短问题。") from exc
    except httpx.HTTPError as exc:
        logger.warning("upstream transport error: %s", exc)
        raise LLMError("无法连接模型服务，请稍后重试。") from exc
