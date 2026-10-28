# Dream AI — Command-line guide (v0.4.0)

<p align="center"><img src="../assets/brand/banner-docs.gif" alt="" width="720"></p>

<sub>[Back to the documentation index](./README.md)</sub>

> This guide is written for someone opening the project for the first time. It answers four
> questions: **what the assistant can do today, how to get it running, how each command works,
> and what to do when something fails.**
> The project will keep moving through `v0.5`, `v0.6` … up to `v1.0`, and this guide moves with it.
>
> Scope:
> 1. This document covers the **command line (`dream_ai` package)** only. For the web service see
>    [../web/README.md](../web/README.md); for the Windows desktop app see
>    [../desktop/README.md](../desktop/README.md).
> 2. For the project overview see [README.md](../README.md); for every document see the
>    [documentation index](./README.md).
> 3. If you only want installation steps, go straight to [SETUP.md](./SETUP.md).

---

## 0. What Dream AI can do today

The current version is **v0.4.0 (Autonomous Planning)**. It consists of four capability layers:

| Layer | Version | What it does today | Default |
|---|---|---|---|
| **Conversation** | v0.1 | Chat through a replaceable model backend; no vendor lock-in | On |
| **Memory** | v0.2 | Conversation history persisted locally and restored on restart; long-term preferences injected into the prompt | On (persistent) |
| **Tools** | v0.3 | Calculator and clock; sandboxed file read/write; optional web search; writes require confirmation | Calculator/clock on, files/search off |
| **Autonomy** | v0.4 | Splits a goal into an ordered plan and runs a **think → act → observe → reflect** loop with a step budget, retries, approval for protected actions, and a full trace | On |

### What it cannot do yet

- **Without an API key it runs in offline placeholder mode.** Replies simply echo what you said —
  **no model is reasoning** — which is enough to learn the commands and the flow.
- **The planner is a deterministic offline baseline.** It recognises time and calculation intents
  only; model-driven decomposition arrives in a later phase.
- **Native function calling is not wired up.** Tools are invoked through `/tool` or by the
  autonomous loop following a plan.
- Streaming output, vector memory, and local open-source models are not available yet. They are on
  the [roadmap](ROADMAP.md).

---

## 1. Environment setup (once)

### 1.1 Requirements

- **Python 3.11 or newer** (tested on 3.11, 3.12, and 3.13).
- A terminal where the `python` command works.
- Docker only if you want to run the container; the command line does not need it.

### 1.2 Check Python

Open a terminal in the project directory and run:

```powershell
python --version
```

Anything like `Python 3.13.16` is fine. If you get `'python' is not recognized`, install Python from
python.org, tick **Add Python to PATH** during installation, then reopen the terminal.

### 1.3 Enter the project directory

```powershell
cd C:\path\to\DreamAI
```

> Cloning on a new machine:
> ```powershell
> git clone https://github.com/Li-Guijiang/DreamAI.git
> cd DreamAI
> ```

### 1.4 Create a virtual environment and install (recommended)

**Windows PowerShell:**

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -e .
```

**macOS / Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
pip install -e .
```

> Development tools (tests, lint, packaging):
> ```powershell
> pip install -e ".[dev]"
> ```

When it works, your prompt is prefixed with `(.venv)`. Before every later session, `cd` into the
project and activate the environment again.

---

## 2. First start

### 2.1 Copy the configuration file

**Windows:**

```powershell
copy .env.example .env
```

**macOS / Linux:**

```bash
cp .env.example .env
```

`.env` is ignored by `.gitignore` and **is never committed**, so it is safe to put keys there.

### 2.2 Start

```powershell
python -m dream_ai
```

After installing the package you can also use:

```powershell
dream-ai
```

A successful start prints the banner, a welcome line, an offline/online notice, and three status
lines:

```text
Offline demo mode: no hosted API key was configured ...
Memory: persistent (C:\Users\you\.dream_ai)
Autonomy: on (max steps: 10, retries: 2)
Tools: 2 registered
```

