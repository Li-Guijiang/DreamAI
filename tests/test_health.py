"""Health must expose the operational state that explains a slow site."""

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
    main = importlib.import_module("app.main")
    return TestClient(main.app)


def test_health_reports_breaker_state_and_cache_counters(client):
    body = client.get("/api/health").json()

    assert body["ok"] is True
    assert body["upstream"] in {"closed", "open", "half-open"}
    assert body["breaker"]["state"] == body["upstream"]
    assert body["breaker"]["threshold"] >= 1
    assert {"items", "capacity", "ttl", "hits", "misses"} <= set(body["cache"])
    assert body["cache"]["items"] >= 0
