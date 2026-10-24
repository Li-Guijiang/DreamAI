# Dream AI Roadmap

This roadmap organizes Dream AI into small, shippable phases. Each version
has a clear goal, a task list, and acceptance criteria. Dates are not fixed —
quality and a working deliverable matter more than deadlines.

---

## `v0.1.0` — Conversation (released)

**Goal:** A working conversational loop through a pluggable provider, runnable
locally with or without an API key.

### Tasks
- [x] Repository, package layout, and engineering configuration
- [x] `Settings` loaded from environment / `.env`
- [x] Abstract `LLMProvider` interface
- [x] OpenAI-compatible hosted provider
- [x] Offline local demo provider (fallback for tests and demos)
- [x] In-memory session memory with system prompt
- [x] `DreamAIAgent` composing provider + memory + tool slot
- [x] CLI REPL with `/help`, `/clear`, `/about`, `/quit`
- [x] Unit and smoke tests
- [ ] Streaming token output
- [ ] Configuration validation and clearer error messages

### Acceptance criteria
- `python -m dream_ai` starts and runs a multi-turn conversation offline.
- With a valid API key, the same code path reaches a hosted model without
  changing the agent core.
- `pytest` passes locally.

---

## `v0.2.0` — Memory (released)

**Goal:** Remember beyond a single session and recall what matters.

### Tasks
- [x] Persistent session history stored locally (JSON)
- [x] User preference memory, injected into the system prompt
- [x] Memory management: inspect (`/memory`), forget (`/forget`), clear session (`/clear`)
- [ ] Long-term memory retrieval over past conversations
- [ ] Optional vector store for semantic recall

### Acceptance criteria
- [x] Closing and reopening the CLI restores the previous conversation.
- [x] The agent recalls stated preferences in later sessions.
- [x] Memory backends implement the existing `Memory` interface.
- [ ] Semantic retrieval over past conversations (deferred to a later phase).

---

## `v0.3.0` — Tools (released)

**Goal:** Let the agent act beyond text using a safe, modular tool registry.

### Tasks
- [x] Finalize tool schema: name, description, parameters, risk level, result format
- [x] Calculator and date/time utilities (safe, always registered)
- [x] Local file read/write tool (sandboxed paths; writes require confirmation)
- [x] Instant-answer web search tool (opt-in, network)
- [x] Tool permission switches and allowlists via settings
- [x] Structured tool-call parsing from model text
- [ ] Native OpenAI function-calling loop driven by the hosted model

### Acceptance criteria
- [x] New tools are added by registering a class; no core rewrite required.
- [x] Dangerous or unapproved actions require explicit user confirmation.
- [x] File and network tools stay disabled until their switch is enabled.

---

## `v0.4.0` — Autonomous Planning (current)

**Goal:** Multi-step agent that decomposes goals and executes a plan.

### Tasks
- [x] Reasoning loop: think → act → observe → reflect
- [x] Task decomposition into ordered steps
- [x] Retry and recovery on failed steps
- [x] Plan review and user confirmation before irreversible actions
- [x] Token/step budget to prevent runaway loops

### Acceptance criteria
- [x] The agent can complete a multi-step request that combines memory and tools.
- [x] Every autonomous action is logged and explainable to the user.
- [ ] Model-driven plan decomposition and native function-calling (deferred).

---

## `v1.0.0` — Stable Assistant

**Goal:** A reliable, polished general-purpose personal agent.

### Tasks
- [ ] Stable public API and documented configuration
- [ ] Settings and memory backups
- [ ] Performance and error-handling hardening
- [ ] Friendly non-technical user experience
- [ ] Full documentation and examples

---

## `Future` — Self-hosted & Owned

**Goal:** Full independence from commercial vendors where desired.

- Local open-source model deployment as a first-class provider
- Model switching without losing conversation or memory
- Data stays local by default; cloud services remain optional
- Long-term evolution toward a more capable, general assistant

---

## Long-term Vision

Dream AI is a lifelong project built alongside continuous learning. The roadmap
above covers the engineering phases; the broader ambition is to grow into a
thoughtful, capable assistant that serves people everywhere, while keeping the
code open and the ownership with its authors and contributors.
