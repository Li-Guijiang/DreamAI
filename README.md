# Dream AI

> Dream AI is a general-purpose AI assistant built around one shared dream: helping people everywhere think clearly, reason deeply, create freely, and solve what matters. It studies the world — its knowledge, logic, and deepest questions — and stays open to everyone, so thoughtful, capable intelligence can serve all people across the world.

[![Status: WIP](https://img.shields.io/badge/status-WIP-orange)](./README.md)
[![CI](https://github.com/Li-Guijiang/DreamAI/actions/workflows/ci.yml/badge.svg)](https://github.com/Li-Guijiang/DreamAI/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/Li-Guijiang/DreamAI?sort=semver)](https://github.com/Li-Guijiang/DreamAI/releases)
[![Container](https://img.shields.io/badge/container-ghcr.io-blue?logo=docker&logoColor=white)](https://github.com/Li-Guijiang/DreamAI/pkgs/container/dream-ai)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python&logoColor=white)](./README.md)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](./docs/CONTRIBUTING.md)

---

## 1. About

**Dream AI** is an open-source, general-purpose AI assistant being built from the ground up as a long-term, lifelong project. It reasons, remembers, uses tools, and plans — growing step by step into a capable assistant that serves everyone around the world.

> **Status: early development (WIP).** Dream AI is under active construction. Many features described here are planned rather than finished. See the [Roadmap](./docs/ROADMAP.md) for what exists today and what comes next.

The repository ships three runnable forms that share one design language and one set of `DREAMAI_*` conventions:

| Form | Entry point | Version |
|---|---|---|
| Command-line package | `python -m dream_ai` · [`dream_ai/`](./dream_ai) | `0.4.0` |
| Web service (FastAPI + static front end) | [`web/`](./web) | `1.4.0` |
| Windows desktop app (Electron) | [`desktop/`](./desktop) | `1.2.0` |

The three version numbers are intentionally independent; see [docs/README.md](./docs/README.md#3-版本号对照) for what must be updated together.

## 2. Web & Desktop

- **Online:** <https://liguijiang.com> — chat / work / documents / coding modes, a free default model, or your own DeepSeek key.
- **Windows desktop v1.2:** <https://liguijiang.com/download.html> — document generation, a coding mode (the agent scaffolds a project, writes code, installs dependencies, and starts the server), and a local file workbench.
- **Source:** [`web/`](./web) (FastAPI + front end), [`desktop/`](./desktop) (Electron).

![Web](./web/docs/preview-hero.png)

![Desktop](./web/web/assets/img/desktop-preview.png)

Developed and maintained by Li Guijiang and the Dream AI team.

## 3. Vision

**Dream** is the shared promise behind this project: people everywhere, united by a common dream, seeking to understand the world — its knowledge, its logic, its deepest questions.

Dream AI is the general-purpose assistant built to walk that path with us. It begins small and grows step by step into a capable, thoughtful intelligence, open to everyone across the world who wants to learn, build, or dream alongside it.

This is a long-term project. It is small today, but every great system starts as a single dream.

## 4. Features by Phase

Status marks: `[x]` done · `[~]` in progress · `[ ]` planned.

### Phase 1 — Conversation (`v0.1`)

- [x] Project skeleton and package layout
- [x] Pluggable provider interface (not locked to any vendor)
- [x] CLI conversation loop with session history
- [x] Hosted model integration (configure your own API key)
- [ ] Streaming responses

### Phase 2 — Memory (`v0.2`)

- [x] Persistent session history stored locally (JSON, restored on restart)
- [x] User preferences remembered across sessions and injected into context
- [ ] Retrieval-based memory (vector search)

### Phase 3 — Tool Use (`v0.3`)

- [x] Tool registry schema with parameters, risk level, and confirmation gate
- [x] Calculator and clock utilities (safe, always available)
- [x] Sandboxed file read/write (opt-in; writes require confirmation)
- [x] Instant-answer web search (opt-in, network access)
- [ ] Native model function-calling loop

### Phase 4 — Autonomous Planning (`v0.4`)

- [x] Reasoning loop: think → act → observe → reflect
- [x] Multi-step task decomposition into an ordered plan
- [x] Retry and recovery on failed steps
- [x] User confirmation before irreversible actions
- [x] Step budget to prevent runaway loops
- [ ] Model-driven plan decomposition (native function-calling)

## 5. Architecture

```
+----------------------------------------------+
|                 Dream AI Core                |
|           CLI / Web UI / Desktop UI          |
+----------------------+-----------------------+
                       |
+----------------------v-----------------------+
|        Agent Core (reasoning loop)           |
|   Plan -> Reason -> Act -> Observe -> Reflect |
+------+----------------+---------------+------+
       |                |               |
+------v------+  +------v------+  +-----v------+
|  Provider   |  |   Memory    |  |   Tools    |
| pluggable:  |  | short term  |  | search, fs |
| API / local |  | long term   |  | calculator |
+-------------+  +-------------+  +------------+
```

The core depends only on small abstract interfaces, so hosted APIs, local open-source models, and future custom backends can be swapped in without rewriting the agent. Full details: [Architecture](./docs/ARCHITECTURE.md).

## 6. Roadmap

| Version | Milestone | Goal |
|---|---|---|
| `v0.1.0` | **Conversation** | Working conversational loop through a pluggable provider |
| `v0.2.0` | **Memory** | Persistent session history and preferences restored across restarts |
| `v0.3.0` | **Tools** | Safe calculator/clock, sandboxed file tools, optional web search with a confirmation gate |
| `v0.4.0` | **Autonomy** | Think → act → observe → reflect loop, plan decomposition, retries, confirmation gate, and step budget |
| `v1.0.0` | **Stable Assistant** | A reliable general-purpose personal agent |
| `Future` | **Self-hosted & owned** | Local open-source model deployment for full independence |

Detailed milestones and acceptance criteria: [docs/ROADMAP.md](./docs/ROADMAP.md).

## 7. Releases

Dream AI ships versioned releases through GitHub Releases. Each tagged version builds the sdist and wheel, validates metadata, and attaches both artifacts to the Release with auto-generated release notes.

1. **Releases** — tagged versions (`vMAJOR.MINOR.PATCH`) appear on the [Releases page](https://github.com/Li-Guijiang/DreamAI/releases), with the built `sdist` and `wheel` attached for download.
2. **Automation** — pushing a `v*` tag triggers [`release.yml`](./.github/workflows/release.yml), which builds the package and creates the Release, so no manual packaging step is required.
3. **Container image** — a multi-architecture image `ghcr.io/li-guijiang/dream-ai` is published to GitHub Packages and listed in the [Packages section](https://github.com/Li-Guijiang/DreamAI/pkgs/container/dream-ai).
4. **Package registry** — GitHub Packages does not host Python packages, so the `sdist` and `wheel` are attached to Releases here. The PyPI workflow ([`python-publish.yml`](./.github/workflows/python-publish.yml)) is opt-in: it builds distributions on demand and only publishes once trusted publishing is configured and the repository variable `ENABLE_PYPI_PUBLISH` is set.

> Early-development versions are pre-release snapshots and may change before `v1.0.0`.

## 8. Plans & Pricing (Vision)

Dream AI is open-source and free to use. A future set of optional hosted plans is planned to support development and add convenience services. **These are vision-level plans only — none are available yet.**

| | **Free** | **Pro** | **Team** |
|---|---|---|---|
| Open-source code & self-hosting | Yes | Yes | Yes |
| Local CLI / offline mode | Yes | Yes | Yes |
| Conversation history | Session | Persistent | Persistent |
| Priority hosted model access | — | Yes | Yes |
| Long-term memory & tools | — | Yes | Yes |
| Shared team workspaces | — | — | Yes |
| Priority support | — | Yes | Yes |

Full plan definitions, feature matrix, and principles: [docs/PRICING.md](./docs/PRICING.md).

## 9. Quick Start

### 9.1 Run from source

```bash
# 1. Clone the repository
git clone https://github.com/Li-Guijiang/DreamAI.git
cd DreamAI

# 2. Create and activate a virtual environment
python -m venv .venv
# Windows:        .venv\Scripts\activate
# macOS / Linux:  source .venv/bin/activate

# 3. Install the project in editable mode with its dependencies
pip install -e .

# 4. Configure your model (copy the example and fill in your API key)
# Windows:  copy .env.example .env
# macOS/Linux: cp .env.example .env

# 5. Start chatting
python -m dream_ai
```

Pre-built `sdist` and `wheel` archives for each release are attached to the [Releases page](https://github.com/Li-Guijiang/DreamAI/releases).

Without an API key, Dream AI starts in **offline demo mode** so you can explore the CLI and conversation flow. See [docs/SETUP.md](./docs/SETUP.md) for a step-by-step guide. A Chinese walkthrough for first-time users lives in [docs/GUIDE.md](./docs/GUIDE.md).

### 9.2 Memory (v0.2)

By default the session history and remembered preferences are saved to `~/.dream_ai/` and restored the next time Dream AI starts. In-chat commands:

| Command | Action |
|---|---|
| `/remember <text>` | Record a preference to long-term memory |
| `/memory` | Show remembered preferences |
| `/forget` | Clear all remembered preferences |
| `/clear` | Clear the current conversation history |

Set `DREAMAI_PERSISTENCE=false` to keep everything in memory only, or change `DREAMAI_DATA_DIR` to choose where memory files are stored.

### 9.3 Tools (v0.3)

Safe tools (`calculator`, `clock`) are registered by default. File and web tools are opt-in through environment switches. In-chat commands:

| Command | Action |
|---|---|
| `/tools` | List registered tools, risk level, and required arguments |
| `/tool <name> <json>` | Run a tool, e.g. `/tool calculator {"expression": "2 * (3 + 4)"}` |

`file_write` always asks for confirmation before changing files. Enable sandboxed file tools with `DREAMAI_FILE_ACCESS_ENABLED=true` and web search with `DREAMAI_WEB_SEARCH_ENABLED=true`; `DREAMAI_WORKSPACE_DIR` sets the file sandbox. Set `DREAMAI_TOOLS_ENABLED=false` to disable the whole registry.

### 9.4 Autonomy (v0.4)

Dream AI can run a multi-step goal through a **think → act → observe → reflect** loop: it decomposes the objective into an ordered plan, calls tools, records every observation, reflects on each result, retries failed steps within budget, and asks for approval before protected actions. In-chat commands:

| Command | Action |
|---|---|
| `/run <objective>` | Run an autonomous multi-step task and print the plan and outcome |
| `/trace` | Review the plan, step status, and full trace of the last autonomous task |

Configuration switches:

| Variable | Default | Purpose |
|---|---|---|
| `DREAMAI_AUTONOMY_ENABLED` | `true` | Master switch for autonomous mode |
| `DREAMAI_MAX_STEPS` | `10` | Maximum tool actions before the loop stops to prevent runaway plans |
| `DREAMAI_MAX_RETRIES` | `2` | Extra retries after a tool failure, per step |
| `DREAMAI_AUTONOMY_VERBOSE` | `false` | Print every think/act/observe/reflect event live |

> The v0.4 planner is a deterministic offline baseline: it maps simple time and calculation intents to built-in tools. A model-driven plan arrives with native function-calling in a later phase.

### 9.5 Run the container image

```bash
# Pull the latest image from the GitHub Container Registry
docker pull ghcr.io/li-guijiang/dream-ai:latest

# Offline demo mode (no API key needed)
docker run -it --rm ghcr.io/li-guijiang/dream-ai:latest

# Connect a hosted model through environment variables
docker run -it --rm \
  -e DREAMAI_API_KEY=your-api-key \
  -e DREAMAI_BASE_URL=https://api.deepseek.com/v1 \
  -e DREAMAI_MODEL=deepseek-chat \
  ghcr.io/li-guijiang/dream-ai:latest
```

The multi-architecture image (`linux/amd64`, `linux/arm64`) is listed under the repository's [Packages section](https://github.com/Li-Guijiang/DreamAI/pkgs/container/dream-ai).

## 10. Project Structure

```
DreamAI/
├── dream_ai/                  # CLI package (published as `dream-ai`)
│   ├── cli.py                 # Command-line interface and in-chat commands
│   ├── config.py              # Environment-based settings
│   ├── agent_factory.py       # Assembles the agent from settings
│   ├── core/                  # Agent and conversation
│   ├── providers/             # Pluggable LLM backends
│   ├── memory/                # Session history, preferences, persistence
│   ├── tools/                 # Registry, built-in tools, call parser
│   └── autonomy/              # Planner, think→act loop, trace models
├── web/                       # Web service and static site
│   ├── app/                   # FastAPI application (config, llm client, routes)
│   ├── web/                   # Static front end served to the browser
│   ├── deploy/                # nginx and systemd deployment templates
│   ├── tools/                 # Maintenance scripts (see its README)
│   └── docs/                  # Screenshots used by the documentation
├── desktop/                   # Electron desktop client
│   ├── electron/              # Main process, preload bridge, local tools
│   ├── test/                  # Node-based tests and E2E helpers
│   └── build/                 # Packaging resources (application icon)
├── docs/                      # Documentation, see docs/README.md
│   ├── adr/                   # Architecture Decision Records
│   └── GUIDE.md               # Chinese walkthrough for first-time users
├── tests/                     # Unit and smoke tests (pytest)
├── examples/                  # Runnable examples
├── assets/                    # Brand logos and media (see assets/README.md)
├── .github/workflows/         # CI, release, PyPI, and container workflows
├── Dockerfile                 # Container image definition
├── .dockerignore              # Files excluded from the build context
├── .editorconfig              # Editor indentation / encoding conventions
├── pyproject.toml             # Package metadata, dependencies, tool config
├── CHANGELOG.md               # Versioned change history
└── LICENSE                    # MIT License
```

## 11. Documentation

Start at [docs/README.md](./docs/README.md) for the full document map. The most-used entries:

| Document | Purpose |
|---|---|
| [docs/GUIDE.md](./docs/GUIDE.md) | Chinese walkthrough: setup, every command, common errors |
| [docs/SETUP.md](./docs/SETUP.md) | Local installation on Windows, macOS, and Linux |
| [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) | Layers, module responsibilities, data flow |
| [docs/ROADMAP.md](./docs/ROADMAP.md) | Phase plan and acceptance criteria |
| [web/README.md](./web/README.md) | Web app features, API, deployment |
| [desktop/README.md](./desktop/README.md) | Desktop development, packaging, security model |

## 12. Contributing

Dream AI is open to the whole world. Issues, suggestions, and pull requests are welcome — whether you are here to learn, to build, or to share your own dream. Start with the [Contributing Guide](./docs/CONTRIBUTING.md) and read the [Code of Conduct](./docs/CODE_OF_CONDUCT.md).

Local checks before opening a pull request:

```bash
pytest
ruff check dream_ai tests examples
ruff format --check dream_ai tests examples
```

## 13. Security

Found a vulnerability? Please report it privately following [SECURITY.md](./docs/SECURITY.md).

## 14. License

Released under the **MIT License**. Copyright (c) 2026 Li Guijiang. All rights reserved.

The MIT License grants others freedom to use and learn from this code; copyright and project ownership remain with the author.

---

> *From a shared dream to a world that understands itself — one step at a time.*
