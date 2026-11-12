# 0014 — Cache-aware accounting: the same tokens, the right price

- **Status:** Accepted
- **Date:** 2026-11-12

## Context

ADR 0012 made the token counts real: the stream asks for `include_usage`, the
three wire formats are parsed into one `usage` event, and one estimate feeds the
counters, the done event and the log. That is correct as far as it goes, and it
still bills prompt caching wrong.

All four vendors in the price table now cache prompts, and each describes the
result differently:

1. **OpenAI-compatible** reports `prompt_tokens_details.cached_tokens` *inside*
   `prompt_tokens`. The cached part is billed at half the input price.
2. **DeepSeek** puts `prompt_cache_hit_tokens` at the top level of `usage`, also
   inside the prompt, billed at roughly a quarter.
3. **Anthropic** reports `cache_read_input_tokens` and
   `cache_creation_input_tokens` *outside* `input_tokens`. A cache read costs a
   tenth of the input price, a cache write a quarter *more* than it.
4. **Gemini** reports `cachedContentTokenCount` inside `promptTokenCount`, plus
   `thoughtsTokenCount` outside `candidatesTokenCount`.

So the same "prompt tokens" number means three different things, and the same
"cached tokens" number is worth four different amounts. Two consequences:

- A cached Anthropic turn under-reported its prompt, because the cache read was
  in neither `input_tokens` nor any other field we read.
- Every cached turn was priced at the full input rate, so the site reported a
  bill up to ten times the real one on exactly the turns that caching exists to
  make cheap.

A Gemini turn had the opposite problem: thinking tokens are billed as output and
were not counted at all.

## Decision 1 — Normalise on the way in, once

`adapters.usage_from_chunk` returns a mapping with three possible keys, and is
the only place that knows a vendor's spelling:

| Key | Meaning | Relation to `prompt_tokens` |
|---|---|---|
| `prompt_tokens` | everything that went in | total |
| `completion_tokens` | everything that came out, thinking included | total |
| `cached_tokens` | the part of the prompt a cache served | **subset** |

Anthropic's two cache fields are summed into `prompt_tokens`; only the read side
is also reported as `cached_tokens`, because that is the discounted part. Gemini's
thinking tokens are added to `completion_tokens`. Both adjustments happen at the
boundary, so nothing downstream has to branch on the vendor.

Rejected: reporting `cached_tokens` on top of `prompt_tokens`. It reads well in a
table and double-bills in a sum.

## Decision 2 — Price the cached part at the cached rate

`pricing.CACHE_PRICES` holds a separate USD/1M figure per model, and
`estimate_cost(..., cached=)` splits the prompt into the two rates. A model with
no published cache price is billed at the full input price: an unknown discount
is assumed to be no discount, which overstates the bill rather than flattering
it. A `cached` count larger than the prompt is clamped, so a provider that
reports the two inconsistently cannot reduce the total.

Rejected: one global multiplier. It would be right for at most one vendor, since
the real ratios are 0.5, 0.26, 0.1 and 0.25.

Rejected: modelling the Anthropic cache *write* premium (1.25×). It would need a
fourth counter that no other vendor has, to correct a number by 25% on the rarer
of the two cache paths. The write is folded into `prompt_tokens` at list price,
and this ADR is the note that says so.

## Decision 3 — The local surfaces keep a ledger

`dream_ai/usage.py` holds a `SessionUsage` per agent and is fed by the provider's
`last_usage`, which `OpenAICompatProvider` fills from the SDK response. It
carries the same three totals plus two admissions: `unmeasured` (the provider
reported nothing) and `unpriced` (the model is not in the table). Either one
turns `costKnown` false and makes `/stats` print "at least …" instead of a number
that looks complete.

Rejected: estimating tokens from character counts for providers that report
nothing. An estimate that sits in the same column as a measurement is worse than
a blank, because it is not marked as a guess.

## Consequences

- `/api/usage` gains `cachedTokens` and `cachedShare`; each model row carries its
  own `cachedTokens`. The share is the useful number: 20k cached out of 1M is
  noise, 20k out of 25k is the cache working.
- The price table exists twice (`dream_ai/pricing.py`, `web/app/pricing.py`)
  because the CLI must install without the web app. `tests/test_price_parity.py`
  compares both tables and seven arithmetic cases, so a change to one without the
  other fails the build.
- `DREAMAI_PRICE_OVERRIDES` accepts an optional third number for the cached
  price: `model=2.5,10,1.25`. Two numbers leave the cache price untouched rather
  than silently asserting it is unchanged.
- A cache hit is now filed under the pseudo-provider `cache` in `byProvider`, so
  the vendor totals still add up to `requests` without inflating a real vendor.
