"""An error frame must be machine-readable without breaking old readers."""

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

from app.guard import CircuitBreaker  # noqa: E402
from app.llm import LLMError  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture()
def main_module(monkeypatch):
    main = importlib.import_module("app.main")
    monkeypatch.setattr(
        main, "settings", dataclasses.replace(main.settings, free_api_key="test-key")
    )
    main._breaker.reset()
    main._cache.clear()
    main.limiter._hits.clear()
    return main


def _errors(body: str) -> list[dict]:
    frames = [frame for frame in body.split("\n\n") if frame.startswith("event: error")]
    return [
        json.loads(next(line[6:] for line in frame.splitlines() if line.startswith("data:")))
        for frame in frames
    ]


def _chat(client) -> str:
    response = client.post("/api/chat", json={"messages": [{"role": "user", "content": "在吗"}]})
    assert response.status_code == 200
    return response.text


def test_an_open_breaker_says_it_is_retryable(main_module):
    breaker = CircuitBreaker(threshold=1, cooldown=60)
    breaker.record_failure()
    main_module._breaker = breaker

    errors = _errors(_chat(TestClient(main_module.app)))

    assert errors
    assert errors[0]["code"] == "breaker"
    assert errors[0]["retryable"] is True
    assert errors[0]["status"] is None
    assert "暂停" in errors[0]["message"], "the old sentence is still there"


def test_an_upstream_failure_carries_its_status(main_module, monkeypatch):
    async def failing_stream(*args, **kwargs):  # noqa: ANN002, ANN003
        raise LLMError("upstream busy", 503)
        yield  # pragma: no cover - makes this an async generator

    monkeypatch.setattr(main_module.llm, "stream_completion", failing_stream)
    monkeypatch.setattr(main_module.llm, "retry_delay", lambda *args: 0)

    errors = _errors(_chat(TestClient(main_module.app)))

    assert errors
    assert errors[0]["code"] == "upstream"
    assert errors[0]["status"] == 503
    assert errors[0]["retryable"] is True


def test_an_unexpected_exception_is_internal(main_module, monkeypatch):
    async def broken_stream(*args, **kwargs):  # noqa: ANN002, ANN003
        raise RuntimeError("unexpected")
        yield  # pragma: no cover

    monkeypatch.setattr(main_module.llm, "stream_completion", broken_stream)
    monkeypatch.setattr(main_module.llm, "retry_delay", lambda *args: 0)

    errors = _errors(_chat(TestClient(main_module.app)))

    assert errors[0]["code"] == "internal"
    assert errors[0]["retryable"] is False
    assert "一点意外" in errors[0]["message"]


def test_a_failed_upstream_is_not_reported_as_an_empty_success(main_module, monkeypatch):
    async def failing_stream(*args, **kwargs):  # noqa: ANN002, ANN003
        raise LLMError("upstream busy", 503)
        yield  # pragma: no cover

    monkeypatch.setattr(main_module.llm, "stream_completion", failing_stream)
    monkeypatch.setattr(main_module.llm, "retry_delay", lambda *args: 0)
    body = _chat(TestClient(main_module.app))

    assert "event: error" in body
    assert "event: done" not in body, "a clean done would hide the failure"
    assert "event: delta" not in body


def test_a_failed_upstream_counts_towards_the_breaker(main_module, monkeypatch):
    async def failing_stream(*args, **kwargs):  # noqa: ANN002, ANN003
        raise LLMError("upstream busy", 503)
        yield  # pragma: no cover

    monkeypatch.setattr(main_module.llm, "stream_completion", failing_stream)
    monkeypatch.setattr(main_module.llm, "retry_delay", lambda *args: 0)
    main_module._breaker.reset()

    _chat(TestClient(main_module.app))

    assert main_module._breaker.stats()["failures"] == 1
