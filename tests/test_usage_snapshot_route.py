"""A restart must not silently reset the usage counters to zero."""

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

from app.state_store import load_snapshot, save_snapshot  # noqa: E402
from app.stats import UsageStats  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture()
def harness(monkeypatch, tmp_path):
    main = importlib.import_module("app.main")
    path = tmp_path / "usage.json"
    monkeypatch.setattr(
        main,
        "settings",
        dataclasses.replace(main.settings, free_api_key="test-key", usage_state=str(path)),
    )
    monkeypatch.setattr(main, "_stats", UsageStats(started_at=main.STARTED_AT))
    # Two turns instead of twenty-five, so the test does not depend on the
    # production cadence to exercise the same code path.
    monkeypatch.setattr(main, "USAGE_SAVE_EVERY", 2)
    main._breaker.reset()
    main._cache.clear()
    main.limiter._hits.clear()

    async def fake_stream(*args, **kwargs):  # noqa: ANN002, ANN003
        yield "content", "好"
        yield "usage", json.dumps({"prompt_tokens": 10, "completion_tokens": 5})

    monkeypatch.setattr(main.llm, "stream_completion", fake_stream)
    return main, TestClient(main.app), path


def _chat(client) -> None:
    response = client.post("/api/chat", json={"messages": [{"role": "user", "content": "在吗"}]})
    assert response.status_code == 200, response.text


def test_counters_are_written_every_n_turns(harness):
    main, client, path = harness

    _chat(client)
    assert not path.exists(), "one turn is not yet a checkpoint"
    _chat(client)

    assert path.exists()
    assert load_snapshot(path)["requests"] == 2
    assert load_snapshot(path)["prompt_tokens"] == 20


def test_the_file_can_rebuild_the_same_snapshot(harness):
    main, client, path = harness
    _chat(client)
    _chat(client)

    restored = UsageStats(started_at=9999.0)
    assert restored.import_counters(load_snapshot(path)) is True

    assert restored.snapshot() == main._stats.snapshot()
    assert restored.started_at == 9999.0


def test_the_endpoint_reports_whether_persistence_is_on(harness):
    _, client, _ = harness

    assert client.get("/api/usage").json()["usagePersisted"] is True


def test_the_switch_is_off_by_default(monkeypatch, harness):
    main, _, path = harness
    monkeypatch.setattr(main, "settings", dataclasses.replace(main.settings, usage_state=""))

    with TestClient(main.app) as client:
        _chat(client)
        assert client.get("/api/usage").json()["usagePersisted"] is False

    assert not path.exists()


def test_startup_restores_a_previous_process(harness, caplog, monkeypatch):
    main, _, path = harness
    save_snapshot(path, _busy_counters())
    fresh = UsageStats(started_at=main.STARTED_AT)
    monkeypatch.setattr(main, "_stats", fresh)

    with caplog.at_level("INFO"):
        with TestClient(main.app):
            pass

    assert fresh.snapshot()["requests"] == 9
    assert "usage snapshot restored" in caplog.text
    # Shutdown writes the counters back, so a second restart sees them too.
    assert load_snapshot(path)["requests"] == 9


def test_a_corrupt_snapshot_is_rejected_without_stopping_the_service(harness, caplog):
    main, _, path = harness
    path.write_text("not json", encoding="utf-8")

    with caplog.at_level("INFO"):
        with TestClient(main.app) as client:
            assert client.get("/api/usage").status_code == 200

    assert "usage snapshot: none" in caplog.text


def _busy_counters() -> dict:
    stats = UsageStats()
    stats.record_turn("m", tier="deep", intent="chat", provider="free")
    stats.record_usage("m", 100, 20, 0.001)
    counters = stats.export_counters()
    counters["requests"] = 9
    return counters
