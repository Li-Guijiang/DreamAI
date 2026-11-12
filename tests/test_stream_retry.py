"""Transient upstream failures are retried, but only before the first token."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))

from app.llm import LLMError, retry_delay, stream_with_retry  # noqa: E402


def run(factory, attempts: int = 2):
    async def collect():
        return [item async for item in stream_with_retry(factory, attempts=attempts, delay=0)]

    return asyncio.run(collect())


def test_transient_failure_is_retried():
    calls = {"n": 0}

    async def factory():
        calls["n"] += 1
        if calls["n"] == 1:
            raise LLMError("上游繁忙", 503)
        yield "content", "好"

    assert run(factory) == [("content", "好")]
    assert calls["n"] == 2


def test_client_error_is_not_retried():
    calls = {"n": 0}

    async def factory():
        calls["n"] += 1
        raise LLMError("Key 无效", 401)
        yield  # pragma: no cover

    with pytest.raises(LLMError):
        run(factory)
    assert calls["n"] == 1


def test_failure_after_first_token_is_not_retried():
    async def factory():
        yield "content", "开头"
        raise LLMError("断了", 502)

    with pytest.raises(LLMError):
        run(factory)


def test_success_needs_no_retry():
    calls = {"n": 0}

    async def factory():
        calls["n"] += 1
        yield "content", "一次成功"

    assert run(factory) == [("content", "一次成功")]
    assert calls["n"] == 1


def test_a_usage_event_is_never_merged_into_text():
    import asyncio

    from app.llm import coalesce

    async def source():
        yield "content", "半句"
        yield "usage", '{"prompt_tokens": 1}'
        yield "content", "下半句"
        yield "usage", '{"completion_tokens": 2}'

    items = asyncio.run(_drain(coalesce(source())))

    assert items == [
        ("content", "半句"),
        ("usage", '{"prompt_tokens": 1}'),
        ("content", "下半句"),
        ("usage", '{"completion_tokens": 2}'),
    ]


async def _drain(source):  # noqa: ANN001
    return [item async for item in source]


def test_a_retry_waits_longer_than_the_one_before():
    # The ranges do not overlap: attempt 1 waits inside [d/2, d], attempt 2
    # inside [d, 2d].
    assert retry_delay(0.6, 2) > retry_delay(0.6, 1)


def test_the_wait_is_half_fixed_and_half_jittered(monkeypatch):
    monkeypatch.setattr("app.llm.random.uniform", lambda low, high: low)
    assert retry_delay(0.6, 1) == pytest.approx(0.3)

    monkeypatch.setattr("app.llm.random.uniform", lambda low, high: high)
    assert retry_delay(0.6, 1) == pytest.approx(0.6)


def test_no_delay_is_still_no_delay():
    assert retry_delay(0.0, 3) == 0.0


def test_a_negative_delay_cannot_make_the_clock_go_backwards():
    assert retry_delay(-5, 2) == 0.0
