"""Cost estimation must be conservative about what it does not know."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))

from app.pricing import (  # noqa: E402
    CACHE_PRICES,
    PRICES,
    configure_prices,
    estimate_cost,
    format_cost,
)


def test_known_model_costs_input_and_output_separately():
    # gpt-4o: 2.5 / 10.0 USD per 1M
    cost = estimate_cost("gpt-4o", 1_000_000, 1_000_000)

    assert cost == 12.5


def test_zero_token_model_is_free():
    assert estimate_cost("glm-4-flash", 5000, 5000) == 0.0


def test_unknown_model_returns_none():
    assert estimate_cost("some-local-model", 10, 10) is None


def test_every_price_is_a_pair_of_floats():
    for model, price in PRICES.items():
        assert len(price) == 2, model
        assert all(isinstance(value, float) for value in price), model


def test_formatting_hides_noise():
    assert format_cost(None) == "unknown"
    assert format_cost(0.0) == "free"
    assert format_cost(0.0012) == "$0.0012"
    assert format_cost(1.5) == "$1.50"


def test_a_cached_prompt_is_billed_at_the_cached_price():
    # gpt-4o keeps a cached input price of 1.25 against a list price of 2.5.
    cost = estimate_cost("gpt-4o", 1_000_000, 0, cached=1_000_000)

    assert cost == 1.25


def test_half_a_cached_prompt_costs_the_average_of_the_two_rates():
    cost = estimate_cost("gpt-4o", 1_000_000, 0, cached=500_000)

    assert cost == 1.875


def test_cached_tokens_never_exceed_the_prompt():
    # A provider that reports the two inconsistently must not lower the bill
    # below what the full prompt costs at the cached rate.
    cost = estimate_cost("gpt-4o", 1000, 0, cached=999_999)

    assert cost == 0.00125


def test_a_model_without_a_cache_price_is_billed_at_the_list_price():
    # glm-4-plus has no published cache rate, so the discount is assumed away.
    assert estimate_cost("glm-4-plus", 1_000_000, 0, cached=1_000_000) == 0.7


def test_every_cache_price_belongs_to_a_priced_model():
    assert set(CACHE_PRICES) <= set(PRICES)


def test_a_third_field_reprices_the_cache_too():
    try:
        configure_prices("probe-cache-model=2,8,0.2")

        assert estimate_cost("probe-cache-model", 1_000_000, 0, cached=1_000_000) == 0.2
    finally:
        PRICES.pop("probe-cache-model", None)
        CACHE_PRICES.pop("probe-cache-model", None)


def test_two_fields_leave_the_cache_price_alone():
    try:
        configure_prices("probe-plain-model=2,8")

        # No third number: the full input price applies to the cached part.
        assert estimate_cost("probe-plain-model", 1_000_000, 0, cached=1_000_000) == 2.0
    finally:
        PRICES.pop("probe-plain-model", None)


def test_non_finite_prices_are_refused():
    assert configure_prices("probe-nan-model=nan,1") == {}


def test_negative_cached_counts_are_clamped():
    assert estimate_cost("gpt-4o", 1_000_000, 0, cached=-5) == 2.5
