"""Exact-match response cache for low-temperature turns.

Semantic caches are tempting and dangerous: "cancel my order" and "don't cancel my
order" sit close together in embedding space. This module deliberately does the
boring thing - the same provider, model, messages and parameters must hash to the
same key - and is only used for deterministic settings.

Entries expire on a TTL and are evicted least-recently-used first, so a long-lived
process cannot grow without bound.
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


class ResponseCache:
    """Small TTL + LRU cache; values are finished answers, not deltas."""

    def __init__(
        self,
        max_items: int = 128,
        ttl: float = 300.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.max_items = max(1, max_items)
        self.ttl = max(1.0, ttl)
        self._clock = clock
        self._items: OrderedDict[str, tuple[str, float]] = OrderedDict()
        self.hits = 0
        self.misses = 0

    def get(self, key: str) -> str | None:
        entry = self._items.get(key)
        if entry is None:
            self.misses += 1
            return None
        value, expires_at = entry
        if self._clock() >= expires_at:
            del self._items[key]
            self.misses += 1
            return None
        self._items.move_to_end(key)
        self.hits += 1
        return value

    def put(self, key: str, value: str) -> None:
        if not value:
            return
        self._items[key] = (value, self._clock() + self.ttl)
        self._items.move_to_end(key)
        while len(self._items) > self.max_items:
            self._items.popitem(last=False)

    def clear(self) -> None:
        self._items.clear()

    def __len__(self) -> int:
        return len(self._items)
