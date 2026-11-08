"""Failover must happen only before the user has seen anything."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))

from app.llm import LLMError, stream_with_fallback  # noqa: E402


def run(primary, fallback):
    async def collect():
        return [item async for item in stream_with_fallback(primary, fallback)]

    return asyncio.run(collect())


def test_primary_failure_before_first_token_uses_fallback():
    async def primary():
        raise LLMError("boom", 503)
        yield  # pragma: no cover

    async def fallback():
        yield "content", "备用回答"

    assert run(primary, fallback) == [("content", "备用回答")]


def test_failure_after_first_token_is_not_swallowed():
    async def primary():
        yield "content", "开头"
        raise LLMError("断了", 502)

    async def fallback():
        yield "content", "不该出现"

    with pytest.raises(LLMError):
        run(primary, fallback)


def test_no_fallback_keeps_the_original_error():
    async def primary():
        raise LLMError("boom", 500)
        yield  # pragma: no cover

    with pytest.raises(LLMError):
        run(primary, None)


def test_primary_success_never_calls_the_fallback():
    calls = {"n": 0}

    async def primary():
        yield "content", "正常"

    async def fallback():
        calls["n"] += 1
        yield "content", "备用"

    assert run(primary, fallback) == [("content", "正常")]
    assert calls["n"] == 0
