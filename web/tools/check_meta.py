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
LINK_REL = re.compile(r'<link[^>]*rel="([^"]+)"[^>]*>', re.I)
LINK_REL_ALT = re.compile(r"<link[^>]*>", re.I)
HREF = re.compile(r'href="([^"]+)"')
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


def icon_hrefs(text: str) -> dict[str, list[str]]:
    """Collect icon links by rel, tolerating attribute order."""
    result: dict[str, list[str]] = {}
    for tag in LINK_REL_ALT.findall(text):
        rel_match = re.search(r'rel="([^"]+)"', tag, re.I)
        href_match = HREF.search(tag)
        if not rel_match or not href_match:
            continue
        for rel in rel_match.group(1).split():
            if rel in ("icon", "apple-touch-icon"):
                result.setdefault(rel, []).append(href_match.group(1))
    return result


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
    if len(title) > 60:
        issues.append(f"<title> is {len(title)} chars (recommended <= 60)")
    description = named.get("description", "")
    if description and len(description) > 160:
        issues.append(f"description is {len(description)} chars (recommended <= 160)")
    for name in REQUIRED_NAMED:
        if not named.get(name):
            issues.append(f"missing meta name={name}")

    icons = icon_hrefs(text)
    if not icons.get("icon"):
        issues.append("missing rel=icon")
    if not icons.get("apple-touch-icon"):
        issues.append("missing rel=apple-touch-icon")
    for hrefs in icons.values():
        for href in hrefs:
            if href.startswith("/") and not (SITE / href.lstrip("/").split("?")[0]).is_file():
                issues.append(f"icon not found: {href}")

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
        "icons": icons,
        "og": og,
        "issues": sorted(issues),
        "ok": not issues,
    }


def check_manifest(site: Path) -> dict:
    """The installable app must agree with the pages on colours and identity."""
    path = site / "manifest.webmanifest"
    if not path.is_file():
        return {"issues": ["manifest.webmanifest: missing"], "ok": False}
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        return {"issues": [f"manifest.webmanifest: unreadable ({type(exc).__name__})"], "ok": False}
    issues: list[str] = []
    for field in (
        "name",
        "short_name",
        "description",
        "lang",
        "start_url",
        "scope",
        "display",
        "theme_color",
        "background_color",
        "icons",
    ):
        if field not in manifest:
            issues.append(f"manifest: missing {field}")
    pages = [named_pairs(p.read_text(encoding="utf-8")) for p in site.glob("*.html")]
    page_themes = {p.get("theme-color") for p in pages if p.get("theme-color")}
    if page_themes and manifest.get("theme_color") not in page_themes:
        issues.append(
            f"manifest theme_color {manifest.get('theme_color')!r} differs from pages {sorted(page_themes)}"
        )
    for icon in manifest.get("icons", []) if isinstance(manifest.get("icons"), list) else []:
        src = icon.get("src", "") if isinstance(icon, dict) else ""
        if src.startswith("/") and not (site / src.lstrip("/")).is_file():
            issues.append(f"manifest icon not found: {src}")
    return {"issues": sorted(issues), "ok": not issues}


def check(site: Path = SITE) -> dict:
    pages = [check_page(path) for path in sorted(site.glob("*.html"))]
    manifest = check_manifest(site)
    return {
        "pages": pages,
        "manifest": manifest,
        "ok": all(page["ok"] for page in pages) and manifest["ok"],
    }


def _format(result: dict) -> str:
    lines = [f"meta: {len(result['pages'])} pages checked"]
    for page in result["pages"]:
        if page["ok"]:
            continue
        lines.append(f"  {page['page']}:")
        for issue in page["issues"]:
            lines.append(f"    {issue}")
    for issue in result["manifest"]["issues"]:
        lines.append(f"  manifest: {issue}")
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
