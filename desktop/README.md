# Dream AI Desktop

<p align="center"><img src="https://cdn.jsdelivr.net/gh/Li-Guijiang/DreamAI@main/assets/brand/banner-desktop.webp" alt="Animated Dream AI desktop banner" width="720"></p>

<sub>[Back to the repository home](../README.md) · [Documentation index](../docs/README.md)</sub>

The Windows desktop edition of Dream AI: an Electron shell that loads the same interface as the
website and adds a **local file workbench** (organise, batch rename, export documents) through a
narrow IPC bridge.

## Development

```bash
cd desktop
pnpm install          # see the mirror settings below if needed
pnpm start            # loads https://liguijiang.com by default

# Local development against the dreamai-web uvicorn server;
# equivalent to: electron . --url=http://127.0.0.1:8787
pnpm start:local
```

Mirrors:

```bash
ELECTRON_MIRROR=https://npmmirror.com/mirrors/electron/
ELECTRON_BUILDER_BINARIES_MIRROR=https://npmmirror.com/mirrors/electron-builder-binaries/
```

## Packaging

```bash
pnpm dist
# output: release/DreamAI-Setup-1.2.0.exe
```

Packaging always reads `build/icon.ico` (16–256 px sizes), exported from the brand asset
`assets/logo/DreamAI-Logo/01_软件图标_圆角底板/DreamAI-icon-1024.png`. The output and resource
directories are set by `build.directories` in `package.json`. Keep the file name stable when
replacing the icon so the packaging config does not need to change.

## Testing

```bash
pnpm test            # runs both scripts below; requires pnpm install first
pnpm test:tools      # pure Node: organise / rename / path constraints
pnpm test:docs       # document generation (docx / xlsx / pptx); needs docx, exceljs, pptxgenjs
```

Electron end-to-end (start the local web service first):

```bash
# start with a debugging port
electron --remote-debugging-port=9222 . --url=http://127.0.0.1:8787
# in another terminal
DREAMAI_DEV_WORKSPACE=<test-folder> node test/e2e.js
```

Development-only flags and variables:

| Flag / variable | Purpose |
| --- | --- |
| `--url=<address>` | Override the loaded site; takes precedence over `DREAMAI_URL` |
| `DREAMAI_URL` | Override the loaded site |
| `DREAMAI_DEV_WORKSPACE` | Preselect the working folder and skip the system dialog |
| `DREAMAI_DEV_AUTO_CONFIRM=1` | Auto-approve write confirmations; automated tests only |

## Security model

- `contextIsolation: true`, `nodeIntegration: false`, `sandbox: true`.
- The preload script exposes a fixed set of IPC methods only — never `fs` or `child_process`.
- Only folders the user picks through a system dialog can be touched, and every path is checked for
  containment.
- Symbolic links and hidden files are ignored.
- Every move, rename, and write is previewed first, then confirmed through a native dialog owned by
  the main process.
- Navigation away from the official domain is blocked; external links open in the system browser.

## Local capabilities (MVP)

| Capability | Description |
| --- | --- |
| Organise by type | Images / documents / video / audio / archives / installers / code / other |
| Batch rename | Shared prefix plus a sequence number, extensions preserved, before/after preview |
| Save conversation | Export the current session as Markdown into the working folder |
| Folder overview | File count, folder count, total size, type distribution |

The same pattern extends naturally to Word/Excel/PPT generation, image compression, duplicate
detection, and scheduled tidying.
