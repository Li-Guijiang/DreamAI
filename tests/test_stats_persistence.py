"""Restoring counters must be exact, all-or-nothing and honest about uptime."""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

WEB = str(Path(__file__).resolve().parent.parent / "web")
if WEB not in sys.path:
    sys.path.insert(0, WEB)

from app.stats import UsageStats  # noqa: E402


def _busy() -> UsageStats:
    stats = UsageStats(started_at=1000.0)
    stats.record_turn("m", tier="deep", intent="error", provider="free", ttft=1.5)
    stats.record_turn("m", tier="light", intent="chat", provider="free", ttft=0.5, failed=True)
    stats.record_usage("m", 1000, 200, 0.002, cached=750)
    stats.record_local()
    stats.record_blocked()
    stats.record_cancelled("m")
    return stats


def test_export_then_import_reproduces_the_snapshot():
    old = _busy()
    counters = old.export_counters()

    fresh = UsageStats(started_at=9999.0)
    assert fresh.import_counters(counters) is True

    assert fresh.snapshot() == old.snapshot()


def test_uptime_belongs_to_the_new_process():
    old = _busy()
    fresh = UsageStats(started_at=9999.0)

    fresh.import_counters(old.export_counters())

    assert fresh.started_at == 9999.0
    assert old.started_at == 1000.0


def test_the_export_is_a_copy_not_a_live_reference():
    old = _busy()
    counters = old.export_counters()
    counters["_by_model"]["m"]["requests"] = 999
    counters["requests"] = 999

    assert old.snapshot()["requests"] != 999
    assert old.snapshot()["byModel"]["m"]["requests"] != 999


def test_the_import_is_a_copy_too():
    counters = _busy().export_counters()
    fresh = UsageStats()
    fresh.import_counters(counters)

    fresh.record_turn("m")

    assert counters["requests"] != fresh.snapshot()["requests"]


@pytest.mark.parametrize(
    "damage",
    [
        lambda d: d.update(requests="many"),
        lambda d: d.update(requests=-1),
        lambda d: d.update(cost_usd=float("nan")),
        lambda d: d.update(known_cost="yes"),
        lambda d: d.update(_by_tier={"deep": None}),
        lambda d: d.update(_by_model={"m": {"requests": "x"}}),
        lambda d: d.update(_by_finish=[]),
        lambda d: d.pop("truncated"),
        lambda d: d.pop("_by_model"),
    ],
)
def test_a_damaged_snapshot_changes_nothing(damage):
    counters = copy.deepcopy(_busy().export_counters())
    damage(counters)
    fresh = _busy()

    assert fresh.import_counters(counters) is False
    assert fresh.snapshot() == _busy().snapshot()


def test_none_and_non_dicts_are_refused():
    fresh = UsageStats()

    assert fresh.import_counters(None) is False
    assert fresh.import_counters([]) is False
    assert fresh.snapshot()["requests"] == 0


def test_an_older_writer_with_fewer_model_fields_is_tolerated():
    counters = _busy().export_counters()
    counters["_by_model"]["m"] = {"requests": 2, "costUsd": 0.5}
    fresh = UsageStats()

    assert fresh.import_counters(counters) is True
    slot = fresh.snapshot()["byModel"]["m"]
    assert slot["requests"] == 2
    # Missing fields come from the default slot, not from a KeyError later.
    assert slot["promptTokens"] == 0
    assert slot["failureRate"] == 0.0


def test_unknown_keys_are_ignored():
    counters = _busy().export_counters()
    counters["a_field_from_the_future"] = 42
    counters["_by_model"]["m"]["also_new"] = 1

    assert UsageStats().import_counters(counters) is True


def test_the_derived_ratios_are_not_stored():
    counters = _busy().export_counters()

    assert "cachedShare" not in counters
    assert "truncationRate" not in counters
    assert "avgTtft" not in counters
    assert "started_at" not in counters
