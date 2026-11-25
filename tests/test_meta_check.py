"""Social previews must not break silently on shared pages."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "web" / "tools" / "check_meta.py"

sys.path.insert(0, str(TOOL.parent))
import check_meta  # noqa: E402

BASE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Dream AI</title>
<meta name="description" content="a demo page">
<meta name="theme-color" content="#08090d">
<link rel="icon" href="/assets/img/favicon.ico" sizes="any">
<link rel="apple-touch-icon" href="/assets/img/apple-touch-icon.png">
{meta}
</head>
<body></body>
</html>
"""

OG = """<meta property="og:type" content="website">
<meta property="og:site_name" content="Dream AI">
<meta property="og:title" content="Dream AI">
<meta property="og:description" content="a demo page">
<meta property="og:url" content="https://liguijiang.com/">
<meta property="og:image" content="https://liguijiang.com/assets/img/og.png">"""


def make_page(tmp_path: Path, meta: str = OG, name: str = "index.html") -> Path:
    path = tmp_path / name
    path.write_text(BASE.format(meta=meta), encoding="utf-8")
    if not (tmp_path / "manifest.webmanifest").exists():
        (tmp_path / "manifest.webmanifest").write_text(
            json.dumps(
                {
                    "name": "Dream AI",
                    "short_name": "Dream AI",
                    "description": "demo",
                    "lang": "zh-CN",
                    "start_url": "/",
                    "scope": "/",
                    "display": "standalone",
                    "theme_color": "#08090d",
                    "background_color": "#08090d",
                    "icons": [],
                }
            ),
            encoding="utf-8",
        )
    return path


def test_the_published_pages_have_consistent_metadata():
    result = check_meta.check()

    assert result["ok"] is True
    assert len(result["pages"]) >= 5


def test_a_complete_public_page_passes(tmp_path):
    page = make_page(tmp_path)

    assert check_meta.check_page(page)["ok"] is True


def test_a_missing_og_image_is_reported(tmp_path):
    meta = OG.replace('<meta property="og:image" content="https://liguijiang.com/assets/img/og.png">', "")
    page = make_page(tmp_path, meta)

    result = check_meta.check_page(page)

    assert "missing og:image" in result["issues"]


def test_an_og_title_that_disagrees_with_the_page_is_reported(tmp_path):
    meta = OG.replace(
        'property="og:title" content="Dream AI"',
        'property="og:title" content="Different title"',
    )
    page = make_page(tmp_path, meta)

    result = check_meta.check_page(page)

    assert any("og:title" in item and "!=" in item for item in result["issues"])


def test_a_staging_og_url_is_reported(tmp_path):
    meta = OG.replace("https://liguijiang.com/", "https://staging.example/")
    page = make_page(tmp_path, meta)

    result = check_meta.check_page(page)

    assert any("og:url" in item for item in result["issues"])


def test_a_wrong_og_image_is_reported(tmp_path):
    meta = OG.replace("assets/img/og.png", "assets/img/other.png")
    page = make_page(tmp_path, meta)

    result = check_meta.check_page(page)

    assert any("og:image differs" in item for item in result["issues"])


def test_a_missing_language_is_reported(tmp_path):
    page = make_page(tmp_path)
    page.write_text(page.read_text(encoding="utf-8").replace(' lang="zh-CN"', ""), encoding="utf-8")

    assert "missing html lang" in check_meta.check_page(page)["issues"]


def test_a_missing_theme_color_is_reported(tmp_path):
    page = make_page(tmp_path)
    text = page.read_text(encoding="utf-8").replace(
        '<meta name="theme-color" content="#08090d">\n', ""
    )
    page.write_text(text, encoding="utf-8")

    assert "missing meta name=theme-color" in check_meta.check_page(page)["issues"]


def test_noindex_pages_are_exempt_from_og(tmp_path):
    page = make_page(tmp_path, meta='<meta name="robots" content="noindex">')

    result = check_meta.check_page(page)

    assert result["noindex"] is True
    assert result["ok"] is True


def test_noindex_pages_must_not_declare_og(tmp_path):
    page = make_page(tmp_path, meta=OG + '\n<meta name="robots" content="noindex">')

    result = check_meta.check_page(page)

    assert any("noindex page declares" in item for item in result["issues"])


def test_a_missing_apple_touch_icon_is_reported(tmp_path):
    page = make_page(tmp_path)
    text = page.read_text(encoding="utf-8").replace(
        '<link rel="apple-touch-icon" href="/assets/img/apple-touch-icon.png">\n', ""
    )
    page.write_text(text, encoding="utf-8")

    assert "missing rel=apple-touch-icon" in check_meta.check_page(page)["issues"]


def test_a_missing_primary_icon_is_reported(tmp_path):
    page = make_page(tmp_path)
    text = page.read_text(encoding="utf-8").replace(
        '<link rel="icon" href="/assets/img/favicon.ico" sizes="any">\n', ""
    )
    page.write_text(text, encoding="utf-8")

    assert "missing rel=icon" in check_meta.check_page(page)["issues"]


def test_an_icon_link_with_reversed_attributes_is_recognised(tmp_path):
    page = make_page(tmp_path)
    text = page.read_text(encoding="utf-8").replace(
        '<link rel="apple-touch-icon" href="/assets/img/apple-touch-icon.png">',
        '<link href="/assets/img/apple-touch-icon.png" rel="apple-touch-icon">',
    )
    page.write_text(text, encoding="utf-8")

    result = check_meta.check_page(page)

    assert result["icons"]["apple-touch-icon"] == ["/assets/img/apple-touch-icon.png"]
    assert result["ok"] is True


def test_a_manifest_theme_that_disagrees_with_pages_is_reported(tmp_path):
    make_page(tmp_path)
    manifest_path = tmp_path / "manifest.webmanifest"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["theme_color"] = "#ffffff"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = check_meta.check_manifest(tmp_path)

    assert any("theme_color" in item for item in result["issues"])


def test_a_missing_manifest_field_is_reported(tmp_path):
    make_page(tmp_path)
    manifest_path = tmp_path / "manifest.webmanifest"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    del manifest["start_url"]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = check_meta.check_manifest(tmp_path)

    assert any("missing start_url" in item for item in result["issues"])


def test_a_missing_manifest_is_reported(tmp_path):
    make_page(tmp_path)
    (tmp_path / "manifest.webmanifest").unlink()

    assert check_meta.check_manifest(tmp_path)["ok"] is False


def test_the_cli_passes_for_the_published_site():
    done = subprocess.run(
        [sys.executable, str(TOOL)], capture_output=True, text=True, check=False
    )

    assert done.returncode == 0
    assert "meta: OK" in done.stdout


def test_the_cli_emits_parseable_json(tmp_path):
    make_page(tmp_path)

    done = subprocess.run(
        [sys.executable, str(TOOL), "--site", str(tmp_path), "--json"],
        capture_output=True,
        text=True,
        check=False,
    )

    payload = json.loads(done.stdout)
    assert done.returncode == 0
    assert payload["ok"] is True
    assert set(payload["pages"][0]) >= {"page", "issues", "ok"}
