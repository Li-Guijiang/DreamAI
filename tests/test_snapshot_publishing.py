"""The status page must say whether counters are actually being saved."""

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

from fastapi.testclient import TestClient  # noqa: E402


def load_main(monkeypatch, tmp_path: Path, interval: float = 0.0):
    main = importlib.import_module("app.main")
    monkeypatch.setattr(
        main,
        "settings",
        dataclasses.replace(
            main.settings,
            usage_state=str(tmp_path / "usage.json"),
            usage_save_interval=interval,
        ),
    )
    return main


def test_a_disabled_snapshot_reports_disabled(monkeypatch):
    main = importlib.import_module("app.main")
    monkeypatch.setattr(main, "settings", dataclasses.replace(main.settings, usage_state=""))

    with TestClient(main.app) as client:
        state = client.get("/api/usage").json()["usageState"]

    assert state["enabled"] is False
    assert state["loadStatus"] == "disabled"


def test_an_absent_snapshot_reports_absent_then_saved(monkeypatch, tmp_path):
    main = load_main(monkeypatch, tmp_path)

    with TestClient(main.app) as client:
        state = client.get("/api/usage").json()["usageState"]

    assert state["loadStatus"] == "absent"
    # The periodic flush may not have fired yet; shutdown always writes.
    state = main._snapshot_state
    assert state["lastSaveAt"] is not None
    assert state["saveFailures"] == 0
    assert (tmp_path / "usage.json").is_file()


def test_a_corrupt_snapshot_is_reported(monkeypatch, tmp_path):
    (tmp_path / "usage.json").write_text("{broken", encoding="utf-8")
    main = load_main(monkeypatch, tmp_path)

    with TestClient(main.app) as client:
        state = client.get("/api/usage").json()["usageState"]

    assert state["loadStatus"] == "corrupt"


def test_a_valid_snapshot_is_reported_as_restored(monkeypatch, tmp_path):
    from app.stats import UsageStats

    path = tmp_path / "usage.json"
    counters = UsageStats()
    counters.record_turn("m")
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "savedAt": 1.0,
                "counters": counters.export_counters(),
            }
        ),
        encoding="utf-8",
    )
    main = load_main(monkeypatch, tmp_path)

    with TestClient(main.app) as client:
        state = client.get("/api/usage").json()["usageState"]

    assert state["loadStatus"] == "restored"


def test_a_write_failure_is_counted(monkeypatch, tmp_path):
    main = load_main(monkeypatch, tmp_path)

    def failing(*args, **kwargs):
        return False

    monkeypatch.setattr(main, "save_snapshot", failing)
    assert main.persist_snapshot() is False

    with TestClient(main.app) as client:
        state = client.get("/api/usage").json()["usageState"]

    assert state["saveFailures"] >= 1


def test_the_periodic_flush_writes_without_a_shutdown(monkeypatch, tmp_path):
    main = load_main(monkeypatch, tmp_path, interval=0.01)

    with TestClient(main.app) as client:
        deadline = time.monotonic() + 2
        state = client.get("/api/usage").json()["usageState"]
        while state["lastSaveAt"] is None and time.monotonic() < deadline:
            time.sleep(0.02)
            state = client.get("/api/usage").json()["usageState"]

    assert state["lastSaveAt"] is not None
    assert (tmp_path / "usage.json").is_file()
