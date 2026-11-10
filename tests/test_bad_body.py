"""A malformed body must be answered in one sentence, not a pydantic dump."""

from __future__ import annotations

import importlib

import pytest

pytest.importorskip("fastapi", reason="web dependencies are not installed")


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.syspath_prepend("web")
    monkeypatch.setenv("DREAMAI_FREE_API_KEY", "test-key")
    from fastapi.testclient import TestClient

    return TestClient(importlib.import_module("app.main").app)


def test_an_empty_body_is_a_400_with_one_sentence(client):
    response = client.post("/api/chat", content=b"", headers={"Content-Type": "application/json"})

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "invalid_body"
    assert len(body["error"]) < 120


def test_a_wrong_typed_field_names_its_location(client):
    response = client.post(
        "/api/chat",
        json={"messages": "不是列表"},
    )

    assert response.status_code == 400
    body = response.json()
    assert "messages" in body["error"]
    # Pydantic's raw dictionaries must not reach the visitor.
    assert isinstance(body["error"], str)


def test_the_validation_dump_is_not_leaked(client):
    response = client.post("/api/chat", json={"messages": [{"role": "user"}]})

    assert response.status_code == 400
    assert "[" not in response.json()["error"]
