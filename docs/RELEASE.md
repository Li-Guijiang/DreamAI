# Release checklist

This document describes what must be true before the site or the desktop
installer is published. All checks are read-only and can run locally; CI runs
the same commands on every push.

## 1. Checks to run

From the repository root:

```bash
python web/tools/check_assets.py        # asset files and ?v= versions
python web/tools/check_site.py          # assets, links, anchors, markup, manifest, service worker
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
