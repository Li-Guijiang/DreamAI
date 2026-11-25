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


def make_site(
    tmp_path: Path,
    page: str,
    manifest: dict | None = None,
    sw_cache: str = "2.0.0",
    shell: list[str] | None = None,
) -> Path:
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
                "date": "2026-10-31",
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "here.html").write_text("ok", encoding="utf-8")
    shell_lines = "".join(f'  "{item}",\n' for item in (shell or []))
    (tmp_path / "sw.js").write_text(
        f'const CACHE = "dreamai-shell-v{sw_cache}";\n'
        f"const SHELL = [\n{shell_lines}];\n",
        encoding="utf-8",
    )
    app = tmp_path / "app"
    app.mkdir()
    (app / "config.py").write_text('VERSION = "1.0.0"\n', encoding="utf-8")
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
    assert set(payload["issues"]) >= {"brokenPages", "brokenAnchors", "manifest", "css", "metadata"}


def test_the_published_site_has_clean_css_and_metadata():
    issues = check_site.check_site(SITE)["issues"]

    assert issues["css"] == []
    assert issues["metadata"] == []
    assert issues["markup"] == []


def test_duplicate_ids_are_reported(tmp_path):
    site = make_site(tmp_path, '<div id="x"></div><div id="x"></div>')

    issues = check_site.check_site(site)["issues"]["markup"]

    assert any("duplicate id #x" in item for item in issues)


def test_a_new_window_link_without_noopener_is_reported(tmp_path):
    site = make_site(tmp_path, '<a href="/here.html" target="_blank">x</a>')

    issues = check_site.check_site(site)["issues"]["markup"]

    assert any("noopener" in item for item in issues)


def test_a_new_window_link_with_noopener_passes(tmp_path):
    site = make_site(
        tmp_path, '<a href="/here.html" target="_blank" rel="noopener noreferrer">x</a>'
    )

    assert check_site.check_site(site)["issues"]["markup"] == []


def test_a_missing_css_reference_is_reported(tmp_path):
    site = make_site(tmp_path, "")
    css_dir = site / "assets" / "css"
    css_dir.mkdir(parents=True)
    (css_dir / "site.css").write_text('a{background:url("../img/gone.png")}', encoding="utf-8")

    issues = check_site.check_site(site)["issues"]["css"]

    assert any("gone.png" in item for item in issues)


def test_an_svg_fragment_reference_is_not_a_missing_file(tmp_path):
    site = make_site(tmp_path, "")
    css_dir = site / "assets" / "css"
    css_dir.mkdir(parents=True)
    (css_dir / "site.css").write_text("a{fill:url(%23n)}", encoding="utf-8")

    assert check_site.check_site(site)["issues"]["css"] == []


def test_a_page_without_metadata_is_reported(tmp_path):
    site = make_site(tmp_path, "<html><body>x</body></html>")

    issues = check_site.check_site(site)["issues"]["metadata"]

    assert any("lang" in item for item in issues)
    assert any("title" in item for item in issues)
    assert any("description" in item for item in issues)


def test_a_bad_manifest_date_is_reported(tmp_path):
    site = make_site(
        tmp_path,
        "",
        {
            "version": "2.0.0",
            "file": "x-2.0.0.exe",
            "size": 1,
            "sha256": "a" * 64,
            "date": "昨天",
        },
    )

    assert any("date" in item for item in check_site.check_site(site)["issues"]["manifest"])


def test_a_service_worker_older_than_the_app_is_reported(tmp_path):
    site = make_site(tmp_path, "")
    (site / "sw.js").write_text('const CACHE = "dreamai-shell-v0.9.0";', encoding="utf-8")

    issues = check_site.check_site(site)["issues"]["serviceWorker"]

    assert any("0.9.0" in item and "1.0.0" in item for item in issues)


def test_a_current_service_worker_passes(tmp_path):
    site = make_site(tmp_path, "")

    assert check_site.check_site(site)["issues"]["serviceWorker"] == []


def test_a_missing_service_worker_is_reported(tmp_path):
    site = make_site(tmp_path, "")
    (site / "sw.js").unlink()

    assert any("missing" in item for item in check_site.check_site(site)["issues"]["serviceWorker"])


def test_the_json_result_has_a_stable_shape():
    result = check_site.check_site(SITE)

    assert set(result) == {
        "pages",
        "assetReferences",
        "pageLinks",
        "issues",
        "ok",
    }
    assert set(result["issues"]) == {
        "missing",
        "conflicts",
        "unversioned",
        "brokenPages",
        "brokenAnchors",
        "css",
        "metadata",
        "markup",
        "serviceWorker",
        "serviceWorkerPins",
        "manifest",
    }


def test_a_stale_service_worker_asset_pin_is_reported(tmp_path):
    site = make_site(
        tmp_path,
        '<link rel="stylesheet" href="/assets/css/app.css?v=2.1.0">',
        sw_cache="1.5.7",
        shell=['/assets/css/app.css?v=2.0.8'],
    )

    issues = check_site.check_site(site)["issues"]["serviceWorkerPins"]

    assert any("app.css" in item and "2.0.8" in item for item in issues)


def test_matching_service_worker_pins_pass(tmp_path):
    site = make_site(
        tmp_path,
        '<link rel="stylesheet" href="/assets/css/app.css?v=2.1.0">',
        sw_cache="1.5.7",
        shell=['/assets/css/app.css?v=2.1.0'],
    )

    assert check_site.check_site(site)["issues"]["serviceWorkerPins"] == []


def test_the_published_service_worker_matches_the_app():
    assert check_site.check_site(SITE)["issues"]["serviceWorker"] == []
