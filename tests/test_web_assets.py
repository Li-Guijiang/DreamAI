"""Guard the static web surface and the documentation image graph.

The web client has no bundler to fail on a missing import, so a deleted CSS or
JS file would otherwise surface as a 404 in production. These tests check local
references in every shipped page and every documentation image.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web" / "web"
ATTACHMENT_MANIFEST = ROOT / "assets" / "readme" / "attachments.json"

# GitHub strips <video>, and repository-relative images need an attachment upload.
# jsDelivr serves files straight from the repository, which keeps the 30 fps WebP
# hero working without a manual upload, so it is the one allowed CDN.
ALLOWED_CDN_PREFIX = "https://cdn.jsdelivr.net/gh/Li-Guijiang/DreamAI@"

PAGES = [WEB / "index.html", WEB / "download.html", WEB / "docs.html"]
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
            if not (
                reference.startswith("/assets/")
                or reference in {"/", "/docs.html", "/download.html"}
            ):
                continue
            target = WEB / reference.lstrip("/")
            if not target.is_file():
                missing.append(f"{page.name} -> {reference}")
    assert not missing, "missing web assets:\n" + "\n".join(missing)


def test_every_documentation_image_is_local_or_in_the_manifest():
    """GitHub's raw image CDN is unreachable on some networks.

    Documentation illustrations therefore use GitHub user attachments registered
    in ``assets/readme/attachments.json``. Relative images remain valid for
    contributor-facing files on disk; anything else must be registered.
    """
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
        "assets/js/desktop-update.js",
    ):
        assert (WEB / relative).is_file(), relative


def test_realtime_greeting_and_starlight_clock():
    landing = (WEB / "assets" / "js" / "landing.js").read_text(encoding="utf-8")
    app = (WEB / "assets" / "js" / "app.js").read_text(encoding="utf-8")
    index = (WEB / "index.html").read_text(encoding="utf-8")
    for greeting in ("早上好", "上午好", "中午好", "下午好", "晚上好", "夜深了"):
        assert greeting in landing, greeting
        assert greeting in app, greeting
    assert "timeGreeting" in landing
    assert "watchDaypart" in landing
    for marker in (
        "starClock",
        "starClockTime",
        "starClockDate",
        "updateGate",
        "updateHint",
        "releaseNote",
    ):
        assert marker in index or marker in (WEB / "download.html").read_text(encoding="utf-8"), (
            marker
        )
    assert "initStarClock" in app


def test_desktop_update_contract_is_shipped():
    manifest = json.loads((ROOT / "desktop" / "package.json").read_text(encoding="utf-8"))
    assert manifest["version"] == "1.3.0"
    main = (ROOT / "desktop" / "electron" / "main.js").read_text(encoding="utf-8")
    preload = (ROOT / "desktop" / "electron" / "preload.js").read_text(encoding="utf-8")
    updater = (ROOT / "desktop" / "electron" / "update.js").read_text(encoding="utf-8")
    web_updater = (WEB / "assets" / "js" / "desktop-update.js").read_text(encoding="utf-8")
    assert "desktop:update-install" in main
    assert "desktop:update-progress" in preload
    assert "DreamAI-Setup-" in updater
    assert "sha256" in updater
    assert "updateGate" in web_updater
    assert "暂不更新" in web_updater
    # The prompt must recur on every fresh entry, so dismissal is not persisted.
    assert "sessionStorage" not in web_updater
    assert (ROOT / "desktop" / "test" / "update.test.js").is_file()


def test_owner_identity_is_fixed_in_the_prompts():
    web_prompt = (ROOT / "web" / "app" / "config.py").read_text(encoding="utf-8")
    cli_prompt = (ROOT / "dream_ai" / "config.py").read_text(encoding="utf-8")
    assert "李贵江" in web_prompt
    assert "独立研发" in web_prompt
    assert "李贵江等人组成的团队" not in web_prompt
    assert "Li Guijiang" in cli_prompt
    assert "created and owned" in cli_prompt
    assert not re.search(r"1[3-9]\d{9}", web_prompt + cli_prompt)


def test_public_pages_do_not_publish_private_contacts():
    for page in PAGES:
        text = page.read_text(encoding="utf-8")
        assert "tel:" not in text, f"private phone link in {page.name}"
        assert "mailto:" not in text, f"private mail link in {page.name}"
        assert "@qq.com" not in text.lower(), f"private QQ mail in {page.name}"
        assert not re.search(r"1[3-9]\d{9}", text), f"private phone number in {page.name}"
        assert "Dream AI 团队" not in text, f"team ownership copy in {page.name}"
        assert "李贵江等人组成的团队" not in text, f"team ownership copy in {page.name}"
