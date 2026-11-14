"""A silently skipped price correction must be detectable at startup."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

WEB = str(Path(__file__).resolve().parent.parent / "web")
if WEB not in sys.path:
    sys.path.insert(0, WEB)

from app.pricing import (  # noqa: E402
    invalid_price_overrides,
    parse_cache_overrides,
    parse_price_overrides,
)


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "new-model=1,2",
        "new-model=1,2,0.5",
        "a=1,2;b=3,4",
        "free-model=0,0",
    ],
)
def test_valid_overrides_produce_no_findings(raw):
    assert invalid_price_overrides(raw) == []


@pytest.mark.parametrize(
    "raw",
    [
        "oops",
        "new-model=1",
        "new-model=x,2",
        "new-model=1,nan",
        "new-model=1,2,inf",
        "new-model=1,2,-3",
        "=1,2",
        "new-model=1,2;broken",
    ],
)
def test_malformed_entries_are_reported(raw):
    assert invalid_price_overrides(raw)


def test_the_findings_agree_with_the_parsers():
    raw = "good=1,2,0.5;short=1;bad=x,2;third=3,4,nope"

    assert invalid_price_overrides(raw) == ["short=1", "bad=x,2", "third=3,4,nope"]
    assert set(parse_price_overrides(raw)) == {"good", "third"}
    assert parse_cache_overrides(raw) == {"good": 0.5}


def test_a_long_entry_is_truncated_for_the_log():
    raw = "x" * 200 + "=1"

    assert len(invalid_price_overrides(raw)[0]) <= 40


def test_a_semicolon_only_string_is_clean():
    assert invalid_price_overrides(";;;") == []
