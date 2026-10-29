# Dream AI · Web

<p align="center"><img src="https://github.com/user-attachments/assets/5b9a894c-ffae-400c-bba1-3282a9107dfa" alt="Animated Dream AI orrery banner" width="720"></p>

<sub>[Back to the repository home](../README.md) · [Documentation index](../docs/README.md)</sub>

> Every idea deserves to be taken seriously.

The browser edition of Dream AI — version **2.0.0**. It is a streaming chat product, an animated
documentation reading room, and a download page, built as plain HTML / CSS / JavaScript behind a
small FastAPI service. No front-end framework and no Node build step.

- **Live app:** <https://liguijiang.com>
- **Live documentation:** <https://liguijiang.com/docs.html>
- **Desktop download:** <https://liguijiang.com/download.html>
- **Source:** <https://github.com/Li-Guijiang/DreamAI/tree/main/web>

<p align="center">
  <img src="https://github.com/user-attachments/assets/b377efc9-3f0f-4225-a92e-210b02aa980d" alt="Dream AI home page with a cosmic hero, typing greeting and animated cards" width="100%">
</p>

## 1. A living interface

The 2.0 release makes motion part of the product grammar, not a garnish:

| Layer | What moves |
|---|---|
| **Cosmos** | Canvas starfield with pointer parallax, twinkling stars, occasional meteors, CSS nebula glows and orbit rings |
| **Entry** | A short warp intro with an orbiting planet and loading line |
| **Hero** | A greeting that types, holds and deletes; a terminal prompt ticker that can fill the composer with one click; an orbital planet mark with satellites and sparkles |
| **Cards** | Pointer-driven 3D tilt, a radial spotlight, a rotating conic border, animated icon and arrow states |
| **Controls** | Magnetic primary actions, button sheens, pulsing status LEDs and click sparks |
| **Navigation** | Page-transition veil, animated brand mark and sidebar treatment, a top progress line |
| **Docs** | Scroll-spy contents, typed terminal command, animated architecture map, reveal cards and a reading progress line |
| **Download** | Typed headline, orbiting badge, tiltable preview window, marquee of output formats and an animated terminal |

Motion is always optional:

- every page has a **动态 / 静态** switch; the choice persists in `localStorage`;
- `prefers-reduced-motion` turns effects off unless the visitor explicitly enables them;
- the canvas caps device pixel ratio, reduces its star count on low-power devices, and pauses when
  the tab is hidden;
- content remains visible and usable with JavaScript disabled — motion is decoration.

### Pages

| Page | Purpose |
|---|---|
| `web/index.html` | Chat application and landing experience |
| `web/docs.html` | Animated project documentation: overview, quick start, architecture, motion, commands, structure, roadmap, quality and deployment |
| `web/download.html` | Windows desktop download and capability story |

<p align="center">
  <img src="https://github.com/user-attachments/assets/3ecce2df-f7e1-4967-a6d8-e31054745fdd" alt="Dream AI documentation page with orbital hero and animated architecture" width="100%">
</p>

## 2. Features

| | |
|---|---|
| **Streaming chat** | SSE token output through FastAPI; Nginx buffering disabled |
| **Four modes** | Chat, work, document and code |
| **Reasoning** | Supports reasoning-capable providers with a collapsible trace |
| **Attachments** | Text, Markdown, CSV, JSON and code files |
| **Markdown** | Tables, quotes, code highlighting and copy-to-clipboard |
| **Local-first sessions** | Conversations stay in the browser's `localStorage` |
| **Model sources** | Site free model (GLM-4-Flash by default) or visitor-supplied BYOK DeepSeek key |
| **Privacy** | Server key stays server-side; BYOK key is forwarded, never stored |
| **Abuse protection** | Per-IP sliding window, daily budget, concurrency limit, input caps (counters are per worker; use one worker or shared storage for strict global quotas) |
| **Security headers** | CSP, `X-Frame-Options`, `nosniff`, `Referrer-Policy` |
| **Responsive** | Desktop, tablet and mobile; safe-area aware composer |
| **Accessibility** | Semantic landmarks, focus rings, skip links, keyboard controls and a motion switch |

