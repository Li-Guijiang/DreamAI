# 0026 — DOM selector integrity

- **Status:** Accepted
- **Date:** 2026-11-25

## Context

A scan of the site's own scripts found 11 literal id selectors with no
matching node in any page. `download-motion.js` queried `#downloadTyped` to
drive a typewriter effect, but the download page's heading was static text
with no such id. The guard clause returned and the feature silently did
nothing, while the static heading still made the page look correct.

The desktop updater queried ten `#update*` nodes that no page declared. Those
nodes are injected by the native webview at runtime, so this is legitimate —
but it is indistinguishable, by static inspection, from the typewriter bug.

## Decision

`web/tools/check_dom_refs.py` extracts literal id selectors from the site's
scripts (`getElementById` and `querySelector('#id')`) and checks that each id
is declared by some HTML page or created at runtime by a script.

Nodes injected by the native desktop shell are allowed through an explicit
allowlist. Every entry carries a reason string, which the tool prints, so an
exemption cannot accumulate without review. Callers can supply additional
allowlist entries for test fixtures.

Rejected: parsing `querySelectorAll` with compound selectors, class selectors
or template-built ids. Literal id selectors cover the real failure mode with
no false positives from dynamic strings.

## Consequences

- Adding a script that queries a new id requires adding that id to the markup
  or documenting a runtime injection.
- The download page heading now carries `id="downloadTyped"`, so the
  typewriter script can find it. The static text remains as a no-JS fallback.
- Desktop-injected ids remain visible in the tool output, making the boundary
  between the web page and the native shell explicit.
- The check runs in CI alongside the other static guards.
