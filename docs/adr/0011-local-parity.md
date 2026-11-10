# 0011 — Local parity: fold the history, follow the language, keep the two copies honest

- **Status:** Accepted
- **Date:** 2026-11-10

## Context

The web service grew a set of per-turn behaviours across ADR 0004–0010. The local
surfaces — the CLI and the desktop shell — kept whatever they had on day one, and
three gaps had become visible:

1. **A long session ate its own context.** Every turn went to the provider whole.
   A user who pastes logs walks the session into the context window within a dozen
   turns, and nothing recorded what the conversation had been about, so a
   follow-up lost its subject.
2. **An English question got Chinese prose.** The web service asks for a
   same-language reply; the local surfaces had no such hint.
3. **A follow-up like 「那它呢？」 went to the model alone.** The web detects the
   pronoun shape and points the model at the earlier turns; the CLI sent the
   fragment and got an answer to a question the user did not ask.

## Decision 1 — Fold, do not truncate

`dream_ai/quality.py` gains `build_digest` and `compress_history`, mirroring the
web copies. The agent folds a copy of the history before every call:

- the newest turns travel whole;
- older turns become a labelled digest (role, order, clipped opening);
- the digest is inserted as a system note after the main system prompt;
- when the new message looks like a follow-up (`needs_context`), a hint says the
  subject is in the digest.

What the agent *stores* is untouched. Folding happens on the copy sent to the
provider, so memory, restarts and `【查看我的全部档案】` all keep the full history.

## Decision 2 — The budget caps the digest, not the tail

`max_history_chars` bounds what the request may carry. When the newest turns alone
exceed it, folding still keeps them whole and the request simply runs over — a
truncated recent turn is worse than a long one, because the model reads it
mid-sentence. The digest carries the bounded part.

## Decision 3 — Keep the duplication, keep it tested

The package must stay installable without the web app, so importing
`web/app/quality.py` from `dream_ai` is not an option. The copies stay small and
pure, and the parity tests walk the same sentences through both
(`tests/test_dream_insight.py`); when a rule changes, both tests must move
together or the suite goes red.

## Decision 4 — The CLI shows what it decided

`agent.turn_count` counts model calls only (owner commands and captured
preferences are free), and `agent.last_tier` says how the last question was rated.
`/stats` prints both plus the history length, so a metered session can answer
"how much have I spent?" without leaving the terminal.

## Alternatives rejected

- **Token counting with tiktoken.** Exact, and a new binary dependency for a
  package whose whole identity is "pip install and go". Character counts with a
  generous margin approximate tokens well enough to decide when to fold.
- **Folding inside the memory backend.** Tempting (one place), but memory is also
  used by autonomy, which needs exact steps; folding is a request-time concern.
- **Dropping the digest once the session ends.** The digest is derived, not
  stored; there is nothing to clean up.

## Consequences

- A paste-heavy session degrades gradually: fewer exact turns, never a silent loss
  of subject.
- Three rules now exist twice. The parity tests are the contract between them.
- `/stats` gives the operator a session-level answer to a question the web answers
  with `/api/usage`.
