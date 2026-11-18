"""A fast upstream must not be able to fill memory faster than the client reads."""

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

from fastapi.testclient import TestClient  # noqa: E402


def test_a_full_queue_waits_for_the_reader():
    async def run() -> None:
        queue: asyncio.Queue = asyncio.Queue(maxsize=2)
        await queue.put(1)
        await queue.put(2)

        with pytest.raises(TimeoutError):
            await asyncio.wait_for(queue.put(3), timeout=0.01)

        assert await queue.get() == 1
        await asyncio.wait_for(queue.put(3), timeout=0.01)
        assert queue.qsize() == 2

    asyncio.run(run())


def test_the_chat_route_builds_a_bounded_queue(monkeypatch):
    main = importlib.import_module("app.main")
    monkeypatch.setattr(
        main,
        "settings",
        dataclasses.replace(main.settings, free_api_key="test-key", stream_queue_size=8),
    )
    main._breaker.reset()
    main._cache.clear()
    main.limiter._hits.clear()

    captured: list[asyncio.Queue] = []
    original = main.stream_queue

    def capture() -> asyncio.Queue:
        queue = original()
        captured.append(queue)
        return queue

    async def fake_stream(*args, **kwargs):  # noqa: ANN002, ANN003
        yield "content", "好"

    monkeypatch.setattr(main, "stream_queue", capture)
    monkeypatch.setattr(main.llm, "stream_completion", fake_stream)

    response = TestClient(main.app).post(
        "/api/chat", json={"messages": [{"role": "user", "content": "在吗"}]}
    )

    assert response.status_code == 200
    assert len(captured) == 1
    assert captured[0].maxsize == 8
    assert captured[0].empty(), "the pump's sentinel must be consumed"


def test_the_helper_uses_the_current_settings(monkeypatch):
    main = importlib.import_module("app.main")
    monkeypatch.setattr(main, "settings", dataclasses.replace(main.settings, stream_queue_size=23))

    assert main.stream_queue().maxsize == 23