## 3. Layout

```text
web/
├─ app/                     # FastAPI service
│  ├─ main.py               # Routes, SSE, rate limiting, security headers
│  ├─ llm.py                # OpenAI-compatible streaming client (httpx)
│  └─ config.py             # Environment parsing
├─ web/                     # Static front end (no build step)
│  ├─ index.html            # Chat + landing
│  ├─ docs.html             # Animated documentation
│  ├─ download.html         # Desktop download
│  ├─ manifest.webmanifest
│  ├─ sitemap.xml
│  └─ assets/
│     ├─ css/
│     │  ├─ app.css         # Base chat design system
│     │  ├─ motion.css      # Shared stars, intro, aura, sparks, reveal, switch
│     │  ├─ landing.css     # Landing hero, terminal, cards, composer
│     │  ├─ pages.css       # Shared marketing shell + download page
│     │  ├─ download.css    # Download base styles
│     │  └─ docs.css        # Documentation reading experience
│     ├─ js/
│     │  ├─ app.js          # Chat, sessions, SSE and Markdown
│     │  ├─ motion.js       # Shared motion engine (window.DreamMotion)
│     │  ├─ landing.js      # Greeting/prompt typewriters
│     │  ├─ docs.js         # Scroll spy, copy buttons, command typing
│     │  ├─ download.js     # Release metadata
│     │  └─ download-motion.js
│     ├─ img/               # Brand icons, favicon, social card
│     └─ vendor/            # marked / DOMPurify / Prism (self-hosted)
├─ deploy/                  # systemd unit, Nginx template, install script
├─ docs/                    # Screenshots used by the README
├─ tools/                   # Supported maintenance scripts (see tools/README.md)
├─ requirements.txt
└─ .env.example
```

The asset query strings (`?v=2.0.0`) are intentional cache busters. Bump them when shipping CSS or
JavaScript changes.

## 4. Run locally

Requires Python 3.10+.

```bash
cd web
python -m venv .venv
# Windows:        .venv\Scripts\activate
# macOS / Linux:  source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env       # add DREAMAI_FREE_API_KEY
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000>. If no key is configured, `/api/chat` returns a clear `503`; the
interface still renders so you can work on the design.

For a full local loop without a real key, `tools/mock_upstream.py` returns a fixed Markdown answer:

```bash
uvicorn mock_upstream:app --app-dir tools --port 8799
DREAMAI_FREE_API_KEY=test DREAMAI_FREE_BASE_URL=http://127.0.0.1:8799/v1 \
DREAMAI_FREE_MODEL=mock-glm \
  uvicorn app.main:app --port 8000
