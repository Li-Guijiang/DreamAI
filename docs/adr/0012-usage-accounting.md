# 0012 — Usage accounting: make the numbers real

- **Status:** Accepted
- **Date:** 2026-11-11

## Context

The service reported `promptTokens`, `completionTokens` and `costUsd` since ADR
0008, and the turn log had a `cost=` field since ADR 0009. Neither was ever
populated from a live stream. Three independent reasons:

1. **The request never asked for usage.** OpenAI-compatible vendors only attach a
   final `usage` object when the request carries
   `stream_options.include_usage`. `adapters.build_request` did not send it.
2. **No parser existed.** `parse_chunk` deliberately returned only text deltas.
   The three wire formats report token counts in three different shapes: a final
   OpenAI `usage` object, Anthropic's split `message_start` / `message_delta`
   counters, and Gemini's camel-cased `usageMetadata` repeated on many chunks.
3. **The chat loop had a branch for a `usage` event that nothing emitted.**
   `main.py` already knew how to forward such an event to the browser and the
   cost table; the producer side was missing entirely.

A fourth defect sat in the accounting itself: `record_usage` was called without a
cost argument, which the stats module reads as "price unknown". That cleared
`costKnown` after every stream, while `cost_usd` was incremented separately by
hand — bypassing the per-model row.

## Decision 1 — Ask, parse, emit

`adapters.build_request` adds `stream_options.include_usage` for
OpenAI-compatible kinds, behind `DREAMAI_STREAM_USAGE` (default on) because a few
gateways reject the extra field. `usage_from_chunk` normalises all three shapes
to `prompt_tokens` / `completion_tokens`. `_stream_raw` accumulates with `max()`
and emits exactly one `usage` event after the last text delta.

`max()`, not "last one wins": Anthropic and Gemini report cumulative counters
which can repeat; a later smaller value must not erase a larger one.

## Decision 2 — Usage events bypass text coalescing

`coalesce()` merges consecutive items of the same kind. A usage event is a JSON
object; merging it with text (or with another usage event) yields a string that
cannot be parsed, and the cost silently stays unknown. Usage items are now
flushed through untouched.

## Decision 3 — One estimate feeds all three consumers

At the end of a turn, `estimate_cost` runs once. Its result goes to
`record_usage` (which updates the total, the per-model row and `costKnown`), the
`done` event and the log line. No direct writes to `_stats.cost_usd` remain.

A free model with a known price of zero keeps `costKnown=true`; a model absent
from the table clears it. No usage payload at all is not an unknown price — it is
absent data, and no flag is changed.

## Decision 4 — Prices are correctable at runtime

`PRICES` is a dated snapshot. `DREAMAI_PRICE_OVERRIDES` accepts
`model=input,output;...` and is applied at startup, with the corrected models
named in the log. Malformed or negative entries are skipped. This is deliberately
an override of a module-level table, not a per-request argument: the price of a
model is a property of the deployment, not of one turn.

## Alternatives rejected

- **Estimating tokens from characters.** Cheap and wrong by 2–4x for mixed
  Chinese / code input. It would have made the dashboard look alive while lying.
- **A semantic cache of costs by prompt.** The same prompt can produce a
  different number of output tokens; the vendor's own counters are the only
  honest source.
- **Failover usage merging.** A fallback happens before the first token, so only
  one upstream produces text. If both ever report usage, the last event wins and
  the log shows the model that answered.

## Consequences

- `/api/usage` now reports real tokens and cost after the first completed stream.
- When `DREAMAI_STREAM_USAGE=0`, token and cost fields stay at zero by design —
  the operator has chosen "streaming works on this gateway" over accounting.
- `costKnown=false` means "a model has no price", not "usage data is missing".
- An end-to-end test drives a fake usage event through `/api/chat` into
  `/api/usage`, so the producer and the consumer cannot drift apart again.
