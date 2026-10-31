"""Guard the static web surface, PWA shell and download manifest.

The web client has no bundler, so a deleted asset would only show up as a 404 in
production. These tests also keep private contact details out of public pages and
make sure the published download manifest matches the desktop version.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web" / "web"
ATTACHMENT_MANIFEST = ROOT / "assets" / "readme" / "attachments.json"
ALLOWED_CDN_PREFIX = "https://cdn.jsdelivr.net/gh/Li-Guijiang/DreamAI@"

PAGES = [WEB / "index.html", WEB / "download.html", WEB / "changelog.html", WEB / "offline.html"]
HTML_REF_RE = re.compile(r"\b(?:src|href)=\"(/[^\"#?]+)")
IMG_RE = re.compile(r"<img\b[^>]*\bsrc=\"([^\"]+)\"", re.IGNORECASE)
MD_IMG_RE = re.compile(r"!\[[^\]]*]\(([^)]+)\)")


def _markdown_files() -> list[Path]:
    ignored = {".git", "node_modules", "release", "__pycache__", ".venv"}
    return [path for path in ROOT.rglob("*.md") if not any(part in ignored for part in path.parts)]


def _markdown_images(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return IMG_RE.findall(text) + MD_IMG_RE.findall(text)


def _attachments() -> dict[str, dict[str, str]]:
    payload = json.loads(ATTACHMENT_MANIFEST.read_text(encoding="utf-8"))
    return payload["images"]


def test_web_pages_reference_existing_local_assets():
    missing = []
    for page in PAGES:
        assert page.is_file(), f"missing page: {page.name}"
        text = page.read_text(encoding="utf-8")
        for reference in HTML_REF_RE.findall(text):
            if not reference.startswith("/assets/"):
                continue
            target = WEB / reference.lstrip("/")
            if not target.is_file():
                missing.append(f"{page.name} -> {reference}")
    assert not missing, "missing web assets:\n" + "\n".join(missing)


def test_every_documentation_image_is_local_or_in_the_manifest():
    attachments = _attachments()
    allowed_urls = {entry["url"] for entry in attachments.values()}
    allowed_badge_prefixes = (
        "https://img.shields.io/",
        "https://github.com/Li-Guijiang/DreamAI/actions/workflows/ci.yml/badge.svg",
    )
    missing = []
    unregistered = []
    for path in _markdown_files():
        for reference in _markdown_images(path):
            clean = reference.split("?")[0]
            if clean in allowed_urls or reference.startswith(allowed_badge_prefixes):
                continue
            if re.match(r"^(https?:|data:|mailto:|#)", clean):
                unregistered.append(f"{path.relative_to(ROOT)} -> {reference}")
                continue
            target = (path.parent / clean).resolve()
            if not target.is_file():
                missing.append(f"{path.relative_to(ROOT)} -> {reference}")
    assert not missing, "broken local documentation images:\n" + "\n".join(missing)
    assert not unregistered, "unregistered remote images:\n" + "\n".join(unregistered)


def test_attachment_manifest_points_at_existing_sources():
    attachments = _attachments()
    assert attachments, "the README attachment manifest is empty"
    for name, entry in attachments.items():
        assert entry["url"].startswith(
            ("https://github.com/user-attachments/assets/", ALLOWED_CDN_PREFIX)
        ), name
        assert (ROOT / entry["source"]).is_file(), f"{name}: missing {entry['source']}"


def test_pwa_shell_is_shipped_and_registered():
    for relative in ("sw.js", "offline.html", "manifest.webmanifest"):
        assert (WEB / relative).is_file(), relative
    index = (WEB / "index.html").read_text(encoding="utf-8")
    app = (WEB / "assets" / "js" / "app.js").read_text(encoding="utf-8")
    assert "serviceWorker" in app and "/sw.js" in app
    assert "manifest.webmanifest" in index


def test_changelog_page_is_in_the_sitemap():
    sitemap = (WEB / "sitemap.xml").read_text(encoding="utf-8")
    assert "https://liguijiang.com/changelog.html" in sitemap


def test_download_manifest_matches_desktop_version():
    manifest = json.loads((WEB / "downloads" / "latest.json").read_text(encoding="utf-8"))
    desktop = json.loads((ROOT / "desktop" / "package.json").read_text(encoding="utf-8"))
    assert manifest["version"] == desktop["version"]
    assert manifest["file"] == f"DreamAI-Setup-{desktop['version']}.exe"
    assert manifest["size"] > 0
    assert len(manifest["sha256"]) == 64
    download = (WEB / "download.html").read_text(encoding="utf-8")
    assert f"v{desktop['version']}" in download
    assert manifest["file"] in download


def test_current_ai_features_are_wired():
    app = (WEB / "assets" / "js" / "app.js").read_text(encoding="utf-8")
    main = (ROOT / "web" / "app" / "main.py").read_text(encoding="utf-8")
    for marker in ("STORE_MEMORY", "STORE_KNOWLEDGE", "retrieveKnowledge", "openCanvas"):
        assert marker in app, marker
    for marker in (
        "/api/read",
        "/api/usage",
        "reader_limiter",
        "payload.memory",
        "payload.context",
    ):
        assert marker in main, marker
    update = (ROOT / "desktop" / "electron" / "update.js").read_text(encoding="utf-8")
    desktop_main = (ROOT / "desktop" / "electron" / "main.js").read_text(encoding="utf-8")
    assert "isNewerVersion" in update
    assert "latest.yml" in desktop_main
    assert (ROOT / "desktop" / "test" / "update.test.js").is_file()


def test_team_credit_is_present_and_private_contacts_are_not_public():
    for page in PAGES:
        text = page.read_text(encoding="utf-8")
        assert "tel:" not in text, f"private phone link in {page.name}"
        assert "mailto:" not in text, f"private mail link in {page.name}"
        assert "@qq.com" not in text.lower(), f"private QQ mail in {page.name}"
        assert not re.search(r"1[3-9]\d{9}", text), f"private phone number in {page.name}"
    index = (WEB / "index.html").read_text(encoding="utf-8")
    assert "李贵江" in index
    assert "团队" in index
    assert "github.com/Li-Guijiang/DreamAI" in index
