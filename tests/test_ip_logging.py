"""Failed-turn logs carry a network label, never the full client address."""

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

from app.llm import LLMError  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


def test_a_failed_turn_logs_only_the_network_prefix(monkeypatch, caplog):
    main = importlib.import_module("app.main")
    monkeypatch.setattr(
        main, "settings", dataclasses.replace(main.settings, free_api_key="test-key")
    )
    main._breaker.reset()
    main._cache.clear()
    main.limiter._hits.clear()

    async def failing_stream(*args, **kwargs):  # noqa: ANN002, ANN003
        raise LLMError("upstream busy", 503)
        yield  # pragma: no cover

    monkeypatch.setattr(main.llm, "stream_completion", failing_stream)
    monkeypatch.setattr(main.llm, "retry_delay", lambda *args: 0)

    with caplog.at_level("INFO"):
        TestClient(main.app, client=("203.0.113.77", 54321)).post(
            "/api/chat", json={"messages": [{"role": "user", "content": "在吗"}]}
        )

    lines = [record.getMessage() for record in caplog.records]
    assert any("203.0.x.x" in line for line in lines)
    assert all("203.0.113.77" not in line for line in lines)