- **Offline demo mode** appears when no key is configured, which is expected.
- `Memory: persistent` — history and preferences are written to disk.
- `Autonomy: on` — autonomous tasks are enabled.
- `Tools: 2 registered` — the calculator and the clock.

Exit with `/quit` or `/exit`.

---

## 3. The two run modes

### 3.1 Offline demo mode (no key needed)

Leave `DREAMAI_API_KEY=` empty in `.env` and the program falls back to the local placeholder
backend. Commands, memory, tools, and the autonomous loop all work; the conversation content is an
echo, not real reasoning.

### 3.2 Connect a real model (DeepSeek as the example)

1. Create an API key in the DeepSeek platform.
2. Open `.env` in the project root and fill in:

```ini
DREAMAI_PROVIDER=openai_compat
DREAMAI_BASE_URL=https://api.deepseek.com/v1
DREAMAI_API_KEY=paste-your-key-here
DREAMAI_MODEL=deepseek-chat
```

3. Save and restart `python -m dream_ai`. The offline notice disappears and the startup line shows
   `Connected via provider: openai-compat`.

**Other compatible endpoints** (change `DREAMAI_BASE_URL` and `DREAMAI_MODEL`):

| Platform | `DREAMAI_BASE_URL` | `DREAMAI_MODEL` example |
|---|---|---|
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` |
| DashScope compatible mode | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-plus` |

> You can also skip `.env` and override values on the command line (these take precedence):
>
> ```powershell
> python -m dream_ai --provider openai_compat --api-key YOUR_KEY --model deepseek-chat --base-url https://api.deepseek.com/v1
> ```

---

## 4. Using the four capability layers

### 4.1 Conversation

Type after the `you ›` prompt and press Enter.

| Command | Action |
|---|---|
| Plain text | One chat turn with Dream AI |
| `/clear` | Clear the current conversation (the system prompt is kept) |
| `/motion` | Toggle the launch sequence, typed replies, and thinking spinner for this session |
| `/about` | Show model, tools, autonomy state, message count, and preference count |

> Motion only starts in an interactive terminal. Redirected output, `NO_COLOR`, or the
> `--no-animation` flag automatically keeps the output plain and stable for logs.

### 4.2 Memory (v0.2)

| Command | Action | Example |
|---|---|---|
| `/remember <text>` | Store a long-term preference that is injected into the prompt | `/remember I cycle to work, keep replies short` |
| `/memory` | Show remembered preferences | — |
| `/forget` | Clear every preference | — |
| `/clear` | Clear the conversation only, keeping preferences | — |

