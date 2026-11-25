# Release checklist

This document describes what must be true before the site or the desktop
installer is published. All checks are read-only and can run locally; CI runs
the same commands on every push.

## 1. Checks to run

From the repository root:

```bash
python web/tools/check_assets.py        # asset files and ?v= versions
python web/tools/check_site.py          # assets, links, anchors, markup, manifest, service worker
python web/tools/check_env_docs.py      # environment reference and numeric defaults
python web/tools/check_docs_index.py    # ADR and document indexes
python web/tools/check_meta.py          # head metadata, icons and manifest
python web/tools/check_versions.py      # the four-version relationship map
python web/tools/check_dom_refs.py      # JS id selectors resolve to real nodes
python web/tools/make_downloads.py --check
ruff check dream_ai tests examples web/app web/tools
ruff format --check dream_ai tests examples web/app web/tools
pytest
```

`check_site.py` already includes every asset check, so the first line is
redundant in CI but useful when diagnosing an asset-only failure.

A failing check means the release must not be published. Do not bypass a
check by deleting the assertion; fix the page, manifest or version.

## 2. Three different version numbers

| Location | Meaning | Rule |
|---|---|---|
| `web/app/config.py` → `VERSION` | Server/API version shown on `/api/usage` | Follows the release tag |
| `web/web/sw.js` → `CACHE` | Service-worker cache name | Must be **at least** `VERSION`; a lower value leaves visitors on an old build |
| `web/web/downloads/latest.json` → `version` | Desktop installer version | Independent of the server; the `file` name must contain it |

They are intentionally independent: a server fix does not require a new
installer. What is not allowed is a service-worker cache older than the app,
because browsers keep the old worker until its cache name changes.

## 3. Static assets

Every CSS/JS reference in a top-level HTML page carries `?v=<version>`.
Assets under `/assets/` are served with a long cache lifetime, so changing a
file without changing its pin makes some visitors keep the old copy.

1. When a shared CSS or JS file changes, raise its `?v=` in **every** page that
   references it. `check_assets.py` fails if versions disagree.
2. Images without a version produce a warning, not a failure; favicons and
   inline SVGs are commonly served unpinned.
3. Use `python web/tools/check_assets.py --strict` when a deployment requires
   every local asset to be pinned.
4. A local CSS `url()` pointing at a missing file is a hard failure. SVG
   fragment references such as `url(%23n)` are not files and are ignored.

## 4. Page and manifest integrity

`check_site.py` additionally fails on:

1. a local `.html` link whose target is not part of the build;
2. an `#anchor` whose target `id` was renamed or removed;
3. a duplicate `id` on one page (anchors become ambiguous);
4. `target="_blank"` without `rel="noopener"`;
5. a page missing `lang`, `title` or `meta name="description"`;
6. a download manifest with a non-semantic version, a file name that
   disagrees with that version, a malformed SHA-256, a non-positive size or a
   non-ISO date.

The installer binary itself is uploaded separately and is not expected to be
present in the repository; the manifest's internal consistency is what the
check verifies.

## 5. After publishing

1. Confirm `/api/health` reports the expected `version` and no unexpected
   `configChecks` findings.
2. Open the site with a fresh browser profile; an old service worker can
   otherwise hide a broken deployment.
3. Verify the download link resolves to the version named in `latest.json`
   and that the file's SHA-256 matches the manifest.

## 6. Usage snapshot on the server

If `DREAMAI_USAGE_STATE` is configured, check `/api/usage.usageState`
after the first successful request:

1. A fresh install reports `loadStatus=absent` and a non-null `lastSaveAt`
   after shutdown. A service that has run for a while should also have
   periodic saves (default every 60 seconds).
2. `corrupt`, `oversized`, `unreadable` or `tampered` means the file was not
   trusted. Do not delete it during an incident: copy it aside first, since it
   may still contain counters worth recovering manually.
3. `saveFailures > 0` points at disk space or directory permissions. The chat
   path is unaffected, but recent counters may be lost on restart.
4. A snapshot written by an older build without a checksum remains readable.
   A checksum mismatch is reported as `tampered`, not silently accepted.
5. `rejected` means the JSON envelope was intact but the counters failed
   validation; the previous in-memory counters continue from zero.

## 7. Cache warm-up after a deployment

A fresh process starts with an empty response cache. If the deployment sends a
burst of identical questions, they all enter the cache at once and expire at
once unless `DREAMAI_CACHE_TTL_JITTER` is set. For sites with scheduled traffic
spikes, set it to roughly 0.1 and confirm `cache.ttlJitter` in `/api/health`.

A sampling-setting change (`DREAMAI_TOP_P`, `DREAMAI_PRESENCE_PENALTY`) after
deployment produces new cache keys by design. The first answer under the new
settings is a miss; that is preferable to replaying an answer generated with
different parameters.
