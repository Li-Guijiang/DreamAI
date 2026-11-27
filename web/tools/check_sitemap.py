"""Keep the published sitemap in step with the pages that exist.

A sitemap with a missing page is invisible in normal testing: every link in
the UI still works, only crawlers get an incomplete list. Worse, the server
used to hand-write a second copy with fewer URLs than the static file, so the
site visitors saw and the crawlers saw different sets of pages.

This tool checks that the sitemap lists exactly the indexable public pages,
that it exists in the build, and that the server serves the file instead of a
second hard-coded copy.

Read-only. Exits non-zero when the sitemap is incomplete or duplicated.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SITE = ROOT / "web" / "web"
MAIN = ROOT / "web" / "app" / "main.py"
ORIGIN = "https://liguijiang.com"
LOC = re.compile(r"<loc>([^<]+)</loc>")
ROBOTS_NOINDEX = re.compile(r'<meta[^>]*name="robots"[^>]*content="[^"]*noindex', re.I)
ROBOTS_NOINDEX_ALT = re.compile(r'<meta[^>]*content="[^"]*noindex"[^>]*name="robots"', re.I)


def indexable_pages(site: Path) -> list[str]:
    """Public HTML pages that are not marked noindex."""
    pages = []
    for page in sorted(site.glob("*.html")):
        text = page.read_text(encoding="utf-8")
        if ROBOTS_NOINDEX.search(text) or ROBOTS_NOINDEX_ALT.search(text):
            continue
        pages.append(page.name)
    return pages


def sitemap_urls(site: Path) -> list[str]:
    path = site / "sitemap.xml"
    if not path.is_file():
        return []
    return LOC.findall(path.read_text(encoding="utf-8"))


def check(site: Path = SITE, main: Path = MAIN) -> dict:
    pages = indexable_pages(site)
    urls = sitemap_urls(site)
    # index.html is served at the origin root; both spellings are valid.
    expected = {
        f"{ORIGIN}/" if name == "index.html" else f"{ORIGIN}/{name}"
        for name in pages
    }
    listed = {
        f"{ORIGIN}/" if url.rstrip("/") == ORIGIN else url
        for url in urls
    }
    issues: list[str] = []

    if not urls:
        issues.append("sitemap.xml: missing or has no <loc> entries")
    for url in sorted(expected - listed):
        issues.append(f"sitemap.xml: missing indexable page {url}")
    for url in sorted(listed - expected):
        issues.append(f"sitemap.xml: lists a non-indexable or absent page {url}")
    if len(urls) != len(listed):
        issues.append("sitemap.xml: duplicate <loc> entries")

    if main.is_file():
        source = main.read_text(encoding="utf-8")
        route = re.search(r'@app\.get\("/sitemap\.xml"\)\s*\nasync def sitemap.*?(?=\n@app\.|\Z)', source, re.S)
        if route:
            body = route.group(0)
            if "<urlset" in body:
                issues.append("main.py: sitemap route hard-codes XML instead of serving the file")
            if "sitemap.xml" not in body:
                issues.append("main.py: sitemap route does not read the static sitemap.xml")

    return {
        "pages": pages,
        "urls": urls,
        "issues": sorted(issues),
        "ok": not issues,
    }


def _format(result: dict) -> str:
    lines = [
        f"sitemap: {len(result['pages'])} indexable pages, {len(result['urls'])} <loc> entries"
    ]
    for issue in result["issues"]:
        lines.append(f"  {issue}")
    lines.append("sitemap: OK" if result["ok"] else "sitemap: FAILED")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=SITE)
    parser.add_argument("--main", type=Path, default=MAIN)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = check(args.site, args.main)
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else _format(result))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
