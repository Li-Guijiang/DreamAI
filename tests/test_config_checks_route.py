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


def test_a_broken_price_table_is_published_at_startup(main_module, monkeypatch):
    from app import pricing

    monkeypatch.setattr(pricing, "CACHE_PRICES", {**pricing.CACHE_PRICES, "ghost": 0.5})

    with TestClient(main_module.app) as client:
        checks = client.get("/api/health").json()["configChecks"]

    assert any(check["code"] == "price_table_inconsistent" for check in checks)


def test_a_bad_url_is_published_without_echoing_the_value(main_module, monkeypatch):
    monkeypatch.setattr(
        main_module,
        "settings",
        dataclasses.replace(
            main_module.settings,
            free_api_key="test-key",
            byok_base_url="https://user:SUPER-SECRET@host.test/v1",
        ),
    )

    with TestClient(main_module.app) as client:
        checks = client.get("/api/health").json()["configChecks"]

    assert any(check["code"] == "base_url_invalid" for check in checks)
    assert "SUPER-SECRET" not in str(checks)


def test_clamped_configuration_names_are_published(main_module, monkeypatch):
    monkeypatch.setattr(
        main_module,
        "settings",
        dataclasses.replace(main_module.settings, clamped_fields=("temperature",)),
    )

    with TestClient(main_module.app) as client:
        assert client.get("/api/health").json()["configClamped"] == ["temperature"]


def test_an_impossible_model_id_is_published_at_startup(main_module, monkeypatch):
    monkeypatch.setattr(
        main_module,
        "settings",
        dataclasses.replace(main_module.settings, free_api_key="test-key", free_model="bad model"),
    )

    with TestClient(main_module.app) as client:
        checks = client.get("/api/health").json()["configChecks"]

    assert any(check["code"] == "model_id_invalid" for check in checks)
