# 0021 — Heartbeats, admission deadlines and counted recovery

- **Status:** Accepted
- **Date:** 2026-11-20

## Context

Three timings in a chat request were either hard-coded or invisible.

1. The SSE heartbeat was a literal `12` inside the read loop. A deployment
   behind a proxy with a 10-second idle timeout had no way to shorten it
   without a code change; nothing warned that a longer value defeats the
   heartbeat entirely.
2. `async with _semaphore` waited forever for a concurrency slot. From outside,
   a queued request and a hung upstream looked identical: neither an answer nor
   an error. The wait was not measured, so queueing could not be told apart
   from a slow provider.
3. `stream_with_retry()` and `stream_with_fallback()` worked correctly but only
   logged. A successful retry produced one `requests` count while making two
   upstream calls, so provider traffic could not be reconciled with the
   dashboard.

A smaller gap: configured model ids were sent verbatim to providers without a
check, so an id containing a space or a control character failed on the first
chat instead of at boot.

## Decision 1 — Configure the heartbeat

`DREAMAI_HEARTBEAT_SECONDS` (default 12, clamped to 1..120) is the timeout of
the consumer's `wait_for(queue.get())`. Values over 60 produce the
`heartbeat_long` finding, since many proxies close an idle connection first.
The heartbeat remains an SSE comment line, not an event.

## Decision 2 — Deadline the admission wait

`DREAMAI_ADMISSION_TIMEOUT` (default 10 seconds, `0` = wait indefinitely as
before) bounds the semaphore acquire. `admit_request()` is an async context
manager: it records the wait, holds the slot for the whole stream and releases
it in `finally`. A timeout raises `AdmissionTimeout`, which yields an `error`
frame with `code=concurrency_limit` and `retryable=true` - no `done`, no
breaker failure.

The wait is recorded separately from TTFT: `admissionWaitAvg` /
`admissionWaitMax` / `admissionWaitSamples`. A timeout calls
`record_admission_timeout()`, which increments `admissionTimeouts`, `blocked`
and `requests`. Because the request never reached a model, it has no
`byModel` row, so the existing reconciliation still holds.

Rejected: rejecting at HTTP level before the stream opens. That would change
the response contract for a condition discovered mid-connection, and would
lose the request's place in the queue.

## Decision 3 — Count retries and fallbacks

`stream_with_retry()` accepts `on_retry(status)` and `stream_with_fallback()`
accepts `on_fallback()`. Both are optional, so every existing caller and test
keeps working. The chat route passes the counters' methods directly.

`UsageStats` gains `retries`, `retriesByStatus` and `fallbacks`, all persisted
in the snapshot and published on `/api/usage`. These are *extra upstream
requests*, not extra chat turns, so they deliberately do not change
`requests` or the reconciliation rules.

Rejected: counting retries as failures. A retry that ends in a successful
answer is a success from the visitor's point of view; only the provider saw
the extra call.

## Decision 4 — Validate model ids

`check_model_id()` rejects empty ids, whitespace, values over 128 characters
and control characters. `model_id_invalid` joins the startup findings; like
the URL finding, it reports a reason and never echoes the value.

## Consequences

- A heavily loaded site now returns a fast, typed refusal instead of an
  endlessly pending stream. Set `DREAMAI_ADMISSION_TIMEOUT=0` to restore the
  old behaviour.
- `/api/usage` gains seven fields. Clients that enumerate keys strictly must
  be updated; unknown-field-tolerant clients are unaffected.
- `blocked` now includes admission refusals as well as breaker refusals.
  `failures` still includes them, preserving the existing invariant.
- Retry counts explain a provider bill that exceeds `requests`; a high
  `retriesByStatus["503"]` points at the upstream, not at the site's router.
