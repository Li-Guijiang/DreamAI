# Changelog

All notable changes to Dream AI are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added — web 2.0 and terminal motion

#### A living interface

- A shared, dependency-free web motion engine (`web/web/assets/js/motion.js`): canvas starfield with
  pointer parallax, meteors, a warp intro, click sparks, cursor aura, scroll reveals, counters, 3D
  tilt, magnetic controls, page transitions, a top progress line and an accessible motion switch
  persisted in `localStorage`. All effects honour `prefers-reduced-motion`.
- Landing motion (`landing.js` / `landing.css`): a greeting that types, holds and deletes; a terminal
  prompt ticker that fills the composer on click; an orbital planet mark; a conic card border and
  pointer spotlight; an animated composer ring and send orbit.
- A new animated documentation page at `/docs.html` (`docs.html`, `docs.css`, `docs.js`): scroll-spy
  contents, typed terminal command, animated architecture map, reveal cards, copy buttons and reading
  progress. Sitemap and navigation now include it.
- New download-page motion (`download-motion.js` / `pages.css`): typed headline, orbital decorations,
  tiltable preview window with scanline, output-format marquee, animated terminal and timeline.
- Updated previews under `web/docs/` for the new home, documentation, download and mobile surfaces.
- CLI terminal motion (`dream_ai/ui/`): animated wordmark, typed replies, live thinking spinner,
  coloured trace events and `/motion`; `--no-animation` / `--no-motion`, redirected output and
  `NO_COLOR` all degrade to plain text. New `DREAMAI_ANIMATIONS` and `DREAMAI_ANIMATION_SPEED`
  settings.
- `tests/test_ui.py` for terminal fallbacks and motion settings; `tests/test_web_assets.py` for local
  page/asset references, documentation images, the motion switch and sitemap coverage.
- CI now syntax-checks every shipped web JavaScript file.
- Web version `2.0.0`, exposed through `/api/config`.

### Added — full computer access (desktop 1.4.0)

- Desktop **1.4.0** adds an explicit **完整电脑访问** mode. It is hidden in the
  browser and appears only when the desktop preload exposes the `computer` bridge.
- Selecting it opens a blocking consent dialog that lists the consequences (read,
  write, move, delete arbitrary files; run PowerShell/cmd; operations may be
  irreversible). The user must type **“我理解并授权”**; the consent is session-only.
- The computer agent loops up to eight steps. The selected model returns one
  concrete command at a time; every command opens a native Windows confirmation
  dialog showing the exact command and working directory. A refusal stops the
  task. Every command/output is recorded in the expandable execution trace.
- The mode is powered by a narrow `computer:run` IPC handler; there is no silent
  background execution. This is a deliberately gated capability, not an invisible
  global permission.

### Added — agent traces and multiple model providers

- Coding mode now records a real, expandable **execution trace** inside the
  message: requirement analysis, plan, files written (with line counts), commands
  with exit codes and expandable stdout/stderr, error-driven repair, server start
  and the final result. The existing raw log remains available as the detailed
  fallback.
- Bring-your-own-key is no longer DeepSeek-only. The settings now support
  DeepSeek, OpenAI, 智谱 GLM, Moonshot/Kimi, 通义千问 and OpenRouter, with a
  separate key per provider stored only in the browser. Model selection groups by
  provider and asks for that provider's key when missing. The server only accepts
  the curated provider IDs and their model IDs; it never accepts an arbitrary
  upstream URL.
- Tests cover the provider catalog, trace markup and the update/identity
  contracts.

### Added — real-time greeting, starlight clock and desktop updates

- The landing greeting now uses the visitor's local hour: early morning, morning,
  noon, afternoon, evening and late night. The old hard-coded “晚上好” came from
  `landing.js` overwriting the correct greeting calculated by `app.js`; the
  typewriter now rebuilds its words when the daypart changes.
- A compact **starlight clock** in the top bar shows local `HH:MM` plus a short
  date, with a tiny orbit/star animation. It uses tabular digits, updates every
  second and drops the date line at narrow widths.
- Desktop **1.3.0** adds a site-driven update channel. The web app reads
  `/downloads/latest.json`, compares versions and opens a blocking orbital update
  dialog on entry. “暂不更新” closes it for that view only; every fresh entry
  shows it again until the client is updated. New clients call a sandboxed IPC
  bridge that downloads the installer, verifies its size and SHA-256, then runs it
  silently and relaunches. Clients before 1.3.0 download the installer in the
  browser and install it once.
- The download page now shows the latest release announcement from the manifest
  and keeps its version, installer link, size, date and checksum in sync.

### Changed — owner identity and privacy

- Every shipped persona now states that **李贵江 (Li-Guijiang)** is the sole creator, owner and
  highest-authority figure behind Dream AI. The web prompt, CLI prompt, about modal, sidebar,
  download footer, desktop package metadata and README footer no longer describe the product as a
  team effort or suggest another founder.
