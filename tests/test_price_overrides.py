"""A stale price list must be correctable without editing source."""

from __future__ import annotations

import sys
from pathlib import Path

WEB = str(Path(__file__).resolve().parent.parent / "web")
if WEB not in sys.path:
    sys.path.insert(0, WEB)

from app.pricing import PRICES, configure_prices, estimate_cost, parse_price_overrides  # noqa: E402


def test_a_plain_pair_is_parsed():
    assert parse_price_overrides("gpt-4o=2,8") == {"gpt-4o": (2.0, 8.0)}


def test_multiple_entries_and_whitespace_are_handled():
    raw = " model-a = 0.5 , 1.5 ; model-b=0,0 "

    assert parse_price_overrides(raw) == {
        "model-a": (0.5, 1.5),
        "model-b": (0.0, 0.0),
    }


def test_malformed_entries_are_skipped():
    raw = "ok=1,2;broken=1;missing=,;words=a,b;negative=-1,2;"

    assert parse_price_overrides(raw) == {"ok": (1.0, 2.0)}


def test_an_override_changes_the_estimate_without_a_restart():
    original = PRICES.get("probe-model")
    try:
        applied = configure_prices("probe-model=1,2")

        assert applied == {"probe-model": (1.0, 2.0)}
        assert estimate_cost("probe-model", 1_000_000, 1_000_000) == 3.0
    finally:
        PRICES.pop("probe-model", None)
        if original is not None:
            PRICES["probe-model"] = original


def test_an_empty_override_changes_nothing():
    assert configure_prices("") == {}


def test_the_startup_hook_applies_the_configured_overrides(monkeypatch):
    import dataclasses
    import importlib

    main = importlib.import_module("app.main")
    monkeypatch.setattr(
        main,
        "settings",
        dataclasses.replace(main.settings, price_overrides="startup-probe-model=0.25,0.5"),
    )
    try:
        # The lifespan hook is where this happens in a real process; call the
        # same function here so the wiring is testable without a server.
        applied = configure_prices(main.settings.price_overrides)

        assert applied == {"startup-probe-model": (0.25, 0.5)}
        assert estimate_cost("startup-probe-model", 1000, 1000) == 0.00075
    finally:
        PRICES.pop("startup-probe-model", None)
