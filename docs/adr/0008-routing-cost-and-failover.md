# 0008 — Routing, money and the second upstream

- **Status:** Accepted
- **Date:** 2026-11-08

## Context

ADR 0007 made the service survive a bad minute. It did not make it cheap, and it
did not give an operator a number to reason about: usage reported raw tokens, a
single model served every tier, and one provider remained a single point of failure.

Three questions had no answer in the code:

1. "Is the expensive model worth it for this question?"
2. "What did this month cost, roughly?"
3. "What happens when the only provider is down?"

## Decision 1 — Route by tier, configured not coded

`routing.parse_tier_map` reads `DREAMAI_MODEL_BY_TIER=light=glm-4-flash,deep=...`
into a dict; `choose_model` resolves after classification and falls back to the
site default for an unmapped tier.

A misspelled tier must cost quality, not availability. That is why the fallback is
the default model rather than an error: the worst case is the behaviour we had
before routing existed.

## Decision 2 — Price in USD, or say nothing

`pricing.estimate_cost` holds a dated snapshot of list prices and returns `None` for
a model it does not know. A wrong cost is worse than an absent one: it silently
distorts every comparison built on it.

`/api/usage` exposes `costUsd`, `costKnown` (false once any unknown model was used
in the window) and `cacheHitRate`. The turn log line gains `cost=$0.0012` when the
price is known.

## Decision 3 — One status policy

`errors.is_retryable` and `errors.user_message` replace a set literal in `llm.py`
and an ad-hoc branch in `main.py`. The two sets are asserted disjoint: a 401 is
never transient, and a 503 never blames the visitor's key.

Provider messages for 4xx still pass through, because "model not found" explains
the request better than any generic line.

## Decision 4 — Failover only before the first token

`llm.stream_with_fallback` runs the primary (itself wrapped in the retry policy) and
falls through only if it fails before yielding anything. After the first token the
error is raised, because a second provider would splice two answers together.

The fallback is configured entirely by environment variables and is off by default,
so an existing deployment behaves identically until an operator opts in.

## Decision 5 — Collapse repeated turns

`quality.dedupe_messages` removes consecutive same-role duplicates, ignoring
whitespace, before history is trimmed. A browser retry after a dropped connection
otherwise asks the same question twice and pays for both.

## Consequences

- Cheap questions can be routed to a cheap model without touching code.
- Cost is visible per turn and in aggregate, with an explicit "unknown" state.
- The same failure produces the same message and the same retry decision.
- A provider outage degrades to the second upstream when configured, otherwise to
  the breaker's fast refusal from ADR 0007.
- The price table will age. It is a snapshot with a date, not a source of truth;
  `costKnown=false` is the signal to update it.
