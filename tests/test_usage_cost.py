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
