# 0006 — Answer shape: classify the question, clean the input, notice repeats

- **Status:** Accepted
- **Date:** 2026-11-06

## Context

ADR 0005 taught the route *how much room* a reply gets. It still sent every
question the same way: an error report and a request for a weekly-report opening
both arrived as one user message and one generic persona, and a pasted log arrived
whole.

Three failures followed from that:

1. shapes were left to chance — a stack trace got a paragraph of theory, a writing
   request got an explanation of the writing;
2. a 900-line log crowded out the actual question, because the model spends its
   attention on the noise nearest the prompt;
3. asking the same question twice produced the same answer twice, which reads as
   not listening.

## Decision 1 — Classify intent, then append a shape

`insight.classify_intent` returns one of six intents: `error`, `design`, `code`,
`writing`, `explain`, `chat`. Each non-chat intent maps to a one-line shape that is
appended to the system prompt for that turn only:

| Intent | Shape |
|---|---|
| error | 现象 → 最可能的原因 → 修复步骤 → 如何验证 |
| design | 目标与约束 → 两三个方案与取舍 → 推荐及理由 |
| code | 最小可运行实现 → 关键行与边界 → 不先讲原理 |
| writing | 先给成稿 → 一句修改说明 |
| explain | 一句话定义 → 一个例子 → 常见误解 |

Ordering is explicit: `error` wins over `design`, because "怎么改" appears in both
and a fix is what was asked for. Code fences count as an error case: a pasted stack
trace is nearly always a debugging request.

## Decision 2 — Trim the paste, keep the signal

`trim_long_input` keeps the first six lines, up to twelve lines matching an error
vocabulary, and the last four lines, with explicit ellipsis markers between them.
The threshold is 3000 characters, so ordinary messages are untouched. This is
extractive: nothing is summarised by a model, so no fact can be invented.

## Decision 3 — Detect a rephrased question

`is_repeat` compares overlapping Chinese bigrams and Latin words between the last
two user turns and fires at 75% overlap. When it fires, the route appends one
sentence asking for a different angle or a more concrete step.

Overlapping bigrams matter: `findall` on a two-character pattern skips every other
pair, which made two rephrasings look unrelated in the first implementation.

## Decision 4 — Sampling knobs are optional, per dialect

`top_p` is accepted by all three wire formats (Gemini spells it `topP` inside
`generationConfig`); `presence_penalty` only by OpenAI-compatible endpoints, which
is where it exists. Both are omitted from the payload when unset, so an existing
deployment sends byte-identical requests until the operator sets the environment
variable.

## Decision 5 — Two copies, one behaviour

`web/app/insight.py` and `dream_ai/insight.py` are duplicates on purpose: the web
service is deployed without the Python package. `tests/test_dream_insight.py`
imports both and asserts they classify the same strings the same way, so drift
fails the suite rather than the user noticing.

## Consequences

- The turn's shape is now observable: `meta` and `done` carry both `tier` and
  `intent`, so a strange answer can be traced to a decision rather than guessed at.
- Huge pastes cost less and no longer bury the question.
- A repeated question gets a different answer instead of the same one louder.
- The intent classifier is a heuristic over vocabulary. It will miss unusual
  phrasings; the cost of a miss is a generic shape, not a wrong answer, which is
  why no model call is spent on it.
