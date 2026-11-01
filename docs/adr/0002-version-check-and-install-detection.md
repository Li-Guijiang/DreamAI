# 0002 — Version checks, in-app updates, and install detection

- **Status:** Accepted
- **Date:** 2026-11-01

## Context

Before this record the desktop client checked for a new version exactly once,
twenty seconds after launch, parsed `latest.yml` with three regexes, and offered a
single button that opened the website. Four consequences followed:

1. anyone who kept the app open never heard about a release;
2. the prompt could not install anything, so every update meant a 120 MB browser
   download and a manual run;
3. `latest.json` had been edited by hand and disagreed with `package.json`, so the
   page, the badge and the app could advertise three different versions;
4. the download page could not tell a first-time visitor from someone who already
   had the app installed.

## Decision 1 — One manifest, generated from the build

`web/web/downloads/latest.json` is the single source of truth. It carries
`version`, `file`, `size`, `sha256`, `date`, `notes`, and optionally
`pending: true` when a version is announced before its installer exists.

`web/tools/make_downloads.py` writes it from `desktop/package.json` plus the
installer on disk, so the version can no longer be typed by hand. Three rules:

| Situation | Behaviour |
|---|---|
| Installer present | size, sha256 and sha512 computed from the file |
| Same version, no installer in this checkout | reuse the hashes the release recorded |
| New version, no installer | `pending: true`, and only with `--allow-pending` |

`--check` compares the committed manifest with the package and exits non-zero on
a mismatch; CI runs it.

## Decision 2 — Check in the main process, on a schedule

| Rule | Value | Why |
|---|---|---|
| First check | 15 s after `ready` | not competing with window creation |
| Repeat | 6 h | freshness without traffic |
| Jitter | ±10 % | no stampede after a release |
| Retry | 5, 15, 60 min, then 6 h | transient failures resolve alone |
| Offline | skipped, retried on `online` | `net.isOnline()` costs nothing |
| Conditional GET | `If-None-Match` | a repeat check is a 304 |
| Timeout / cap | 10 s / 64 KB | a hung or huge response cannot hang the check |

The policy lives in `update-schedule.js` as pure functions, the transport in
`update-feed.js`, and the state machine in `update-service.js`
(`idle → checking → available | up-to-date | error`). Checks are serialised, and a
manifest older than the running version reports up-to-date, so a mistaken rollback
cannot downgrade a client.

## Decision 3 — Prompt, then one click, without blocking the UI

The service pushes every state change to the renderer, and the main process shows
a native dialog once per version: **稍后** or **立即更新**.

Installing runs `installer.js`: stream to `<temp>/DreamAI-Setup-<version>.exe.part`
while hashing, verify size and SHA-256, rename into place, then spawn the NSIS
installer detached with `/S` and quit 1.2 s later. Progress is throttled to four
events per second. No synchronous filesystem call, no `execSync`, and no work on
the renderer thread — the window keeps painting while 120 MB move through.

A failure deletes the partial file and reports the message; the user keeps a
working app and the next check retries.

## Decision 4 — Install detection through a custom protocol

A browser cannot read the registry, so the only honest signal is "the app
answered". The client registers `dreamai://` and handles two links:

```
dreamai://probe?return=https://liguijiang.com/download.html
  → the app opens the return URL with ?dreamai=1&version=<installed>&latest=<newest>
dreamai://update
  → the app focuses its window and forces a check
```

The download page probes only after a user gesture (browsers block protocol
launches otherwise) and gives up after 2.5 s:

| Result | Page shows |
|---|---|
| installed ≥ latest | 本机已安装，无需继续安装 · open the app, or download anyway |
| installed < latest | 已安装 vX，可更新到 vY · both paths |
| no answer | the normal download, plus a button to probe again |

The answer is cached for ten minutes keyed by the published version and stripped
from the URL afterwards, so a reload cannot replay it.

## Edge cases

| Case | Handling |
|---|---|
| Portable build / protocol not registered | probe times out, normal download |
| User dismisses the browser's protocol prompt | same timeout path, no error |
| Prerelease published by mistake | rejected: manifests must be releases |
| `beta.10` vs `beta.2` | numeric identifier ordering, not string comparison |
| Clock skew | staleness uses the response, not the local clock |
| Truncated download | size and hash checked before spawn; `.part` deleted |
| Disk full | size is checked against the manifest before writing |
| Antivirus blocks the installer | spawn error surfaces with the temp path kept |
| Two instances | single-instance lock, second launch only forwards the deep link |
| macOS / Linux | check still reports; install is refused with a link to the site |

## Consequences

- Releasing is `pnpm dist` + `make_downloads.py` + upload; the manifest cannot
  drift from the package without CI failing.
- Auto-install stays Windows-only; the check, prompt and detection are
  platform-neutral and already work elsewhere.
- The probe is a hint, not proof: a user can fake the redirect. It only changes
  which buttons appear, never what is downloaded or installed.
