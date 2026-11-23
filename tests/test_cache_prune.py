"""Expired entries must not occupy capacity that a fresh answer needs."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))

from app.cache import ResponseCache  # noqa: E402


def make_cache(clock: list[float], **kwargs):
    return ResponseCache(clock=lambda: clock[0], **kwargs)


def test_prune_removes_only_expired_entries():
    now = [0.0]
    cache = make_cache(now, max_items=4, ttl=10)
    cache.put("old-a", "A")
    now[0] = 5.0
    cache.put("fresh", "B")
    now[0] = 11.0

    removed = cache.prune()

    assert removed == 1
    assert cache.get("fresh") == "B"
    assert cache.stats()["items"] == 1


def test_an_insert_prunes_before_evicting_a_live_entry():
    now = [0.0]
    cache = make_cache(now, max_items=2, ttl=10)
    cache.put("a", "A")
    cache.put("b", "B")
    now[0] = 11.0
    cache.put("c", "C")

    snapshot = cache.stats()
    assert snapshot["items"] == 1
    assert snapshot["evictions"] == 0, "an expired slot is not a capacity eviction"
    assert cache.get("c") == "C"


def test_bytes_are_released_when_entries_are_pruned():
    now = [0.0]
    cache = make_cache(now, max_items=10, ttl=10, max_bytes=100)
    cache.put("a", "中文" * 10)
    before = cache.stats()["bytes"]
    assert before > 0
    now[0] = 11.0

    cache.prune()

    assert cache.stats()["bytes"] == 0


def test_prune_counts_are_reported_separately_from_get_expirations():
    now = [0.0]
    cache = make_cache(now, ttl=10)
    cache.put("a", "A")
    now[0] = 11.0
    cache.prune()
    cache.put("b", "B")
    now[0] = 22.0
    assert cache.get("b") is None

    snapshot = cache.stats()
    assert snapshot["expired"] == 2
    assert snapshot["pruned"] == 1


def test_a_disabled_cache_prunes_nothing():
    cache = make_cache([0.0], ttl=0)

    assert cache.prune() == 0
    assert cache.stats()["pruned"] == 0


def test_live_items_excludes_entries_waiting_for_the_next_prune():
    now = [0.0]
    cache = make_cache(now, ttl=10)
    cache.put("a", "A")
    now[0] = 11.0

    snapshot = cache.stats()
    assert snapshot["items"] == 1
    assert snapshot["liveItems"] == 0

    cache.put("b", "B")
    assert cache.stats()["liveItems"] == 1


def test_pruning_twice_does_not_double_count():
    now = [0.0]
    cache = make_cache(now, ttl=10)
    cache.put("a", "A")
    now[0] = 11.0

    assert cache.prune() == 1
    assert cache.prune() == 0
