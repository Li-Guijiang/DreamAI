# 0001 — One repository, three deliverables, three version numbers

<p align="center"><img src="https://github.com/user-attachments/assets/9ec27a73-47d4-489f-b71e-106a84e1b70c" alt="Animated Dream AI documentation banner" width="720"></p>

<sub>[ADR index](./README.md) · [Documentation index](../README.md)</sub>

- **Status:** Accepted
- **Date:** 2026-10-28
- **Deciders:** Dream AI maintainers

<p align="center"><img src="../../assets/brand/divider.gif" alt="" width="640"></p>

## Context

The repository now ships three runnable deliverables from one tree:

| Deliverable | Version source | Cadence |
|---|---|---|
| Command-line package `dream-ai` | `pyproject.toml` → `[project].version` | Follows the CLI roadmap (`v0.1` … `v0.4`) |
| Web service | `web/app/config.py` → `VERSION` | Follows site iterations, exposed through `/api/config` |
| Windows desktop app | `desktop/package.json` → `version` | Follows client releases, embedded in the installer name |

They do not share a release cycle: the CLI advances through documented phases,
while the web service and the desktop client ship independently to
`liguijiang.com`. Keeping a single number would either freeze the site behind
CLI milestones or force the CLI to burn minor versions it has not earned.

The cost of three numbers is reader confusion. A visitor sees `0.4.0` in
`pyproject.toml`, `1.4.0` from `/api/config`, and `DreamAI-Setup-1.2.0.exe` on
the download page, and reasonably concludes that one of them is stale.

<p align="center"><img src="../../assets/brand/divider.gif" alt="" width="640"></p>

## Decision

1. Keep all three deliverables in one repository. They share brand assets,
   documentation conventions, CI, and the `DREAMAI_*` configuration vocabulary;
   splitting them would duplicate that surface.
2. Keep version numbers independent, each declared in one authoritative file.
3. Publish the mapping in `docs/README.md` (section 3) instead of adding a
   fourth "repository version".
4. Treat a change as a release only per deliverable: the `v*` git tag and
   `release.yml` build the **CLI package**; the container workflow tags the
   **web image**; the desktop installer is built and attached through
   `desktop/` packaging and `web/downloads/latest.json`.

<p align="center"><img src="../../assets/brand/divider.gif" alt="" width="640"></p>

## Consequences

- Before touching any version, check three companions: `CHANGELOG.md`, the
  `?v=` cache-busting query strings in `web/web/index.html`, and
  `web/web/downloads/latest.json` (version, file name, size, SHA-256).
- `pip install dream-ai` and `docker pull ghcr.io/li-guijiang/dream-ai` are
  versioned independently of the site; do not assume they match.
- A reader who only knows "Dream AI v1.2" is referring to the desktop client,
  not to the Python package.

<p align="center"><img src="../../assets/brand/divider.gif" alt="" width="640"></p>

## Alternatives considered

1. **Single repository-wide version.** Rejected: it would force the CLI package
   to jump to `1.x` before its roadmap reaches `v1.0` (Stable Assistant), and
   every site tweak would imply a new CLI release.
2. **Separate repositories per deliverable.** Rejected for now: the desktop
   client loads the live site, the docs cross-reference each other, and the
   brand assets are shared. Revisit if the deliverables start needing different
   access control or release permissions.
3. **A generated `version.json` shared by all three.** Rejected: it adds a build
   step to a repository that deliberately has none for the web front end.

<p align="center"><img src="../../assets/brand/footer.gif" alt="" width="720"></p>
