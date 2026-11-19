"""The totals must agree with their breakdowns, before and after a snapshot."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))

from app.stats import UsageStats  # noqa: E402


def _mixed() -> UsageStats:
    stats = UsageStats(max_tracked_models=3)
    stats.record_turn("a", tier="deep", intent="error", provider="free", ttft=1.2)
    stats.record_turn(
        "a",
        tier="light",
        intent="chat",
        provider="free",
        failed=True,
        truncated=True,
        finish="length",
    )
    stats.record_turn("b", tier="deep", intent="chat", provider="byok", ttft=0.4)
    stats.record_local(tier="light")
    stats.record_blocked()
    stats.record_cancelled("a")
    stats.record_usage("a", 100, 20, 0.01, cached=30)
    stats.record_usage("b", 50, 10, None)
    return stats


def _assert_invariants(snapshot: dict) -> None:
    slots = snapshot["byModel"]
    slot_requests = sum(slot["requests"] for slot in slots.values())
    slot_failures = sum(slot["failures"] for slot in slots.values())
    slot_truncated = sum(slot["truncated"] for slot in slots.values())
    slot_prompt = sum(slot["promptTokens"] for slot in slots.values())
    slot_cost = sum(slot["costUsd"] for slot in slots.values())

    assert snapshot["requests"] == slot_requests + snapshot["blocked"]
    assert snapshot["failures"] == slot_failures + snapshot["blocked"]
    assert snapshot["truncated"] == slot_truncated
    assert snapshot["truncated"] == sum(snapshot["truncatedByTier"].values())
    assert snapshot["promptTokens"] == slot_prompt
    assert snapshot["costUsd"] == pytest.approx(round(slot_cost, 4))
    assert snapshot["ttftSamples"] <= snapshot["requests"]


def test_the_live_snapshot_is_internally_consistent():
    snapshot = _mixed().snapshot()
    _assert_invariants(snapshot)

    assert snapshot["local"] == 1
    assert snapshot["cancelled"] == 1


def test_a_snapshot_round_trip_keeps_the_invariants():
    restored = UsageStats(max_tracked_models=3)
    assert restored.import_counters(_mixed().export_counters()) is True

    _assert_invariants(restored.snapshot())


def test_compacting_an_oversized_snapshot_keeps_the_invariants():
    source = UsageStats(max_tracked_models=100)
    for index in range(30):
        source.record_turn(f"model-{index}")
        source.record_usage(f"model-{index}", 7, 2, 0.001)
    source.record_blocked()

    restored = UsageStats(max_tracked_models=6)
    assert restored.import_counters(source.export_counters()) is True

    _assert_invariants(restored.snapshot())


def test_an_empty_stats_object_has_zeroed_breakdowns():
    _assert_invariants(UsageStats().snapshot())
