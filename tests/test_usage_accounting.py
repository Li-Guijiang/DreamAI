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


def test_cached_prompt_tokens_reach_the_usage_endpoint(harness, monkeypatch):
    main, client = harness

    async def cached_stream(*args, **kwargs):  # noqa: ANN002, ANN003
        yield "content", "答。"
        yield (
            "usage",
            json.dumps({"prompt_tokens": 2000, "completion_tokens": 10, "cached_tokens": 1792}),
        )

    monkeypatch.setattr(main.llm, "stream_completion", cached_stream)
    _chat(client)

    usage = client.get("/api/usage").json()

    assert usage["promptTokens"] == 2000
    assert usage["cachedTokens"] == 1792
    assert usage["cachedShare"] == 0.896
    assert usage["byModel"][main.settings.free_model]["cachedTokens"] == 1792


def test_a_cache_hit_is_filed_under_the_cache_not_the_vendor(harness):
    main, client = harness
    body = {"messages": [{"role": "user", "content": "在吗"}], "temperature": 0.2}

    first = client.post("/api/chat", json=body)
    second = client.post("/api/chat", json=body)

    assert first.headers["X-Cache"] == "MISS"
    assert second.headers["X-Cache"] == "HIT"
    snapshot = main._stats.snapshot()
    assert snapshot["requests"] == 2
    # A hit spent no tokens, so it must not be counted as a vendor turn; the
    # totals still have to add up to the number of requests served.
    assert snapshot["byProvider"] == {"free": 1, "cache": 1}
    assert sum(snapshot["byIntent"].values()) == 2
    assert snapshot["promptTokens"] == 1000


def _done_payload(body: str) -> dict:
    """The JSON object carried by the last `event: done` frame."""
    done = [frame for frame in body.split("\n\n") if frame.startswith("event: done")]
    data = next(line[6:] for line in done[-1].splitlines() if line.startswith("data:"))
    return json.loads(data)


def test_a_truncated_stream_is_reported_as_truncated(harness, monkeypatch):
    main, client = harness

    async def truncated_stream(*args, **kwargs):  # noqa: ANN002, ANN003
        yield "content", "写到一半"
        yield "usage", json.dumps({"prompt_tokens": 10, "completion_tokens": 5})
        yield "finish", "length"

    monkeypatch.setattr(main.llm, "stream_completion", truncated_stream)
    body = _chat(client)

    done = _done_payload(body)
    assert done["truncated"] is True
    assert done["finish"] == "length"
    # The word "length" is metadata; it must not appear in the answer itself.
    assert "length" not in "".join(
        json.loads(line[6:])["t"]
        for line in body.splitlines()
        if line.startswith("data:") and '"t"' in line
    )
    usage = client.get("/api/usage").json()
    assert usage["truncated"] == 1
    assert usage["truncationRate"] == 1.0


def test_a_normal_finish_is_not_called_truncated(harness, monkeypatch):
    main, client = harness

    async def finished_stream(*args, **kwargs):  # noqa: ANN002, ANN003
        yield "content", "完整的回答"
        yield "finish", "stop"

    monkeypatch.setattr(main.llm, "stream_completion", finished_stream)
    body = _chat(client)

    done = _done_payload(body)
    assert done["truncated"] is False
    assert done["finish"] == "stop"
    assert client.get("/api/usage").json()["truncated"] == 0


def test_a_truncated_answer_is_never_cached(harness, monkeypatch):
    main, client = harness

    async def truncated_stream(*args, **kwargs):  # noqa: ANN002, ANN003
        yield "content", "写到一半"
        yield "finish", "length"

    monkeypatch.setattr(main.llm, "stream_completion", truncated_stream)
    body = {"messages": [{"role": "user", "content": "在吗"}], "temperature": 0.2}

    first = client.post("/api/chat", json=body)
    second = client.post("/api/chat", json=body)

    # Both must go upstream: a cached half-answer would be replayed forever.
    assert first.headers["X-Cache"] == "MISS"
    assert second.headers["X-Cache"] == "MISS"
    assert main._cache.stats()["items"] == 0
