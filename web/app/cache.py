"""Exact-match response cache for low-temperature turns.

Semantic caches are tempting and dangerous: "cancel my order" and "don't cancel my
order" sit close together in embedding space. This module deliberately does the
boring thing - the same provider, model, messages and parameters must hash to the
same key - and is only used for deterministic settings.

Entries expire on a TTL and are evicted least-recently-used first, so a long-lived
process cannot grow without bound. Two independent ceilings apply: a number of
entries and a number of UTF-8 bytes. Counting entries alone is not enough - one
cached essay can weigh as much as a hundred cached greetings.

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


DEFAULT_MAX_BYTES = 4 * 1024 * 1024


class ResponseCache:
    """Small TTL + LRU cache; values are finished answers, not deltas."""

    def __init__(
        self,
        max_items: int = 128,
        ttl: float = 300.0,
        clock: Callable[[], float] = time.monotonic,
        max_bytes: int = DEFAULT_MAX_BYTES,
    ) -> None:
        self.max_items = max(1, max_items)
        self.ttl = max(0.0, ttl)
        self.enabled = self.ttl > 0
        # Zero disables the byte ceiling; anything else is a hard budget.
        self.max_bytes = max(0, max_bytes)
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
        # Entries removed by prune() rather than by a get() that noticed them.
        # A high number means many answers are never asked for a second time.
        self.pruned = 0
        self.evictions = 0
        # Evictions caused by the byte budget, separated from the ones caused by
        # the item count: they point at different knobs to turn.
        self.byte_evictions = 0

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

    def prune(self) -> int:
        """Remove entries nobody will ask for again.

        ``get()`` only expires the key it was asked about. A key that is never
        requested again keeps its slot until an LRU eviction throws away a
        *fresh* answer instead. Pruning before an insert keeps capacity for
        entries that are still alive.
        """
        if not self.enabled:
            return 0
        now = self._clock()
        removed = 0
        for key, (value, expires_at) in list(self._items.items()):
            if now < expires_at:
                continue
            del self._items[key]
            self._bytes -= _size(value)
            self.expired += 1
            self.pruned += 1
            removed += 1
        return removed

    def put(self, key: str, value: str) -> None:
        if not self.enabled or not value:
            return
        self.prune()
        size = _size(value)
        if self.max_bytes and size > self.max_bytes:
            # One answer larger than the whole budget must not evict every other
            # entry just to hold a single one. Skip it and keep serving misses.
            return
        old = self._items.get(key)
        if old is not None:
            self._bytes -= _size(old[0])
        self._items[key] = (value, self._clock() + self.ttl)
        self._bytes += size
        self._items.move_to_end(key)
        while len(self._items) > self.max_items or (
            self.max_bytes and self._bytes > self.max_bytes
        ):
            over_bytes = bool(self.max_bytes and self._bytes > self.max_bytes)
            _, (evicted, _) = self._items.popitem(last=False)
            self._bytes -= _size(evicted)
            self.evictions += 1
            if over_bytes:
                self.byte_evictions += 1

    def stats(self) -> dict:
        """What both status endpoints report about the cache."""
        asked = self.hits + self.misses
        return {
            "enabled": self.enabled,
            "items": len(self._items),
            "capacity": self.max_items,
            "bytes": self._bytes,
            "maxBytes": self.max_bytes,
            "byteEvictions": self.byte_evictions,
            "avgBytes": round(self._bytes / len(self._items), 1) if self._items else 0,
            "ttl": self.ttl,
            "hits": self.hits,
            "misses": self.misses,
            "expired": self.expired,
            "pruned": self.pruned,
            "evictions": self.evictions,
            # Share of answers that cost nothing; 0.0 before anything is asked.
            "hitRate": round(self.hits / asked, 3) if asked else 0.0,
            "full": len(self._items) >= self.max_items,
            "byteFull": bool(self.max_bytes and self._bytes >= self.max_bytes),
        }

    def clear(self) -> None:
        """Drop the entries, keeping the lifetime hit/miss counters."""
        self._items.clear()
        self._bytes = 0

    def __len__(self) -> int:
        return len(self._items)
