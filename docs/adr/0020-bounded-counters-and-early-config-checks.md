# 0020 — Bounded counters and configuration errors found at boot

- **Status:** Accepted
- **Date:** 2026-11-19

## Context

Two growth paths and one class of silent configuration error remained.

1. `resolve_model()` deliberately accepts any custom model id: gateways expose
   names a static list cannot enumerate. `UsageStats._by_model` created a slot
   for every distinct name, so a client cycling random ids could grow both the
   in-memory table and the persisted snapshot without limit.
2. Importing a snapshot with more models than the local ceiling silently kept
   **only one** of the merged values: the import loop assigned rather than
   added, so every model folded into the overflow bucket overwrote its
   predecessor. A bounded table that loses data is worse than an unbounded one.
3. Upstream URLs and the system prompt were read from environment variables
   with no validation. `api.example.com/v1` (no scheme), a URL containing
   `user:pass@`, or an 8000-character system prompt all reached runtime: the
   first request fails, or every request pays for a prompt that leaves no room
   for the answer.

## Decision 1 — Cap the per-model table

`DREAMAI_MAX_TRACKED_MODELS` (default 64, clamped to 2..512) bounds the table.
One slot is reserved for `other`; names beyond the named-model capacity are
folded into it. Counts, tokens and cost accumulate there rather than being
discarded, so `requests` and the breakdown still reconcile.

The import path now distinguishes "first value for this bucket" from "another
model folded into an existing bucket": the first assigns, later ones add.
This keeps oversized snapshots from older or differently configured processes
consistent.

Rejected: refusing unknown model ids. The whole point of custom gateways is
that the site cannot enumerate their catalogue. Rejected equally: an LRU that
drops old models entirely - the totals would stop reconciling.

## Decision 2 — Validate URLs without echoing them

`validation.check_base_url()` requires an empty value (optional fallback), or
an `http` / `https` URL with a host, no whitespace, no embedded credentials,
no query and no fragment. `check_settings()` applies it to the three base URLs
and the two key URLs, reporting `base_url_invalid`.

The finding quotes the **variable name and the reason**, never the value. A URL
with `user:secret@host` must not put that secret into a log or into the
read-only `/api/health.configChecks` array.

## Decision 3 — Bound the system prompt

A prompt over 8000 characters produces `system_prompt_long`. Empty prompts keep
the existing `system_prompt_empty` finding; the two are mutually exclusive, so
the code says which mistake was made.

## Decision 4 — State the reconciliation rules

`tests/test_stats_invariants.py` now asserts, before and after a snapshot round
trip, that:

```
requests == sum(byModel.requests) + blocked
failures  == sum(byModel.failures) + blocked
truncated == sum(byModel.truncated) == sum(truncatedByTier)
promptTokens == sum(byModel.promptTokens)
```

`blocked` is deliberately excluded from `byModel`: the request never reached a
model, so inventing a slot for it would misstate the model mix.

## Consequences

- `byModel` may contain an `other` row. Clients must not treat it as a real
  model or use the row sum to reconstruct `requests`.
- Snapshots from a higher limit are compacted on import without losing totals.
- Two new finding codes (`base_url_invalid`, `system_prompt_long`) and one
  (`tracked_models_low`) join `configChecks`; all remain non-blocking.
- A malformed URL is still accepted at runtime - checks report, they do not
  refuse - but the operator sees the reason at boot instead of in the first
  failed chat.
