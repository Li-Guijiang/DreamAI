# 0005 — Reply quality: plan the turn, keep the context, survive a bad minute

- **Status:** Accepted
- **Date:** 2026-11-05

## Context

ADR 0004 fixed how an answer is written. What it did not touch was everything
around generation, and three complaints survived that change:

1. every turn used the same temperature and token budget, so a greeting was
   answered with a 4k allowance and a design question could be truncated;
2. history was cut at a character count, which silently dropped the turn a
   follow-up referred to — "那它呢？" arrived with no "它";
3. a transient 503 from the provider ended the turn with an error the user could
   do nothing about.

None of these need a bigger model. They need the request to be planned.

## Decision 1 — Classify the question, then size the reply

`web/app/quality.py::classify_tier` rates a turn `light` / `standard` / `deep`
from four cheap signals: length, code fences, question count, and the vocabulary
of trade-offs (`为什么`, `对比`, `架构`, `原理` …). `plan_generation` turns that
into temperature, max_tokens and a one-line hint that is appended to the prompt.

The hint matters more than the numbers for a small model: telling it "本轮问题很
直接：一两句话答完" changes the output more reliably than lowering temperature.

Targets: `light` ≤ 768 tokens and ≤ 0.4; `deep` +1024 tokens and ≥ 0.5. Every
value is clamped again in `plan_generation`, so a caller cannot produce an
out-of-range request.

## Decision 2 — Fold history instead of deleting it

`compress_history` keeps the newest six turns and returns a digest of the rest:
role label plus the opening of each dropped message, capped by a character budget.
The route appends that digest to the system prompt when it is non-empty, and adds
one sentence when the current turn looks like a follow-up
(`needs_context`: short message with a pronoun).

The digest is extractive on purpose. Summarising with a model would cost a second
request on every long conversation and could invent facts; clipping the actual
text cannot.

## Decision 3 — Retry only what is safe to retry

`llm.stream_with_retry` re-runs a request once for 408/425/429/5xx **before the
first token**. After the first token a retry would duplicate the opening in the
user's bubble, so it is refused; 401/402/403 are never retried because repeating
them only burns quota.

## Decision 4 — Decide before writing

The quality block gained a decision section ahead of the reasoning contract:
classify the question type, state an assumption instead of interrogating, ask at
most one question and only when the assumption changes the conclusion, check
coverage of the sub-questions, and never invent an API or a version.

## Decision 5 — Repair locally where streaming cannot

The web service streams, so it cannot rewrite text it has already sent. The CLI
and the desktop shell receive whole replies and can: `dream_ai/quality.py` closes
an unclosed code fence, drops a back-to-back repeated sentence, and detects an
empty reply so the agent can retry once with an explicit nudge before admitting
failure.

## Consequences

- The turn's shape is now observable: `meta` and `done` events carry `tier`, so a
  truncated answer can be traced to a classification rather than guessed at.
- Cheap turns cost less and read tighter; deep turns get room. Both directions are
  enforced in code, not in the prompt alone.
- Long conversations keep their subject without a second model call.
- A provider hiccup no longer surfaces as a user-visible failure in the common
  case.
- The web surface still cannot post-process streamed text; that asymmetry is
  deliberate and documented rather than hidden.