History and preferences live in `~/.dream_ai/` (`C:\Users\you\.dream_ai\` on Windows) and are
restored on the next start. The switches are listed in section 6.

### 4.3 Tools (v0.3)

**List what is registered:**

```text
/tools
```

**Call a tool manually:**

```text
/tool <tool-name> {"argument": "value"}
```

The four built-in tools:

#### 1. `calculator` (safe, on by default)

Supports numbers, `+ - * / % // **`, parentheses, and `abs` / `round` / `min` / `max` / `sqrt`.
It does **not use `eval`** and rejects names, imports, subscripts, and every other unsafe construct.

```text
/tool calculator {"expression": "2 + 3 * 4"}
/tool calculator {"expression": "(12 + 8) / 5"}
/tool calculator {"expression": "sqrt(144)"}
```

Actual output:

```text
tool › 2 + 3 * 4 = 14
tool › (12 + 8) / 5 = 4
tool › sqrt(144) = 12
```

#### 2. `clock` (safe, on by default)

```text
/tool clock
```

Actual output:

```text
tool › Current local time: 2026-10-24 19:56:07 +0800
Weekday: Saturday
```

#### 3. `file_read` / `file_write` (protected, off by default)

Enable them in `.env` first:

```ini
DREAMAI_FILE_ACCESS_ENABLED=true
# DREAMAI_WORKSPACE_DIR=.dream_ai/workspace   # optional: custom sandbox directory
```

- Every path stays inside the workspace directory: **absolute paths and `..` traversal are rejected**.
- `file_write` changes state, so it **asks for confirmation** before running.

Read:

```text
/tool file_read {"path": "notes.txt"}
```

Write (the prompt `Tool 'file_write' will modify files. Confirm? [y/N]` appears; only `y` or `yes`
proceeds):

```text
/tool file_write {"path": "notes.txt", "content": "First note from Dream AI v0.4"}
```

#### 4. `web_search` (protected, off by default)

Enable it in `.env` first:

```ini
DREAMAI_WEB_SEARCH_ENABLED=true
```

```text
/tool web_search {"query": "OpenAI"}
```

> This tool uses the DuckDuckGo instant-answer endpoint and returns a short summary only. When the
> network is unavailable it raises a clear error instead of crashing.

**Master switch:** `DREAMAI_TOOLS_ENABLED=false` disables the whole registry.

### 4.4 Autonomous tasks (v0.4)

Let Dream AI decompose a goal and work through it step by step.

#### Start a task

```text
/run What time is it now, and calculate 12 * 7?
```

The engine **plans → thinks → calls a tool → observes → reflects → moves on**, recording every event
in the trace. Turn on verbose logging to watch it live:

```ini
DREAMAI_AUTONOMY_VERBOSE=true
```

#### Review the last task

```text
/trace
```

It prints the objective, the final status, each step's title/status/observation, and the full
`plan / think / act / observe / reflect / confirm / done / abort` trace.

#### Safety rails

- **Step budget** — `DREAMAI_MAX_STEPS` caps how many tool calls one task may make; when it runs out
  the loop stops, so a plan cannot run away.
- **Retries** — `DREAMAI_MAX_RETRIES` sets extra attempts per failed step; when they are spent the
  step is marked failed and the run stops.
- **Protected actions** — writing files and similar actions ask
  `Protected action 'file_write' {...}` / `Confirm this action? [y/N]` before running. Declining
  cancels the whole task safely.

#### Offline demo objectives

```text
/run What time is it now?
/run What time is it now, and calculate 12 * 7?
```

---

## 5. Command reference (v0.4.0, complete)

| Command | Action |
|---|---|
| `/help` | Show help |
| `/run <objective>` | Start an autonomous multi-step task |
| `/trace` | Review the plan, steps, and trace of the last task |
| `/tools` | List registered tools, risk level, and required arguments |
| `/tool <name> <JSON>` | Call a tool, e.g. `/tool calculator {"expression": "2 * 3"}` |
| `/remember <text>` | Store a long-term preference |
| `/memory` | Show remembered preferences |
| `/forget` | Clear every preference |
| `/clear` | Clear the current conversation |
| `/motion` | Toggle terminal visual effects for the current session |
| `/about` | Show model, tools, autonomy, turns, preferences, and the last task status |
| `/quit` or `/exit` | Leave Dream AI |
| Anything else | A normal chat turn |

---

## 6. Configuration reference (`.env`)

### Model backend

| Variable | Default | Meaning |
|---|---|---|
| `DREAMAI_PROVIDER` | `openai_compat` | `openai_compat` for any compatible endpoint, `local` to force offline |
| `DREAMAI_BASE_URL` | `https://api.deepseek.com/v1` | Endpoint URL |
| `DREAMAI_API_KEY` | empty | Empty falls back to the offline placeholder |
| `DREAMAI_MODEL` | `deepseek-chat` | Model name |
| `DREAMAI_SYSTEM_PROMPT` | built-in persona | System prompt for the assistant |

### Memory

| Variable | Default | Meaning |
|---|---|---|
| `DREAMAI_PERSISTENCE` | `true` | Persist conversation and preferences; `false` keeps them in memory only |
| `DREAMAI_DATA_DIR` | `~/.dream_ai` | Directory for memory files; a relative path such as `.dream_ai` also works |

### Tools

| Variable | Default | Meaning |
|---|---|---|
| `DREAMAI_TOOLS_ENABLED` | `true` | Master switch for the registry |
| `DREAMAI_FILE_ACCESS_ENABLED` | `false` | Enable sandboxed file read/write |
| `DREAMAI_WEB_SEARCH_ENABLED` | `false` | Enable web search |
| `DREAMAI_WORKSPACE_DIR` | `<data dir>/workspace` | Sandbox root for the file tools |

### Autonomy

| Variable | Default | Meaning |
|---|---|---|
| `DREAMAI_AUTONOMY_ENABLED` | `true` | Master switch; with `false`, `/run` is unavailable |
| `DREAMAI_MAX_STEPS` | `10` | Maximum tool calls per task (step budget) |
| `DREAMAI_MAX_RETRIES` | `2` | Extra attempts per failed step; `0` disables retries |
| `DREAMAI_AUTONOMY_VERBOSE` | `false` | Print every think/act/observe/reflect event live |

### Terminal motion

| Variable | Default | Meaning |
|---|---|---|
| `DREAMAI_ANIMATIONS` | `auto` | Enable the launch wordmark, typed replies, and spinner in an interactive terminal; `false` forces plain text |
| `DREAMAI_ANIMATION_SPEED` | `1.0` | Speed multiplier for terminal effects (`0.25`–`4.0`) |

`--no-animation` (alias `--no-motion`) disables effects for one run; `/motion` toggles them for the
current session. The web surface has its own independent motion switch on every page.

---

## 7. Run the bundled examples (no interactive shell needed)

From the project root:

```powershell
python examples/basic_chat.py      # minimal single-turn chat
python examples/tool_demo.py       # list tools, run the calculator and clock
python examples/autonomy_demo.py   # run a two-step autonomous task and print plan + trace
```

None of them need an API key.

---

## 8. Run in a container (optional, Docker required)

```bash
# Pull the image
docker pull ghcr.io/li-guijiang/dream-ai:latest

# Offline demo mode
docker run -it --rm ghcr.io/li-guijiang/dream-ai:latest

# Connect a real model
docker run -it --rm \
  -e DREAMAI_API_KEY=your-key \
  -e DREAMAI_BASE_URL=https://api.deepseek.com/v1 \
  -e DREAMAI_MODEL=deepseek-chat \
  ghcr.io/li-guijiang/dream-ai:latest
```

The image is published for both `linux/amd64` and `linux/arm64`. See the
[Packages page](https://github.com/Li-Guijiang/DreamAI/pkgs/container/dream-ai).

---

## 9. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `'python' is not recognized` | Python is not on PATH | Reinstall Python with "Add to PATH", then reopen the terminal |
| `No module named openai` | Dependencies missing or the environment is not active | Activate `.venv`, then `pip install -e .` |
| Replies start with `[Local demo mode]` | `DREAMAI_API_KEY` is empty | Set the key in `.env` and restart; this is the offline fallback, not an error |
| Provider authentication error | Key, URL, or model name mismatch, or an expired key | Check all three against the provider's documentation |
| Web search fails | Network unreachable or endpoint timeout | Check proxy/firewall; the tool never crashes the program |
| `Path escapes the workspace sandbox` | The path leaves the workspace | Use workspace-relative paths only, no absolute paths or `..` |
| `Tool error: Unknown tool: 'xxx'` | Typo, or the tool is disabled | Run `/tools` to see what is registered |
| `.env` changes have no effect | The program was not restarted | `/quit`, then run `python -m dream_ai` again |
| `/run` reports autonomy disabled | `DREAMAI_AUTONOMY_ENABLED=false` | Set it back to `true` and restart |

Tests and lint (for developers):

```powershell
pytest
ruff check dream_ai tests examples web/app web/tools
```

---

## 10. Where the project goes next

- **v0.5 / v0.6 …** — stronger model integration, better plans, and a wider capability surface.
- **v1.0.0** — a stable release: stable public API, configuration and memory backup, hardened error
  handling, and a friendly experience for non-developers.
- **Future** — self-hosted open-source models, model switching without losing sessions or memory,
  and data that stays local by default.

The full plan is in [ROADMAP.md](ROADMAP.md); version history is in [CHANGELOG.md](../CHANGELOG.md).
