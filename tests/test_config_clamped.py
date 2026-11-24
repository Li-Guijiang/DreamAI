"""Silently corrected configuration should still be visible to the operator."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))

from app.config import load_settings  # noqa: E402


def clean(monkeypatch, names: tuple[str, ...]) -> None:
    for name in names:
        monkeypatch.delenv(name, raising=False)


def test_a_clean_environment_reports_no_clamping(monkeypatch):
    clean(
        monkeypatch,
        (
            "DREAMAI_TEMPERATURE",
            "DREAMAI_CACHE_TTL_JITTER",
            "DREAMAI_HEARTBEAT_SECONDS",
            "DREAMAI_ADMISSION_TIMEOUT",
            "DREAMAI_STREAM_QUEUE_SIZE",
            "DREAMAI_USAGE_SAVE_INTERVAL",
        ),
    )

    assert load_settings().clamped_fields == ()


def test_an_out_of_range_temperature_is_recorded(monkeypatch):
    clean(monkeypatch, ("DREAMAI_CACHE_TTL_JITTER", "DREAMAI_HEARTBEAT_SECONDS"))
    monkeypatch.setenv("DREAMAI_TEMPERATURE", "9")

    settings = load_settings()
    assert settings.temperature == 2.0
    assert "temperature" in settings.clamped_fields


def test_low_heartbeat_is_recorded(monkeypatch):
    clean(monkeypatch, ("DREAMAI_TEMPERATURE", "DREAMAI_CACHE_TTL_JITTER"))
    monkeypatch.setenv("DREAMAI_HEARTBEAT_SECONDS", "0")

    settings = load_settings()
    assert settings.heartbeat_seconds == 1.0
    assert "heartbeatSeconds" in settings.clamped_fields


def test_multiple_corrections_are_recorded_together(monkeypatch):
    clean(monkeypatch, ("DREAMAI_TEMPERATURE",))
    monkeypatch.setenv("DREAMAI_TEMPERATURE", "-5")
    monkeypatch.setenv("DREAMAI_CACHE_TTL_JITTER", "9")
    monkeypatch.setenv("DREAMAI_ADMISSION_TIMEOUT", "999")
    monkeypatch.setenv("DREAMAI_STREAM_QUEUE_SIZE", "999")

    fields = load_settings().clamped_fields

    assert {"temperature", "cacheTtlJitter", "admissionTimeout", "streamQueueSize"} <= set(fields)


def test_the_snapshot_interval_above_its_ceiling_is_recorded(monkeypatch):
    clean(monkeypatch, ("DREAMAI_TEMPERATURE", "DREAMAI_CACHE_TTL_JITTER"))
    monkeypatch.setenv("DREAMAI_USAGE_SAVE_INTERVAL", "99999")

    settings = load_settings()
    assert settings.usage_save_interval == 3600.0
    assert "usageSaveInterval" in settings.clamped_fields


def test_upper_and_lower_bounds_both_count_as_clamping(monkeypatch):
    clean(monkeypatch, ("DREAMAI_TEMPERATURE", "DREAMAI_CACHE_TTL_JITTER"))
    monkeypatch.setenv("DREAMAI_TEMPERATURE", "9")
    monkeypatch.delenv("DREAMAI_TEMPERATURE")
    monkeypatch.setenv("DREAMAI_TEMPERATURE", "-1")

    settings = load_settings()
    assert settings.temperature == 0.0
    assert "temperature" in settings.clamped_fields


def test_valid_values_are_not_recorded(monkeypatch):
    clean(monkeypatch, ("DREAMAI_TEMPERATURE", "DREAMAI_HEARTBEAT_SECONDS"))
    monkeypatch.setenv("DREAMAI_CACHE_TTL_JITTER", "0.2")
    monkeypatch.setenv("DREAMAI_ADMISSION_TIMEOUT", "10")

    assert "cacheTtlJitter" not in load_settings().clamped_fields


def test_clamped_names_never_reach_public_config(monkeypatch):
    clean(monkeypatch, ("DREAMAI_CACHE_TTL_JITTER",))
    monkeypatch.setenv("DREAMAI_TEMPERATURE", "9")

    settings = load_settings()

    assert "clampedFields" not in settings.public_config()
    assert "clamped_fields" not in settings.public_config()
