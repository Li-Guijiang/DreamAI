# 0018 — Quota continuity and input boundaries

- **Status:** Accepted
- **Date:** 2026-11-16

## Context

ADR 0016 made the usage counters survive a restart. This round examined what
else a restart silently resets, and what the request parser was silently
accepting. Three findings, one of them a functional bug.

1. **The daily free quota never applied.** `event_stream()` guarded the budget
   with `if upstream.kind == "free"`. `Upstream.kind` is the *wire protocol*
   (`openai` / `anthropic` / `google`); the free provider's `id` is `"free"`.
   The condition was therefore always false, so `/api/health.freeRemaining`
   never moved and `DREAMAI_DAILY_LIMIT` had no effect at all.
2. **A restart handed out a second daily allowance.** ADR 0016 persisted the
   lifetime counters but not `_daily_state`. The totals continued while the
   admission cap reset, which is exactly backwards for a key-protection limit:
   an operator restarting the service repeatedly could exceed the intended
   daily spend while every number on the dashboard looked continuous.
3. **The request model accepted shapes the pipeline cannot handle.**
   `temperature` had no range, `model` / `provider` / `style` / each `memory`
   entry had no length bound, and a history ending in an `assistant` message
   was accepted even though the pipeline treats `messages[-1]` as the question.
   Validation happened too late, or not at all.

A fourth, smaller gap: operator price overrides were checked for syntax but
never for *meaning* - a cached-input price above the list input price, or a
cached price for a model with no base price, would make the cost estimate go
down as usage rose without any warning.

## Decision 1 — Key the quota on the provider id

`upstream.provider.id == "free"`, with a comment recording that `kind` is the
protocol. The existing 400 / 429 response and `daily_limit` log stay exactly
as they were; only the condition changes. Tests now prove a free turn consumes
the counter and that the next turn is refused once the limit is reached.

## Decision 2 — Persist the daily counter with the usage snapshot

`snapshot_payload()` adds a `daily` key (`date`, `count`) to the counter
envelope. `restore_daily_quota()` applies it only when the stored date is
today; a count is clipped to the configured limit so a hand-edited file cannot
grant unlimited requests. `UsageStats.import_counters()` tolerates the extra
key by design (unknown keys are ignored), so the two concerns stay separate:
lifetime totals in `UsageStats`, per-day admission in `_daily_state`.

Rejected: making the daily count a `UsageStats` field. It is not a traffic
statistic, it resets every day, and importing it would blur the meaning of
`requests`. Rejected equally: persisting the rate limiter's sliding window -
a restart legitimately resets short-lived per-client admission.

## Decision 3 — Validate the request where it enters

`ChatRequest` now bounds `temperature` (0–2), `model`, `provider`, `apiKey`,
`style`, each `memory` entry, `context` and `maxTokens`, and a model validator
requires the final message to be from the user. The existing
`RequestValidationError` handler already turns any of these into a readable
400 with `code=invalid_body`, so no new response shape was introduced.
`docs/API.md` §2.1 records every bound, and a contract test compares the
documented field names with `ChatRequest.model_fields`.

## Decision 4 — Check that the price table still makes sense

`pricing.check_price_tables()` reports non-finite or negative prices,
malformed pairs, a cached price above the input price, and cached prices with
no base price. It is wired into `validation.check_settings()` as
`price_table_inconsistent`, so both syntax and meaning are checked at startup.

## Consequences

- The daily limit is now enforced for the first time. Deployments that relied
  on it being inert will see 429 once the configured cap is reached; that is
  the intended behaviour, not a regression.
- A test that measured the daily-budget log needed explicit state isolation,
  because free turns in earlier tests now consume a genuinely global counter.
- A hand-edited snapshot can no longer raise the quota, and a snapshot from a
  previous day cannot lower it.
- `configChecks` gains one possible code (`price_table_inconsistent`); the
  findings remain non-blocking and secret-free.
