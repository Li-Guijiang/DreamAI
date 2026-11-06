"""Streaming client for the three provider wire formats.

The wire details live in ``adapters.py``; this module owns the HTTP client, the
SSE loop and error mapping. Keeping it to httpx plus two pure helpers means a new
OpenAI-compatible vendor needs no change here at all.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncIterator

import httpx

from .adapters import build_request, parse_chunk

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


#: One SSE event per token means ~40 events a second, each with its own JSON
#: envelope, its own write on the client and its own frame budget. Merging
#: consecutive tokens of the same kind keeps the stream visually identical while
#: cutting the event count by roughly four.
COALESCE_CHARS = 24


async def coalesce(
    source: AsyncIterator[tuple[str, str]], max_chars: int = COALESCE_CHARS
) -> AsyncIterator[tuple[str, str]]:
    """Merge consecutive ``(kind, text)`` items until ``max_chars`` or a kind change."""
    kind = ""
    buffer: list[str] = []
    size = 0

    async for next_kind, text in source:
        if not text:
            continue
        if kind and next_kind != kind:
            yield kind, "".join(buffer)
            buffer, size = [], 0
        kind = next_kind
        buffer.append(text)
        size += len(text)
        if size >= max_chars:
            yield kind, "".join(buffer)
            buffer, size = [], 0

    if buffer:
        yield kind, "".join(buffer)


async def stream_completion(
    provider,
    *,
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 4096,
    top_p: float | None = None,
    presence_penalty: float | None = None,
) -> AsyncIterator[tuple[str, str]]:
    """Yield coalesced ``(kind, text)`` where kind is ``content`` or ``reasoning``."""
    async for item in coalesce(
        _stream_raw(
            provider,
            api_key=api_key,
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            presence_penalty=presence_penalty,
        )
    ):
        yield item


async def _stream_raw(
    provider,
    *,
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 4096,
    top_p: float | None = None,
    presence_penalty: float | None = None,
) -> AsyncIterator[tuple[str, str]]:
    """Parse the provider stream into per-token items."""
    url, headers, payload = build_request(
        provider,
        api_key=api_key,
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
        presence_penalty=presence_penalty,
    )
    headers["User-Agent"] = "DreamAI-Web/1.0 (+https://liguijiang.com)"

    client = get_client()
    try:
        async with client.stream("POST", url, headers=headers, json=payload) as response:
            if response.status_code != 200:
                body = await response.aread()
                logger.warning("upstream %s: %s", response.status_code, body[:300])
                raise LLMError(_extract_error(response.status_code, body), response.status_code)

            event_name = ""
            async for line in response.aiter_lines():
                if not line:
                    event_name = ""
                    continue
                if line.startswith(":"):  # comment / keep-alive
                    continue
                if line.startswith("event:"):
                    event_name = line[6:].strip()
                    continue
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if not data:
                    continue
                if data == "[DONE]":
                    break
                try:
                    items = parse_chunk(provider.kind, event_name, data)
                except ValueError as exc:
                    raise LLMError(str(exc)) from exc
                for kind, text in items:
                    yield kind, text
    except LLMError:
        raise
    except httpx.TimeoutException as exc:
        raise LLMError("模型响应超时，请稍后重试或缩短问题。") from exc
    except httpx.HTTPError as exc:
        logger.warning("upstream transport error: %s", exc)
        raise LLMError("无法连接模型服务，请稍后重试。") from exc


RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}


async def stream_with_retry(
    factory, attempts: int = 2, delay: float = 0.6
) -> AsyncIterator[tuple[str, str]]:
    """Run ``factory()`` and retry a transient upstream failure once.

    Only failures raised *before* the first token are retried: once text has been
    sent, a second attempt would duplicate it in the user's bubble.
    """
    produced = False
    for attempt in range(1, attempts + 1):
        try:
            async for item in factory():
                produced = True
                yield item
            return
        except LLMError as error:
            retryable = error.status_code in RETRYABLE_STATUS
            if produced or not retryable or attempt == attempts:
                raise
            logger.info("upstream %s, retrying (%s/%s)", error.status_code, attempt, attempts)
            await asyncio.sleep(delay * attempt)
