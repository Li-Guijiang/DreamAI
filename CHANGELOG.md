# Changelog

All notable changes to Dream AI are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `docs/README.md`: document index with the document map, the entry point of each
  of the three deliverables, and the version-number cross-reference.
- `docs/adr/0001-three-deliverables-one-repository.md`: the first Architecture
  Decision Record, covering why the CLI, web, and desktop versions differ.
- `.editorconfig` pinning UTF-8, LF, final newline, and indent size per file type.
- `web/tools/README.md`: which maintenance scripts are supported, and the policy
  for the new `web/tools/archive/` directory.
- `tests/test_config.py`: nine cases covering settings defaults, invalid values,
  directory overrides, and the CLI argument overrides.
- Tests proving that a remembered preference reaches the payload sent to the
  provider, both in a fresh session and after a restart.

### Changed
- `README.md` restructured: numbered plain-text headings, a rewritten project
  tree that includes `web/`, `desktop/`, and `docs/adr/`, a deliverables table,
  and a documentation table.
- `docs/GUIDE.md` retitled to "命令行版" and scoped explicitly to the CLI package,
  with links to the web and desktop documents.
- `ruff format` applied to `dream_ai/`, `tests/`, and `examples/`; CI now also
  lints `web/app` and `web/tools` and checks formatting of the CLI packages.
- `Memory` gains `set_system_prompt()`; both backends implement it.
- `.gitignore`: the ~70 hand-listed scratch files collapsed into anchored
  patterns (`/*.txt` with `requirements*.txt` re-included); Python build rules
  anchored to the repository root so they no longer hide `desktop/build/`.
- Desktop packaging resources now live in `desktop/build/`, and the Node tests
  are reachable through `pnpm test`, `pnpm test:tools`, `pnpm test:docs`.

### Fixed
- Remembered preferences are now part of the system message actually sent to the
  provider. Previously `/remember` updated only an internal property, so the
  preference never influenced a reply in the default persistent configuration.
  (`Memory.set_system_prompt()` and `DreamAIAgent._sync_system_prompt()`.)
- `pnpm start:local` no longer depends on the undeclared `cross-env`; the target
  URL is passed as `--url=` and `DREAMAI_URL` still works.
- `desktop/build/icon.ico` added, so `pnpm dist` and the window icon no longer
  fall back to the Electron default.
- `web/tools/make_og.py` runs outside the author's machine: the mark path is
  derived from the repository and CJK fonts are resolved per platform.
- `dream_ai/config.py`: the `.env` precedence docstring matched neither the code
  nor `.env.example`; it now states that a working-directory `.env` only fills
  gaps.
- `web_search` sends the current package version instead of a hardcoded `0.4`.
- Unused imports and a placeholder-free f-string removed from `web/app/main.py`
  and `web/tools/make_assets.py`.
- Offline placeholder replies are no longer persisted to session history and
  are filtered out when restoring an old session, so demo replies cannot
  pollute the context sent to a hosted model after an API key is configured.
- The project-root `.env` is loaded regardless of the current working
  directory; existing shell environment variables keep priority.

### Removed
- 21 `.jpeg` assets that were byte-identical to the `.jpg` file next to them
  (4.9 MB in the working tree); `.jpg` is now the single retained format.
- 42 single-use operational scripts moved from `web/tools/` to
  `web/tools/archive/`, where they are kept for traceability but not maintained.

### Notes
- No version number was bumped: this batch is repository hygiene, documentation,
  and small fixes. The three deliverables stay at `0.4.0` / `1.4.0` / `1.2.0`.

## [0.4.0] — 2026-10-24

### Added
- Autonomous planning layer (`dream_ai/autonomy/`): a planner, a
  think → act → observe → reflect execution engine, and an explainable trace.
- Deterministic offline `RuleBasedPlanner` that maps simple time and
  calculation intents to ordered tool steps; a future LLM planner can reuse
  the same interface.
- Step budget (`DREAMAI_MAX_STEPS`) that stops the loop to prevent runaway
  plans, and per-step retry policy (`DREAMAI_MAX_RETRIES`).
- Confirmation gate for protected actions inside autonomous runs; a declined
  action cancels the run safely.
- Agent `autonomous_task()` that records the objective and final summary in
  session memory and exposes the last `ExecutionResult` for review.
