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
    stats.record_turn("deepseek-chat")
    stats.record_turn("deepseek-chat", failed=True)

    assert stats.requests == 2
    assert stats.failures == 1


def test_tokens_and_cost_accumulate_across_turns():
    stats = UsageStats()
    stats.record_usage("deepseek-chat", 120, 80, 0.0012)
    stats.record_usage("deepseek-chat", 30, 20, 0.0003)

    assert stats.prompt_tokens == 150
    assert stats.completion_tokens == 100
    assert stats.cost_usd == pytest.approx(0.0015)
    assert stats.known_cost is True


def test_an_unknown_price_marks_the_total_but_keeps_counting_tokens():
    stats = UsageStats()
    stats.record_usage("deepseek-chat", 10, 10, 0.002)
    stats.record_usage("mystery-model", 10, 10, None)

    assert stats.prompt_tokens == 20
    assert stats.cost_usd == pytest.approx(0.002)
    assert stats.known_cost is False


def test_negative_token_counts_cannot_shrink_the_total():
    stats = UsageStats()
    stats.record_usage("deepseek-chat", -5, -5, None)

    assert stats.prompt_tokens == 0
    assert stats.completion_tokens == 0


def test_each_model_keeps_its_own_row():
    stats = UsageStats()
    stats.record_turn("light-model")
    stats.record_turn("deep-model")
    stats.record_usage("light-model", 10, 5, 0.0001)
    stats.record_usage("deep-model", 900, 700, 0.03)

    rows = stats.snapshot()["byModel"]

    assert rows["light-model"]["requests"] == 1
    assert rows["light-model"]["promptTokens"] == 10
    assert rows["deep-model"]["promptTokens"] == 900
    assert rows["deep-model"]["costUsd"] == pytest.approx(0.03)
    assert rows["light-model"]["costUsd"] == pytest.approx(0.0001)


def test_an_unpriced_model_still_shows_its_tokens():
    stats = UsageStats()
    stats.record_turn("brand-new-model")
    stats.record_usage("brand-new-model", 40, 60, None)

    row = stats.snapshot()["byModel"]["brand-new-model"]

    assert row["promptTokens"] == 40
    assert row["completionTokens"] == 60
    assert row["costUsd"] == 0.0
    assert stats.known_cost is False


def test_a_failed_turn_is_attributed_to_its_model():
    stats = UsageStats()
    stats.record_turn("deep-model", failed=True)

    assert stats.snapshot()["byModel"]["deep-model"]["failures"] == 1


def test_first_token_time_averages_over_the_turns_that_had_one():
    stats = UsageStats()
    stats.record_turn("deep-model", ttft=0.4)
    stats.record_turn("deep-model", ttft=0.8)

    assert stats.avg_ttft() == pytest.approx(0.6)
    assert stats.snapshot()["avgTtft"] == pytest.approx(0.6)
    assert stats.snapshot()["ttftSamples"] == 2


def test_a_cache_hit_does_not_pull_the_average_down():
    stats = UsageStats()
    stats.record_turn("deep-model", ttft=1.0)
    stats.record_turn("deep-model")

    assert stats.avg_ttft() == pytest.approx(1.0)
    assert stats.snapshot()["requests"] == 2


def test_no_first_token_yet_means_no_average_rather_than_zero():
    stats = UsageStats()

    assert stats.avg_ttft() == 0.0
    assert stats.snapshot()["ttftSamples"] == 0


def test_turns_are_tallied_per_tier():
    stats = UsageStats()
    stats.record_turn("light-model", tier="light")
    stats.record_turn("light-model", tier="light")
    stats.record_turn("deep-model", tier="deep")

    assert stats.snapshot()["byTier"] == {"light": 2, "deep": 1}


def test_a_turn_without_a_tier_is_not_filed_under_empty():
    stats = UsageStats()
    stats.record_turn("local")

    assert stats.snapshot()["byTier"] == {}


def test_local_answers_are_counted_but_carry_no_tokens():
    stats = UsageStats()
    stats.record_local()

    snapshot = stats.snapshot()

    assert snapshot["local"] == 1
    assert snapshot["requests"] == 1
    assert snapshot["promptTokens"] == 0
    assert snapshot["byModel"]["local"]["requests"] == 1


def test_a_blocked_turn_is_a_request_and_a_failure():
    stats = UsageStats()
    stats.record_blocked()

    snapshot = stats.snapshot()

    assert snapshot["blocked"] == 1
    assert snapshot["requests"] == 1
    assert snapshot["failures"] == 1


def test_a_cancelled_turn_is_counted_without_blaming_the_model():
    stats = UsageStats()
    stats.record_cancelled("deepseek-chat")

    snapshot = stats.snapshot()

    assert snapshot["cancelled"] == 1
    assert snapshot["requests"] == 1
    assert snapshot["failures"] == 0
    assert snapshot["byModel"]["deepseek-chat"]["requests"] == 1
    assert snapshot["byModel"]["deepseek-chat"]["failures"] == 0


def test_turns_are_tallied_per_intent():
    stats = UsageStats()
    stats.record_turn("m", intent="error")
    stats.record_turn("m", intent="error")
    stats.record_turn("m", intent="chat")

    assert stats.snapshot()["byIntent"] == {"error": 2, "chat": 1}


def test_a_turn_without_an_intent_is_not_filed_under_empty():
    stats = UsageStats()

    assert stats.snapshot()["byIntent"] == {}


def test_the_worst_first_token_time_is_kept_separately():
    stats = UsageStats()
    stats.record_turn("m", ttft=0.4)
    stats.record_turn("m", ttft=2.8)
    stats.record_turn("m", ttft=0.9)

    snapshot = stats.snapshot()

    assert snapshot["avgTtft"] == pytest.approx((0.4 + 2.8 + 0.9) / 3, abs=0.01)
    assert snapshot["ttftMax"] == pytest.approx(2.8)


def test_each_model_row_carries_its_own_failure_rate():
    stats = UsageStats()
    stats.record_turn("a", failed=True)
    stats.record_turn("a")
    stats.record_turn("b")

    rows = stats.snapshot()["byModel"]

    assert rows["a"]["failureRate"] == pytest.approx(0.5)
    assert rows["b"]["failureRate"] == 0.0
