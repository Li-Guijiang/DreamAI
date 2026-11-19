"""A caller can invent model ids; the counter table must still stay bounded."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))

from app.stats import DEFAULT_MAX_TRACKED_MODELS, OTHER_MODEL, UsageStats  # noqa: E402


def test_the_default_ceiling_leaves_room_for_the_overflow_bucket():
    stats = UsageStats()

    assert stats.max_tracked_models == DEFAULT_MAX_TRACKED_MODELS
    assert stats.snapshot()["byModel"] == {}


def test_unknown_models_are_merged_into_one_bucket():
    stats = UsageStats(max_tracked_models=4)

    for index in range(6):
        stats.record_turn(f"model-{index}")

    slots = stats.snapshot()["byModel"]
    assert len(slots) == 4
    assert OTHER_MODEL in slots
    assert sum(slot["requests"] for slot in slots.values()) == 6


def test_a_first_seen_model_is_not_merged_away():
    stats = UsageStats(max_tracked_models=4)
    stats.record_turn("kept-1")
    stats.record_turn("kept-2")
    stats.record_turn("kept-3")
    stats.record_turn("overflow-1")

    stats.record_turn("kept-1")
    stats.record_turn("kept-2")

    slots = stats.snapshot()["byModel"]
    assert slots["kept-1"]["requests"] == 2
    assert slots["kept-2"]["requests"] == 2
    assert slots[OTHER_MODEL]["requests"] == 1


def test_the_overflow_bucket_accumulates_tokens_and_cost():
    stats = UsageStats(max_tracked_models=3)
    for index in range(5):
        stats.record_turn(f"m{index}")
        stats.record_usage(f"m{index}", 10, 2, 0.5, cached=3)

    other = stats.snapshot()["byModel"][OTHER_MODEL]

    assert other["requests"] == 3
    assert other["promptTokens"] == 30
    assert other["cachedTokens"] == 9
    assert other["costUsd"] == 1.5


def test_a_local_answer_counts_towards_a_real_slot():
    stats = UsageStats(max_tracked_models=4)

    stats.record_local()

    assert "local" in stats.snapshot()["byModel"]


def test_an_imported_oversized_snapshot_is_compacted():
    source = UsageStats(max_tracked_models=100)
    for index in range(20):
        source.record_turn(f"m{index}", tier="deep")
        source.record_usage(f"m{index}", 10, 1, 0.25)
    payload = source.export_counters()

    restored = UsageStats(max_tracked_models=4)
    assert restored.import_counters(payload) is True

    slots = restored.snapshot()["byModel"]
    assert len(slots) == 4
    assert sum(slot["requests"] for slot in slots.values()) == 20
    assert sum(slot["promptTokens"] for slot in slots.values()) == 200
    assert sum(slot["costUsd"] for slot in slots.values()) == 5.0


def test_the_limit_is_clamped_to_a_usable_value():
    assert UsageStats(max_tracked_models=0).max_tracked_models == 2
    assert UsageStats(max_tracked_models=-10).max_tracked_models == 2


def test_the_limit_is_not_stored_as_a_counter():
    payload = UsageStats(max_tracked_models=8).export_counters()

    assert "max_tracked_models" not in payload
    assert "maxTrackedModels" not in payload
