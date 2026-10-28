"""Guard the static web surface and the documentation image graph.

The web client has no bundler to fail on a missing import, so a deleted CSS or
JS file would otherwise surface as a 404 in production. These tests check local
references in every shipped page and every documentation image.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web" / "web"

PAGES = [WEB / "index.html", WEB / "download.html", WEB / "docs.html"]
HTML_REF_RE = re.compile(r"\b(?:src|href)=\"(/[^\"#?]+)")
IMG_RE = re.compile(r"<img\b[^>]*\bsrc=\"([^\"]+)\"", re.IGNORECASE)
MD_IMG_RE = re.compile(r"!\[[^\]]*]\(([^)]+)\)")


def _markdown_files() -> list[Path]:
    ignored = {".git", "node_modules", "release", "__pycache__", ".venv"}
    return [path for path in ROOT.rglob("*.md") if not any(part in ignored for part in path.parts)]


def _local_images(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    references = IMG_RE.findall(text) + MD_IMG_RE.findall(text)
    return [
        reference
        for reference in references
        if not re.match(r"^(https?:|data:|mailto:|#)", reference)
    ]


def test_web_pages_reference_existing_local_assets():
    missing = []
    for page in PAGES:
        assert page.is_file(), f"missing page: {page.name}"
        text = page.read_text(encoding="utf-8")
        for reference in HTML_REF_RE.findall(text):
            if not (
                reference.startswith("/assets/")
                or reference in {"/", "/docs.html", "/download.html"}
            ):
                continue
            target = WEB / reference.lstrip("/")
            if not target.is_file():
                missing.append(f"{page.name} -> {reference}")
    assert not missing, "missing web assets:\n" + "\n".join(missing)


def test_every_documentation_image_exists():
    missing = []
    for path in _markdown_files():
        for reference in _local_images(path):
            target = (path.parent / reference.split("?")[0]).resolve()
            if not target.is_file():
                missing.append(f"{path.relative_to(ROOT)} -> {reference}")
    assert not missing, "broken documentation images:\n" + "\n".join(missing)


def test_every_web_page_has_the_motion_switch():
    for page in PAGES:
        assert "data-motion-toggle" in page.read_text(encoding="utf-8"), page.name


def test_docs_page_is_in_the_sitemap():
    sitemap = (WEB / "sitemap.xml").read_text(encoding="utf-8")
    assert "https://liguijiang.com/docs.html" in sitemap


def test_web_motion_files_are_present():
    for relative in (
        "assets/css/motion.css",
        "assets/css/landing.css",
        "assets/css/pages.css",
        "assets/css/docs.css",
        "assets/js/motion.js",
        "assets/js/landing.js",
        "assets/js/docs.js",
    ):
        assert (WEB / relative).is_file(), relative
