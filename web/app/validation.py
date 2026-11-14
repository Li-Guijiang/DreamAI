"""Startup checks for operator-supplied configuration.

Environment variables are the only deployment interface this service has, and a
typo used to be discovered at runtime: a half-configured fallback sits idle
until the primary fails, and a stale price correction is skipped without a word.
This module turns those silent outcomes into a short list of named findings.

Two rules matter:

* Nothing here blocks startup. A warning is information, not a refusal to serve.
* No secret is ever included. Findings quote a model name, a number, or a code -
  never a key, a URL with credentials, or the system prompt itself.
"""

from __future__ import annotations

from dataclasses import dataclass

from .pricing import invalid_price_overrides

WARNING = "warning"
INFO = "info"


@dataclass(frozen=True)
class Check:
    code: str
    severity: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "severity": self.severity, "message": self.message}


def check_settings(settings) -> list[Check]:
    """Named findings about a configuration, ordered from most to least severe."""
    checks: list[Check] = []

    fallback = (
        settings.fallback_base_url,
        settings.fallback_api_key,
        settings.fallback_model,
    )
    if any(fallback) and not all(fallback):
        checks.append(
            Check(
                "fallback_partial",
                WARNING,
                "Fallback is only partly configured (base URL, key and model are all "
                "required); it will not be used when the primary fails.",
            )
        )

    if settings.breaker_cooldown * 10 < settings.upstream_read_timeout:
        checks.append(
            Check(
                "cooldown_shorter_than_timeout",
                WARNING,
                f"Breaker cooldown ({settings.breaker_cooldown:g}s) is far shorter "
                f"than one read timeout ({settings.upstream_read_timeout:g}s); probes "
                "may go out while earlier requests are still waiting.",
            )
        )

    if 0 < settings.daily_limit < settings.rate_limit:
        checks.append(
            Check(
                "daily_below_window",
                WARNING,
                f"Daily limit ({settings.daily_limit}) is below one rate-limit window "
                f"({settings.rate_limit}); the daily cap will always be reached first.",
            )
        )

    if not settings.system_prompt.strip():
        checks.append(
            Check(
                "system_prompt_empty",
                WARNING,
                "DREAMAI_SYSTEM_PROMPT is empty; identity and safety rules are gone.",
            )
        )

    if settings.max_concurrency > settings.rate_limit:
        checks.append(
            Check(
                "max_concurrency_over_limit",
                WARNING,
                f"max_concurrency ({settings.max_concurrency}) exceeds the rate limit "
                f"({settings.rate_limit}); some concurrent requests cannot be admitted.",
            )
        )

    if settings.cache_ttl > 0 and settings.cache_max_items < 8:
        checks.append(
            Check(
                "cache_capacity_low",
                WARNING,
                f"Cache holds only {settings.cache_max_items} answers; hit rate will "
                "be low under normal traffic.",
            )
        )

    if settings.rate_window < 60:
        checks.append(
            Check(
                "rate_window_short",
                WARNING,
                f"Rate window ({settings.rate_window}s) is under a minute; clients "
                "will see a burst limit rather than a sustained one.",
            )
        )

    ignored = invalid_price_overrides(settings.price_overrides)
    if ignored:
        checks.append(
            Check(
                "price_overrides_invalid",
                WARNING,
                "Price overrides ignored: " + ", ".join(ignored[:3]) + ".",
            )
        )

    if not settings.stream_usage:
        checks.append(
            Check(
                "stream_usage_off",
                INFO,
                "Usage chunks are not requested; token and cost totals will be empty.",
            )
        )
    if settings.cache_ttl <= 0:
        checks.append(Check("cache_off", INFO, "Response cache is disabled."))
    if settings.usage_state:
        checks.append(
            Check("usage_state_on", INFO, "Usage counters are persisted across restarts.")
        )

    return checks


def format_checks(checks: list[Check]) -> str:
    """One line for the startup log."""
    warnings = sum(1 for check in checks if check.severity == WARNING)
    infos = len(checks) - warnings
    if not checks:
        return "config checks: clean"
    return f"config checks: {warnings} warning(s), {infos} info"
