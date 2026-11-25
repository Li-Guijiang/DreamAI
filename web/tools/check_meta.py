"""Check head metadata consistency across the static site.

Social previews break quietly: a page that works perfectly in a browser can
still show a blank card when shared. This tool checks that every public page
declares a complete Open Graph set, that ``og:title`` agrees with ``<title>``,
that preview images exist locally, and that basic head fields are present.

Pages marked ``noindex`` are intentionally exempt from social tags: an offline
fallback should not be indexable or shareable. They still need the basic head
fields. The canonical public origin is fixed so staging URLs cannot leak into
shared links.

Read-only. Exits non-zero when a public page is missing required metadata.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SITE = ROOT / "web" / "web"
PUBLIC_ORIGIN = "https://liguijiang.com"
DEFAULT_IMAGE = "/assets/img/og.png"

OG = re.compile(r'<meta[^>]*property="(og:[^"]+)"[^>]*content="([^"]*)"', re.I)
OG_ALT = re.compile(r'<meta[^>]*content="([^"]*)"[^>]*property="(og:[^"]+)"', re.I)
META_NAME = re.compile(r'<meta[^>]*name="([^"]+)"[^>]*content="([^"]*)"', re.I)
TITLE = re.compile(r"<title>([^<]*)</title>", re.I)
LANG = re.compile(r'<html[^>]*\blang="([^"]+)"', re.I)

REQUIRED_OG = ("og:type", "og:site_name", "og:title", "og:description", "og:url", "og:image")
REQUIRED_NAMED = ("description", "viewport", "theme-color")


def meta_pairs(text: str) -> dict[str, str]:
    """Open Graph values, tolerating either attribute order."""
    result = dict(OG.findall(text))
    for value, key in OG_ALT.findall(text):
        result.setdefault(key.lower(), value)
    return result


def named_pairs(text: str) -> dict[str, str]:
    return {name.lower(): value for name, value in META_NAME.findall(text)}


def is_noindex(named: dict[str, str]) -> bool:
    return "noindex" in named.get("robots", "").lower()


def check_page(path: Path, origin: str = PUBLIC_ORIGIN, image: str = DEFAULT_IMAGE) -> dict:
    """Validate one HTML page's head metadata."""
    text = path.read_text(encoding="utf-8")
    named = named_pairs(text)
    og = meta_pairs(text)
    title_match = TITLE.search(text)
    title = title_match.group(1).strip() if title_match else ""
    lang_match = LANG.search(text)
    issues: list[str] = []

    if not lang_match:
        issues.append("missing html lang")
    if not title:
        issues.append("missing <title>")
    for name in REQUIRED_NAMED:
        if not named.get(name):
            issues.append(f"missing meta name={name}")

    if not is_noindex(named):
        for key in REQUIRED_OG:
            if not og.get(key):
                issues.append(f"missing {key}")
        if og.get("og:title") and title and og["og:title"] != title:
            issues.append(f"og:title {og['og:title']!r} != <title> {title!r}")
        url = og.get("og:url", "")
        if url and not url.startswith(origin):
            issues.append(f"og:url does not start with {origin}: {url}")
        if og.get("og:image"):
            image_value = og["og:image"]
            if image_value.startswith("/"):
                if not (SITE / image_value.lstrip("/")).is_file():
                    issues.append(f"og:image not found: {image_value}")
            elif not image_value.startswith(origin):
                issues.append(f"og:image is not a public origin URL: {image_value}")
        if og.get("og:image") and og["og:image"] != f"{origin}{image}":
            issues.append(f"og:image differs from the default {image}")
    elif og:
        issues.append("noindex page declares Open Graph tags")

    return {
        "page": path.name,
        "noindex": is_noindex(named),
        "title": title,
        "og": og,
        "issues": sorted(issues),
        "ok": not issues,
    }


def check(site: Path = SITE) -> dict:
    pages = [check_page(path) for path in sorted(site.glob("*.html"))]
    return {"pages": pages, "ok": all(page["ok"] for page in pages)}


def _format(result: dict) -> str:
    lines = [f"meta: {len(result['pages'])} pages checked"]
    for page in result["pages"]:
        if page["ok"]:
            continue
        lines.append(f"  {page['page']}:")
        for issue in page["issues"]:
            lines.append(f"    {issue}")
    lines.append("meta: OK" if result["ok"] else "meta: FAILED")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site", type=Path, default=SITE)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = check(args.site)
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else _format(result))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
