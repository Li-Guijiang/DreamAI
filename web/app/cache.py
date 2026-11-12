"""Exact-match response cache for low-temperature turns.

Semantic caches are tempting and dangerous: "cancel my order" and "don't cancel my
order" sit close together in embedding space. This module deliberately does the
boring thing - the same provider, model, messages and parameters must hash to the
same key - and is only used for deterministic settings.

Entries expire on a TTL and are evicted least-recently-used first, so a long-lived
process cannot grow without bound.

A TTL of zero (or less) turns the cache off entirely: gets and puts become no-ops
that cost one attribute check. This is the documented way to disable caching when a
provider's answers change per call - a flag beats deleting lines.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections import OrderedDict
from collections.abc import Callable, Sequence


def make_key(
    provider: str,
    model: str,
    messages: Sequence[dict[str, str]],
    temperature: float,
    max_tokens: int,
) -> str:
    """Stable hash of everything that influences the answer."""
    payload = json.dumps(
        {
            "p": provider,
            "m": model,
            "t": round(temperature, 2),
            "n": max_tokens,
            "msg": [{"r": m.get("role"), "c": m.get("content")} for m in messages],
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _size(value: str) -> int:
    """Bytes an answer actually occupies, so CJK text is not counted as ASCII."""
    return len(value.encode("utf-8"))


class ResponseCache:
    """Small TTL + LRU cache; values are finished answers, not deltas."""

    def __init__(
        self,
        max_items: int = 128,
        ttl: float = 300.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.max_items = max(1, max_items)
        self.ttl = max(0.0, ttl)
        self.enabled = self.ttl > 0
        self._clock = clock
        self._items: OrderedDict[str, tuple[str, float]] = OrderedDict()
        self.hits = 0
        self.misses = 0
        # Answers are stored in memory for minutes at a time. Counting items
        # alone says nothing about how much RAM that is: one cached essay can be
        # worth a hundred cached greetings. Sizes are UTF-8 bytes, not chars.
        self._bytes = 0
        # A miss because nobody asked yet, a miss because the entry aged out and
        # a capacity eviction mean different things; only the last two say the
        # cache is too small or the TTL too short.
        self.expired = 0
        self.evictions = 0

    def get(self, key: str) -> str | None:
        if not self.enabled:
            return None
        entry = self._items.get(key)
        if entry is None:
            self.misses += 1
            return None
        value, expires_at = entry
        if self._clock() >= expires_at:
            del self._items[key]
            self._bytes -= _size(value)
            self.misses += 1
            self.expired += 1
            return None
        self._items.move_to_end(key)
        self.hits += 1
        return value

    def put(self, key: str, value: str) -> None:
        if not self.enabled or not value:
            return
        old = self._items.get(key)
        if old is not None:
            self._bytes -= _size(old[0])
        self._items[key] = (value, self._clock() + self.ttl)
        self._bytes += _size(value)
        self._items.move_to_end(key)
        while len(self._items) > self.max_items:
            _, (evicted, _) = self._items.popitem(last=False)
            self._bytes -= _size(evicted)
            self.evictions += 1

    def stats(self) -> dict:
        """What both status endpoints report about the cache."""
        asked = self.hits + self.misses
        return {
            "enabled": self.enabled,
            "items": len(self._items),
            "capacity": self.max_items,
            "bytes": self._bytes,
            "avgBytes": round(self._bytes / len(self._items), 1) if self._items else 0,
            "ttl": self.ttl,
            "hits": self.hits,
            "misses": self.misses,
            "expired": self.expired,
            "evictions": self.evictions,
            # Share of answers that cost nothing; 0.0 before anything is asked.
            "hitRate": round(self.hits / asked, 3) if asked else 0.0,
            "full": len(self._items) >= self.max_items,
        }

    def clear(self) -> None:
        """Drop the entries, keeping the lifetime hit/miss counters."""
        self._items.clear()
        self._bytes = 0

    def __len__(self) -> int:
        return len(self._items)
