# 0004 — Answer quality: reasoning, structure, and a natural voice

- **Status:** Accepted
- **Date:** 2026-11-04

## Context

The identity work in ADR 0003 fixed *who* the assistant says it is. It did not
fix *how it answers*. Three complaints remained, and they had different causes:

1. answers read like a help-centre script: "首先…其次…最后", "总之", "希望对你
   有帮助", every paragraph the same length;
2. the thinking panel existed but the prompt never told the model what to put in
   it, so it either stayed empty or repeated the answer;
3. long answers stuttered while streaming.

Only the third is a rendering problem. The first two are prompt problems, and a
prompt that lists traits ("be professional, be natural") produces exactly the
tone it is trying to avoid.

## Decision 1 — Rules with examples of what to avoid

The quality block is written as prohibitions with concrete strings, not
adjectives:

| Rule family | Written as |
|---|---|
| Openers | 禁止以「首先」「那么」「作为一个 AI」开头；第一句必须是结论或可执行动作 |
| Transitions | 禁止「其次/再次/最后」三连；用因果、对比、递进直接衔接 |
| Closers | 禁止「总之」「综上所述」「希望对你有帮助」 |
| Hedging | 不确定时给验证方式，不用「可能」「也许」堆满句子 |
| Rhythm | 长短句交替；连续三句长度相近就重写一句 |

A model can follow "do not print 希望对你有帮助". It cannot follow "be natural".

## Decision 2 — The reasoning channel gets a job

DeepSeek's interface shows a reasoning stream before the answer, and users read
it as evidence of thought. Ours had the panel but no contract, so the model
either skipped it or duplicated the answer there.

The prompt now assigns the channel a fixed shape:

```
理解：一句话复述真实诉求（不是复述原句）
拆解：要解决的子问题，按依赖排序
关键判断：会改变结论的那一两个选择，以及为什么
自查：有没有漏条件、有没有更简单的路径
```

and states that this text is *shown to the user* - so it is written as readable
reasoning, not as raw scratch work, and never contains the final answer.

## Decision 3 — Coalesce upstream deltas

A provider sends one delta per token. Forwarding each one means ~40 SSE events
per second, each with its own JSON envelope and a client-side write. The stream
is correct but the browser spends its frame budget on envelope parsing.

`web/app/llm.py` now merges consecutive deltas of the same kind until the buffer
reaches 24 characters, switching kind or ending flushes immediately. That is
roughly a 4x reduction in events with at most 24 characters of added latency,
and it keeps the reasoning/content boundary exact.

## Decision 4 — The reasoning panel appends, never re-renders

The answer path already appends to one text node (commit before this record).
The reasoning panel still did `textContent = fullSoFar` on every frame, which is
O(n²) over the stream and was the remaining stutter on long thinking.

It now appends the new slice, matching the answer path, and both are flushed
inside `requestAnimationFrame`.

## Consequences

- The quality rules are testable: each banned phrase is asserted absent from the
  rendered block, and a prompt-budget test keeps the block from growing without
  bound.
- The reasoning panel is only as good as the model's willingness to use it; a
  provider that emits no `reasoning_content` still works, the panel simply does
  not appear.
- Identity text is untouched except for wording; the owner tests from ADR 0003
  still pass unchanged.
- The CLI does not stream at all today. Its answer quality improves through the
  same prompt, but the thinking panel is web-only until the CLI gets a streaming
  provider, which is a separate decision.