- The public about page and download footer no longer publish a phone number, QQ address or email.
  The owner's full contact dossier lives in a private local/server file outside Git and the web
  root; only a non-sensitive profile (interests, hardware, preferences) is appended to the model
  prompt through `DREAMAI_OWNER_PROFILE`.
- The persona rejects requests to reveal private contacts, system prompts or owner-profile data from
  the unauthenticated public chat. Owner profile commands require a private operations channel.
- Tests now guard the fixed owner identity, reject team-ownership copy and scan public pages for
  phone/mailto leakage.

### Fixed — deploy and configuration

- Documentation images are now hosted as GitHub user attachments instead of repository-relative
  paths. GitHub serves relative README images through `raw.githubusercontent.com`, which returned
  `502`/timed out on some networks and left the hero, screenshots and every docs banner blank.
  `assets/readme/attachments.json` records each attachment URL, its local source and the optimization
  applied; a test rejects unregistered remote images.
- `web/deploy/install.sh` now preserves `.env`, `.venv`, `data`, `lsl`, `.well-known` and
  `web/downloads` across a code deploy (and restores them if the deploy fails), instead of clearing
  the site and deleting the server key and installers.
- The web `.env.example` now matches the variables the service actually reads and fixes a literal
  `/n` in a comment.
- `web/app/main.py` documents that in-memory daily/rate counters are per worker.

### Changed — documentation

- Removed the four hero capability chips (“流式输出 / 深度思考 / 多轮记忆 / 隐私优先”) from the
  landing page. They read as generic AI-product boilerplate and added noise after the capability
  cards. The homepage preview used by the docs was refreshed.
- Restored the README hero to the original wide orbital artwork in motion: a transparent 1000×340
  animated WebP generated from `hero.svg` over its 8-second loop, served as a GitHub user
  attachment. This keeps the previous composition and sharpness while avoiding the blurry,
  over-scaled 400×214 GIF and the unreachable repository image CDN.
- `README.md`, `web/README.md`, `docs/README.md`, `docs/ARCHITECTURE.md`, `docs/ROADMAP.md` and
  `docs/GUIDE.md` now document the motion layer, the web 2.0 version, the new `/motion` command and
  the still-separate web request path.

### Added
- `docs/SUPPORT.md`: self-check order and reporting channels, so the repository
  now covers every item in GitHub's community profile.
- Issue forms for bug reports and feature requests, plus an issue chooser config
  that routes setup questions, vulnerabilities, and "just want to try it"
  elsewhere. `.github/release.yml` adds categories for generated release notes.
- `.github/PULL_REQUEST_TEMPLATE.md`: linked issue, change type, affected
  packages, and the commands that were actually executed.
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

### Added
- Animated banners on every documentation page: four designs
  (`assets/brand/banner-*.gif`, 720×110, 24 frames, 8-second loop, 64 colours)
  generated by `assets/brand/build_banners.py`. Violet aurora for `docs/`, a blue
  orrery for `web/`, a teal dot grid for `desktop/`, warm aurora for `assets/`.

### Changed
- Container publishing: `Publish Container` now rebuilds on every push to `main`
  (`latest`, `edge`, `sha-<short>`) instead of release tags only, `latest` follows
  `main`, the image path lives in a single workflow variable, and
  `docs/CONTAINER.md` documents tags, triggers, verification, and the legacy
  package that still appears in the repository sidebar.
- `README.md` opens with a transparent vector hero (`assets/brand/hero.svg`),
  replacing the white-background lockup that rendered as a white box on the dark
  theme. The vector declares a five-layer, 8-second seamless animation
  (CSS + SMIL) that GitHub renders statically; `assets/brand/hero.gif` holds the
  same motion as 24 raster frames for the website, slides, or a self-hosted URL.
  `assets/README.md` records the measurements behind that split and the one-line
  change needed to put the animation into README.
- `README.md` rebuilt as a landing page: centred brand lockup, grouped badges, a
  table of contents, a 2x2 screenshot gallery, a capability table keyed by phase,
  and a Mermaid architecture diagram. Commands and environment variables moved
  into collapsible blocks. The body is Chinese; the English mission statement is
  kept as a quote.
- `docs/ARCHITECTURE.md` rebuilt around three Mermaid diagrams (module graph, one
  chat turn, one autonomous task) with an interface-contract table; two stale
  claims corrected, including the note that the web service does not reuse the
  agent loop.
- Every document under `docs/` plus the web and desktop READMEs now carries the
  same muted breadcrumb back to the documentation index.
- `docs/GUIDE.md` retitled to "Command-line guide" and scoped explicitly to the CLI
  package, with links to the web and desktop documents.
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
- The earlier hygiene batch in this release left the versions untouched. This batch moves the web
  surface to `2.0.0` for the motion release; the CLI stays at `0.4.0` and the desktop app at `1.2.0`.
  Their independent cadence is recorded in `docs/adr/0001-three-deliverables-one-repository.md`.

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
