"""Environment switches must read on/off values without guessing."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

WEB = str(Path(__file__).resolve().parent.parent / "web")
if WEB not in sys.path:
    sys.path.insert(0, WEB)

from app.config import _env_bool, load_settings  # noqa: E402


def test_the_on_spellings(monkeypatch):
    for value in ("1", "true", "YES", "on"):
        monkeypatch.setenv("PROBE_FLAG", value)
        assert _env_bool("PROBE_FLAG", False) is True


def test_the_off_spellings(monkeypatch):
    for value in ("0", "false", "NO", "off"):
        monkeypatch.setenv("PROBE_FLAG", value)
        assert _env_bool("PROBE_FLAG", True) is False


def test_a_garbled_value_keeps_the_default(monkeypatch):
    monkeypatch.setenv("PROBE_FLAG", "maybe")
    assert _env_bool("PROBE_FLAG", True) is True
    assert _env_bool("PROBE_FLAG", False) is False


def test_the_stream_usage_switch_reaches_settings(monkeypatch):
    monkeypatch.setenv("DREAMAI_STREAM_USAGE", "0")
    assert load_settings().stream_usage is False

    monkeypatch.delenv("DREAMAI_STREAM_USAGE")
    assert load_settings().stream_usage is True


def test_price_overrides_are_read_from_the_environment(monkeypatch):
    monkeypatch.setenv("DREAMAI_PRICE_OVERRIDES", "brand-new-model=1,3")

    assert load_settings().price_overrides == "brand-new-model=1,3"


def test_the_prompt_cache_switch_is_on_by_default(monkeypatch):
    assert load_settings().prompt_cache is True

    monkeypatch.setenv("DREAMAI_PROMPT_CACHE", "0")
    assert load_settings().prompt_cache is False


def test_the_usage_snapshot_switch_is_off_by_default(monkeypatch):
    monkeypatch.delenv("DREAMAI_USAGE_STATE", raising=False)

    assert load_settings().usage_state == ""

    monkeypatch.setenv("DREAMAI_USAGE_STATE", " /var/lib/dreamai/usage.json ")
    assert load_settings().usage_state == "/var/lib/dreamai/usage.json"


def test_the_cache_byte_budget_is_four_mib_by_default(monkeypatch):
    monkeypatch.delenv("DREAMAI_CACHE_MAX_BYTES", raising=False)

    assert load_settings().cache_max_bytes == 4 * 1024 * 1024


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("0", 0),
        ("1024", 1024),
        ("-5", 0),
        ("999999999", 64 * 1024 * 1024),
        ("garbage", 4 * 1024 * 1024),
    ],
)
def test_the_cache_byte_budget_is_clamped(monkeypatch, raw, expected):
    monkeypatch.setenv("DREAMAI_CACHE_MAX_BYTES", raw)

    assert load_settings().cache_max_bytes == expected


def test_the_parsed_budget_reaches_a_cache_instance(monkeypatch):
    from app.cache import ResponseCache

    monkeypatch.setenv("DREAMAI_CACHE_MAX_BYTES", "2048")

    assert ResponseCache(max_bytes=load_settings().cache_max_bytes).stats()["maxBytes"] == 2048
