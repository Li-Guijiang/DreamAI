"""Usage must expose cost and cache counters, and admit unknown prices."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest.importorskip("fastapi", reason="web dependencies are not installed")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))

from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture()
def client(monkeypatch):
    import importlib

    monkeypatch.syspath_prepend("web")
    return TestClient(importlib.import_module("app.main").app)


def test_usage_carries_cost_and_cache_fields(client):
    body = client.get("/api/usage").json()

    assert "costUsd" in body
    assert isinstance(body["costKnown"], bool)
    assert 0.0 <= body["cacheHitRate"] <= 1.0
    assert body["promptTokens"] >= 0


def test_usage_reports_latency_tier_and_local_traffic(client):
    body = client.get("/api/usage").json()

    assert body["avgTtft"] >= 0.0
    assert body["ttftSamples"] >= 0
    assert isinstance(body["byTier"], dict)
    assert body["local"] >= 0
    assert body["blocked"] >= 0


def test_usage_by_model_rows_carry_cost_and_tokens(client):
    import importlib

    main = importlib.import_module("app.main")
    main._stats.record_turn("probe-model", tier="light", ttft=0.5)
    main._stats.record_usage("probe-model", 12, 8, 0.0004)

    body = client.get("/api/usage").json()
    row = body["byModel"]["probe-model"]

    assert row["requests"] == 1
    assert row["promptTokens"] == 12
    assert row["completionTokens"] == 8
    assert row["costUsd"] == pytest.approx(0.0004)
    assert body["byTier"]["light"] == 1
    assert body["ttftSamples"] == 1


def test_an_identity_answer_is_counted_as_local_traffic(client):
    import importlib

    main = importlib.import_module("app.main")
    before = main._stats.local_answers

    response = client.post(
        "/api/chat", json={"messages": [{"role": "user", "content": "你的主人是谁"}]}
    )

    assert response.status_code == 200
    assert main._stats.local_answers == before + 1
    assert main._stats.snapshot()["byModel"]["local"]["requests"] >= 1
