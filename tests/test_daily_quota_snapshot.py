"""A restart must not hand out a second daily allowance."""

from __future__ import annotations

import dataclasses
import importlib
import json
import sys
import time
from pathlib import Path

import pytest

pytest.importorskip("fastapi", reason="web dependencies are not installed")
WEB = str(Path(__file__).resolve().parent.parent / "web")
if WEB not in sys.path:
    sys.path.insert(0, WEB)

from app.state_store import load_snapshot, save_snapshot  # noqa: E402
from app.stats import UsageStats  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

TODAY = time.strftime("%Y-%m-%d")


@pytest.fixture()
def harness(monkeypatch, tmp_path):
    main = importlib.import_module("app.main")
    path = tmp_path / "usage.json"
    monkeypatch.setattr(
        main,
        "settings",
        dataclasses.replace(
            main.settings,
            free_api_key="test-key",
            usage_state=str(path),
            daily_limit=5,
        ),
    )
    monkeypatch.setattr(main, "_daily_state", {"date": TODAY, "count": 0})
    monkeypatch.setattr(main, "_stats", UsageStats(started_at=main.STARTED_AT))
    main._breaker.reset()
    main._cache.clear()
    main.limiter._hits.clear()

    async def fake_stream(*args, **kwargs):  # noqa: ANN002, ANN003
        yield "content", "好"
        yield "usage", json.dumps({"prompt_tokens": 5, "completion_tokens": 2})

    monkeypatch.setattr(main.llm, "stream_completion", fake_stream)
    return main, TestClient(main.app), path


def _chat(client) -> None:
    response = client.post("/api/chat", json={"messages": [{"role": "user", "content": "在吗"}]})
    assert response.status_code == 200, response.text


def test_a_free_turn_actually_consumes_the_quota(harness):
    main, client, _ = harness

    _chat(client)
    _chat(client)

    assert main._daily_state["count"] == 2
    assert client.get("/api/usage").json()["daily"]["count"] == 2


def test_reaching_the_limit_refuses_the_next_free_turn(harness, monkeypatch):
    main, client, _ = harness
    monkeypatch.setattr(main, "settings", dataclasses.replace(main.settings, daily_limit=1))

    assert (
        client.post(
            "/api/chat", json={"messages": [{"role": "user", "content": "在吗"}]}
        ).status_code
        == 200
    )
    refused = client.post("/api/chat", json={"messages": [{"role": "user", "content": "还在吗"}]})

    assert refused.status_code == 429
    assert refused.json()["code"] == "daily_limit"
    assert main._daily_state["count"] == 1


def test_the_snapshot_carries_the_daily_quota(harness):
    main, client, _ = harness
    _chat(client)
    _chat(client)

    payload = main.snapshot_payload()

    assert payload["daily"] == {"date": TODAY, "count": 2}
    assert payload["requests"] == 2


def test_a_same_day_snapshot_restores_the_used_quota(harness):
    main, _, _ = harness

    assert main.restore_daily_quota({"daily": {"date": TODAY, "count": 4}}) is True
    assert main._daily_state["count"] == 4


def test_a_snapshot_from_another_day_is_ignored(harness):
    main, _, _ = harness

    assert main.restore_daily_quota({"daily": {"date": "2020-01-01", "count": 99}}) is False
    assert main._daily_state["count"] == 0


@pytest.mark.parametrize(
    "daily",
    [
        None,
        [],
        {},
        {"date": TODAY},
        {"date": TODAY, "count": -1},
        {"date": TODAY, "count": True},
        {"date": TODAY, "count": "4"},
        {"date": TODAY, "count": 1.5},
        {"date": 123, "count": 2},
    ],
)
def test_a_malformed_daily_entry_is_ignored(harness, daily):
    main, _, _ = harness

    assert main.restore_daily_quota({"daily": daily} if daily is not None else {}) is False
    assert main._daily_state["count"] == 0


def test_an_edited_count_cannot_exceed_the_configured_limit(harness):
    main, _, _ = harness

    assert main.restore_daily_quota({"daily": {"date": TODAY, "count": 10_000}}) is True
    assert main._daily_state["count"] == 5


def test_an_unlimited_daily_budget_restores_no_count(harness, monkeypatch):
    main, _, _ = harness
    monkeypatch.setattr(main, "settings", dataclasses.replace(main.settings, daily_limit=0))

    assert main.restore_daily_quota({"daily": {"date": TODAY, "count": 999}}) is True
    assert main._daily_state["count"] == 0


def test_a_restart_through_the_lifespan_keeps_the_quota(harness, monkeypatch):
    main, client, path = harness
    for _ in range(3):
        _chat(client)
    assert main._daily_state["count"] == 3
    assert save_snapshot(path, main.snapshot_payload()) is True

    # Simulate a fresh process: counters and quota start empty, the file is read
    # through the real startup path rather than by calling the helper directly.
    monkeypatch.setattr(main, "_daily_state", {"date": TODAY, "count": 0})
    monkeypatch.setattr(main, "_stats", UsageStats(started_at=main.STARTED_AT))
    with TestClient(main.app):
        pass

    assert main._daily_state["count"] == 3
    assert main._stats.snapshot()["requests"] == 3
    assert load_snapshot(path)["daily"]["count"] == 3
