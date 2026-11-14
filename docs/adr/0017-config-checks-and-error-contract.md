# 0017 — Startup checks, a typed error contract, and failures that actually arrive

- **Status:** Accepted
- **Date:** 2026-11-14

## Context

Previous rounds made the service measurable and recoverable, but three gaps
remained in how it *reports* trouble. One of them was a real functional bug.

1. **A failed upstream looked like an empty success.** `event_stream()` starts a
   background `_pump()` task to feed an `asyncio.Queue`. That task had a
   `finally: queue.put(None)` but no error channel. When `stream_with_retry`
   exhausted its attempts and raised `LLMError`, the exception stayed inside the
   pump task, the sentinel told the request loop to break, and the visitor
   received a clean `done` with `chars=0` and no `error` frame. The circuit
   breaker never recorded the failure either, because the request loop's
   `except LLMError` was never reached.
2. **Error events were prose only.** `{"message": "…中文句子…"}` is right for a
   chat bubble but useless to a client deciding whether to retry. Deriving a
   category from the sentence would break the moment an editor reworded it.
3. **Configuration mistakes were silent.** A half-configured fallback sits idle
   until the primary fails; a malformed `DREAMAI_PRICE_OVERRIDES` entry is
   skipped by the parser with no trace; a breaker cooldown far shorter than one
   read timeout sends probes into requests that have not finished yet.
4. **Private owner turns entered the shared answer cache.** The dossier text is
   already part of the system prompt and therefore part of the cache key, but a
   private answer should not live in a shared in-memory cache at all.

## Decision 1 — Treat the pump's exception as data

`_pump()` now catches `Exception` and puts it on the same queue as the stream
items; the request loop re-raises it before unpacking `(kind, text)`. A failure
therefore reaches the existing `except LLMError` branch, yields an `error` frame,
records the failure on the breaker, and produces no `done`.

Rejected: awaiting the pump task directly (it would give up the 12-second
heartbeat): a separate error queue (two queues to drain); letting the task
exception surface through `asyncio` logging (the visitor still sees nothing).

## Decision 2 — A typed, backward-compatible `error` event

`errors.error_payload()` keeps `message` unchanged and adds `code`, `status` and
`retryable`. `code` comes from `error_code(status)`: `auth`, `payload`,
`rate_limit`, `address`, `upstream`, `internal`; a breaker refusal uses the
explicit code `breaker`. `retryable` defaults to the same `is_retryable()`
policy the server uses, so the client and the server never disagree. An empty
sentence falls back to the generic one, so no client renders a blank bubble.

The three call sites - open breaker, upstream failure, unexpected exception -
all go through the builder. `docs/API.md` is the contract; a test parses its
machine-readable event list and checks it against the `sse(...)` calls in
`main.py`, so the document cannot silently drift.

## Decision 3 — Named startup checks, visible but non-blocking

`validation.check_settings()` returns `Check(code, severity, message)` findings
for a partial fallback, an implausible cooldown, a daily cap below one rate
window, an empty system prompt, impossible concurrency, a tiny cache, a short
rate window, ignored price overrides, and three informational opt-in/opt-out
states. It runs at startup, logs one summary line plus one line per finding, and
is published as `/api/health.configChecks`.

Nothing blocks startup, and no finding contains a key, a credential-bearing
URL, or the system prompt. `pricing.invalid_price_overrides()` reports exactly
the entries the parsers would otherwise skip.

## Decision 4 — Keep private turns out of the cache

Owner requests bypass response caching entirely, and `verify_cookie()` refuses
a signed cookie whose expiry is zero or negative. The latter is defence in
depth - the signature already protects the field - but an explicit boundary is
easier to audit than an implicit `< now`.

## Consequences

- A failed upstream now produces an `error` frame and a breaker failure. This
  changes what visitors see: an error sentence instead of an empty reply.
- Clients can branch on `code` / `retryable` without parsing Chinese text; old
  clients reading only `message` are unaffected.
- `configChecks` is a read-only, secret-free array; a warning is information,
  not a refusal to serve.
- Owner answers are never cached, so a dossier edit cannot serve a stale
  private reply.
