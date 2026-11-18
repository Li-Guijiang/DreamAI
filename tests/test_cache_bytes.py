"""A cache that counts entries but not bytes can still grow without bound."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))

from app.cache import DEFAULT_MAX_BYTES, ResponseCache  # noqa: E402


class Clock:
    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t


def make(max_bytes: int, max_items: int = 100) -> ResponseCache:
    return ResponseCache(max_items=max_items, ttl=300, clock=Clock(), max_bytes=max_bytes)


def test_the_default_ceiling_is_a_real_number_of_bytes():
    cache = ResponseCache(clock=Clock())

    assert cache.max_bytes == DEFAULT_MAX_BYTES
    assert cache.stats()["maxBytes"] == DEFAULT_MAX_BYTES


def test_an_answer_larger_than_the_whole_budget_is_not_cached():
    cache = make(max_bytes=100)

    cache.put("big", "x" * 101)

    assert len(cache) == 0
    assert cache.get("big") is None
    assert cache.stats()["bytes"] == 0


def test_the_oldest_entry_is_evicted_until_the_byte_budget_holds():
    cache = make(max_bytes=30)

    for index in range(3):
        cache.put(f"k{index}", "x" * 12)

    assert len(cache) == 2, "36 bytes must be reduced to 24"
    assert cache.get("k0") is None
    assert cache.get("k1") == "x" * 12
    assert cache.get("k2") == "x" * 12
    assert cache.stats()["bytes"] == 24


def test_byte_evictions_are_counted_separately_from_item_evictions():
    cache = make(max_bytes=30)

    for index in range(3):
        cache.put(f"k{index}", "x" * 12)

    assert cache.stats()["byteEvictions"] == 1
    assert cache.stats()["evictions"] == 1


def test_an_item_count_eviction_is_not_counted_as_a_byte_eviction():
    cache = make(max_bytes=10_000, max_items=2)

    for index in range(3):
        cache.put(f"k{index}", "hi")

    assert cache.stats()["evictions"] == 1
    assert cache.stats()["byteEvictions"] == 0


def test_a_zero_byte_budget_disables_the_ceiling():
    cache = make(max_bytes=0)

    cache.put("k", "x" * 5000)

    assert len(cache) == 1
    assert cache.stats()["maxBytes"] == 0
    assert cache.stats()["byteFull"] is False


def test_replacing_an_entry_keeps_the_byte_total_correct():
    cache = make(max_bytes=100)

    cache.put("k", "x" * 40)
    cache.put("k", "y" * 10)

    assert cache.stats()["bytes"] == 10
    assert cache.get("k") == "y" * 10


def test_recently_read_entries_survive_a_byte_eviction():
    cache = make(max_bytes=30)
    cache.put("old", "a" * 12)
    cache.put("new", "b" * 12)
    assert cache.get("old") == "a" * 12  # now most recently used

    cache.put("third", "c" * 12)

    assert cache.get("old") == "a" * 12
    assert cache.get("new") is None


def test_byte_full_is_reported_when_the_budget_is_reached():
    cache = make(max_bytes=12)

    cache.put("k", "x" * 12)

    assert cache.stats()["byteFull"] is True


def test_clear_resets_the_bytes_but_not_the_lifetime_counters():
    cache = make(max_bytes=30)
    for index in range(3):
        cache.put(f"k{index}", "x" * 12)

    cache.clear()

    assert cache.stats()["bytes"] == 0
    assert cache.stats()["byteEvictions"] == 1
    assert len(cache) == 0
