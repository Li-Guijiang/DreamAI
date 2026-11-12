"""The cache must be exact, bounded and time-limited."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))

from app.cache import ResponseCache, make_key  # noqa: E402

MSGS = [{"role": "user", "content": "你好"}]


class FakeClock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t


def test_same_request_gives_the_same_key():
    a = make_key("openai", "gpt-4o-mini", MSGS, 0.2, 512)
    b = make_key("openai", "gpt-4o-mini", MSGS, 0.2, 512)

    assert a == b


def test_key_changes_with_model_messages_and_params():
    base = make_key("openai", "gpt-4o-mini", MSGS, 0.2, 512)

    assert base != make_key("deepseek", "gpt-4o-mini", MSGS, 0.2, 512)
    assert base != make_key("openai", "gpt-4o", MSGS, 0.2, 512)
    assert base != make_key("openai", "gpt-4o-mini", [{"role": "user", "content": "嗨"}], 0.2, 512)
    assert base != make_key("openai", "gpt-4o-mini", MSGS, 0.7, 512)


def test_hit_returns_the_stored_answer():
    cache = ResponseCache()
    key = make_key("openai", "m", MSGS, 0.2, 256)

    cache.put(key, "答案是 A。")

    assert cache.get(key) == "答案是 A。"
    assert cache.hits == 1


def test_miss_counts_and_returns_none():
    cache = ResponseCache()

    assert cache.get("nope") is None
    assert cache.misses == 1


def test_expired_entry_is_dropped():
    clock = FakeClock()
    cache = ResponseCache(ttl=10, clock=clock)
    cache.put("k", "v")

    clock.t = 11

    assert cache.get("k") is None


def test_least_recently_used_is_evicted():
    cache = ResponseCache(max_items=2)
    cache.put("a", "1")
    cache.put("b", "2")
    cache.get("a")  # a becomes most recent
    cache.put("c", "3")

    assert cache.get("a") == "1"
    assert cache.get("b") is None
    assert cache.get("c") == "3"


def test_empty_answer_is_not_cached():
    cache = ResponseCache()
    cache.put("k", "")

    assert len(cache) == 0


def test_capacity_evictions_are_counted_separately_from_misses():
    from app.cache import ResponseCache

    cache = ResponseCache(max_items=2, ttl=60.0)
    cache.put("a", "1")
    cache.put("b", "2")
    cache.put("c", "3")

    assert cache.evictions == 1
    assert cache.misses == 0
    assert len(cache) == 2


def test_an_expired_entry_is_a_miss_and_an_expiry():
    from app.cache import ResponseCache

    now = [0.0]
    cache = ResponseCache(max_items=2, ttl=10.0, clock=lambda: now[0])
    cache.put("a", "1")
    now[0] = 11.0

    assert cache.get("a") is None
    assert cache.expired == 1
    assert cache.misses == 1
    assert cache.evictions == 0


def test_the_snapshot_says_how_full_the_cache_is():
    from app.cache import ResponseCache

    cache = ResponseCache(max_items=2, ttl=60.0)
    cache.put("a", "1")
    cache.put("b", "2")
    cache.put("a", "1")
    cache.get("a")

    snapshot = cache.stats()

    assert snapshot["items"] == 2
    assert snapshot["capacity"] == 2
    assert snapshot["full"] is True
    assert snapshot["hits"] == 1
    assert snapshot["hitRate"] == 1.0


def test_an_empty_cache_reports_a_zero_hit_rate_rather_than_dividing_by_zero():
    from app.cache import ResponseCache

    assert ResponseCache().stats()["hitRate"] == 0.0


def test_a_zero_ttl_turns_the_cache_off():
    from app.cache import ResponseCache

    cache = ResponseCache(max_items=8, ttl=0)
    cache.put("a", "1")

    assert cache.get("a") is None
    assert len(cache) == 0
    assert cache.enabled is False
    assert cache.stats()["enabled"] is False


def test_a_disabled_cache_does_not_count_misses_as_traffic():
    from app.cache import ResponseCache

    cache = ResponseCache(max_items=8, ttl=0)

    assert cache.get("a") is None
    assert cache.misses == 0


def test_the_snapshot_counts_utf8_bytes_not_characters():
    cache = ResponseCache()
    cache.put("a", "abc")  # 3 bytes
    cache.put("b", "你好")  # 6 bytes

    snapshot = cache.stats()

    assert snapshot["bytes"] == 9
    assert snapshot["avgBytes"] == 4.5


def test_replacing_a_key_does_not_double_count_it():
    cache = ResponseCache()
    cache.put("a", "abc")
    cache.put("a", "abcde")

    assert cache.stats()["bytes"] == 5


def test_an_evicted_entry_releases_its_bytes():
    cache = ResponseCache(max_items=2)
    cache.put("a", "12345")
    cache.put("b", "12")
    cache.put("c", "1")

    assert cache.stats()["bytes"] == 3
    assert cache.stats()["items"] == 2


def test_an_expired_entry_releases_its_bytes():
    clock = FakeClock()
    cache = ResponseCache(ttl=10, clock=clock)
    cache.put("a", "12345")
    clock.t = 11

    assert cache.get("a") is None
    assert cache.stats()["bytes"] == 0


def test_clear_releases_the_bytes_but_keeps_the_counters():
    cache = ResponseCache()
    cache.put("a", "12345")
    cache.get("a")
    cache.clear()

    snapshot = cache.stats()

    assert snapshot["bytes"] == 0
    assert snapshot["avgBytes"] == 0
    assert snapshot["hits"] == 1
