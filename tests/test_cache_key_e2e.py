"""Changing a sampling setting must not replay an old cached answer."""

from __future__ import annotations

import dataclasses
import importlib
import sys
from pathlib import Path

import pytest

pytest.importorskip("fastapi", reason="web dependencies are not installed")
WEB = str(Path(__file__).resolve().parent.parent / "web")
if WEB not in sys.path:
    sys.path.insert(0, WEB)

from app.cache import ResponseCache  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

BODY = {"messages": [{"role": "user", "content": "在吗"}], "temperature": 0.0}


@pytest.fixture()
def harness(monkeypatch):
    main = importlib.import_module("app.main")
    main._cache = ResponseCache(max_items=8, ttl=300, max_bytes=0)
    main._breaker.reset()
    main.limiter._hits.clear()

    async def fake_stream(*args, **kwargs):  # noqa: ANN002, ANN003
        yield "content", "好"

    monkeypatch.setattr(main.llm, "stream_completion", fake_stream)
    return main


def set_top_p(main, value: float) -> None:
    main.settings = dataclasses.replace(main.settings, free_api_key="test-key", top_p=value)


def post(main):
    return TestClient(main.app).post("/api/chat", json=BODY)


def test_a_changed_top_p_does_not_hit_the_old_answer(harness):
    main = harness
    set_top_p(main, 0.1)
    post(main)
    assert main._cache.stats()["hits"] == 0

    set_top_p(main, 0.9)
    post(main)

    assert main._cache.stats()["hits"] == 0
    assert main._cache.stats()["misses"] == 2


def test_the_same_sampling_settings_still_hit_the_cache(harness):
    main = harness
    set_top_p(main, 0.5)
    post(main)
    post(main)

    assert main._cache.stats()["hits"] == 1
