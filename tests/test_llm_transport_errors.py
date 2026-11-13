"""Transport failures must arrive at the retry layer with a usable status."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import httpx
import pytest

WEB = str(Path(__file__).resolve().parent.parent / "web")
if WEB not in sys.path:
    sys.path.insert(0, WEB)

from app import llm  # noqa: E402
from app.errors import is_retryable  # noqa: E402
from app.llm import LLMError, stream_with_retry  # noqa: E402

from tests.test_llm_usage import _provider  # noqa: E402


class FailingStream:
    def __init__(self, exc: Exception) -> None:
        self.exc = exc

    async def __aenter__(self):
        raise self.exc

    async def __aexit__(self, *args):  # noqa: ANN002
        return False


class FailingClient:
    def __init__(self, exc: Exception) -> None:
        self.exc = exc

    def stream(self, method, url, headers=None, json=None, **kwargs):  # noqa: A002, ARG002
        return FailingStream(self.exc)


def _failure(exc: Exception) -> LLMError:
    async def run() -> LLMError:
        original = llm.get_client
        llm.get_client = lambda: FailingClient(exc)
        try:
            with pytest.raises(LLMError) as caught:
                async for _ in llm.stream_completion(
                    _provider(), api_key="k", model="m", messages=[]
                ):
                    pass
            return caught.value
        finally:
            llm.get_client = original

    return asyncio.run(run())


def test_a_read_timeout_becomes_a_retryable_408():
    error = _failure(httpx.ReadTimeout("timed out"))

    assert error.status_code == 408
    assert is_retryable(error.status_code)


def test_a_connect_error_becomes_a_retryable_503():
    error = _failure(httpx.ConnectError("connection refused"))

    assert error.status_code == 503
    assert is_retryable(error.status_code)


def test_a_transport_failure_keeps_a_readable_message():
    error = _failure(httpx.ConnectError("10.0.0.1:443"))

    assert "connection refused" not in error.message
    assert error.message


def test_a_statusless_failure_still_fails_fast():
    error = LLMError("no response", None)

    assert not is_retryable(error.status_code)


def test_a_read_timeout_is_actually_retried_once():
    calls = {"n": 0}

    async def factory():
        calls["n"] += 1
        if calls["n"] == 1:
            raise LLMError("模型响应超时，请稍后重试或缩短问题。", 408)
        yield "content", "好"

    async def run():
        return [item async for item in stream_with_retry(factory, attempts=2, delay=0)]

    assert asyncio.run(run()) == [("content", "好")]
    assert calls["n"] == 2
