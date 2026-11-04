#!/usr/bin/env python3
"""Deploy the web app to the production server in one step.

It packages `web/`, uploads it over SFTP, runs the same `deploy/install.sh` the
project documents, restarts the service and verifies the result. The only input
it needs is the SSH password, which is read from the environment and never
written to disk:

    set DREAMAI_SSH_PASSWORD=...
    python web/tools/deploy_site.py            # full deploy
    python web/tools/deploy_site.py --dry-run  # build the bundle, touch nothing

A key works too, and is the better option once one is installed on the server:

    set DREAMAI_SSH_KEY=%USERPROFILE%/.ssh/dreamai_deploy
    python web/tools/deploy_site.py

Exit codes: 0 deployed and healthy, 1 failed (the remote output is printed).
"""

from __future__ import annotations

import argparse
import io
import os
import sys
import tarfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "web"
APP_DIR = "/www/wwwroot/liguijiang.com"
RELEASE_DIR = "/tmp/dreamai-release"
SITE = "https://liguijiang.com"

EXCLUDE = {".venv", "__pycache__", ".env", "node_modules", ".pytest_cache", "release"}


def build_bundle() -> bytes:
    """Tar `web/` without secrets, virtualenvs, or caches."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for path in sorted(WEB.rglob("*")):
            if any(part in EXCLUDE for part in path.parts):
                continue
            if path.is_file():
                tar.add(path, arcname=str(path.relative_to(WEB)))
    return buffer.getvalue()


def upload_and_install(
    payload: bytes,
    host: str,
    user: str,
    password: str = "",
    key_path: str = "",
    port: int = 22,
) -> None:
    import paramiko

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        host,
        port=port,
        username=user,
        password=password or None,
        key_filename=key_path or None,
        timeout=25,
        banner_timeout=25,
        auth_timeout=25,
        look_for_keys=False,
        allow_agent=False,
    )
    try:
        sftp = client.open_sftp()
        remote_tar = "/tmp/dreamai-web.tar.gz"
        with sftp.open(remote_tar, "wb") as handle:
            handle.write(payload)
        sftp.close()

        def run(command: str, timeout: int = 600) -> str:
            stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
            out = stdout.read().decode("utf-8", "replace")
            err = stderr.read().decode("utf-8", "replace")
            status = stdout.channel.recv_exit_status()
            if status != 0:
                raise RuntimeError(f"{command}\n{out}\n{err}")
            return out

        run(
            f"rm -rf {RELEASE_DIR} && mkdir -p {RELEASE_DIR} && tar xzf {remote_tar} -C {RELEASE_DIR}"
        )
        print("uploaded and unpacked")
        # install.sh backs up the current site, rebuilds the venv, writes systemd
        # and nginx config, then calls /api/health.
        print(run(f"bash {RELEASE_DIR}/deploy/install.sh", timeout=900))
    finally:
        client.close()


def verify(attempts: int = 12) -> bool:
    """Poll the live site until the new build answers, then sanity-check it."""
    for _ in range(attempts):
        try:
            with urllib.request.urlopen(f"{SITE}/api/health", timeout=8) as response:
                if response.status == 200:
                    break
        except Exception:
            time.sleep(5)
    else:
        return False

    try:
        with urllib.request.urlopen(f"{SITE}/download.html", timeout=8) as response:
            html = response.read().decode("utf-8", "replace")
    except Exception:
        return False

    checks = {
        "motion.css": "assets/css/motion.css" in html,
        "pages.css": "assets/css/pages.css" in html,
        "download.js": "assets/js/download.js" in html,
    }
    for name, ok in checks.items():
        print(f"  {name}: {'ok' if ok else 'MISSING'}")
    return all(checks.values())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--host", default=os.environ.get("DREAMAI_SSH_HOST", "8.156.85.180"))
    parser.add_argument("--user", default=os.environ.get("DREAMAI_SSH_USER", "root"))
    args = parser.parse_args()

    payload = build_bundle()
    print(f"bundle: {len(payload) / 1024 / 1024:.1f} MB")
    if args.dry_run:
        print("dry run: nothing uploaded")
        return 0

    password = os.environ.get("DREAMAI_SSH_PASSWORD", "")
    key_path = os.environ.get("DREAMAI_SSH_KEY", "")
    if not password and not key_path:
        print("set DREAMAI_SSH_PASSWORD or DREAMAI_SSH_KEY first", file=sys.stderr)
        return 1

    try:
        upload_and_install(payload, args.host, args.user, password=password, key_path=key_path)
    except Exception as error:
        print(f"deploy failed: {error}", file=sys.stderr)
        return 1

    print("waiting for the service ...")
    if not verify():
        print("deployed, but verification did not see the new build", file=sys.stderr)
        return 1
    print("deployed and verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
