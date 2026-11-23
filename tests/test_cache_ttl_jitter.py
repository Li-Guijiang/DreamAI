"""Answers written together should not all expire at the same instant."""

from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))

from app.cache import ResponseCache  # noqa: E402


def make_cache(clock: list[float], **kwargs):
    return ResponseCache(clock=lambda: clock[0], rng=random.Random(7), **kwargs)


def test_jitter_is_off_by_default():
    cache = make_cache([0.0], ttl=10)

    assert cache.stats()["ttlJitter"] == 0.0
    cache.put("a", "A")
    assert cache.stats()["items"] == 1


def test_a_burst_of_writes_gets_distinct_expiry_times():
    now = [0.0]
    cache = make_cache(now, ttl=10, ttl_jitter=0.2)

    for index in range(5):
        cache.put(f"k{index}", "x")

    expiries = [expiry for _, expiry in cache._items.values()]
    assert len(set(expiries)) == len(expiries)
    assert all(8.0 <= expiry <= 12.0 for expiry in expiries)


def test_jitter_never_expires_before_the_lower_bound():
    now = [0.0]
    cache = make_cache(now, ttl=10, ttl_jitter=0.5)

    for index in range(40):
        cache.put(f"k{index}", "x")

    assert all(expiry >= 5.0 for _, (_, expiry) in cache._items.items())
    assert all(expiry <= 15.0 for _, (_, expiry) in cache._items.items())


def test_zero_jitter_is_exact():
    now = [0.0]
    cache = make_cache(now, ttl=10, ttl_jitter=0.0)
    cache.put("a", "A")

    assert next(iter(cache._items.values()))[1] == 10.0


def test_jitter_is_clamped():
    assert make_cache([0.0], ttl_jitter=-1).ttl_jitter == 0.0
    assert make_cache([0.0], ttl_jitter=9).ttl_jitter == 0.5


def test_a_jittered_entry_can_still_be_pruned():
    now = [0.0]
    cache = make_cache(now, ttl=10, ttl_jitter=0.2)
    cache.put("a", "A")
    now[0] = 20.0

    assert cache.prune() == 1
