"""A sitemap that omits a page is invisible until a crawler notices."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("fastapi", reason="web dependencies are not installed")
WEB = str(Path(__file__).resolve().parent.parent / "web")
if WEB not in sys.path:
    sys.path.insert(0, WEB)

from fastapi.testclient import TestClient  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "web" / "tools" / "check_sitemap.py"

sys.path.insert(0, str(TOOL.parent))
import check_sitemap  # noqa: E402

ORIGIN = "https://liguijiang.com"


def make_site(tmp_path: Path, pages: dict[str, str], urls: list[str]) -> Path:
    for name, extra in pages.items():
        (tmp_path / name).write_text(
            f'<html><head><title>t</title>{extra}</head><body></body></html>',
            encoding="utf-8",
        )
    entries = "".join(f"<url><loc>{url}</loc></url>\n" for url in urls)
    (tmp_path / "sitemap.xml").write_text(
        f'<?xml version="1.0"?><urlset>{entries}</urlset>', encoding="utf-8"
    )
    return tmp_path


def test_the_published_sitemap_is_complete():
    result = check_sitemap.check()

    assert result["ok"] is True
    assert "docs.html" in result["pages"]


def test_the_served_sitemap_matches_the_static_file():
    from app import main

    with TestClient(main.app) as client:
        served = client.get("/sitemap.xml").text
    published = (ROOT / "web" / "web" / "sitemap.xml").read_text(encoding="utf-8")

    assert served == published


def test_the_served_sitemap_lists_every_public_page():
    from app import main

    with TestClient(main.app) as client:
        served = client.get("/sitemap.xml").text

    for name in ("download.html", "docs.html", "changelog.html"):
        assert f"{ORIGIN}/{name}" in served
    assert f"{ORIGIN}/" in served
    assert "offline.html" not in served


def test_an_omitted_page_is_reported(tmp_path):
    urls = [f"{ORIGIN}/", f"{ORIGIN}/docs.html"]
    site = make_site(
        tmp_path,
        {"index.html": "", "docs.html": "", "download.html": ""},
        urls,
    )

    result = check_sitemap.check(site, tmp_path / "main.py")

    assert any("download.html" in item for item in result["issues"])


def test_a_noindex_page_is_not_required(tmp_path):
    site = make_site(
        tmp_path,
        {
            "index.html": "",
            "offline.html": '<meta name="robots" content="noindex">',
        },
        [f"{ORIGIN}/"],
    )

    assert check_sitemap.check(site, tmp_path / "main.py")["ok"] is True


def test_a_noindex_page_that_is_listed_is_reported(tmp_path):
    site = make_site(
        tmp_path,
        {
            "index.html": "",
            "offline.html": '<meta name="robots" content="noindex">',
        },
        [f"{ORIGIN}/", f"{ORIGIN}/offline.html"],
    )

    result = check_sitemap.check(site, tmp_path / "main.py")

    assert any("offline.html" in item for item in result["issues"])


def test_a_missing_sitemap_is_reported(tmp_path):
    (tmp_path / "index.html").write_text("<title>t</title>", encoding="utf-8")

    result = check_sitemap.check(tmp_path, tmp_path / "main.py")

    assert result["ok"] is False
    assert any("no <loc>" in item for item in result["issues"])


def test_a_duplicate_url_is_reported(tmp_path):
    site = make_site(
        tmp_path,
        {"index.html": ""},
        [f"{ORIGIN}/", f"{ORIGIN}/"],
    )

    result = check_sitemap.check(site, tmp_path / "main.py")

    assert any("duplicate" in item for item in result["issues"])


def test_a_hardcoded_sitemap_route_is_reported(tmp_path):
    site = make_site(tmp_path, {"index.html": ""}, [f"{ORIGIN}/"])
    main = tmp_path / "main.py"
    main.write_text(
        '@app.get("/sitemap.xml")\nasync def sitemap():\n'
        '    return "<urlset><url></url></urlset>"\n',
        encoding="utf-8",
    )

    result = check_sitemap.check(site, main)

    assert any("hard-codes" in item for item in result["issues"])


def test_the_cli_passes_for_the_published_site():
    done = subprocess.run(
        [sys.executable, str(TOOL)], capture_output=True, text=True, check=False
    )

    assert done.returncode == 0
    assert "sitemap: OK" in done.stdout
