# Architecture

## Design Principles

1. **Interfaces over implementations.** The agent core depends on abstract
   contracts (`LLMProvider`, `Memory`, `Tool`), not concrete backends.
2. **Vendor-neutral.** No core logic assumes a specific model provider.
3. **Small, replaceable parts.** Each layer can be swapped, tested, and improved
   independently.
4. **Safe by default.** Tools and autonomous actions require explicit user
   consent and clear logging.
5. **Progressive disclosure.** Simple usage stays simple; advanced features are
   opt-in modules.

## Layers

### 1. Interface / CLI (`dream_ai/cli.py`)
Parses arguments, loads settings, builds the agent, and runs the conversation
loop. It contains no business logic.

### 2. Agent Core (`dream_ai/core/`)
- `agent.py`: composes provider, memory, conversation, and tools; exposes
  `chat()` and `reset()`.
- `conversation.py`: high-level user/assistant message operations on top of a
  `Memory` backend.

### 3. Providers (`dream_ai/providers/`)
- `base.py`: `LLMProvider.generate(messages) -> str`.
- `openai_compat.py`: any OpenAI-compatible HTTP endpoint.
- `local.py`: offline placeholder for tests and demos.
- `__init__.py`: `build_provider(settings)` factory with safe fallback.

### 4. Memory (`dream_ai/memory/`)
- `base.py`: `Memory.append()`, `messages()`, `clear()`, `set_system_prompt()`.
  The agent calls `set_system_prompt()` on start-up and whenever a preference is
  remembered or cleared, so the first message sent to the provider always
  contains the effective prompt.
- `session_memory.py`: in-memory session buffer.
- `persistent_session.py`: JSON-backed session history restored on restart.
- `preferences.py`: long-term user preferences injected into the system prompt.
- `storage.py`: atomic JSON read/write helpers shared by memory backends.
- Vector retrieval memory arrives in a later phase.

### 5. Tools (`dream_ai/tools/`)
- `base.py`: `Tool` schema — name, description, parameters, risk level, and
  whether confirmation is required before running.
- `registry.py`: register, look up, list, and execute tools by name.
- `parser.py`: extract structured `<<TOOL {...}>>` calls from model text.
- `factory.py`: register tools according to the permission switches in settings.
- `builtin/`: calculator, clock, sandboxed file read/write, and web search.

### 6. Autonomy (`dream_ai/autonomy/`)
- `models.py`: `PlanStep`, `TraceEntry`, `ExecutionResult`, and lifecycle phases
  (`think`, `act`, `observe`, `reflect`, `confirm`, `plan`, `done`, `abort`).
- `planner.py`: `Planner` interface and the deterministic offline
  `RuleBasedPlanner`; a future model-driven planner reuses the same interface.
- `engine.py`: the think → act → observe → reflect loop. It enforces the step
  budget, retries failed steps, asks for approval before protected actions, and
  records an explainable trace for every action.

## Data Flow (one chat turn)

```
User input
   │
   ▼
CLI ──► Agent.chat(text)
            │
            ├─► Conversation.add_user(text)
            │        └─► Memory.append("user", text)
            │
            ├─► Provider.generate(Memory.messages())
            │        └─► model reply
            │
            ├─► Conversation.add_assistant(reply)
            │
            └─► return reply ──► CLI prints it
```

## Data Flow (one autonomous task)

```
Objective
   │
   ▼
Agent.autonomous_task(objective)
   │
   ├─► record objective in session memory
   │
   ├─► Planner.decompose(objective) ──► ordered PlanStep list
   │
   └─► AutonomyEngine.run(plan)
            │
            ├─► think      ──► mark the next step active
            ├─► confirm    ──► protected action waits for approval
            ├─► act        ──► Agent.execute_tool(name, confirmed, **args)
            ├─► observe    ──► record the tool output
            ├─► reflect   ──► retry on failure, mark success/failure
            └─► repeat until complete, budget exhausted, or cancelled
   │
   ├─► record final summary in session memory
   └─► ExecutionResult (steps + trace) ──► CLI prints plan and summary
```

## Extension Points

### Add a new provider
1. Create a class implementing `LLMProvider` in `dream_ai/providers/`.
2. Implement `name` and `generate()`.
3. Register it in `build_provider()` in `providers/__init__.py`.

### Add a new tool
1. Create a class implementing `Tool` in `dream_ai/tools/builtin/`.
2. Implement `name`, `description`, `parameters`, and `run(**kwargs)`.
3. Set `risk` and `requires_confirmation`; read-only safe tools default to `safe`.
4. Register it in `tools/factory.py` behind the matching permission switch.

### Add a memory backend
1. Implement the `Memory` interface.
2. Keep the same `append / messages / clear` contract.
3. Inject it into `Conversation` and `DreamAIAgent`.

### Add a planner
1. Create a class implementing `Planner` in `dream_ai/autonomy/`.
2. Implement `decompose(objective) -> list[PlanStep]`.
3. Pass it to `AutonomyEngine(..., planner=your_planner)`; the loop, budget,
   retry, and confirmation logic stay unchanged.

## Future Architecture Notes

- The v0.4 loop currently runs a deterministic offline planner; a hosted
  model will later drive plan decomposition and native tool selection through
  function-calling, reusing the same engine, trace, budget, and confirmation.
- A future UI layer will call the same agent API instead of duplicating logic.
- Local open-source models will be added as a provider for full self-hosting.
