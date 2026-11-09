"""The usage counters must add up, and must admit what they do not know."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))

from app.stats import UsageStats  # noqa: E402


def test_a_fresh_counter_reports_zeroes():
    snapshot = UsageStats(started_at=1000.0).snapshot()

    assert snapshot["requests"] == 0
    assert snapshot["failures"] == 0
    assert snapshot["promptTokens"] == 0
    assert snapshot["costUsd"] == 0.0
    assert snapshot["costKnown"] is True


def test_turns_and_failures_are_counted_separately():
    stats = UsageStats()
    stats.record_turn()
    stats.record_turn(failed=True)

    assert stats.requests == 2
    assert stats.failures == 1


def test_tokens_and_cost_accumulate_across_turns():
    stats = UsageStats()
    stats.record_usage(120, 80, 0.0012)
    stats.record_usage(30, 20, 0.0003)

    assert stats.prompt_tokens == 150
    assert stats.completion_tokens == 100
    assert stats.cost_usd == pytest.approx(0.0015)
    assert stats.known_cost is True


def test_an_unknown_price_marks_the_total_but_keeps_counting_tokens():
    stats = UsageStats()
    stats.record_usage(10, 10, 0.002)
    stats.record_usage(10, 10, None)

    assert stats.prompt_tokens == 20
    assert stats.cost_usd == pytest.approx(0.002)
    assert stats.known_cost is False


def test_negative_token_counts_cannot_shrink_the_total():
    stats = UsageStats()
    stats.record_usage(-5, -5, None)

    assert stats.prompt_tokens == 0
    assert stats.completion_tokens == 0
