# 0016 — Recovery and continuity: what survives a bad minute and a restart

- **Status:** Accepted
- **Date:** 2026-11-13

## Context

Earlier rounds made the streaming path measurable (ADR 0012), cache-aware
(ADR 0014), and able to say why a reply stopped (ADR 0015). All of them assume
the process and its upstream are basically well behaved. Four cases break that
assumption, and all four were silent rather than loud:

1. A read timeout or a dropped connection produces **no HTTP status** at all.
   `stream_with_retry` asks `is_retryable(None)`, gets `False`, and shows the
   visitor an error for the most ordinary transient failure there is.
2. The upstream read timeout was a hard-coded `240.0` inside a shared
   `httpx.AsyncClient`. A gateway that legitimately takes longer had no knob.
3. The circuit breaker's `state` property *returned* `HALF_OPEN` after the
   cooldown but never **stored** it, so `record_failure()`'s half-open branch was
   dead code. Worse: if a half-open probe's request was cancelled mid-stream,
   neither `record_success` nor `record_failure` ran, `_probe_in_flight` stayed
   `True`, and every later request was refused forever.
4. `/api/usage` is process-lifetime. Restart the service and the weekly traffic,
   cost and truncation totals all read zero, which makes a trend impossible to
   see and an incident impossible to reconstruct.

## Decision 1 — Give transport failures a status

`llm._stream_raw` maps `httpx.TimeoutException` to `408` and other
`httpx.HTTPError` to `503`, both already in `RETRYABLE_STATUS`. The retry layer
may therefore do its one retry **before the first token**. `is_retryable` now
accepts `int | None` and documents that an unknown status still fails fast; a
blanket "retry everything without a status" would double a request whose outcome
nobody can determine. Failed turns append `status=<code>` to the log line.

## Decision 2 — Timeout is a request-level operator setting

`DREAMAI_UPSTREAM_READ_TIMEOUT` (default 240, clamped to 10..900) becomes
`Settings.upstream_read_timeout` and is passed to both the primary and fallback
upstreams. The value is applied as a **request-level** `httpx.Timeout` on
`client.stream(...)`, not to the shared client: rebuilding the connection pool
for one slow model would drop every other in-flight stream.

Rejected: one timeout per model/tier. The tier already selects `max_tokens`, and
a second knob with the same name would be more confusing than useful.

## Decision 3 — Make the breaker's state machine real

`state` now lazily migrates `OPEN -> HALF_OPEN` and stores it, so the half-open
branch of `record_failure` is reachable. `allow()` timestamps a probe; if no
answer arrives within one cooldown, the slot is released and a new probe may go
out. A cancelled request can no longer pin the breaker.

## Decision 4 — Optional, aggregate-only usage snapshots

`state_store.py` writes a versioned JSON envelope with `os.replace`, so a reader
never sees a partial file and a crash leaves the last good snapshot. It is off
by default (`DREAMAI_USAGE_STATE`); writes happen on shutdown and every 25
turns; failures are non-fatal.

`UsageStats.export_counters()` contains only aggregates and raw accumulators -
no IP, message, request id, or derived ratio. `import_counters()` validates
every field before applying any of them (finite, non-negative, correct types),
tolerates unknown keys, fills missing model fields from the default slot, and
**never imports `started_at`**: uptime belongs to the process running now.
`/api/usage` reports `usagePersisted` so an operator can see whether the switch
took effect.

Rejected: writing on every request (a disk write in the hot path for a
dashboard number); a database (a second system to operate for one file);
importing partially valid data (a plausible-looking wrong total is worse than
zero).

## Consequences

- A slow upstream may now be retried once, adding at most one bounded wait
  before any token is sent.
- `DREAMAI_UPSTREAM_READ_TIMEOUT` and `DREAMAI_USAGE_STATE` join the operator
  switches in `docs/OPERATIONS.md`.
- CI now format-checks `web/app` and no longer runs `desktop/test/update.test.js`
  twice.
- A snapshot file is deliberately **not** a backup of the service: it is a
  counter file, and a corrupt one is ignored with a log line rather than
  preventing startup.
