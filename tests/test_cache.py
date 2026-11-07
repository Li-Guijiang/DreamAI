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
    cache.get("a")          # a becomes most recent
    cache.put("c", "3")

    assert cache.get("a") == "1"
    assert cache.get("b") is None
    assert cache.get("c") == "3"


def test_empty_answer_is_not_cached():
    cache = ResponseCache()
    cache.put("k", "")

    assert len(cache) == 0
