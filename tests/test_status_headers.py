"""Status endpoints must never be served from a browser cache."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest.importorskip("fastapi", reason="web dependencies are not installed")
WEB = str(Path(__file__).resolve().parent.parent / "web")
if WEB not in sys.path:
    sys.path.insert(0, WEB)

from fastapi.testclient import TestClient  # noqa: E402


def test_health_and_usage_are_not_cacheable():
    main = __import__("app.main", fromlist=["app"])

    with TestClient(main.app) as client:
        for path in ("/api/health", "/api/usage"):
            response = client.get(path)

            assert response.status_code == 200
            assert response.headers["cache-control"] == "no-store"


def test_the_chat_stream_keeps_its_own_cache_directive(monkeypatch):
    import dataclasses

    main = __import__("app.main", fromlist=["app"])
    monkeypatch.setattr(
        main, "settings", dataclasses.replace(main.settings, free_api_key="test-key")
    )
    main._breaker.reset()
    main._cache.clear()

    async def fake_stream(*args, **kwargs):  # noqa: ANN002, ANN003
        yield "content", "好"

    monkeypatch.setattr(main.llm, "stream_completion", fake_stream)

    response = TestClient(main.app).post(
        "/api/chat", json={"messages": [{"role": "user", "content": "在吗"}]}
    )

    assert response.headers["cache-control"] == "no-store, no-transform"
    assert "no-transform" in response.headers["cache-control"]
