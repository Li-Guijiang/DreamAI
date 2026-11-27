"""Keep the project's four independent version numbers coherent.

This repository ships four things that each carry a version:

1. the server/API (``web/app/config.py`` → ``VERSION``);
2. the service-worker cache name (``web/web/sw.js`` → ``CACHE``);
3. the desktop installer (``desktop/package.json`` and ``downloads/latest.json``);
4. the latest release listed on ``changelog.html``.

They are intentionally not equal: a server fix does not require a new
installer. But a few relationships must hold, or users get stale pages, a
wrong download, or release notes that do not match the shipped binary.

Read-only. Exits non-zero when a relationship is broken.
"""

from __future__ import annotations

import argparse
import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG = ROOT / "web" / "app" / "config.py"
SW = ROOT / "web" / "web" / "sw.js"
LATEST = ROOT / "web" / "web" / "downloads" / "latest.json"
DESKTOP_PKG = ROOT / "desktop" / "package.json"
CLI_PYPROJECT = ROOT / "pyproject.toml"
CHANGELOG_PAGE = ROOT / "web" / "web" / "changelog.html"
SHELL_LIST = re.compile(r"const\s+SHELL\s*=\s*\[(.*?)\]", re.S)
SHELL_ENTRY = re.compile(r'"([^"]+)"')

SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
APP_VERSION = re.compile(r'^VERSION\s*=\s*"([^"]+)"', re.M)
SW_CACHE = re.compile(r"dreamai-shell-v(\d+\.\d+\.\d+)")


def segments(version: str) -> tuple[int, int, int]:
    """Numeric version parts for ordering; callers validate SEMVER first."""
    try:
        major, minor, patch = version.split(".")
        return int(major), int(minor), int(patch)
    except (ValueError, TypeError):
        return 0, 0, 0


def read_versions(root: Path = ROOT) -> dict[str, str | None]:
    """Collect the versions from each artefact, or None if unreadable."""
    result: dict[str, str | None] = {
        "server": None,
        "serviceWorker": None,
        "installer": None,
        "desktopPackage": None,
        "cli": None,
        "changelog": None,
        "changelogLatest": None,
    }
    config = (root / "web" / "app" / "config.py").read_text(encoding="utf-8")
    match = APP_VERSION.search(config)
    if match:
        result["server"] = match.group(1)

    sw = (root / "web" / "web" / "sw.js").read_text(encoding="utf-8")
    match = SW_CACHE.search(sw)
    if match:
        result["serviceWorker"] = match.group(1)

    latest = json.loads(
        (root / "web" / "web" / "downloads" / "latest.json").read_text(encoding="utf-8")
    )
    result["installer"] = latest.get("version")
    result["changelogLatest"] = latest.get("changelogVersion")

    pkg = json.loads((root / "desktop" / "package.json").read_text(encoding="utf-8"))
    result["desktopPackage"] = pkg.get("version")

    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        with pyproject.open("rb") as handle:
            data = tomllib.load(handle)
        result["cli"] = data.get("project", {}).get("version")

    page = (root / "web" / "web" / "changelog.html").read_text(encoding="utf-8")
    versions = re.findall(r"\bv(\d+\.\d+\.\d+)\b", page)
    result["changelog"] = max(versions, key=segments) if versions else None
    return result


def read_versions_safe(root: Path) -> dict[str, str | None]:
    """Best-effort read used to report which files are missing."""
    try:
        return read_versions(root)
    except (OSError, ValueError, TypeError):
        return {}


def check(root: Path = ROOT) -> dict:
    issues: list[str] = []

    required = (
        root / "web" / "app" / "config.py",
        root / "web" / "web" / "sw.js",
        root / "web" / "web" / "downloads" / "latest.json",
        root / "desktop" / "package.json",
        root / "web" / "web" / "changelog.html",
    )
    missing_files = [str(path.relative_to(root)) for path in required if not path.is_file()]
    if missing_files:
        return {
            "versions": read_versions_safe(root),
            "issues": [f"missing file: {name}" for name in missing_files],
            "ok": False,
        }

    versions = read_versions(root)

    # CLI and the optional changelog pin are informational when absent: not
    # every checkout carries pyproject.toml, and latest.json predates that
    # field. The release-critical artefacts must always be present.
    always = ("server", "serviceWorker", "installer", "desktopPackage", "changelog")
    for name, value in versions.items():
        if name == "changelogLatest":
            continue
        if value is None:
            if name in always:
                issues.append(f"{name}: version missing")
            continue
        if not SEMVER.match(value):
            issues.append(f"{name}: not a semantic version ({value})")

    server = versions["server"]
    worker = versions["serviceWorker"]
    if server and worker and SEMVER.match(server) and SEMVER.match(worker):
        if segments(worker) < segments(server):
            issues.append(f"service worker cache {worker} is older than server {server}")

    installer = versions["installer"]
    package = versions["desktopPackage"]
    if installer and package and installer != package:
        issues.append(f"installer manifest {installer} differs from desktop package {package}")

    # The changelog records whole-product milestones, which are not the same
    # scale as the installer build number. It only has to mention the server
    # release so a deployed version has matching release notes.
    changelog = versions["changelog"]
    if server and changelog and SEMVER.match(server) and SEMVER.match(changelog):
        if segments(changelog) < segments(server):
            issues.append(f"changelog latest v{changelog} is older than server {server}")

    # The download page shows fallback values before download.js replaces them
    # from latest.json. If the JSON fetch fails, those fallbacks are what the
    # visitor sees, so they must agree with the manifest.
    latest_path = root / "web" / "web" / "downloads" / "latest.json"
    page_path = root / "web" / "web" / "download.html"
    if latest_path.is_file() and page_path.is_file():
        try:
            manifest = json.loads(latest_path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            manifest = {}
        page = page_path.read_text(encoding="utf-8")
        version = str(manifest.get("version", ""))
        if version and f"DreamAI-Setup-{version}.exe" not in page:
            issues.append(f"download.html: fallback link does not match installer {version}")
        sha = str(manifest.get("sha256", ""))
        if sha and sha not in page:
            issues.append("download.html: fallback sha256 differs from the manifest")
        date = str(manifest.get("date", ""))
        if date and date not in page:
            issues.append(f"download.html: fallback date differs from the manifest ({date})")
        size = manifest.get("size")
        if isinstance(size, int) and size > 0:
            expected = f"{size / (1024 * 1024):.1f} MB"
            if expected not in page:
                issues.append(f"download.html: fallback size differs from the manifest ({expected})")

    # Every pre-cached file must exist. A missing entry makes the install step
    # reject the whole cache write, so the offline shell never becomes ready.
    sw_path = root / "web" / "web" / "sw.js"
    site = sw_path.parent
    if sw_path.is_file():
        shell = SHELL_LIST.search(sw_path.read_text(encoding="utf-8"))
        if shell:
            for entry in SHELL_ENTRY.findall(shell.group(1)):
                if entry in ("/", ""):
                    continue  # the origin root is served by index.html
                target = site / entry.split("?")[0].lstrip("/")
                if not target.is_file():
                    issues.append(f"service worker pre-cache target missing: {entry}")

    return {"versions": versions, "issues": sorted(issues), "ok": not issues}


def _format(result: dict) -> str:
    lines = ["versions:"]
    for name, value in result["versions"].items():
        if name == "changelogLatest":
            continue
        lines.append(f"  {name}: {value or 'MISSING'}")
    for issue in result["issues"]:
        lines.append(f"  ISSUE: {issue}")
    lines.append("versions: OK" if result["ok"] else "versions: FAILED")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = check(args.root)
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else _format(result))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
