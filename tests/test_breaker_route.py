"""When the breaker is open, the route must refuse fast and say so."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

pytest.importorskip("fastapi", reason="web dependencies are not installed")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))

from app.guard import CircuitBreaker  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture()
def main_module(monkeypatch):
    import dataclasses
    import importlib

    monkeypatch.syspath_prepend("web")
    main = importlib.import_module("app.main")
    if not main.settings.free_configured:
        main.settings = dataclasses.replace(main.settings, free_api_key="test-key")
    return main


def test_open_breaker_returns_a_short_error_and_a_done_marker(main_module):
    breaker = CircuitBreaker(threshold=1, cooldown=60)
    breaker.record_failure()
    main_module._breaker = breaker

    response = TestClient(main_module.app).post(
        "/api/chat", json={"messages": [{"role": "user", "content": "在吗"}]}
    )
    events = [
        json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")
    ]
    errors = [event for event in events if "message" in event]
    done = [event for event in events if event.get("blocked")]

    assert response.status_code == 200
    assert errors and "暂停" in errors[0]["message"]
    assert done and done[0]["chars"] == 0
