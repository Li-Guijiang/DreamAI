"""Guard local page links, anchors and the download manifest.

``check_assets`` covers versioned static files. This tool covers the other
things a browser can follow to a 404: a link to a page that is not in the
build, an ``#anchor`` whose target id was renamed, and a download manifest
whose file name disagrees with its own version.

All checks are read-only and fail CI when the published site would be broken.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

from check_assets import DEFAULT_ROOT
from check_assets import check as check_assets

LOCAL_PAGE = re.compile(r'(?:href|src)="(/[^"#?]+\.html)(?:[?#][^"]*)?"')
ANCHOR = re.compile(r'href="#([A-Za-z][A-Za-z0-9_-]*)"')
ID_ATTR = re.compile(r'\bid="([^"]+)"')
CSS_URL = re.compile(r'url\(\s*["\']?([^\)"\']+)["\']?\s*\)')
LANG = re.compile(r"<html[^>]*\blang=\"([^\"]+)\"", re.I)
TITLE = re.compile(r"<title>\s*\S", re.I)
DESCRIPTION = re.compile(r'<meta\s+name="description"\s+content="\s*\S', re.I)
BLANK_LINK = re.compile(r"<a\b[^>]*target=\"_blank\"[^>]*>", re.I)
NOOPENER = re.compile(r"\brel=\"[^\"]*\bnoopener\b", re.I)
SW_CACHE = re.compile(r'const\s+CACHE\s*=\s*["\']dreamai-shell-v(\d+\.\d+\.\d+)["\']')
APP_VERSION = re.compile(r'^VERSION\s*=\s*"([^"]+)"', re.M)
SEMVER = re.compile(r"\d+\.\d+\.\d+")
SHA256 = re.compile(r"[0-9a-f]{64}")


def scan_page_links(root: Path) -> list[tuple[str, str]]:
    """(page, absolute local html path) for every navigation link."""
    links: list[tuple[str, str]] = []
    for page in sorted(root.glob("*.html")):
        for target in LOCAL_PAGE.findall(page.read_text(encoding="utf-8")):
            links.append((page.name, target))
    return links


def broken_page_links(root: Path, links: list[tuple[str, str]]) -> list[str]:
    """Links to pages that are not part of the build."""
    return sorted(
        f"{page}: {target}" for page, target in links if not (root / target.lstrip("/")).is_file()
    )


def broken_anchors(root: Path) -> list[str]:
    """In-page links whose target id no longer exists."""
    issues: list[str] = []
    for page in sorted(root.glob("*.html")):
        text = page.read_text(encoding="utf-8")
        ids = set(ID_ATTR.findall(text))
        for anchor in ANCHOR.findall(text):
            if anchor not in ids:
                issues.append(f"{page}: #{anchor}")
    return sorted(issues)


def css_issues(root: Path) -> list[str]:
    """Local files referenced from CSS that are not in the build.

    Data URLs, remote URLs and SVG fragment references ("%23" is an encoded
    '#') are not files and must not be reported as missing.
    """
    issues: list[str] = []
    css_dir = root / "assets" / "css"
    if not css_dir.is_dir():
        return issues
    for css in sorted(css_dir.glob("*.css")):
        for url in CSS_URL.findall(css.read_text(encoding="utf-8", errors="replace")):
            if url.startswith(("data:", "http://", "https://", "//", "#")) or "%23" in url:
                continue
            path = url.split("#", 1)[0].split("?", 1)[0]
            if not path:
                continue
            target = (css.parent / path).resolve()
            if not target.is_file() or not target.is_relative_to(root.resolve()):
                issues.append(f"{css.relative_to(root)}: {url}")
    return sorted(issues)


def metadata_issues(root: Path) -> list[str]:
    """Pages missing the metadata a published page should always carry."""
    issues: list[str] = []
    for page in sorted(root.glob("*.html")):
        text = page.read_text(encoding="utf-8")
        if not LANG.search(text):
            issues.append(f"{page.name}: missing html lang")
        if not TITLE.search(text):
            issues.append(f"{page.name}: missing title")
        if not DESCRIPTION.search(text):
            issues.append(f"{page.name}: missing description")
    return issues


def markup_issues(root: Path) -> list[str]:
    """Duplicate ids and new-window links without ``rel=noopener``."""
    issues: list[str] = []
    for page in sorted(root.glob("*.html")):
        text = page.read_text(encoding="utf-8")
        for name, count in Counter(ID_ATTR.findall(text)).items():
            if count > 1:
                issues.append(f"{page.name}: duplicate id #{name} ({count}x)")
        for tag in BLANK_LINK.findall(text):
            if not NOOPENER.search(tag):
                issues.append(f"{page.name}: target=_blank without rel=noopener")
    return sorted(issues)


def sw_issues(root: Path) -> list[str]:
    """The offline shell must not be older than the server build.

    Browsers keep the old service worker until its cache name changes. If the
    app version moves forward without it, visitors keep receiving yesterday's
    HTML after a deployment.
    """
    sw = root / "sw.js"
    if not sw.is_file():
        return ["sw.js: missing"]
    match = SW_CACHE.search(sw.read_text(encoding="utf-8"))
    if not match:
        return ["sw.js: CACHE constant is missing or not semantic"]
    config = root.parent / "app" / "config.py"
    if not config.is_file():
        config = root / "app" / "config.py"
    if not config.is_file():
        return []
    app_match = APP_VERSION.search(config.read_text(encoding="utf-8"))
    if not app_match:
        return ["config.py: VERSION is missing or not semantic"]

    def parts(value: str) -> tuple[int, int, int]:
        return tuple(int(piece) for piece in value.split("."))  # type: ignore[return-value]

    if parts(match.group(1)) < parts(app_match.group(1)):
        return [f"sw.js: cache v{match.group(1)} is older than app v{app_match.group(1)}"]
    return []


def manifest_issues(root: Path) -> list[str]:
    """A download manifest that cannot describe a real, complete artefact.

    The installer itself is uploaded separately and is not expected in the
    repository; only the manifest's internal consistency is checked here.
    """
    path = root / "downloads" / "latest.json"
    if not path.is_file():
        return ["downloads/latest.json: missing"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        return [f"downloads/latest.json: unreadable ({type(exc).__name__})"]
    if not isinstance(data, dict):
        return ["downloads/latest.json: not an object"]

    issues: list[str] = []
    version = str(data.get("version", ""))
    if not SEMVER.fullmatch(version):
        issues.append("version: expected three numeric components")
    name = str(data.get("file", ""))
    if version not in name:
        issues.append("file: name does not contain the manifest version")
    if not SHA256.fullmatch(str(data.get("sha256", ""))):
        issues.append("sha256: expected 64 lowercase hex characters")
    size = data.get("size")
    if not isinstance(size, int) or isinstance(size, bool) or size <= 0:
        issues.append("size: expected a positive integer")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(data.get("date", ""))):
        issues.append("date: expected YYYY-MM-DD")
    return issues


def check_site(root: Path) -> dict:
    """Machine-readable result for the whole published site."""
    assets = check_assets(root)
    links = scan_page_links(root)
    issues = {
        "missing": assets["issues"]["missing"],
        "conflicts": assets["issues"]["conflicts"],
        "unversioned": assets["issues"]["unversioned"],
        "brokenPages": broken_page_links(root, links),
        "brokenAnchors": broken_anchors(root),
        "css": css_issues(root),
        "metadata": metadata_issues(root),
        "markup": markup_issues(root),
        "serviceWorker": sw_issues(root),
        "manifest": manifest_issues(root),
    }
    hard = (
        "missing",
        "conflicts",
        "brokenPages",
        "brokenAnchors",
        "css",
        "metadata",
        "markup",
        "serviceWorker",
        "manifest",
    )
    return {
        "pages": assets["pages"],
        "assetReferences": assets["references"],
        "pageLinks": len(links),
        "issues": issues,
        "ok": not any(issues[key] for key in hard),
    }


def _format(result: dict) -> str:
    lines = [
        f"site: {result['pages']} pages, "
        f"{result['assetReferences']} assets, {result['pageLinks']} page links"
    ]
    for key, label in (
        ("missing", "MISSING ASSET"),
        ("conflicts", "VERSION CONFLICT"),
        ("brokenPages", "BROKEN PAGE LINK"),
        ("brokenAnchors", "BROKEN ANCHOR"),
        ("css", "MISSING CSS ASSET"),
        ("metadata", "MISSING METADATA"),
        ("markup", "BAD MARKUP"),
        ("serviceWorker", "STALE SERVICE WORKER"),
        ("manifest", "BAD MANIFEST"),
        ("unversioned", "unversioned (warning)"),
    ):
        for item in result["issues"][key]:
            lines.append(f"  {label}: {item}")
    lines.append("site: OK" if result["ok"] else "site: FAILED")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if not args.root.is_dir():
        print(f"site: root not found: {args.root}", file=sys.stderr)
        return 2

    result = check_site(args.root)
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else _format(result))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
