# Web maintenance scripts

<sub>[Back to the repository home](../../README.md) · [Documentation index](../../docs/README.md)</sub>

This directory holds **local maintenance scripts** for the web service. They are not part of the
runtime, and deploying the server does not need them. Paths are resolved relative to the repository;
the environment comes from `web/requirements.txt`, and some scripts additionally need `pillow`,
`numpy`, `paramiko`, or `requests`.

## 1. Scripts kept at the top level

| Script | Purpose | When to use |
|---|---|---|
| `make_assets.py` | Generate the site icons (favicon, PWA icons, social card) from the brand assets | After a brand change, to rebuild `web/web/assets/img/` |
| `make_og.py` | Regenerate only the 1200×630 social card `web/web/assets/img/og.png` | After changing the tagline or the card layout |
| `mock_upstream.py` | Local mock of an OpenAI-compatible streaming endpoint | Developing the UI without an API key |
| `server_exec.py` | Generic SSH helper (`exec` / `put` / `get` / `shell`) | Running a command or moving a file on the server |

Examples:

```bash
# Start the front end against the mock model
.venv/bin/uvicorn mock_upstream:app --app-dir tools --port 8799

# Rebuild the brand icons
python tools/make_assets.py

# Run a script remotely (the password comes from the environment, never from disk)
export DREAMAI_SSH_PASSWORD=...
python tools/server_exec.py exec ./some-script.sh
```

## 2. The `archive/` directory

`archive/` keeps **one-off operations and diagnostic scripts**: the upload script written while
shipping one particular release, the `fix_*` / `check_*` / `test_*` scripts used to chase an nginx
or static-asset problem, and so on.

What they have in common:

1. they hardcode a host, an absolute server path, or a local `D:\...` path, so they only ever ran on
   one machine;
2. they target a specific version (for example `deploy_v12.py`) and stop being useful afterwards;
3. they only print diagnostics — they take no part in build, test, or deployment.

They are kept for traceability: when you need to know what a past release actually did, the script
is the record. **They are not maintained and should not be run against production.**

Rules for new scripts:

1. one-off scripts go straight into `archive/`, named with a `check_` / `fix_` / `push_` / `test_`
   prefix;
2. scripts that will be reused stay in this directory and are added to the table above;
3. never hardcode a local absolute path — derive it with
   `ROOT = Path(__file__).resolve().parent.parent`;
4. never put a secret in the source; read it from the environment.
