# Documentation index

<p align="center"><img src="https://cdn.jsdelivr.net/gh/Li-Guijiang/DreamAI@main/assets/brand/banner-docs.webp" alt="Animated Dream AI documentation banner" width="720"></p>

<sub>[Back to the repository home](../README.md)</sub>

All project documentation lives here. The repository ships three runnable forms — command line, web service, and Windows desktop app — so this page explains what each document answers, in what order to read them, and how the version numbers map to the code.

---

## 1. Document map

| Document | Contents | Audience |
|---|---|---|
| [../README.md](../README.md) | Positioning, capabilities, quick start, repository layout | Anyone visiting the repository |
| [GUIDE.md](./GUIDE.md) | Guided walkthrough: environment setup, every command, common errors | First-time users |
| [SETUP.md](./SETUP.md) | Local installation (Windows first, macOS / Linux notes) | Users running it locally |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Layers, module responsibilities, both data flows | Developers reading or extending the code |
| [ROADMAP.md](./ROADMAP.md) | Phase plan, task lists, acceptance criteria | Anyone tracking progress |
| [adr/](./adr/) | Architecture Decision Records: what was decided, why, what was rejected | Developers who need the trade-offs |
| [CONTRIBUTING.md](./CONTRIBUTING.md) | Branch conventions, commit format, code style, PR checklist | Contributors |
| [SUPPORT.md](./SUPPORT.md) | Self-check order and which channel to use | All users |
| [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md) | Community standards | Everyone involved |
| [SECURITY.md](./SECURITY.md) | Vulnerability reporting and security boundaries | Security researchers, deployers |
| [PRICING.md](./PRICING.md) | Possible future hosted plans (none available today) | Anyone curious about sustainability |
| [../CHANGELOG.md](../CHANGELOG.md) | Versioned change history (Keep a Changelog) | People upgrading or bisecting |
| [../web/README.md](../web/README.md) | Web features, API, deployment, operations | Web deployers and maintainers |
| [../desktop/README.md](../desktop/README.md) | Desktop development, packaging, testing, security model | Desktop developers |
| [../assets/README.md](../assets/README.md) | Brand asset layout and usage | Designers and anyone producing materials |

---

## 2. Entry points for the three deliverables

1. **Command line (Python package)** — `pip install -e .`, then `python -m dream_ai` or `dream-ai`.
   Configuration lives in [.env.example](../.env.example); the walkthrough is [GUIDE.md](./GUIDE.md).
2. **Web service (FastAPI)** — `cd web`, install the requirements, start uvicorn. See
   [web/README.md](../web/README.md). Configuration lives in `web/.env.example`. The deployed
   animated documentation page is <https://liguijiang.com/docs.html>.
3. **Windows desktop (Electron)** — `cd desktop`, `pnpm install`, `pnpm start`. See
   [desktop/README.md](../desktop/README.md) for packaging.

The three share the interface and the `DREAMAI_*` conventions, but **their version numbers are independent**. See the next section.

---

## 3. Version cross-reference

The repository produces three artifacts that version separately. This is intentional, not drift:

| Artifact | Version source | Current version | Notes |
|---|---|---|---|
| CLI package `dream-ai` | `pyproject.toml` → `[project].version` | `0.4.0` | Follows the CLI roadmap; tagged releases publish sdist and wheel |
| Web service | `web/app/config.py` → `VERSION` | `2.0.0` | Ships on its own cadence, exposed through `/api/config`; adds the motion system and `/docs.html` |
| Windows desktop app | `desktop/package.json` → `version` | `1.4.0` | Embedded in the installer name `DreamAI-Setup-<version>.exe`; the site manifest enables in-app updates |

When bumping any of them, check the three companions:

1. `CHANGELOG.md` has a matching entry;
2. the `?v=` cache-busting query strings in `web/web/index.html` are updated;
3. `web/web/downloads/latest.json` matches the installer (version, file name, size, SHA-256).

---

## 4. Documentation rules

1. New documents go in this directory and must be added to the table in section 1 — no orphan files.
2. User-facing procedures use ordered lists; commands go in fenced code blocks.
3. When a document mentions a configuration key, update the matching `.env.example` so both use the same variable name. That includes the terminal motion keys `DREAMAI_ANIMATIONS` and `DREAMAI_ANIMATION_SPEED`.
4. Architecture decisions are recorded in `adr/` as `0001-<topic>.md`, numbered upward. Do not rewrite accepted records; supersede them.
5. Document links stay relative. Images use GitHub user-attachment URLs registered in [`assets/readme/attachments.json`](../assets/readme/attachments.json): repository-relative images depend on `raw.githubusercontent.com`, which is unreachable on some networks. The manifest records the original local source and the optimization applied.
6. Everything is written in English. Readers who prefer another language can use browser translation.
