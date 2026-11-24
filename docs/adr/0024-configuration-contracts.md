# 0024 — Configuration contracts

- **Status:** Accepted
- **Date:** 2026-11-24

## Context

The repository has three components that all use `DREAMAI_*` environment
variables: the Web server, the command-line client and the desktop shell. Only
the client variables had a systematic reference (`docs/SETUP.md`). The server
read 44 variables whose defaults and allowed ranges existed only in
`web/app/config.py`.

Two consequences followed. Operators read source code to learn what a setting
did, and a newly added setting could ship undocumented because nothing checked
the gap. Separately, out-of-range numbers were silently clamped to a boundary.
That prevented a crash but left the operator believing their value was in
effect.

A review of `/api/config` also showed no test guarding its shape. A future
refactor could accidentally include a model's base URL or an operator's
snapshot path in the browser-facing payload without any test noticing.

## Decision 1 — One reference for server variables

`docs/CONFIGURATION.md` documents every variable read by
`web/app/config.py`, grouped by purpose: core output, free upstream, BYOK,
fallback, limits, cache, stream timing, and site/persistence. A final section
explicitly names client, desktop and owner variables as out of scope, with
links to their own documentation.

`web/tools/check_env_docs.py` compares the variable names in code with the
document. A variable missing from the reference fails CI. Names that do not
exist in `config.py` are allowed only in the out-of-scope section, so they
cannot be mistaken for server settings.

## Decision 2 — Indexes are checked too

`web/tools/check_docs_index.py` verifies that each numbered ADR appears in
`docs/adr/README.md` and each top-level document in `docs/README.md`. Both
tools run in CI before pytest.

## Decision 3 — Report clamping without leaking values

`load_settings()` records the field names whose supplied values were replaced
by a boundary. `Settings.clamped_fields` is published as
`/api/health.configClamped` using camelCase names. Values are never published.

Rejected: warning on every clamped value at startup. Warnings are easy to
ignore in logs, and a value written in a deployment manifest is harder to
audit than a field name on a status endpoint. Rejected: exposing the list on
`/api/config`; browser clients have no reason to know how the operator
configured the server.

## Decision 4 — A browser-facing allowlist test

`tests/test_public_config_contract.py` asserts that the public payload has a
stable top-level shape, that model entries carry only display fields, and
that injected markers for keys, private URLs, prompts and snapshot paths never
appear in `/api/config` or `/api/health`.

## Consequences

- Adding an environment variable requires a documentation change in the same
  commit; CI will reject a code-only change.
- Adding an ADR or top-level document likewise requires an index row.
- A misconfigured deployment can be diagnosed from `configClamped` without
  revealing secrets.
- The public configuration shape is now a contract. Adding a field is a
  deliberate change to both the test and the API documentation.
