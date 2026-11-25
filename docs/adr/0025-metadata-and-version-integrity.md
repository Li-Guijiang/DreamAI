# 0025 — Metadata and version integrity

- **Status:** Accepted
- **Date:** 2026-11-25

## Context

Two classes of defect were invisible to tests because they only appear
outside the browser window.

1. Social previews. Three public pages declared no Open Graph tags and no
   apple-touch-icon. They rendered correctly, so nobody noticed that sharing
   them produced a blank card and adding them to a home screen produced a
   generic icon.
2. Version drift. The project ships a server version, a service-worker cache
   name, an installer version and a CLI version. They are intentionally
   different. A scan found `sw.js` pre-caching `app.css?v=2.0.8` and
   `app.js?v=2.1.0` while the pages served `2.1.0` and `2.2.2`. Online users
   could not see it: the worker answered from its cache, so the old assets
   were exactly what loaded.

Neither problem has a runtime symptom in normal use. Both need a static
cross-file comparison.

## Decision 1 — Check head metadata as a contract

`web/tools/check_meta.py` requires every public page to declare `lang`,
`title`, `description`, `viewport`, `theme-color`, the Open Graph set, an
`icon` and an `apple-touch-icon`. It asserts `og:title` matches `<title>`,
`og:url` uses the public origin, and `og:image` points at the shared preview
image. Attribute order is tolerated.

Pages marked `robots=noindex` are exempt from social tags and must not declare
them: an offline fallback should not be indexable or shareable. They still
need the basic head fields.

## Decision 2 — Check the version map, not equality

`web/tools/check_versions.py` collects the four versions and checks only the
relationships that must hold:

1. the service-worker cache name is not older than the server;
2. the installer manifest version equals the desktop package version;
3. the changelog's newest milestone is not older than the server;
4. every value is a three-part semantic version, compared numerically.

Equality across artefacts is explicitly **not** required. An earlier draft
required the changelog's newest version to equal the installer version and
failed immediately: `v1.5.0` is a whole-product milestone while `1.3.0` is an
installer build number. The rule was corrected rather than the data.

## Decision 3 — Check worker pre-cache pins

`check_site.py` gained a `serviceWorkerPins` check: every versioned asset in
the worker's `SHELL` list must also be served by at least one page at that
same version. A stale pin is a hard failure because the offline cache would
otherwise install an old file.

Rejected: requiring every pre-cached asset to appear in a page. Vendor files
and some images are cached deliberately without a page reference.

## Consequences

- Adding a public page requires the full metadata set or CI fails.
- Changing a pre-cached asset's `?v=` requires the same change in `sw.js` and
  a bump of `CACHE`, otherwise the installed worker keeps the old list.
- Publishing a server version requires a changelog entry at least as new.
- `docs/VERSIONS.md` is the human-readable companion to the tool.
