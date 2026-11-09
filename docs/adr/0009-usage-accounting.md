# 0009 — Counting the service: say what happened, not just how many

- **Status:** Accepted
- **Date:** 2026-11-08

## Context

`/api/usage` existed for one reason: to answer "is the site being used, and by
what". It did that with a dict of nine integers kept inside `main.py`. Three
questions could not be answered from it:

1. **Which model costs the money?** `by_model` stored one integer per model, so it
   counted requests and nothing else. A light model handling 90% of the traffic and
   a reasoning model handling 10% looked like a traffic report, not a cost report.
2. **Is it slow?** TTFT was printed per turn in the log and then discarded. There
   was no way to say "the average first token takes 0.8 s" without grepping a file.
3. **Is the cache working, or is it full?** A miss covered "never asked", "aged
   out" and "pushed out by capacity". The cache size only grew silently.

There was also a correctness problem: the counters lived next to the code that
updated them, so the endpoint and the pipeline each spelled out the same string
keys. Adding a number meant editing two files, and a typo produced a `KeyError`
only on the status page.

## Decision 1 — Counters get a module, endpoints get a snapshot

`web/app/stats.py` owns three things: the counters, the meaning of each update
(`record_turn`, `record_usage`, `record_local`, `record_blocked`), and the shape of
the snapshot the endpoints report. `main.py` calls methods that name the event that
happened; `/api/usage` formats one dict.

The counters are plain attributes, not locks: the service runs one event loop, every
update sits between two `await` points, and a lock would only introduce a scheduling
point where a half-updated total could be read.

## Decision 2 — A row per model, not a number per model

Each model keeps requests, failures, prompt tokens, completion tokens and cost.
The total is the sum of rows plus what could not be attributed, which makes the
bill explainable: "these 900 tokens were the deep model, that is why the month cost
what it did".

A model missing from the price table does not vanish. It contributes tokens, its
cost stays at zero, and `costKnown` becomes `false` — a total that silently omits
an unpriced model is worse than a total that admits it is a lower bound.

## Decision 3 — Average TTFT over the turns that had a first token

A cache hit produces no first token and an early failure produces none either.
Counting them as zero would make a slow week look fast; excluding them keeps the
average honest, and `ttftSamples` publishes how many turns it is based on, so a
single sample is not read as a trend.

## Decision 4 — Separate the traffic that never left the process

Identity answers, owner commands and the breaker refusing a request are all
"requests" from the client's point of view and none of them is a model call.
They are counted as `local` and `blocked` instead of being folded into the model
totals. A local answer still appears as a request under a `local` model row, so the
request count adds up.

## Alternatives rejected

- **Prometheus / OpenTelemetry.** Correct for a fleet, disproportionate for one
  process that already has a health endpoint. The snapshot is a dict; a scraper can
  read it without a new dependency.
- **Persisting counters to disk.** They are process metrics: after a restart the
  numbers describe the new process. A daily limit is enforced separately, per day,
  and is the one thing that would need persistence if it had to survive a restart.
- **A time-series ring buffer in memory.** Tempting for percentiles, but it grows
  without bound and the interesting questions so far (cost, hit rate, TTFT) are
  answerable from sums.

## Consequences

- Adding a number is one edit in `stats.py`; the endpoint spreads the snapshot.
- The cost of a month can be reconstructed per model, and an unpriced model is
  visible rather than invisible.
- The counters are per process. Two workers report two halves; the health endpoint
  says `uptime` for exactly this reason.
- Nothing in the page reads these fields, so widening the payload is safe.
