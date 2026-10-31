# Architecture

Dream AI is a small full-stack assistant with three runtimes:

```
Browser / Electron renderer
        │  HTTPS + SSE
        ▼
FastAPI service (app/)  ──►  OpenAI-compatible model endpoint
        │
        ├─ static site (web/)
        └─ /api/read  ──► public web pages (SSRF guarded)

Electron main (desktop/electron/)
        ├─ local file tools      workspace only
        ├─ document engine       docx / xlsx / pptx / pdf / md
        ├─ coding agent          workspace/Dream AI 项目
        └─ tray / updater
```

## Web service (`app/`)

- `main.py` — routes, rate limiting, daily budget, SSE streaming, memory / context injection, `/api/read`.
- `llm.py` — streaming client for any OpenAI-compatible endpoint; emits `content`, `reasoning` and `usage`.
- `config.py` — environment-driven settings and public model catalog.
- Static files live in `web/` and are served by Nginx in production; Uvicorn serves the entry points during local development.

### Chat request flow

1. Browser posts `POST /api/chat` with messages, model, provider and optional `memory` / `context`.
2. Server resolves the upstream (site free model or the user's BYOK key), applies style and safety prompts.
3. Upstream SSE chunks become `meta`, `delta`, `reasoning`, `usage`, `done` or `error` events.
4. The client renders Markdown, records local usage, and keeps the conversation in `localStorage`.

### Client-only AI features

| Feature | Where it lives | Notes |
| --- | --- | --- |
| Long-term memory | `localStorage` | Injected into the system prompt per request |
| Knowledge base | `localStorage` + BM25 in `app.js` | Top 4 chunks become `context`, citations shown in chat |
| Artifact canvas | sandboxed iframe | HTML / SVG / Markdown only, no same-origin access |
| Prompt library | `localStorage` | Presets + user prompts, `/` command menu |
| Usage dashboard | `localStorage` + `/api/usage` | Local counts and aggregate server counters |
| PWA shell | `web/sw.js` | Network-first navigation, cache-first assets, `/api/*` never cached |

## Desktop (`desktop/`)

- `electron/main.js` — window, IPC, tray, global shortcut, update check.
- `electron/local-tools.js` — scan / organise / rename inside the selected workspace.
- `electron/documents.js` — pure-JS document generation; PDF through `printToPDF`.
- `electron/agent.js` — coding agent: project directories, file writes, command execution, dev servers.
- `electron/update.js` — version / `latest.yml` helpers used by tests.

### Coding mode

1. The renderer asks the model for a project plan (JSON).
2. It creates `workspace/Dream AI 项目/<name>` through IPC.
3. Files are generated in small batches and written with path containment checks.
4. Setup commands run with a timeout, output cap and a command log.
5. A dev server is started, its output is polled, failures trigger a fix-and-retry loop.
6. The user can open the folder, open the URL, or stop the server from the chat card.

## Deployment

- Nginx serves `web/` at `https://liguijiang.com`, proxies `/api/` to `127.0.0.1:8010` with buffering disabled.
- `dreamai-web.service` runs Uvicorn with two workers.
- `/lsl/` is a sibling static directory with its own Nginx location (teacher tools).
- Desktop installers and `latest.yml` live under `web/downloads/`.

## Local development

```bash
# web
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
.venv/Scripts/uvicorn app.main:app --port 8787

# desktop
cd desktop && pnpm install && pnpm start
```
