"""A link that 404s after publishing is a delivery bug, not a typo."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "web" / "tools" / "check_site.py"
SITE = ROOT / "web" / "web"

sys.path.insert(0, str(TOOL.parent))
import check_site  # noqa: E402


def make_site(tmp_path: Path, page: str, manifest: dict | None = None) -> Path:
    (tmp_path / "a.html").write_text(page, encoding="utf-8")
    downloads = tmp_path / "downloads"
    downloads.mkdir()
    (downloads / "latest.json").write_text(
        json.dumps(
            manifest
            or {
                "version": "1.2.3",
                "file": "DreamAI-Setup-1.2.3.exe",
                "size": 1024,
                "sha256": "a" * 64,
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "here.html").write_text("ok", encoding="utf-8")
    return tmp_path


def test_the_published_site_passes_every_check():
    result = check_site.check_site(SITE)

    assert result["ok"] is True
    assert result["pageLinks"] > 0
    assert result["issues"]["brokenPages"] == []
    assert result["issues"]["brokenAnchors"] == []
    assert result["issues"]["manifest"] == []


def test_a_link_to_a_missing_page_is_reported(tmp_path):
    site = make_site(tmp_path, '<a href="/gone.html">x</a>')

    result = check_site.check_site(site)

    assert result["ok"] is False
    assert any("gone.html" in item for item in result["issues"]["brokenPages"])


def test_a_link_to_an_existing_page_passes(tmp_path):
    site = make_site(tmp_path, '<a href="/here.html?v=2">x</a>')

    assert check_site.check_site(site)["issues"]["brokenPages"] == []


def test_an_anchor_whose_id_was_renamed_is_reported(tmp_path):
    site = make_site(tmp_path, '<a href="#old">x</a><section id="new"></section>')

    result = check_site.check_site(site)

    assert any("#old" in item for item in result["issues"]["brokenAnchors"])


def test_a_matching_anchor_passes(tmp_path):
    site = make_site(tmp_path, '<a href="#new">x</a><section id="new"></section>')

    assert check_site.check_site(site)["issues"]["brokenAnchors"] == []


def test_a_bare_hash_is_not_treated_as_a_broken_anchor(tmp_path):
    site = make_site(tmp_path, '<a href="#">top</a>')

    assert check_site.check_site(site)["issues"]["brokenAnchors"] == []


def test_a_manifest_whose_name_disagrees_with_its_version(tmp_path):
    site = make_site(
        tmp_path,
        "",
        {"version": "2.0.0", "file": "DreamAI-Setup-1.9.0.exe", "size": 1, "sha256": "a" * 64},
    )

    issues = check_site.check_site(site)["issues"]["manifest"]

    assert any("file" in item for item in issues)


def test_a_manifest_with_a_broken_hash_is_reported(tmp_path):
    site = make_site(
        tmp_path,
        "",
        {"version": "2.0.0", "file": "x-2.0.0.exe", "size": 1, "sha256": "xyz"},
    )

    assert any("sha256" in item for item in check_site.check_site(site)["issues"]["manifest"])


def test_a_missing_manifest_is_reported(tmp_path):
    (tmp_path / "a.html").write_text("", encoding="utf-8")

    issues = check_site.check_site(tmp_path)["issues"]["manifest"]

    assert any("missing" in item for item in issues)


def test_the_cli_prints_parseable_json_and_succeeds():
    done = subprocess.run(
        [sys.executable, str(TOOL), "--json"], capture_output=True, text=True, check=False
    )

    payload = json.loads(done.stdout)
    assert done.returncode == 0
    assert payload["ok"] is True
    assert set(payload["issues"]) >= {"brokenPages", "brokenAnchors", "manifest"}
