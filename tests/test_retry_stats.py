"""Retries and fallbacks are real upstream traffic, even when the user wins."""

from __future__ import annotations

import asyncio
import dataclasses
import importlib
import sys
from pathlib import Path

import pytest

pytest.importorskip("fastapi", reason="web dependencies are not installed")
WEB = str(Path(__file__).resolve().parent.parent / "web")
if WEB not in sys.path:
    sys.path.insert(0, WEB)

from app.llm import LLMError, stream_with_fallback, stream_with_retry  # noqa: E402
from app.stats import UsageStats  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


def test_the_retry_hook_receives_the_failing_status():
    seen: list[int | None] = []
    attempts = {"n": 0}

    async def factory():
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise LLMError("busy", 503)
        yield "content", "好"

    async def run() -> None:
        [item async for item in stream_with_retry(factory, delay=0, on_retry=seen.append)]

    asyncio.run(run())

    assert seen == [503]


def test_no_hook_is_called_when_the_first_attempt_succeeds():
    seen: list[int | None] = []

    async def factory():
        yield "content", "好"

    async def run() -> None:
        [item async for item in stream_with_retry(factory, delay=0, on_retry=seen.append)]

    asyncio.run(run())

    assert seen == []


def test_the_fallback_hook_fires_only_when_the_primary_fails():
    seen: list[str] = []

    async def failing():
        raise LLMError("busy", 503)
        yield  # pragma: no cover

    async def working():
        yield "content", "备用"

    async def run() -> None:
        [
            item
            async for item in stream_with_fallback(
                failing, working, on_fallback=lambda: seen.append("used")
            )
        ]

    asyncio.run(run())

    assert seen == ["used"]


def test_retry_counts_survive_a_snapshot_round_trip():
    source = UsageStats()
    source.record_retry(503)
    source.record_retry(503)
    source.record_retry(None)
    source.record_fallback()

    restored = UsageStats()
    assert restored.import_counters(source.export_counters()) is True

    snapshot = restored.snapshot()
    assert snapshot["retries"] == 3
    assert snapshot["retriesByStatus"] == {"503": 2, "none": 1}
    assert snapshot["fallbacks"] == 1


def test_a_successful_retry_is_counted_end_to_end(monkeypatch):
    main = importlib.import_module("app.main")
    monkeypatch.setattr(
        main, "settings", dataclasses.replace(main.settings, free_api_key="test-key")
    )
    monkeypatch.setattr(main, "_stats", UsageStats())
    main._breaker.reset()
    main._cache.clear()
    main.limiter._hits.clear()

    attempts = {"n": 0}

    async def flaky_stream(*args, **kwargs):  # noqa: ANN002, ANN003
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise LLMError("busy", 503)
        yield "content", "好"

    monkeypatch.setattr(main.llm, "stream_completion", flaky_stream)
    monkeypatch.setattr(main.llm, "retry_delay", lambda *args: 0)

    response = TestClient(main.app).post(
        "/api/chat", json={"messages": [{"role": "user", "content": "在吗"}]}
    )

    assert response.status_code == 200
    assert main._stats.snapshot()["retries"] == 1
    assert main._stats.snapshot()["retriesByStatus"] == {"503": 1}


def test_a_fallback_is_counted_end_to_end(monkeypatch):
    main = importlib.import_module("app.main")
    monkeypatch.setattr(
        main,
        "settings",
        dataclasses.replace(
            main.settings,
            free_api_key="test-key",
            fallback_base_url="https://fallback.test/v1",
            fallback_api_key="k" * 40,
            fallback_model="fallback-model",
        ),
    )
    monkeypatch.setattr(main, "_stats", UsageStats())
    main._breaker.reset()
    main._cache.clear()
    main.limiter._hits.clear()

    async def failing_primary(*args, **kwargs):  # noqa: ANN002, ANN003
        raise LLMError("busy", 503)
        yield  # pragma: no cover

    async def working_secondary(*args, **kwargs):  # noqa: ANN002, ANN003
        yield "content", "备用"

    def pick(provider, **kwargs):
        if provider.id == "fallback":
            return working_secondary(**kwargs)
        return failing_primary(**kwargs)

    monkeypatch.setattr(main.llm, "stream_completion", pick)

    response = TestClient(main.app).post(
        "/api/chat", json={"messages": [{"role": "user", "content": "在吗"}]}
    )

    assert response.status_code == 200
    assert "备用" in response.text
    assert main._stats.snapshot()["fallbacks"] == 1
