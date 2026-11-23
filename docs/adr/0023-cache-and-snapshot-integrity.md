# 0023 — Cache and snapshot integrity

- **Status:** Accepted
- **Date:** 2026-11-23

## Context

Two subsystems treated "nothing went wrong" as "everything is fine".

1. `ResponseCache` expired an entry only when someone asked for that exact
   key. A key never repeated held its slot until LRU eviction, which then
   discarded a still-live answer. `stats()["items"]` counted those stale
   entries, so the number did not describe available capacity. The key also
   covered `temperature` but not `top_p` or `presence_penalty`, even though
   both change the generated text.
2. The usage snapshot was written atomically and validated on import, but its
   outcome was invisible. A missing file, a truncated file and a file rejected
   by validation all produced the same log shape, and `/api/usage` only said
   whether a path was configured. There was no periodic flush, so a crash
   could lose everything since the last shutdown.

## Decision 1 — Reclaim before evicting

`ResponseCache.put()` calls `prune()` first: expired entries are removed, their
bytes returned to the budget, and both `expired` and a new `pruned` counter are
incremented. Live entries are no longer evicted to make room for dead ones.
`stats()` adds `liveItems`, computed without mutating the cache.

Rejected: pruning on every `get()`. That would add a full scan to the hot path
for no benefit. Rejected: a background timer. The cache is small and writes
already provide a natural point to reclaim.

`DREAMAI_CACHE_TTL_JITTER` (default 0, clamped to 0..0.5) optionally adds a
per-entry random offset to the TTL. It is off by default because exact TTLs
are easier to reason about in tests and small deployments; it exists for
bursty sites where a synchronised expiry would otherwise become an upstream
spike. The active value is reported as `cache.ttlJitter`.

## Decision 2 — Hash every sampling parameter

`make_key()` adds `top_p` and `presence_penalty`, with defaults that keep
standalone callers compatible. Both may be `None` when the operator disables
them; the key encodes that explicitly instead of raising. The chat route
passes the configured values.

## Decision 3 — Report snapshot health, not just presence

`state_store.describe_snapshot()` classifies a configured path as `disabled`,
`absent`, `valid`, `corrupt`, `oversized`, `unreadable` or `tampered`. Snapshots
carry a checksum of their counters; a mismatch is `tampered`, while files
written before checksums existed remain readable. A non-finite counter is
never written, and files over 8 MiB are not parsed at startup.

`/api/usage.usageState` publishes `enabled`, `loadStatus`, `lastSaveAt` and
`saveFailures`. `DREAMAI_USAGE_SAVE_INTERVAL` (default 60s, `0` = shutdown
only) drives a periodic flush task that is cancelled before the final write.

Rejected: refusing chat requests when a snapshot fails. The snapshot is an
operational aid, not a source of truth for the current turn. Rejected:
treating a checksum as a security boundary - an attacker can recompute it;
it detects accidental edits and truncation.

## Consequences

- `cache.items` may exceed `cache.liveItems` between writes. Dashboards that
  care about usable capacity must read `liveItems`.
- A sampling-configuration change produces new cache keys, so the first turn
  after a change is a miss. That is correct: the old answer is not the answer
  the new settings would produce.
- An operator can tell a fresh install from a corrupted or edited snapshot and
  can see whether writes are still succeeding.
- Snapshot files written by this build have an extra `checksum` field; older
  builds ignore unknown fields and still load the counters.
