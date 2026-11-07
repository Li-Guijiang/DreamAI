# 0007 — Serving behaviour: fail fast, repeat free, stay connected

- **Status:** Accepted
- **Date:** 2026-11-07

## Context

ADR 0005 and 0006 made a single answer better. Neither touched what happens
around it, and three operational failures were still visible to visitors:

1. when the provider was down, every request waited out the full timeout before
   failing — one outage became a minute of slow errors;
2. asking the same question twice paid twice, and the second answer drifted
   because sampling is stochastic even at low temperature;
3. a proxy drops a connection that is silent for 30–60 seconds, which a slow first
   token plus a long reasoning phase can exceed.

A fourth problem was internal: a bug report ("that answer was wrong") could not be
matched to a log line, because nothing tied the lines of one turn together.

## Decision 1 — Three-state breaker, fail before the first byte

`guard.CircuitBreaker` counts consecutive failures, opens at a threshold, and after
a cooldown allows exactly one probe. A second concurrent probe is refused, so a
recovering provider is not flooded.

The route checks `allow()` before opening the upstream stream and answers with a
short `error` plus a `done` carrying `blocked: true`. This is the only point where
refusing is honest: once a token is out, the client has already rendered part of an
answer, and a failover would splice two replies together.

## Decision 2 — Exact-match cache, not semantic

`cache.make_key` hashes provider, model, messages, temperature and budget. The cache
is TTL + LRU bounded, and is only consulted at temperature ≤ 0.3.

A semantic cache would hit more often and be wrong more often: "cancel my order"
and "don't cancel my order" are neighbours in embedding space. For a public site, a
wrong answer costs more than a saved call.

Cached turns replay as ordinary `delta` events, so the client needs no special case;
`meta.cache` reports `hit` or `miss` for anyone watching.

## Decision 3 — Heartbeat while the upstream is silent

The upstream iterator is pumped through an `asyncio.Queue`; the response loop waits
12 seconds for an item and, on timeout, emits an SSE comment (`: ping`). Browsers
ignore comment lines, proxies treat them as traffic, and the connection survives a
long reasoning phase.

Pumping has a second effect: cancelling the response cancels the pump, so the
upstream request stops instead of generating tokens nobody reads.

## Decision 4 — Request id and TTFT

Every turn mints `req_xxxxxxxx`, returns it in `X-Request-Id` and in the body, and
writes one structured line on completion:

```
chat done id=req_1a2b3c4d tier=deep intent=error ttft=0.84s total=6.21s chars=812 model=…
```

TTFT is the number the visitor feels; total is the number that appears on a bill.
Both are needed to tell "slow model" from "long answer".

## Decision 5 — Notice prompt injection, do not block it

`safety.detect_injection` matches override phrasings in both languages and, on a
hit, appends one guard sentence to the system prompt for that turn.

Blocking the message was rejected: it invites gaming and breaks legitimate text that
merely mentions the phrase. The patterns are narrow — a bare 忽略 is ordinary
Chinese and must not fire — and the request id is logged so attempts are visible.

## Consequences

- An outage degrades to a fast, explicit message instead of a slow timeout.
- Repeat questions cost nothing and return byte-identical text.
- Long reasoning no longer trips proxy timeouts.
- `/api/health` reports `upstream` state and cache counters, so "the site is slow"
  can be answered without reading logs first.
- The knobs (`DREAMAI_BREAKER_*`, `DREAMAI_CACHE_*`) are environment variables;
  defaults are tuned for one small provider, not for a fleet.