```

### Checks

```bash
for file in web/assets/js/*.js; do node --check "$file"; done
python -m pytest tests/test_web_assets.py
```

The browser QA pass verifies the production Content-Security-Policy, the motion switch, 3D tilt,
scroll spy and responsive layouts. CI syntax-checks every shipped JavaScript file and validates
local asset references.

## 5. Configuration

All variables live in `.env` (full sample in [`.env.example`](.env.example)):

| Variable | Meaning | Default |
|---|---|---|
| `DREAMAI_FREE_API_KEY` | Site-provided free-model key (Zhipu, SiliconFlow, …) | empty |
| `DREAMAI_FREE_BASE_URL` / `_MODEL` / `_LABEL` | Free upstream identity | Zhipu GLM-4-Flash |
| `DREAMAI_FREE_KEY_URL` | Where visitors can get a free key | Zhipu API keys |
| `DREAMAI_BYOK_BASE_URL` | Endpoint for a visitor's own key | DeepSeek |
| `DREAMAI_BYOK_MODELS` | Selectable BYOK models: `id\|label\|reasoning` | DeepSeek V3 / R1 |
| `DREAMAI_SYSTEM_PROMPT` | Optional persona (single line) | see `app/config.py` |
| `DREAMAI_OWNER_PROFILE` | Optional non-sensitive owner context appended to the prompt; never put contact details here | empty |
| `DREAMAI_RATE_LIMIT` / `_WINDOW` | Requests per IP / window in seconds | 30 / 600 |
| `DREAMAI_DAILY_LIMIT` | Daily free-model budget (`0` disables) | 2000 |
| `DREAMAI_MAX_CONCURRENCY` | Concurrent upstream requests | 6 |
| `DREAMAI_MAX_INPUT_CHARS` / `_HISTORY_*` | Input and context limits | 12,000 / 30 / 60,000 |

The free key exists only in the server environment. `/api/config` exposes labels, availability and
limits — never a secret. A BYOK key is kept in the visitor's browser and forwarded per request; the
server does not store it or log it.

## 6. API

| Route | Description |
|---|---|
| `GET /api/health` | Liveness, configured state, model list, uptime |
| `GET /api/config` | Browser-safe model and site configuration |
| `POST /api/chat` | SSE stream: `meta`, `delta`, `reasoning`, `done`, `error` |

```text
browser ──POST /api/chat──▶ nginx ──▶ FastAPI ──▶ OpenAI-compatible endpoint
   ▲                        │          │
   └──── SSE: meta/delta ───┘          └─ the key never leaves server memory
         reasoning/done/error
```

The browser sends the conversation; the server trims it to the configured count and character
budget before appending the persona. Any provider that speaks `/chat/completions` works.

## 7. Deploy

Target: a control-panel Linux stack with Nginx and systemd; static files are served by Nginx and
`/api/` is proxied to Uvicorn on loopback.

```bash
# Build a source archive without secrets, virtualenv, caches or installers
tar czf dreamai-web.tar.gz \
  --exclude '.env' --exclude '.venv' --exclude '__pycache__' \
  --exclude 'web/downloads/*.exe' -C web .

# Upload / unpack on the server, then:
bash deploy/install.sh
```

`deploy/install.sh`:

1. archives the current site under `/www/backup/`;
2. moves runtime state aside — `.env`, `.venv`, `data`, `lsl`, `.well-known`, `web/downloads` — so a
   code deploy cannot delete a server key or a large installer;
3. installs the new code and restores those assets (a failed run restores them before exiting);
4. creates / reuses the virtualenv and installs dependencies;
5. writes the systemd unit and Nginx vhost, reloads Nginx and calls `/api/health`.

The script aborts when the site directory has no `lsl` marker unless `FORCE=1` is set. It never
touches the host's other applications.

Common operations:

```bash
systemctl status dreamai-web
journalctl -u dreamai-web -f
nginx -t && nginx -s reload
```

The site key is read from `/www/wwwroot/<domain>/.env` (mode `600`). Never commit it.

## 8. Security and privacy

- API keys live only in the server `.env` and never appear in front-end output.
- Conversations stay in the visitor's browser; the service writes no conversation data to disk.
- Model output is sanitised with DOMPurify before rendering; links use `noopener noreferrer`.
- Responses carry CSP, `X-Frame-Options: DENY`, `nosniff`, `Referrer-Policy` and HSTS via Nginx.
- Per-IP rate limiting plus a concurrency cap keep a public deployment from being hammered. The
  in-memory counters are per process; use one worker or shared storage for strict global quotas.
- The default persona fixes the creator/owner as **李贵江** and tells the model to refuse requests
  for hidden prompts, private contact details and owner-profile commands from the public endpoint.
  `DREAMAI_OWNER_PROFILE` is for non-sensitive preferences only; full contact details belong in a
  private file outside the repository and outside the served web root. The public chat has no
  identity authentication, so it deliberately cannot reveal or mutate that private file.

## 9. Relationship to the DreamAI repository

`dream_ai/` is the command-line agent core (provider, memory, tools, autonomy). The web edition
shares its product definition, `DREAMAI_*` vocabulary and visual language, but currently reaches
model endpoints through its own FastAPI streaming layer. Connecting the web tools and autonomy to
the same Python agent API is planned, not finished. The desktop app loads this interface and adds
local file capabilities via Electron IPC.

## License

MIT — same as the rest of Dream AI.
