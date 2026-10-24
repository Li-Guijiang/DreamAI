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
- `base.py`: `Memory.append()`, `messages()`, `clear()`.
- `session_memory.py`: in-memory session buffer (v0.1).
- Persistent and vector memory arrive in `v0.2`.

### 5. Tools (`dream_ai/tools/`)
- `base.py`: `Tool.name`, `Tool.description`, `Tool.run()`.
- `registry.py`: register, look up, and execute tools by name.
- Real tools arrive in `v0.3`.

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

## Extension Points

### Add a new provider
1. Create a class implementing `LLMProvider` in `dream_ai/providers/`.
2. Implement `name` and `generate()`.
3. Register it in `build_provider()` in `providers/__init__.py`.

### Add a new tool
1. Create a class implementing `Tool` in `dream_ai/tools/`.
2. Implement `name`, `description`, and `run(**kwargs)`.
3. Register it on the agent's `ToolRegistry`.

### Add a memory backend
1. Implement the `Memory` interface.
2. Keep the same `append / messages / clear` contract.
3. Inject it into `Conversation` and `DreamAIAgent`.

## Future Architecture Notes

- A reasoning loop (`v0.4`) will sit between the agent core and tools, deciding
  when to call a tool, observe the result, and continue.
- A future UI layer will call the same agent API instead of duplicating logic.
- Local open-source models will be added as a provider for full self-hosting.
