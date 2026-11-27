# 0027 — Crawler files and client identity

- **Status:** Accepted
- **Date:** 2026-11-27

## Context

Three independent defects were found in the public surface:

1. `/sitemap.xml` was generated from a hand-written string in `main.py` that
   listed only the home page. A static `sitemap.xml` with three URLs existed in
   the build and had a test, but the server never served it. `docs.html` was
   missing from both. Crawlers saw a smaller site than visitors.
2. `client_ip()` trusted `X-Real-IP` and `X-Forwarded-For` from any caller.
   A visitor could send a different address on every request and get a fresh
   rate-limit bucket, defeating both the chat limiter and the link-reader
   limiter. The owner cookie had the mirrored problem: a forged
   `X-Forwarded-Proto: http` stripped the `Secure` flag.
3. `/api/read` unpacked the limiter's result into two names, but `hit()` had
   been extended to return three. Every call raised `ValueError` and fell into
   the generic handler, so the endpoint answered 502 for all inputs.

## Decision 1 — One source of truth for crawler files

Both `/robots.txt` and `/sitemap.xml` now read the published files from
`WEB_DIR`. No XML or crawler rules are embedded in Python. `docs.html` was
added to the sitemap; `offline.html` stays out because it is `noindex`.

`check_sitemap.py` verifies that the sitemap lists exactly the indexable
pages, that the routes read the static files, and that the root favicon
matches the one referenced by pages.

## Decision 2 — Trust forwarding headers only from configured proxies

Added `DREAMAI_TRUSTED_PROXIES`, a comma-separated list of IPs or CIDR ranges.
Empty is the safe default: no forwarding header is honoured, and the direct
peer is used for rate limiting. `web/app/peer.py` holds the single definition
of trust, shared by the limiter and the owner cookie to avoid a circular
import.

Rejected: trusting `X-Forwarded-For` unconditionally (the original bug), and
trusting the last chain entry (any proxy can append). The first entry is used,
and only when the peer that opened the connection is allowlisted.

## Decision 3 — Keep the limiter contract explicit

The three-value return of `RateLimiter.hit()` is now unpacked at every call
site. Tests assert the tuple length and cover the validation and rate-limit
paths of `/api/read`, which previously had no dedicated tests.

## Consequences

- Adding a public page requires adding it to the sitemap; CI enforces this.
- Deployments behind a reverse proxy must set `DREAMAI_TRUSTED_PROXIES` to the
  proxy address or range, or every visitor will share one rate-limit bucket.
- A direct-exposure deployment needs no configuration and cannot be bypassed
  with a header.
- The link reader works again; invalid URLs now return 400 rather than 502.
