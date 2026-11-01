#!/usr/bin/env python3
"""Generate the release manifests from the desktop build.

Two files describe a release and they must agree:

* ``web/web/downloads/latest.json`` - what the app and the download page read;
* ``web/web/downloads/latest.yml``  - electron-builder's format, kept for tooling.

Both used to be edited by hand, which is how the repository advertised 1.2.0
while ``desktop/package.json`` said 1.4.0 and the deployed site answered 1.3.0.

Usage (repository root):

    python web/tools/make_downloads.py                   # rebuild from the installer
    python web/tools/make_downloads.py --allow-pending    # announce a version with no build yet
    python web/tools/make_downloads.py --check            # fail when the files disagree
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "desktop" / "package.json"
DOWNLOADS = ROOT / "web" / "web" / "downloads"
JSON_PATH = DOWNLOADS / "latest.json"
YML_PATH = DOWNLOADS / "latest.yml"


def digest(path: Path, algorithm: str = "sha256") -> bytes:
    hasher = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.digest()


def build_manifest(version: str, installer: Path | None, notes: str, previous: dict | None = None) -> dict:
    """Describe a release, reusing verified hashes when the build is not here.

    The repository does not carry the 120 MB installer, so a manifest that is
    regenerated on a machine without it must not silently lose the hash that was
    recorded when the release was built.
    """
    file_name = f"DreamAI-Setup-{version}.exe"
    manifest = {
        "version": version,
        "file": file_name,
        "size": 0,
        "sha256": "",
        "date": date.today().isoformat(),
        "notes": notes,
    }

    if installer and installer.is_file():
        manifest["size"] = installer.stat().st_size
        manifest["sha256"] = digest(installer, "sha256").hex()
        manifest["sha512"] = base64.b64encode(digest(installer, "sha512")).decode()
        return manifest

    if previous and previous.get("version") == version and len(previous.get("sha256", "")) == 64:
        # Same version, no build in this checkout: keep what the release recorded.
        manifest["size"] = int(previous.get("size", 0))
        manifest["sha256"] = previous["sha256"]
        manifest["date"] = previous.get("date", manifest["date"])
        if previous.get("sha512"):
            manifest["sha512"] = previous["sha512"]
        return manifest

    manifest["pending"] = True
    return manifest


def to_yml(manifest: dict) -> str:
    release_date = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
    lines = [f"version: {manifest['version']}", "files:", f"  - url: {manifest['file']}"]
    if manifest.get("sha512"):
        lines.append(f"    sha512: {manifest['sha512']}")
    if manifest.get("size"):
        lines.append(f"    size: {manifest['size']}")
    lines.append(f"path: {manifest['file']}")
    if manifest.get("sha512"):
        lines.append(f"sha512: {manifest['sha512']}")
    lines.append(f"releaseDate: '{release_date}'")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allow-pending", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--notes", default="")
    args = parser.parse_args()

    version = json.loads(PACKAGE.read_text(encoding="utf-8"))["version"]
    installer = DOWNLOADS / f"DreamAI-Setup-{version}.exe"
    previous = json.loads(JSON_PATH.read_text(encoding="utf-8")) if JSON_PATH.is_file() else None

    if args.check:
        if not previous:
            print("latest.json is missing", file=sys.stderr)
            return 1
        if previous.get("version") != version:
            print(f"latest.json says {previous.get('version')}, package.json says {version}", file=sys.stderr)
            return 1
        if previous.get("file") != f"DreamAI-Setup-{version}.exe":
            print("latest.json points at the wrong installer name", file=sys.stderr)
            return 1
        print(f"latest.json is current ({version})")
        return 0

    manifest = build_manifest(version, installer, args.notes or (previous or {}).get("notes", ""), previous)

    if manifest.get("pending") and not args.allow_pending:
        print(
            f"installer missing: {installer}\n"
            "build it first (pnpm dist) or pass --allow-pending to announce the version only",
            file=sys.stderr,
        )
        return 1

    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # latest.yml is electron-builder's format and needs sha512. Without a build
    # in this checkout there is nothing to hash, so the previous file is left
    # alone rather than rewritten without the field that makes it valid.
    if manifest.get("sha512"):
        YML_PATH.write_text(to_yml(manifest), encoding="utf-8")

    state = "pending" if manifest.get("pending") else f"{manifest['size']} bytes, sha256 {manifest['sha256'][:12]}…"
    print(f"wrote {JSON_PATH.relative_to(ROOT)}: v{version}, {state}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
