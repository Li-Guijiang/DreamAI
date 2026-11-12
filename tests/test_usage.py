"""The session ledger must add up, and must say what it could not measure."""

from __future__ import annotations

import pytest

from dream_ai.usage import SessionUsage


def test_a_fresh_ledger_is_empty_and_known():
    snapshot = SessionUsage().snapshot()

    assert snapshot["turns"] == 0
    assert snapshot["promptTokens"] == 0
    assert snapshot["costKnown"] is True


def test_tokens_and_cost_accumulate():
    usage = SessionUsage()
    usage.record("deepseek-chat", {"prompt_tokens": 1000, "completion_tokens": 500})
    usage.record("deepseek-chat", {"prompt_tokens": 500, "completion_tokens": 250})

    snapshot = usage.snapshot()

    assert snapshot["turns"] == 2
    assert snapshot["promptTokens"] == 1500
    assert snapshot["completionTokens"] == 750
    # 1500 in at 0.27/M plus 750 out at 1.1/M
    assert snapshot["costUsd"] == pytest.approx(0.000405 + 0.000825)


def test_a_cached_prompt_is_cheaper():
    usage = SessionUsage()
    usage.record(
        "gpt-4o",
        {"prompt_tokens": 1_000_000, "completion_tokens": 0, "cached_tokens": 1_000_000},
    )

    assert usage.snapshot()["costUsd"] == pytest.approx(1.25)


def test_a_turn_without_counts_makes_the_total_a_lower_bound():
    usage = SessionUsage()
    usage.record("deepseek-chat", {"prompt_tokens": 10, "completion_tokens": 10})
    usage.record("deepseek-chat", None)

    snapshot = usage.snapshot()

    assert snapshot["turns"] == 2
    assert snapshot["unmeasured"] == 1
    assert snapshot["costKnown"] is False


def test_an_empty_mapping_counts_as_nothing_reported():
    usage = SessionUsage()
    usage.record("deepseek-chat", {})

    assert usage.snapshot()["unmeasured"] == 1


def test_an_unpriced_model_is_counted_but_not_priced():
    usage = SessionUsage()
    usage.record("mystery-model", {"prompt_tokens": 100, "completion_tokens": 100})

    snapshot = usage.snapshot()

    assert snapshot["promptTokens"] == 100
    assert snapshot["unpriced"] == 1
    assert snapshot["costKnown"] is False
    assert snapshot["models"] == {"mystery-model": 1}


def test_a_cached_count_above_the_prompt_is_clamped():
    usage = SessionUsage()
    usage.record(
        "gpt-4o", {"prompt_tokens": 100, "completion_tokens": 0, "cached_tokens": 5000}
    )

    snapshot = usage.snapshot()

    assert snapshot["cachedTokens"] == 100
    assert snapshot["costUsd"] == pytest.approx(100 * 1.25 / 1_000_000)


def test_negative_counts_cannot_shrink_the_total():
    usage = SessionUsage()
    usage.record("deepseek-chat", {"prompt_tokens": -5, "completion_tokens": -5})

    snapshot = usage.snapshot()

    assert snapshot["promptTokens"] == 0
    assert snapshot["completionTokens"] == 0


def test_turns_are_counted_per_model():
    usage = SessionUsage()
    usage.record("a", {"prompt_tokens": 1, "completion_tokens": 1})
    usage.record("a", {"prompt_tokens": 1, "completion_tokens": 1})
    usage.record("b", {"prompt_tokens": 1, "completion_tokens": 1})

    assert usage.snapshot()["models"] == {"a": 2, "b": 1}


def test_reset_starts_over():
    usage = SessionUsage()
    usage.record("deepseek-chat", {"prompt_tokens": 10, "completion_tokens": 10})
    usage.reset()

    assert usage.snapshot()["turns"] == 0
    assert usage.snapshot()["costKnown"] is True
