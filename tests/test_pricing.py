"""Cost estimation must be conservative about what it does not know."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))

from app.pricing import PRICES, estimate_cost, format_cost  # noqa: E402


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
