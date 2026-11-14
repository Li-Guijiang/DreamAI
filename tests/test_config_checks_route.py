"""Startup findings must be visible on /api/health without blocking startup."""

from __future__ import annotations

import dataclasses
import importlib
import sys
from pathlib import Path

import pytest

pytest.importorskip("fastapi", reason="web dependencies are not installed")
WEB = str(Path(__file__).resolve().parent.parent / "web")
if WEB not in sys.path:
    sys.path.insert(0, WEB)

from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture()
def main_module(monkeypatch):
    main = importlib.import_module("app.main")
    monkeypatch.setattr(
        main, "settings", dataclasses.replace(main.settings, free_api_key="test-key")
    )
    return main


def test_a_clean_startup_publishes_an_empty_list(main_module, caplog):
    main_module._config_checks = []

    with caplog.at_level("INFO"):
        with TestClient(main_module.app) as client:
            assert client.get("/api/health").json()["configChecks"] == []

    assert "config checks: clean" in caplog.text


def test_a_warning_is_published_and_logged(main_module, monkeypatch, caplog):
    monkeypatch.setattr(
        main_module,
        "settings",
        dataclasses.replace(
            main_module.settings,
            free_api_key="test-key",
            fallback_base_url="https://example.test/v1",
        ),
    )

    with caplog.at_level("WARNING"):
        with TestClient(main_module.app) as client:
            checks = client.get("/api/health").json()["configChecks"]

    assert any(check["code"] == "fallback_partial" for check in checks)
    assert "config check fallback_partial" in caplog.text


def test_a_startup_warning_does_not_refuse_traffic(main_module, monkeypatch):
    monkeypatch.setattr(
        main_module,
        "settings",
        dataclasses.replace(main_module.settings, free_api_key="test-key", system_prompt=""),
    )

    with TestClient(main_module.app) as client:
        assert client.get("/api/health").json()["ok"] is True


def test_no_secret_reaches_the_published_findings(main_module, monkeypatch):
    monkeypatch.setattr(
        main_module,
        "settings",
        dataclasses.replace(
            main_module.settings,
            free_api_key="test-key",
            fallback_base_url="https://example.test/v1",
            fallback_api_key="SUPER-SECRET-KEY",
        ),
    )

    with TestClient(main_module.app) as client:
        payload = str(client.get("/api/health").json()["configChecks"])

    assert "SUPER-SECRET-KEY" not in payload
    assert "fallback_partial" in payload


def test_every_finding_has_the_same_three_fields(main_module, monkeypatch):
    monkeypatch.setattr(
        main_module,
        "settings",
        dataclasses.replace(main_module.settings, cache_ttl=0, system_prompt=""),
    )

    with TestClient(main_module.app) as client:
        checks = client.get("/api/health").json()["configChecks"]

    assert checks
    assert all(set(check) == {"code", "severity", "message"} for check in checks)
