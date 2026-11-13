"""The upstream read timeout is an operator decision, not a constant."""

from __future__ import annotations

import asyncio
import dataclasses
import importlib
import sys
from pathlib import Path

import pytest

WEB = str(Path(__file__).resolve().parent.parent / "web")
if WEB not in sys.path:
    sys.path.insert(0, WEB)

from app import llm  # noqa: E402
from app.config import load_settings  # noqa: E402

from tests.test_llm_usage import FakeClient, _provider  # noqa: E402


@pytest.fixture()
def clean_env(monkeypatch):
    monkeypatch.delenv("DREAMAI_UPSTREAM_READ_TIMEOUT", raising=False)


def test_the_default_read_timeout(clean_env):
    assert load_settings().upstream_read_timeout == 240.0


def test_a_custom_timeout_is_read(monkeypatch):
    monkeypatch.setenv("DREAMAI_UPSTREAM_READ_TIMEOUT", "420")

    assert load_settings().upstream_read_timeout == 420.0


@pytest.mark.parametrize(("raw", "expected"), [("1", 10.0), ("99999", 900.0), ("garbage", 240.0)])
def test_out_of_range_and_garbage_values_are_clamped(monkeypatch, raw, expected):
    monkeypatch.setenv("DREAMAI_UPSTREAM_READ_TIMEOUT", raw)

    assert load_settings().upstream_read_timeout == expected


def test_the_timeout_reaches_the_http_request():
    client = FakeClient(["data: [DONE]", ""])

    async def run():
        original = llm.get_client
        llm.get_client = lambda: client
        try:
            return [
                item
                async for item in llm.stream_completion(
                    _provider(),
                    api_key="k",
                    model="m",
                    messages=[],
                    read_timeout=123.0,
                )
            ]
        finally:
            llm.get_client = original

    asyncio.run(run())

    assert client.timeouts[0].read == 123.0
    assert client.timeouts[0].connect == 15.0


def test_the_default_timeout_is_still_applied_when_not_given():
    client = FakeClient(["data: [DONE]", ""])

    async def run():
        original = llm.get_client
        llm.get_client = lambda: client
        try:
            return [
                item
                async for item in llm.stream_completion(
                    _provider(), api_key="k", model="m", messages=[]
                )
            ]
        finally:
            llm.get_client = original

    asyncio.run(run())

    assert client.timeouts[0].read == 240.0


def test_the_chat_route_passes_the_configured_timeout(monkeypatch):
    pytest.importorskip("fastapi", reason="web dependencies are not installed")
    main = importlib.import_module("app.main")
    monkeypatch.setattr(
        main,
        "settings",
        dataclasses.replace(main.settings, upstream_read_timeout=77.0, free_api_key="test-key"),
    )
    main._breaker.reset()
    main._cache.clear()
    main.limiter._hits.clear()
    seen: dict = {}

    async def fake_stream(*args, **kwargs):
        seen.update(kwargs)
        yield "content", "好"

    monkeypatch.setattr(main.llm, "stream_completion", fake_stream)
    from fastapi.testclient import TestClient

    response = TestClient(main.app).post(
        "/api/chat", json={"messages": [{"role": "user", "content": "在吗"}]}
    )

    assert response.status_code == 200
    assert seen["read_timeout"] == 77.0
