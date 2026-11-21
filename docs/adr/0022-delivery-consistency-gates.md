# 0022 — Delivery consistency gates

- **Status:** Accepted
- **Date:** 2026-11-21

## Context

A scan of the published site found `download.css` pinned at `?v=1.0.0` on two
pages and `?v=2.0.3` on a third. Because `/assets/` is served with a long
cache lifetime, the first two pages silently rendered with an older
stylesheet. Nothing in CI could detect it: the site built, the tests passed,
and only a visual comparison revealed the drift.

The same class of problem had no guard elsewhere:

- a page link to a missing `.html` file 404s only after deployment;
- renaming an `id` silently breaks every `#anchor` pointing at it;
- a CSS `url()` to a moved image fails only on the page that uses it;
- a service worker whose cache name is older than the app keeps visitors on
  the previous build even after a successful deployment;
- a download manifest whose `file` name disagrees with its `version` sends
  users to a filename that does not exist.

## Decision

Two read-only tools, both wired into CI:

1. `web/tools/check_assets.py` scans every local CSS/JS reference in the
   top-level HTML pages. It fails on a missing file or on two pages pinning
   different versions of the same path. Unversioned local assets are a warning
   by default; `--strict` promotes them to a failure for deployments that pin
   everything. SVG fragment references (`url(%23n)`) and remote/data URLs are
   not files and are ignored.
2. `web/tools/check_site.py` reuses the asset check and adds page links,
   anchors, duplicate ids, `target="_blank"` without `rel="noopener"`, basic
   page metadata, CSS-local URLs, service-worker cache age and download
   manifest consistency (semantic version, file name, SHA-256, positive size,
   ISO date).

Both print a human-readable summary and, with `--json`, a machine-readable
result. Exit codes are 0 (ok), 1 (checks failed) and 2 (bad arguments).

The real drift found by the first run was fixed: all three pages now pin
`download.css?v=2.0.3`. `offline.html` also gained a missing description.

## Version rules

`VERSION` in `web/app/config.py`, the `CACHE` constant in `sw.js` and
`version` in `downloads/latest.json` describe different artefacts. They are
not required to be equal. The one invariant is that the service-worker cache
must not be older than the server version, otherwise browsers keep serving a
previous build.

## Consequences

- A consistent site is now a CI gate rather than a matter of review attention.
- Adding a page, renaming an anchor or bumping a shared stylesheet requires
  the related references to be updated in the same change.
- The checks are intentionally conservative: metadata and links are checked
  only in top-level HTML, and the installer binary is not expected in the
  repository. Widening the scope should be a separate decision.
- `docs/RELEASE.md` records how to run the checks and how to interpret each
  version number.
