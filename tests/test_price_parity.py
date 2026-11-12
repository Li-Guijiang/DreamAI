"""The two price tables must not drift apart.

``dream_ai`` ships without the web app, so the table exists twice. This test is
the only thing keeping the copies honest: it compares both the tables and the
arithmetic, on models a session is likely to use.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))

from app.pricing import CACHE_PRICES as WEB_CACHE_PRICES  # noqa: E402
from app.pricing import PRICES as WEB_PRICES  # noqa: E402
from app.pricing import estimate_cost as web_estimate  # noqa: E402

from dream_ai.pricing import CACHE_PRICES as LOCAL_CACHE_PRICES  # noqa: E402
from dream_ai.pricing import PRICES as LOCAL_PRICES  # noqa: E402
from dream_ai.pricing import estimate_cost as local_estimate  # noqa: E402

CASES = (
    ("glm-4-flash", 10_000, 2_000, 0),
    ("deepseek-chat", 8_000, 1_500, 0),
    ("deepseek-chat", 8_000, 1_500, 6_400),
    ("gpt-4o", 1_200, 300, 1_000),
    ("claude-3-5-sonnet-latest", 4_000, 900, 3_500),
    ("gemini-2.0-flash", 2_000, 400, 1_500),
    ("a-model-nobody-priced", 10, 10, 0),
)


def test_the_list_prices_are_identical():
    assert LOCAL_PRICES == WEB_PRICES


def test_the_cached_prices_are_identical():
    assert LOCAL_CACHE_PRICES == WEB_CACHE_PRICES


@pytest.mark.parametrize(("model", "prompt", "completion", "cached"), CASES)
def test_the_arithmetic_agrees(model, prompt, completion, cached):
    assert local_estimate(model, prompt, completion, cached=cached) == web_estimate(
        model, prompt, completion, cached=cached
    )
