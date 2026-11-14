"""Private owner conversations must never enter the shared answer cache."""

from __future__ import annotations

import dataclasses
import importlib
import json
import sys
from pathlib import Path

import pytest

pytest.importorskip("fastapi", reason="web dependencies are not installed")
WEB = str(Path(__file__).resolve().parent.parent / "web")
if WEB not in sys.path:
    sys.path.insert(0, WEB)

from app import owner_auth  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture()
def harness(monkeypatch):
    main = importlib.import_module("app.main")
    monkeypatch.setattr(
        main, "settings", dataclasses.replace(main.settings, free_api_key="test-key")
    )
    monkeypatch.setenv(owner_auth.SECRET_ENV, "test-secret")
    main._cache.clear()
    main._breaker.reset()
    main.limiter._hits.clear()

    async def fake_stream(*args, **kwargs):  # noqa: ANN002, ANN003
        yield "content", "好"
        yield "usage", json.dumps({"prompt_tokens": 5, "completion_tokens": 2})

    monkeypatch.setattr(main.llm, "stream_completion", fake_stream)
    return main, TestClient(main.app)


BODY = {"messages": [{"role": "user", "content": "在吗"}], "temperature": 0.2}


def test_a_public_low_temperature_turn_is_cached(harness):
    _, client = harness

    first = client.post("/api/chat", json=BODY)
    second = client.post("/api/chat", json=BODY)

    assert first.headers["X-Cache"] == "MISS"
    assert second.headers["X-Cache"] == "HIT"


def test_an_owner_turn_is_never_cached(harness):
    main, client = harness
    cookie = owner_auth.issue_cookie()
    client.cookies.set(owner_auth.COOKIE_NAME, cookie)

    first = client.post("/api/chat", json=BODY)
    second = client.post("/api/chat", json=BODY)

    assert first.headers["X-Cache"] == "MISS"
    assert second.headers["X-Cache"] == "MISS"
    assert main._cache.stats()["items"] == 0


def test_an_expired_owner_cookie_does_not_disable_the_cache(harness):
    _, client = harness
    client.cookies.set(owner_auth.COOKIE_NAME, "1.deadbeef")

    client.post("/api/chat", json=BODY)
    second = client.post("/api/chat", json=BODY)

    assert second.headers["X-Cache"] == "HIT"


def test_the_public_cache_is_not_poisoned_by_an_owner_turn(harness):
    main, client = harness
    cookie = owner_auth.issue_cookie()
    client.cookies.set(owner_auth.COOKIE_NAME, cookie)
    client.post("/api/chat", json=BODY)

    client.cookies.delete(owner_auth.COOKIE_NAME)
    first_public = client.post("/api/chat", json=BODY)
    second_public = client.post("/api/chat", json=BODY)

    assert first_public.headers["X-Cache"] == "MISS"
    assert second_public.headers["X-Cache"] == "HIT"
    assert main._cache.stats()["items"] == 1
