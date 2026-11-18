# 0019 — Back-pressure, a real memory ceiling, and network-only log labels

- **Status:** Accepted
- **Date:** 2026-11-18

## Context

Four places where the service quietly trusted its inputs or its environment:

1. `event_stream()` used an unbounded `asyncio.Queue()`. A provider that emits
   faster than a browser reads - or a client that stops reading but keeps the
   socket open - grows the queue for the whole length of an answer.
2. `ResponseCache` counted entries (`max_items=128`) and tracked bytes in
   `stats()`, but never *enforced* a byte ceiling. `max_items=128` still allows
   128 complete essays in memory; `bytes` was an observation, not a limit.
3. Three log lines wrote the full client IP (`ip=%s`). Logs are kept to spot a
   misbehaving network, and a full address is personal data that the log
   readers do not need.
4. `/api/health` and `/api/usage` returned JSON with no cache-control header,
   so an operator could be shown a stale snapshot from a browser cache. At the
   same time a middleware overwrote the SSE response's `no-cache,
   no-transform` with plain `no-store`, silently dropping the directive that
   stops proxies from rewriting a stream.

## Decision 1 — Bound the stream queue

`DREAMAI_STREAM_QUEUE_SIZE` (default 64, clamped to 8..512) sets the `maxsize`
of the queue created by `stream_queue()`. `put()` now waits when the writer is
behind, which back-pressures the pump and therefore the upstream generator.
The 12-second `wait_for(queue.get())` heartbeat is unchanged: a silent upstream
still produces `: ping` lines.

Rejected: dropping tokens when the queue is full. A chat answer is not a
metric; a gap in the middle would be worse than a slow answer.

## Decision 2 — Enforce the byte budget

`ResponseCache(max_bytes=...)` defaults to 4 MiB and `DREAMAI_CACHE_MAX_BYTES`
can set 0 (off) or up to 64 MiB. `put()`:

- refuses a single answer larger than the whole budget, so one essay cannot
  evict every other entry just to be stored;
- evicts least-recently-used entries while either ceiling is exceeded;
- counts byte-driven evictions separately from count-driven ones.

Stats gain `maxBytes`, `byteEvictions` and `byteFull`; the startup checks warn
on a budget under 64 KiB (`cache_bytes_small`). Unknown models and short
answers keep the old behaviour.

Rejected: a fixed number of characters. UTF-8 CJK text occupies three bytes per
character; only encoded bytes bound memory.

## Decision 3 — Log the network, not the host

`telemetry.mask_ip()` keeps the first two IPv4 octets (`1.2.x.x`) or the first
two IPv6 hextets (`2001:db8::`). The rate limiter still keys on the full
address; only the three log call sites changed. Unrecognised values pass
through, so proxy names remain readable.

## Decision 4 — State replies are not cacheable

Both status endpoints send `Cache-Control: no-store`. For `/api/chat` the
middleware now sends `no-store, no-transform`, and the stream responses carry
the same value: nothing caches the answer, and no proxy may rewrite its body.

## Consequences

- A slow reader now slows the upstream instead of growing memory. Very slow
  clients may see a longer answer; that is the intended trade-off.
- Cached entries may be evicted before `max_items` is reached. Read
  `cache.byteEvictions` rather than assuming the item count explains a miss.
- Logs no longer identify a single machine. Incident reports should quote the
  network prefix plus the request id.
- Clients that asserted the old `no-cache, no-transform` header verbatim must
  accept `no-store, no-transform`; the change is documented in `docs/API.md`.