- CLI `/run <objective>` autonomous command and `/trace` plan/step/trace view;
  `/about` reports autonomy status and the last task outcome.
- Configuration switches: `DREAMAI_AUTONOMY_ENABLED`, `DREAMAI_MAX_STEPS`,
  `DREAMAI_MAX_RETRIES`, `DREAMAI_AUTONOMY_VERBOSE`.
- `examples/autonomy_demo.py` non-interactive autonomous task demo.

### Changed
- The agent factory passes autonomy budget and switches from settings into the
  agent defaults.

### Notes
- The v0.4 planner is a deterministic baseline for offline testing and demos.
  Model-driven plan decomposition and native function-calling arrive with a
  hosted-model integration in a later phase.

## [0.3.0] — 2026-10-24

### Added
- Tool schema with parameters, risk level, and confirmation gate (`Tool`).
- Built-in safe tools: `calculator` (AST allowlist arithmetic, no `eval`) and
  `clock`.
- Sandboxed `file_read` / `file_write` confined to a workspace directory;
  writes require explicit confirmation; traversal and absolute paths are
  rejected.
- Opt-in `web_search` instant-answer tool implemented with the standard
  library only.
- Permission switches: `DREAMAI_TOOLS_ENABLED`, `DREAMAI_FILE_ACCESS_ENABLED`,
  `DREAMAI_WEB_SEARCH_ENABLED`, `DREAMAI_WORKSPACE_DIR`.
- Structured tool-call parser for `<<TOOL {...}>>` blocks; the agent can parse
  and run calls embedded in model text.
- CLI `/tools` and `/tool <name> <json>` commands; `/about` lists registered tools.
- `examples/tool_demo.py` non-interactive tool demo.

### Changed
- The agent factory builds the tool registry from settings; the agent exposes
  `list_tools`, `execute_tool`, `run_tool_calls`, and a provider-ready schema.

### Notes
- Native OpenAI function-calling (model-driven tool selection) arrives with a
  hosted-model integration in a later phase; offline mode exposes tools through
  the `/tool` command and the text parser.

## [0.2.0] — 2026-10-24

### Added
- Persistent session history stored in JSON and restored when the agent starts
  again (`DREAMAI_PERSISTENCE`, `DREAMAI_DATA_DIR`).
- Preference memory: remember user preferences across sessions and inject them
  into the system prompt (`/remember`, `/memory`, `/forget`).
- Agent factory that selects the in-memory or persistent backends from settings.
- Atomic JSON persistence helpers shared by memory backends.
- Tests covering session restore, clearing, preference recall, and persistence
  disabled writing nothing to disk.

### Changed
- The CLI shows the memory mode at startup and the preference count in `/about`.
- `Settings` gained `data_dir` and `persistence_enabled`.

### Notes
- Vector / semantic retrieval over past conversations is deferred to a later phase.

## [0.1.0] — 2026-10-24

### Added
- Repository skeleton with `dream_ai`, `tests`, `examples`, and `docs` layout.
- Environment-based `Settings` loaded from `.env`.
- Pluggable `LLMProvider` interface with:
  - OpenAI-compatible hosted provider.
  - Offline local demo provider as fallback.
- In-memory session memory with system prompt and conversation history.
- `DreamAIAgent` composing provider, memory, conversation, and tool registry.
- CLI REPL with `/help`, `/clear`, `/about`, `/quit`.
- Tool registry contract for future tool use.
- Unit and smoke tests.
- Project documentation: README, roadmap, architecture, contributing guide,
  code of conduct, security policy, setup guide, and pricing vision.
- MIT License.
- CI workflow: Ruff lint and pytest across Python 3.11, 3.12, and 3.13.
- Release workflow: on a `v*` tag, build the `sdist` and `wheel`, validate
  metadata, and attach both archives to the GitHub Release.
- Package metadata in `pyproject.toml` for standard sdist and wheel builds.
- `Dockerfile` and `.dockerignore` for a non-root, slim container deployment.
- Container workflow publishing a multi-architecture image to the GitHub
  Container Registry on version tags and manual dispatch.

### Notes
- This is the initial development skeleton (`v0.1`). Real model connectivity
  requires a configured API key; offline demo mode works without one.
- The `dream_ai-0.1.0` `wheel` and `sdist` archives are attached to the
  [v0.1.0 Release](https://github.com/Li-Guijiang/DreamAI/releases/tag/v0.1.0).
