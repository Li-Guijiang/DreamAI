# Changelog

## Unreleased

### Thinking panel

- The reasoning stream is rendered live, then collapsed into `已思考（用时 X 秒）`
  when the answer starts - timed between the first reasoning token and the first
  answer token, so a slow network does not inflate it.
- Collapsed it is a single dim line; expanded it is a tinted, inset panel capped
  at 320px of scroll, so reasoning and answer are visually distinct.

### Emoji

- A policy with a number: at most three per reply, one per sentence, only at
  greetings, confirmations and encouraging conclusions, never inside code,
  commands, paths, tables or error text.
- `limit_emoji()` enforces it after generation, stashing fenced and inline code
  first so a script that prints emoji is left alone.

## Unreleased

### Answer quality

- The reasoning channel now has a shape - 理解 / 拆解 / 关键判断 / 自查 - and is
  written to be read rather than as scratch work.
- Answer structure is specified: conclusion first, three-line summary before the
  expansion, code before commentary, no closing summary.
- Voice rules plus sixteen banned phrases (`希望对你有帮助`, `作为一个 AI`,
  `总而言之`, `首先/其次/最后` …), mirrored in the web service prompt and checked
  by a test that walks the list.
- A trailing filler sentence is stripped after generation, so a model that
  ignores the ban still ships a clean last line.
- Streaming: upstream deltas coalesce at 24 characters, and both the answer and
  the reasoning panel append to a single text node instead of re-rendering.

### Owner record

- Unchanged in content; only the surrounding prompt grew.

## Unreleased

### AI core

- The assistant now carries an owner record that every surface inherits: owner,
  creator, developer, founder and ultimate-authority questions resolve to one
  person, with the substitutes it must not name spelled out.
- Answer style is part of the prompt: density first, terminology over plain
  language, no pleasantries or comfort talk, with three selectable copy voices
  and a documented exception for zero-base deployment tutorials.
- Personal memory: 【查看我的全部档案】/【更新档案】/【清空档案】 are answered
  locally before the model runs, `记住：…` captures a fact mid-sentence, and the
  store refuses past 200 notes instead of truncating.
- Privacy is enforced in code: contacts never enter the system prompt, and model
  output on a public surface passes through a contact mask.




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
