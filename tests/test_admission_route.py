"""A request that cannot get a concurrency slot must fail fast and honestly."""

from __future__ import annotations

import asyncio
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

from fastapi.testclient import TestClient  # noqa: E402

BODY = {"messages": [{"role": "user", "content": "在吗"}]}


class BlockedSemaphore:
    """A slot that never frees, so wait_for must decide the outcome."""

    async def acquire(self) -> None:
        await asyncio.sleep(10)

    def release(self) -> None:
        pass


@pytest.fixture()
def harness(monkeypatch):
    main = importlib.import_module("app.main")
    monkeypatch.setattr(
        main,
        "settings",
        dataclasses.replace(main.settings, free_api_key="test-key", admission_timeout=0.01),
    )
    monkeypatch.setattr(
        main, "_stats", __import__("app.stats", fromlist=["UsageStats"]).UsageStats()
    )
    main._breaker.reset()
    main._cache.clear()
    main.limiter._hits.clear()

    async def fake_stream(*args, **kwargs):  # noqa: ANN002, ANN003
        yield "content", "好"

    monkeypatch.setattr(main.llm, "stream_completion", fake_stream)
    return main, TestClient(main.app)


def _errors(body: str) -> list[dict]:
    return [
        json.loads(line[6:])
        for frame in body.split("\n\n")
        if frame.startswith("event: error")
        for line in frame.splitlines()
        if line.startswith("data:")
    ]


def test_a_blocked_admission_yields_a_machine_readable_error(harness, monkeypatch):
    main, client = harness
    monkeypatch.setattr(main, "_semaphore", BlockedSemaphore())

    response = client.post("/api/chat", json=BODY)

    assert response.status_code == 200
    errors = _errors(response.text)
    assert errors[0]["code"] == "concurrency_limit"
    assert errors[0]["retryable"] is True
    assert "event: done" not in response.text


def test_a_refused_admission_counts_as_blocked(harness, monkeypatch):
    main, client = harness
    monkeypatch.setattr(main, "_semaphore", BlockedSemaphore())

    client.post("/api/chat", json=BODY)

    snapshot = main._stats.snapshot()
    assert snapshot["admissionTimeouts"] == 1
    assert snapshot["blocked"] == 1
    assert snapshot["byModel"] == {}


def test_the_breaker_is_not_blamed_for_queueing(harness, monkeypatch):
    main, client = harness
    monkeypatch.setattr(main, "_semaphore", BlockedSemaphore())
    main._breaker.reset()

    client.post("/api/chat", json=BODY)

    assert main._breaker.stats()["failures"] == 0
    assert main._breaker.stats()["state"] == "closed"


def test_a_normal_turn_records_its_wait(harness):
    main, client = harness

    response = client.post("/api/chat", json=BODY)

    assert response.status_code == 200
    assert main._stats.snapshot()["admissionWaitSamples"] == 1
    assert main._stats.snapshot()["admissionTimeouts"] == 0


def test_a_normal_turn_still_ends_with_done(harness):
    _, client = harness

    response = client.post("/api/chat", json=BODY)

    assert "event: done" in response.text
    assert "event: error" not in response.text
