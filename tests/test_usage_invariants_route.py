"""The published snapshot must reconcile, not just the in-process object."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest.importorskip("fastapi", reason="web dependencies are not installed")
WEB = str(Path(__file__).resolve().parent.parent / "web")
if WEB not in sys.path:
    sys.path.insert(0, WEB)

from fastapi.testclient import TestClient  # noqa: E402


def test_the_usage_endpoint_reconciles_its_totals():
    main = __import__("app.main", fromlist=["app"])
    snapshot = TestClient(main.app).get("/api/usage").json()
    slots = snapshot["byModel"]

    assert snapshot["requests"] == sum(s["requests"] for s in slots.values()) + snapshot["blocked"]
    assert snapshot["failures"] == sum(s["failures"] for s in slots.values()) + snapshot["blocked"]
    assert snapshot["promptTokens"] == sum(s["promptTokens"] for s in slots.values())
    assert snapshot["truncated"] == sum(s["truncated"] for s in slots.values())
    assert len(slots) <= main.settings.max_tracked_models


def test_other_is_a_reserved_bucket():
    main = __import__("app.main", fromlist=["app"])
    slots = TestClient(main.app).get("/api/usage").json()["byModel"]

    if "other" in slots:
        assert set(slots["other"]) >= {
            "requests",
            "failures",
            "truncated",
            "promptTokens",
            "completionTokens",
            "cachedTokens",
            "costUsd",
        }
