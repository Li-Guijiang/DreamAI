"""The breaker must open on repeated failure and close again after a probe."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))

from app.guard import CLOSED, HALF_OPEN, OPEN, CircuitBreaker  # noqa: E402


class FakeClock:
    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds


def make(threshold: int = 3, cooldown: float = 30.0):
    clock = FakeClock()
    return CircuitBreaker(threshold=threshold, cooldown=cooldown, clock=clock), clock


def test_closed_breaker_allows_traffic():
    breaker, _ = make()

    assert breaker.state == CLOSED
    assert breaker.allow()


def test_opens_after_threshold_failures():
    breaker, _ = make(threshold=2)

    breaker.record_failure()
    assert breaker.allow()
    breaker.record_failure()

    assert breaker.state == OPEN
    assert not breaker.allow()


def test_a_success_resets_the_count():
    breaker, _ = make(threshold=2)

    breaker.record_failure()
    breaker.record_success()
    breaker.record_failure()

    assert breaker.state == CLOSED


def test_open_turns_half_open_after_cooldown():
    breaker, clock = make(threshold=1, cooldown=30)

    breaker.record_failure()
    assert breaker.state == OPEN
    clock.advance(31)

    assert breaker.state == HALF_OPEN
    assert breaker.allow()


def test_half_open_allows_only_one_probe():
    breaker, clock = make(threshold=1, cooldown=5)
    breaker.record_failure()
    clock.advance(6)

    assert breaker.allow()
    assert not breaker.allow(), "a second probe would flood a recovering provider"


def test_probe_success_closes_the_breaker():
    breaker, clock = make(threshold=1, cooldown=5)
    breaker.record_failure()
    clock.advance(6)

    breaker.allow()
    breaker.record_success()

    assert breaker.state == CLOSED
    assert breaker.allow()


def test_probe_failure_reopens_with_a_fresh_cooldown():
    breaker, clock = make(threshold=1, cooldown=5)
    breaker.record_failure()
    opened_at = clock.t
    clock.advance(6)
    breaker.allow()

    breaker.record_failure()
    assert breaker.state == OPEN
    clock.advance(4)
    assert breaker.state == OPEN, "cooldown must restart from the failed probe"
    clock.advance(2)
    assert breaker.state == HALF_OPEN
    assert clock.t > opened_at


def test_an_open_breaker_counts_down_to_its_probe():
    now = [0.0]
    breaker = CircuitBreaker(threshold=1, cooldown=30.0, clock=lambda: now[0])
    breaker.record_failure()

    assert breaker.remaining() == pytest.approx(30.0)
    now[0] = 12.0
    assert breaker.remaining() == pytest.approx(18.0)
    now[0] = 45.0
    assert breaker.remaining() == 0.0


def test_a_closed_breaker_has_nothing_to_wait_for():
    assert CircuitBreaker().remaining() == 0.0


def test_opening_the_breaker_is_counted_each_time():
    now = [0.0]
    breaker = CircuitBreaker(threshold=1, cooldown=10.0, clock=lambda: now[0])

    breaker.record_failure()
    assert breaker.stats()["openings"] == 1

    now[0] = 11.0
    assert breaker.allow() is True
    breaker.record_failure()
    assert breaker.stats()["openings"] == 2


def test_the_snapshot_reads_the_breaker_without_touching_it():
    now = [0.0]
    breaker = CircuitBreaker(threshold=2, cooldown=30.0, clock=lambda: now[0])
    breaker.record_failure()

    snapshot = breaker.stats()

    assert snapshot["state"] == CLOSED
    assert snapshot["failures"] == 1
    assert snapshot["retryIn"] == 0.0
    assert snapshot["threshold"] == 2
