"""A price table that contradicts itself must be visible at startup."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))

from app import pricing  # noqa: E402


def test_the_published_tables_are_consistent():
    assert pricing.check_price_tables() == []


def test_a_nan_price_is_reported(monkeypatch):
    monkeypatch.setattr(pricing, "PRICES", {**pricing.PRICES, "bad": (float("nan"), 1.0)})

    assert any(
        "bad" in issue and "invalid price pair" in issue for issue in pricing.check_price_tables()
    )


def test_a_negative_price_is_reported(monkeypatch):
    monkeypatch.setattr(pricing, "PRICES", {**pricing.PRICES, "worse": (-1.0, 2.0)})

    assert any("worse" in issue for issue in pricing.check_price_tables())


def test_a_wrongly_shaped_price_pair_is_reported(monkeypatch):
    monkeypatch.setattr(pricing, "PRICES", {**pricing.PRICES, "bad": (1.0,)})

    assert any("bad" in issue for issue in pricing.check_price_tables())


def test_a_cached_price_above_the_input_price_is_reported(monkeypatch):
    monkeypatch.setattr(pricing, "PRICES", {**pricing.PRICES, "new": (1.0, 2.0)})
    monkeypatch.setattr(pricing, "CACHE_PRICES", {**pricing.CACHE_PRICES, "new": 9.0})

    assert any("cached price exceeds" in issue for issue in pricing.check_price_tables())


def test_a_cached_price_for_an_unknown_model_is_reported(monkeypatch):
    monkeypatch.setattr(pricing, "CACHE_PRICES", {**pricing.CACHE_PRICES, "ghost": 0.1})

    assert any("without a base price" in issue for issue in pricing.check_price_tables())


def test_an_invalid_cached_price_is_reported(monkeypatch):
    monkeypatch.setattr(pricing, "CACHE_PRICES", {**pricing.CACHE_PRICES, "new": float("inf")})

    assert any("invalid cached price" in issue for issue in pricing.check_price_tables())


def test_an_override_that_breaks_the_table_is_detected(monkeypatch):
    monkeypatch.setattr(pricing, "PRICES", dict(pricing.PRICES))
    monkeypatch.setattr(pricing, "CACHE_PRICES", dict(pricing.CACHE_PRICES))

    applied = pricing.configure_prices("new-model=1,2,9")

    assert applied["new-model"] == (1.0, 2.0)
    assert any("new-model: cached price exceeds" in issue for issue in pricing.check_price_tables())


def test_a_valid_override_leaves_the_tables_consistent(monkeypatch):
    monkeypatch.setattr(pricing, "PRICES", dict(pricing.PRICES))
    monkeypatch.setattr(pricing, "CACHE_PRICES", dict(pricing.CACHE_PRICES))

    pricing.configure_prices("new-model=1,2,0.5")

    assert pricing.check_price_tables() == []
