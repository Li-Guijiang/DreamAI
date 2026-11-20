"""Time spent waiting for a concurrency slot is not upstream latency."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))

from app.stats import UsageStats  # noqa: E402


def test_wait_times_are_reported_separately_from_ttft():
    stats = UsageStats()
    stats.record_admission_wait(0.5)
    stats.record_admission_wait(1.5)

    snapshot = stats.snapshot()
    assert snapshot["admissionWaitSamples"] == 2
    assert snapshot["admissionWaitAvg"] == 1.0
    assert snapshot["admissionWaitMax"] == 1.5
    assert snapshot["ttftSamples"] == 0


def test_an_admission_timeout_counts_as_a_blocked_request():
    stats = UsageStats()
    stats.record_admission_timeout()

    snapshot = stats.snapshot()
    assert snapshot["admissionTimeouts"] == 1
    assert snapshot["blocked"] == 1
    assert snapshot["requests"] == 1
    assert snapshot["failures"] == 1
    assert snapshot["byModel"] == {}, "the request never reached a model"


def test_wait_times_survive_a_snapshot_round_trip():
    source = UsageStats()
    source.record_admission_wait(2.5)
    source.record_admission_timeout()

    restored = UsageStats()
    assert restored.import_counters(source.export_counters()) is True

    snapshot = restored.snapshot()
    assert snapshot["admissionWaitMax"] == 2.5
    assert snapshot["admissionWaitSamples"] == 1
    assert snapshot["admissionTimeouts"] == 1


def test_the_totals_still_reconcile_after_a_timeout():
    stats = UsageStats()
    stats.record_admission_timeout()
    stats.record_admission_wait(0.1)
    stats.record_turn("m")
    stats.record_usage("m", 10, 2, 0.01)

    snapshot = stats.snapshot()
    assert (
        snapshot["requests"]
        == sum(s["requests"] for s in snapshot["byModel"].values()) + snapshot["blocked"]
    )
    assert (
        snapshot["failures"]
        == sum(s["failures"] for s in snapshot["byModel"].values()) + snapshot["blocked"]
    )
