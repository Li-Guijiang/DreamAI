# 0010 — Local reply sizing: the same question gets the same room

- **Status:** Accepted
- **Date:** 2026-11-08

## Context

ADR 0005 gave the web service a per-turn budget: `classify_tier` rates the
question, `tier_params` turns the rating into temperature and `max_tokens`, and a
one-line hint tells the model how much room it has.

The local surfaces — the CLI and the desktop shell — never got that treatment. They
asked the provider for its maximum on every turn, so `在吗` and `为什么要把缓存做成
两层` were both allowed the same thousands of tokens. Three costs followed:

1. a small model given a large budget writes a preamble, a bullet list and a
   summary for a two-character greeting;
2. the reply takes longer, because generation is sequential;
3. on a metered key the greeting is billed at the same ceiling as the review.

There was a second, subtler problem: `OpenAICompatProvider.generate` accepted
`**kwargs` and then only read `temperature`. A caller could not pass a budget even
if it had one, because the value never reached the request.

## Decision 1 — Mirror the tiers locally, keep the thresholds in one shape

`dream_ai/quality.py` now carries `classify_tier`, `reply_budget` and `tier_hint`
with the same thresholds as `web/app/quality.py`. The duplication is deliberate and
already documented in `dream_ai/insight.py`: this package is installable without the
web app, and importing across the two would tie a CLI to FastAPI.

The two copies are kept honest by being small and by having the same tests. They do
not need to agree on every word — they need to agree on the decision.

## Decision 2 — Budgets are relative to what the caller configured

`reply_budget(tier, base)` clamps rather than replaces: light is `min(base, 768)`,
deep is `min(base + 1024, 8192)`, standard is `base`. A site that configured 512
tokens for cost reasons does not get 8192 because a question looked deep.

## Decision 3 — A provider from before the budget still works

The agent calls `generate(messages, max_tokens=budget)`. A third-party provider
written against the one-argument signature would raise `TypeError`, so `_generate`
catches exactly that case — and only when the message names `max_tokens`. Anything
else, including a `TypeError` raised inside `generate`'s own body, propagates.

Swallowing every `TypeError` would turn a real bug into a silent downgrade, which
is the failure mode this codebase spends the most effort avoiding.

## Decision 4 — The model is told what it has

A budget is invisible to the model. The tier's hint joins the intent hint in the
system prompt, because "answer in one or two sentences" changes behaviour in a way
that `max_tokens: 768` alone does not.

## Alternatives rejected

- **Only cap `max_tokens`.** Cheaper to implement, but a truncated answer is worse
  than a short one: the model fills the budget and stops mid-sentence.
- **Send the budget to every provider kind at once.** The Anthropic and Gemini
  adapters have their own field names (`max_tokens` is required for Anthropic,
  `maxOutputTokens` sits in `generationConfig` for Gemini); the web service already
  handles that split in `adapters.py`. The local package only ships the
  OpenAI-compatible provider, so this ADR covers that one.
- **Move the classic tiers into the provider.** The provider does not know what a
  turn is; the agent does.

## Consequences

- A greeting is bounded at 768 tokens instead of the provider maximum.
- `agent.last_tier` is public, so the CLI and the desktop shell can show the
  decision instead of hiding it.
- Two copies of the heuristic now exist. If the thresholds change, both change, and
  `tests/test_local_tier.py` plus `tests/test_quality.py` are the places to look.
