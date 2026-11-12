# 0015 — Finishing a stream: know why it stopped

- **Status:** Accepted
- **Date:** 2026-11-12

## Context

An SSE stream ending cleanly does not mean the answer is complete. When a model
hits its `max_tokens` budget it stops just as politely as when it decides it is
done: the connection closes, the last delta looks normal, and the browser renders
a half sentence. Before this change nothing in the service could tell the two
apart, which produced three concrete problems:

1. A truncated answer was treated as a finished turn and written into the
   exact-match response cache. Every later visitor asking the same question
   received the same half answer until the TTL expired.
2. `/api/usage` had no way to answer "are the tier budgets too tight?", so a
   rising number of cut-off replies was indistinguishable from normal traffic.
3. A content-filter stop and a token-budget stop both looked like "the stream
   ended", though one is an incident and the other is a tuning decision.

The three vendors put the reason in different places: OpenAI uses
`choices[0].finish_reason`, Anthropic uses `delta.stop_reason` on the
`message_delta` event, and Gemini uses `candidates[0].finishReason`. Their
vocabularies differ as well (`length` / `max_tokens` / `MAX_TOKENS`).

## Decision 1 — Normalise at the wire boundary, emit one event

`adapters.finish_from_chunk` returns one of four words - `length`, `stop`,
`filter`, `other` - or `None` when a chunk carries no reason. `llm._stream_raw`
keeps the last non-empty reason and emits a single `("finish", reason)` item
after the usage event. Both `usage` and `finish` are control events and bypass
`coalesce`; merging either into a run of text would put the word `length` into
the visitor's answer.

Unknown vendor reasons become `other` rather than being discarded, so a new
value is visible in `byFinish` instead of silently looking like a clean finish.
An explicitly unspecified reason (Gemini's `FINISH_REASON_UNSPECIFIED`) is
treated as "no reason", not as a finish.

## Decision 2 — Extend `done`, do not add a new SSE event

The chat loop consumes the `finish` item and puts `finish` and `truncated` on the
existing `done` event. The browser's event vocabulary stays exactly as it was,
which keeps the frontend untouched. The log line gains `finish=<word>`, so a
slow or short turn can be explained without opening the API.

## Decision 3 — A truncated answer is never cached

`_cache.put` is skipped when the reason is `length`. Response caching is an
exact-match optimisation for deterministic answers; a half answer is neither
deterministic nor finished. This is the single behavioural change a visitor
could notice: asking again now goes upstream and can produce the whole answer.

Rejected: caching it with a shorter TTL. A short TTL still replays a broken
answer, and the client has no way to know that it should ask again.

## Decision 4 — Count it where an operator can act on it

`UsageStats` records `truncated`, `truncationRate`, `truncatedByTier` and
`byFinish`. The tier split is the useful one: if only deep turns are truncated,
the fix belongs in the deep budget, not in the global `max_tokens`.

The local surfaces mirror the same normalisation in `dream_ai/finish.py`, the
hosted provider exposes `last_finish`, and the session ledger counts truncated
turns for `/stats`. `tests/test_finish_parity.py` runs the same corpus through
both copies, as the difficulty rules and the price tables already do.

Rejected: automatically retrying a truncated turn with a larger budget. Text
has already been streamed; a second attempt would splice two answers together
(ADR 0005). Rejected equally: buffering the whole reply so it can be inspected
first, which gives up streaming.

## Consequences

- `done.truncated` is always a boolean, even when the provider said nothing;
  `done.finish` is present only when a reason was reported.
- A cache miss is not a failure: a truncated turn carries no `X-Cache: HIT` on a
  repeat, by design.
- `/api/usage` now answers three separate questions: how many replies were cut
  off (`truncated`), which tier cap caused it (`truncatedByTier`), and whether
  any replies were stopped by a safety filter (`byFinish.filter`).
