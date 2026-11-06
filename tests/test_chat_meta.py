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
    monkeypatch.syspath_prepend("web")
    monkeypatch.setenv("DREAMAI_FREE_API_KEY", "test-key")
    import importlib

    main = importlib.import_module("app.main")
    importlib.reload(main)
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
