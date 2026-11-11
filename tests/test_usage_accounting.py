"""End to end: a usage event must become tokens, cost and a done field."""

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


@pytest.fixture()
def harness(monkeypatch):
    main = importlib.import_module("app.main")
    from app.stats import UsageStats

    monkeypatch.setattr(
        main, "settings", dataclasses.replace(main.settings, free_api_key="test-key")
    )
    # The counters, breaker and limiter are module-level and shared with every
    # other web test. Start from a clean slate so this file measures one turn.
    monkeypatch.setattr(main, "_stats", UsageStats(started_at=main.STARTED_AT))
    main._breaker.reset()
    main._cache.clear()
    main.limiter._hits.clear()

    async def fake_stream(*args, **kwargs):  # noqa: ANN002, ANN003
        yield "content", "先给结论。"
        yield "usage", json.dumps({"prompt_tokens": 1000, "completion_tokens": 500})

    monkeypatch.setattr(main.llm, "stream_completion", fake_stream)
    from fastapi.testclient import TestClient

    return main, TestClient(main.app)


def _chat(client) -> str:
    response = client.post(
        "/api/chat", json={"messages": [{"role": "user", "content": "用一句话解释 SSE"}]}
    )
    assert response.status_code == 200, response.text
    return response.text


def test_the_usage_event_reaches_the_client(harness):
    _, client = harness

    body = _chat(client)

    assert "event: usage" in body
    assert '"prompt_tokens": 1000' in body


def test_tokens_and_cost_are_counted(harness):
    main, client = harness
    _chat(client)
    after = main._stats.snapshot()

    assert after["promptTokens"] == 1000
    assert after["completionTokens"] == 500
    # The site's default model is free, so the cost is zero but known, and the
    # tokens are attributed to that model's row rather than only to the total.
    assert after["costUsd"] == 0.0
    assert after["costKnown"] is True
    model = main.settings.free_model
    assert after["byModel"][model]["promptTokens"] == 1000


def test_the_done_event_carries_its_cost(harness):
    _, client = harness

    body = _chat(client)

    assert '"cost"' in body
    assert '"text"' in body


def test_the_provider_is_recorded_for_a_real_turn(harness):
    main, client = harness

    _chat(client)

    assert main._stats.snapshot()["byProvider"] == {"free": 1}
