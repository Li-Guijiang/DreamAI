"""Startup checks must be named, quiet by default and free of secrets."""

from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

import pytest

WEB = str(Path(__file__).resolve().parent.parent / "web")
if WEB not in sys.path:
    sys.path.insert(0, WEB)

from app.config import load_settings  # noqa: E402
from app.validation import INFO, WARNING, check_settings, format_checks  # noqa: E402


def settings_with(**overrides):
    return dataclasses.replace(load_settings(), **overrides)


def codes(**overrides) -> list[str]:
    return [check.code for check in check_settings(settings_with(**overrides))]


def test_a_default_configuration_has_no_findings(monkeypatch):
    monkeypatch.delenv("DREAMAI_PRICE_OVERRIDES", raising=False)

    assert check_settings(load_settings()) == []


def test_a_partly_configured_fallback_is_reported():
    found = codes(fallback_base_url="https://example.test/v1")

    assert "fallback_partial" in found


def test_a_complete_fallback_is_not_reported():
    found = codes(
        fallback_base_url="https://example.test/v1",
        fallback_api_key="k" * 40,
        fallback_model="m",
    )

    assert "fallback_partial" not in found


def test_findings_never_contain_a_secret():
    checks = check_settings(
        settings_with(
            fallback_base_url="https://example.test/v1", fallback_api_key="SUPER-SECRET-KEY"
        )
    )

    assert all("SUPER-SECRET-KEY" not in check.message for check in checks)


def test_an_invalid_base_url_is_reported():
    assert "base_url_invalid" in codes(byok_base_url="api.example.com/v1")


def test_an_invalid_model_id_is_reported():
    assert "model_id_invalid" in codes(free_model="bad model")


def test_valid_model_ids_are_not_reported():
    assert "model_id_invalid" not in codes()


def test_a_partly_broken_key_url_is_reported():
    assert "base_url_invalid" in codes(free_key_url="https://")


def test_valid_urls_are_not_reported():
    assert "base_url_invalid" not in codes()


def test_url_findings_do_not_echo_a_credential():
    checks = check_settings(settings_with(free_base_url="https://u:SUPER-SECRET@host.test/v1"))
    finding = next(check for check in checks if check.code == "base_url_invalid")

    assert "SUPER-SECRET" not in finding.message


def test_a_cooldown_far_shorter_than_one_timeout_is_reported():
    assert "cooldown_shorter_than_timeout" in codes(
        breaker_cooldown=10.0, upstream_read_timeout=900.0
    )


def test_the_default_cooldown_is_not_reported():
    assert "cooldown_shorter_than_timeout" not in codes()


def test_a_daily_limit_below_one_window_is_reported():
    assert "daily_below_window" in codes(daily_limit=5, rate_limit=30)


def test_an_unlimited_daily_budget_is_not_reported():
    assert "daily_below_window" not in codes(daily_limit=0, rate_limit=30)


def test_an_empty_system_prompt_is_reported():
    assert "system_prompt_empty" in codes(system_prompt="   ")


def test_an_overlong_system_prompt_is_reported():
    assert "system_prompt_long" in codes(system_prompt="x" * 8001)


def test_a_normal_system_prompt_is_not_reported():
    assert "system_prompt_long" not in codes()


def test_an_empty_prompt_is_not_also_reported_as_long():
    assert "system_prompt_long" not in codes(system_prompt="")


def test_concurrency_above_the_rate_limit_is_reported():
    assert "max_concurrency_over_limit" in codes(max_concurrency=50, rate_limit=30)


def test_a_tiny_cache_is_reported():
    assert "cache_capacity_low" in codes(cache_max_items=2)


def test_a_tiny_cache_is_not_reported_when_the_cache_is_off():
    assert "cache_capacity_low" not in codes(cache_max_items=2, cache_ttl=0)


def test_a_tiny_byte_budget_is_reported():
    assert "cache_bytes_small" in codes(cache_max_bytes=1024)


def test_a_disabled_byte_budget_is_not_reported():
    assert "cache_bytes_small" not in codes(cache_max_bytes=0)


def test_a_long_heartbeat_is_reported():
    assert "heartbeat_long" in codes(heartbeat_seconds=120.0)


def test_the_default_heartbeat_is_not_reported():
    assert "heartbeat_long" not in codes()


def test_a_very_short_admission_timeout_is_reported():
    assert "admission_timeout_short" in codes(admission_timeout=0.2)


def test_an_unlimited_admission_wait_is_not_reported():
    assert "admission_timeout_short" not in codes(admission_timeout=0)


def test_the_default_admission_timeout_is_not_reported():
    assert "admission_timeout_short" not in codes()


def test_a_tiny_model_table_is_reported():
    assert "tracked_models_low" in codes(max_tracked_models=2)


def test_the_default_model_table_is_not_reported():
    assert "tracked_models_low" not in codes()


def test_a_tiny_byte_budget_does_not_matter_when_the_cache_is_off():
    assert "cache_bytes_small" not in codes(cache_max_bytes=1024, cache_ttl=0)


def test_a_short_rate_window_is_reported():
    assert "rate_window_short" in codes(rate_window=30)


def test_invalid_price_overrides_are_reported():
    assert "price_overrides_invalid" in codes(price_overrides="new-model=1;broken")


def test_valid_price_overrides_are_not_reported():
    assert "price_overrides_invalid" not in codes(price_overrides="new-model=1,2,0.5;gpt-4o=2.5,10")


def test_a_broken_price_table_is_reported(monkeypatch):
    from app import pricing

    monkeypatch.setattr(pricing, "CACHE_PRICES", {**pricing.CACHE_PRICES, "ghost": 0.5})

    assert "price_table_inconsistent" in codes()


def test_a_clean_price_table_is_not_reported(monkeypatch):
    from app import pricing

    monkeypatch.setattr(pricing, "PRICES", dict(pricing.PRICES))
    monkeypatch.setattr(pricing, "CACHE_PRICES", dict(pricing.CACHE_PRICES))

    assert "price_table_inconsistent" not in codes()


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"stream_usage": False}, "stream_usage_off"),
        ({"cache_ttl": 0}, "cache_off"),
        ({"usage_state": "/var/lib/dreamai/usage.json"}, "usage_state_on"),
    ],
)
def test_opt_in_and_opt_out_states_are_informational(overrides, expected):
    checks = {check.code: check for check in check_settings(settings_with(**overrides))}

    assert checks[expected].severity == INFO


def test_warnings_come_before_informational_findings():
    checks = check_settings(settings_with(cache_ttl=0, system_prompt=""))

    assert [check.severity for check in checks] == [WARNING, INFO]


def test_the_log_line_counts_by_severity():
    checks = check_settings(settings_with(cache_ttl=0, system_prompt=""))

    assert format_checks(checks) == "config checks: 1 warning(s), 1 info"


def test_a_clean_run_says_so():
    assert format_checks([]) == "config checks: clean"


def test_every_finding_is_serialisable():
    checks = check_settings(settings_with(fallback_model="m", system_prompt=""))

    assert all(set(check.as_dict()) == {"code", "severity", "message"} for check in checks)
