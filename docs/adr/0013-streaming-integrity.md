# 0013 — Streaming integrity: repair the last byte, not the whole reply

- **Status:** Accepted
- **Date:** 2026-11-11

## Context

A streamed answer cannot be rewritten: once a delta is on the wire, the browser
has rendered it. ADR 0005 and 0006 put the effort into "before the first token"
(tiers, intent outlines, history folding), which is correct but leaves three
edge cases that only appear at the end of a stream or in its metadata.

1. A model that stops mid-code leaves an open ```` ``` ```` fence; everything
   after it — including the site's own UI text — renders as code.
2. Every prompt-injection hit wrote the same warning line, whether the visitor
   asked to see the prompt (curiosity) or demanded a rule override (an attempt
   to take control).
3. A retired model (HTTP 410) fell through to the generic sentence and could
   have shown the vendor's deprecation notice verbatim.

## Decision 1 — Append, never rewrite

`quality.unclosed_fence` is a pure predicate over the accumulated answer text.
Before the `done` event, the chat loop appends one final ``\n``` `` delta when
the count of fences is odd. The patch is also appended to `answered`, so the
cached copy and the visitor's copy are identical. Counting fences is enough:
inline triple-backtick pairs inside prose still leave an even count.

Rejected: buffering the whole reply so it can be post-processed like the CLI.
That would throw away streaming, which is the point of the web surface.

## Decision 2 — Severity, not volume

`safety.classify_injection` keeps the existing narrow patterns and adds
`none / low / high`. A reveal request is logged at info; an override or role
switch stays a warning. Both still harden the system prompt. A turn that trips
the guard is excluded from the response cache entirely — such replies are rare,
and a security-sensitive answer should never be replayed to a later visitor.

## Decision 3 — Permanent failures get permanent wording

HTTP 410 now has its own sentence naming who must act (change the model or the
configured list), is never retried, and is in `CURATED_STATUS` so a provider's
deprecation notice cannot replace it. This follows the same rule as 404: our
words for what the visitor can fix, the provider's words for a rejected
parameter, never raw JSON in the chat bubble.

## Consequences

- The last delta can be a repair, so a client that counts characters sees a
  slightly longer answer than the model produced. The `done.chars` field counts
  the repaired text, matching what is on screen.
- Guarded turns are never cache hits; `cacheHitRate` therefore describes normal
  traffic only.
- An incident timeline has both ends now: `breaker open` and
  `breaker recovered` (the successful half-open probe), plus `byProvider` in
  `/api/usage` to see which vendor all the failures belong to.
