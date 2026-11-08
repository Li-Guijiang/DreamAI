"""The first event tells the client how the turn was classified."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

pytest.importorskip("fastapi", reason="web dependencies are not installed")
pytest.importorskip("httpx")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))

from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture()
def client(monkeypatch):
    # Import once and reuse: reloading the module would create a second
    # UpstreamError class and break isinstance checks in other test modules.
    # A free key is injected on the settings object instead of the environment,
    # so the module can be shared no matter which test imported it first.
    import dataclasses
    import importlib

    monkeypatch.syspath_prepend("web")
    main = importlib.import_module("app.main")
    if not main.settings.free_configured:
        main.settings = dataclasses.replace(main.settings, free_api_key="test-key")
    return TestClient(main.app)


def _meta(client: TestClient, text: str) -> dict:
    response = client.post("/api/chat", json={"messages": [{"role": "user", "content": text}]})
    assert response.status_code == 200
    for line in response.text.splitlines():
        if line.startswith("data: "):
            event = json.loads(line[6:])
            if "intent" in event:
                return event
    raise AssertionError("meta event with intent not found")


def test_error_question_reports_the_intent_and_tier(client):
    meta = _meta(client, "启动报错：端口被占用，怎么修")

    assert meta["intent"] == "error"
    assert meta["tier"] in {"light", "standard", "deep"}


def test_writing_question_reports_the_writing_intent(client):
    meta = _meta(client, "帮我写一段周报开头，说明本周做了登录改造")

    assert meta["intent"] == "writing"


def test_response_header_carries_the_same_request_id(client):
    response = client.post("/api/chat", json={"messages": [{"role": "user", "content": "你好"}]})
    header = response.headers.get("x-request-id", "")
    body_id = ""
    for line in response.text.splitlines():
        if line.startswith("data: "):
            event = json.loads(line[6:])
            if event.get("requestId"):
                body_id = event["requestId"]
                break

    assert header.startswith("req_")
    assert body_id == header


def test_uncached_response_is_marked_as_a_miss(client):
    response = client.post("/api/chat", json={"messages": [{"role": "user", "content": "你好"}]})

    assert response.headers.get("x-cache") == "MISS"
