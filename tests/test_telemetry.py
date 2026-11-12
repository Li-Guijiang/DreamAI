"""The turn log line must stay greppable and complete."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))

from app.telemetry import format_turn_log  # noqa: E402


def test_line_carries_every_field_in_a_fixed_order():
    line = format_turn_log(
        "req_abc12345",
        tier="deep",
        intent="error",
        ttft=0.84,
        total=6.21,
        chars=812,
        model="deepseek-chat",
    )

    assert line.startswith("chat done id=req_abc12345 ")
    assert "tier=deep" in line
    assert "intent=error" in line
    assert "ttft=0.84s" in line
    assert "total=6.21s" in line
    assert "chars=812" in line
    assert "model=deepseek-chat" in line


def test_outcome_can_mark_a_failure():
    line = format_turn_log(
        "req_x",
        tier="light",
        intent="chat",
        ttft=0.0,
        total=1.5,
        chars=0,
        model="m",
        outcome="failed",
    )

    assert line.startswith("chat failed ")
    assert "ttft=0.00s" in line


def test_cost_is_appended_only_when_known():
    without = format_turn_log(
        "req_x", tier="light", intent="chat", ttft=0.1, total=0.2, chars=3, model="m"
    )
    with_cost = format_turn_log(
        "req_x",
        tier="light",
        intent="chat",
        ttft=0.1,
        total=0.2,
        chars=3,
        model="m",
        cost=0.0012,
    )

    assert "cost=" not in without
    assert "cost=$0.0012" in with_cost


def test_the_cache_outcome_sits_between_the_numbers_and_the_cost():
    line = format_turn_log(
        "req_1",
        tier="light",
        intent="chat",
        ttft=0.1,
        total=0.2,
        chars=10,
        model="m",
        cost=0.001,
        cache="hit",
    )

    assert "cache=hit" in line
    assert line.index("cache=hit") < line.index("cost=")


def test_a_turn_without_cache_or_cost_ends_at_the_model():
    line = format_turn_log(
        "req_2", tier="deep", intent="design", ttft=1.2, total=4.0, chars=300, model="m"
    )

    assert line.endswith("model=m")


def test_the_cached_share_is_logged_so_a_low_cost_makes_sense():
    line = format_turn_log(
        "req_3",
        tier="standard",
        intent="code",
        ttft=0.3,
        total=2.0,
        chars=200,
        model="gpt-4o",
        cached_tokens=1792,
        cost=0.0041,
    )

    assert "cachedTokens=1792" in line
    assert line.index("cachedTokens=") < line.index("cost=")


def test_no_cached_tokens_no_field():
    line = format_turn_log(
        "req_4", tier="light", intent="chat", ttft=0.1, total=0.2, chars=3, model="m", cost=0.0
    )

    assert "cachedTokens" not in line


def test_the_finish_reason_sits_next_to_the_cost():
    line = format_turn_log(
        "req_5",
        tier="deep",
        intent="design",
        ttft=0.4,
        total=5.0,
        chars=4000,
        model="m",
        finish="length",
        cost=0.02,
    )

    assert "finish=length" in line
    assert line.index("finish=") < line.index("cost=")


def test_no_finish_reason_no_field():
    line = format_turn_log(
        "req_6", tier="light", intent="chat", ttft=0.1, total=0.2, chars=3, model="m"
    )

    assert "finish=" not in line


def test_the_breaker_line_reports_the_numbers_that_explain_it():
    from app.telemetry import format_breaker_log

    line = format_breaker_log({"state": "open", "failures": 3, "openings": 1, "cooldown": 30.0})

    assert line.startswith("breaker open")
    assert "failures=3" in line
    assert "openings=1" in line
    assert "cooldown=30.0s" in line


def test_the_breaker_line_survives_an_empty_snapshot():
    from app.telemetry import format_breaker_log

    assert "failures=0" in format_breaker_log({})


def test_the_recovery_line_is_short_and_says_it_closed():
    from app.telemetry import format_recovery_log

    line = format_recovery_log({"state": "closed", "openings": 2})

    assert line.startswith("breaker recovered")
    assert "state=closed" in line
    assert "openings=2" in line
