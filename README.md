# Dream AI

> Dream AI is a general-purpose AI assistant built around one shared dream: helping people everywhere think clearly, reason deeply, create freely, and solve what matters. It studies the world — its knowledge, logic, and deepest questions — and stays open to everyone, so thoughtful, capable intelligence can serve all people across the world.

[![Status: WIP](https://img.shields.io/badge/status-WIP-orange)](./README.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](./LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python&logoColor=white)](./README.md)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](./docs/CONTRIBUTING.md)

---

## 📖 About

**Dream AI** is an open-source, general-purpose AI assistant being built from the ground up as a long-term, lifelong project. It reasons, remembers, uses tools, and plans — growing step by step into a capable assistant that serves everyone around the world.

> ⚠️ **Status: Early development (WIP).** Dream AI is under active construction. Many features described here are planned rather than finished. See the [Roadmap](./docs/ROADMAP.md) for what exists today and what comes next.

## 🌙 Vision

**Dream** is the shared promise behind this project: people everywhere, united by a common dream, seeking to understand the world — its knowledge, its logic, its deepest questions.

Dream AI is the general-purpose assistant built to walk that path with us. It begins small and grows step by step into a capable, thoughtful intelligence, open to everyone across the world who wants to learn, build, or dream alongside it.

This is a long-term project. It is small today, but every great system starts as a single dream.

## ✨ Features by Phase

> Status marks: `[x]` done · `[~]` in progress · `[ ]` planned.

### Phase 1 — Conversation (`v0.1`)
- [x] Project skeleton and package layout
- [x] Pluggable provider interface (not locked to any vendor)
- [x] CLI conversation loop with session history
- [~] Hosted model integration (configure your own API key)
- [ ] Streaming responses

### Phase 2 — Memory (`v0.2`)
- [ ] Persistent long-term memory
- [ ] Preference and profile recall
- [ ] Retrieval-based memory (vector search)

### Phase 3 — Tool Use (`v0.3`)
- [x] Tool registry contract
- [ ] Web search
- [ ] File read/write
- [ ] Calculator and built-in utilities

### Phase 4 — Autonomous Planning (`v0.4`)
- [ ] Reasoning loop: think → act → observe
- [ ] Multi-step task decomposition
- [ ] Autonomous execution of complex goals

## 🏗️ Architecture

```
┌──────────────────────────────────────────────┐
│                   Dream AI                    │
│              CLI / Future UI                   │
└───────────────────┬──────────────────────────┘
                     │
┌───────────────────▼──────────────────────────┐
│              Agent Core (Reasoning Loop)      │
│   Plan → Reason → Act → Observe → Reflect      │
└───────┬────────────────┬────────────┬────────┘
        │                │            │
┌───────▼──────┐  ┌──────▼──────┐ ┌──▼─────────┐
│ LLM Provider │  │   Memory    │ │   Tools    │
│ (pluggable:  │  │ short/long  │ │ search, fs,│
│  API/local)  │  │ term, vector│ │ calculator │
└─────────────┘  └─────────────┘ └────────────┘
```

The core depends only on small abstract interfaces, so hosted APIs, local open-source models, and future custom backends can be swapped in without rewriting the agent. Full details: [Architecture](./docs/ARCHITECTURE.md).

## 🗺️ Roadmap

| Version | Milestone | Goal |
|---------|-----------|------|
| `v0.1.0` | **Conversation** | Working conversational loop through a pluggable provider |
| `v0.2.0` | **Memory** | Session context plus persistent long-term memory |
| `v0.3.0` | **Tools** | Tool registry with search, file, and calculator utilities |
| `v0.4.0` | **Autonomy** | Reasoning loop, task decomposition, multi-step planning |
| `v1.0.0` | **Stable Assistant** | A reliable general-purpose personal agent |
| `Future` | **Self-hosted & owned** | Local open-source model deployment for full independence |

Detailed milestones and acceptance criteria: [docs/ROADMAP.md](./docs/ROADMAP.md).

## 💡 Plans & Pricing (Vision)

Dream AI is open-source and free to use. A future set of optional hosted plans is planned to support development and add convenience services. **These are vision-level plans only — none are available yet.**

| | **Free** | **Pro** | **Team** |
|---|---|---|---|
| Open-source code & self-hosting | ✅ | ✅ | ✅ |
| Local CLI / offline mode | ✅ | ✅ | ✅ |
| Conversation history | Session | Persistent | Persistent |
| Priority hosted model access | — | ✅ | ✅ |
| Long-term memory & tools | — | ✅ | ✅ |
| Shared team workspaces | — | — | ✅ |
| Priority support | — | ✅ | ✅ |

Full plan definitions, feature matrix, and principles: [docs/PRICING.md](./docs/PRICING.md).

## 🚀 Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/Li-Guijiang/DreamAI.git
cd DreamAI

# 2. Create and activate a virtual environment
python -m venv .venv
# Windows:        .venv\Scripts\activate
# macOS / Linux:  source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure your model (copy the example and fill in your API key)
# Windows:  copy .env.example .env
# macOS/Linux: cp .env.example .env

# 5. Start chatting
python -m dream_ai
```

Without an API key, Dream AI starts in **offline demo mode** so you can explore the CLI and conversation flow. See [docs/SETUP.md](./docs/SETUP.md) for a step-by-step guide.

## 📁 Project Structure

```
DreamAI/
├── dream_ai/
│   ├── cli.py              # Command-line interface
│   ├── config.py           # Environment-based settings
│   ├── core/               # Agent, conversation
│   ├── providers/          # Pluggable LLM backends
│   ├── memory/             # Conversation and long-term memory
│   └── tools/              # Tool registry and capabilities
├── tests/                  # Unit and smoke tests
├── examples/               # Runnable examples
├── docs/                   # Roadmap, architecture, plans, guides
└── assets/                 # Logos and media
```

## 🤝 Contributing

Dream AI is open to the whole world. Issues, suggestions, and pull requests are welcome — whether you are here to learn, to build, or to share your own dream. Start with [Contributing Guide](./docs/CONTRIBUTING.md) and read the [Code of Conduct](./docs/CODE_OF_CONDUCT.md).

## 🔒 Security

Found a vulnerability? Please report it privately following [SECURITY.md](./docs/SECURITY.md).

## 📄 License

Released under the **MIT License**. Copyright (c) 2026 Li Guijiang. All rights reserved.

The MIT License grants others freedom to use and learn from this code; copyright and project ownership remain with the author.

---

> *From a shared dream to a world that understands itself — one step at a time.*
