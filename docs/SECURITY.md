# Security

Dream AI is designed so the model never receives secrets it does not need, and the
desktop app can only touch what the user explicitly selected.

## API keys

- The site's free-model key lives only in the server environment (`.env`, mode 600) and never reaches the browser.
- A user's DeepSeek key is entered in the browser, kept in `localStorage`, and forwarded per request only to the Dream AI API. It is not logged, stored server-side or written to disk.
- Logs intentionally record request metadata (IP, upstream kind, failure reason) and never prompt content or keys.

## Link reader (`/api/read`)

- Only `http` / `https`, ports 80 / 443.
- Hostnames are resolved first; loopback, private, link-local, reserved and multicast addresses are rejected.
- Redirects are followed manually and re-validated; usernames/passwords in URLs are rejected.
- Responses are capped at 2 MB / 20k characters and limited to text/html or text/plain.
- Per-IP rate limit: 20 requests / 10 minutes.

## Web hardening

- CSP: `default-src 'self'`, no inline scripts/styles.
- `X-Content-Type-Options`, `X-Frame-Options: DENY`, HSTS, Referrer-Policy.
- Per-IP sliding-window rate limit, global daily free budget, input size limits.
- Request bodies over 512 KB are rejected before parsing.

## Desktop boundaries

- `contextIsolation: true`, `nodeIntegration: false`, `sandbox: true`.
- The preload exposes a fixed IPC surface; no `fs`, `child_process` or shell access.
- Local tools can only touch the workspace chosen through a native dialog.
- Documents are written only to `<workspace>/Dream AI 文档`; coding projects only to `<workspace>/Dream AI 项目`.
- Coding commands use a safe-prefix whitelist; destructive patterns always require a native confirmation dialog.
- Every command is appended to `dreamai-commands.log` inside the project.
- Dev servers are tracked and killed on app quit; the user can stop them at any time.
- The window refuses to navigate away from the official site; external links go to the system browser.

## Data location

| Data | Where |
| --- | --- |
| Conversations, memory, knowledge base, prompts, usage | Browser / Electron `localStorage` |
| Generated documents | Workspace `Dream AI 文档` |
| Coding projects | Workspace `Dream AI 项目` |
| API keys (BYOK) | Browser `localStorage` only |

## Reporting

Please open a private security advisory on GitHub or email the maintainer instead of
filing a public issue for vulnerabilities. Include reproduction steps and impact.
