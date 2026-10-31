# Changelog

## v1.5.0 — 2026-10-31

### Web

- **Long-term memory**: auto-capture `记住：…`, manager with enable/disable, injected into the system prompt.
- **Local knowledge base**: import text/code files, BM25 retrieval on-device, top chunks sent as context, citations under each answer.
- **Artifact canvas**: HTML / SVG / Markdown code blocks can be previewed in a sandboxed iframe and downloaded.
- **Link reader**: `/api/read` extracts readable text from public pages with SSRF protection; composer button and citation chip.
- **Prompt library and slash commands**: 8 built-in presets, custom prompts, `/` quick menu.
- **Smart routing**: with a BYOK key, coding/document tasks use DeepSeek Chat and complex questions use R1.
- **Usage dashboard**: local requests/tokens per day, 7-day chart, model distribution, server aggregate via `/api/usage`.
- **Read aloud** for assistant replies (Web Speech API).
- **PWA offline shell**: service worker caches the app shell; API calls are never cached.
- **Changelog page** and refreshed navigation.
- API: `usage` SSE event, enriched `/api/health`, `/api/usage`, `memory` / `context` request fields.

### Desktop

- **Project manager** tab in the agent panel: list projects, open folder, stop all services.
- **Update check**: reads the published `latest.yml`, compares versions and offers the download page when a newer build exists.
- **Tray icon** and global shortcut `Ctrl+Alt+D`; closing the window keeps the app in the tray.
- Updater version helpers with unit tests.

### Engineering

- CI checks the web client, service worker and every Electron module.
- Architecture and security documentation.

## v1.2.0 — 2026-10-27

- Desktop coding mode: plan, write files, install dependencies, run commands, start a server, fix errors.
- Zero-dependency defaults, built-in scaffold fallback, command whitelist and `dreamai-commands.log`.

## v1.1.0 — 2026-10-26

- Document generation (Word / Excel / PPT / PDF / Markdown), six office templates.
- Frameless desktop shell, agent activity panel, artifact list.

## v1.0.0 — 2026-10-26

- Windows desktop MVP: local file workbench (organise, rename, export), native confirmations.
