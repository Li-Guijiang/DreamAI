"""A published page must not silently use yesterday's stylesheet."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "web" / "tools" / "check_assets.py"
SITE = ROOT / "web" / "web"

sys.path.insert(0, str(TOOL.parent))
import check_assets  # noqa: E402


def make_site(tmp_path: Path, first: str, second: str | None = None) -> Path:
    assets = tmp_path / "assets" / "css"
    assets.mkdir(parents=True)
    (assets / "site.css").write_text("body{}", encoding="utf-8")
    (tmp_path / "a.html").write_text(first, encoding="utf-8")
    if second is not None:
        (tmp_path / "b.html").write_text(second, encoding="utf-8")
    return tmp_path


def test_the_published_site_has_no_missing_or_conflicting_assets():
    result = check_assets.check(SITE)

    assert result["ok"] is True
    assert result["pages"] >= 5
    assert result["references"] > 20
    assert result["issues"]["missing"] == []
    assert result["issues"]["conflicts"] == []


def test_two_pages_pinning_different_versions_are_reported(tmp_path):
    site = make_site(
        tmp_path,
        '<link rel="stylesheet" href="/assets/css/site.css?v=1.0.0">',
        '<link rel="stylesheet" href="/assets/css/site.css?v=2.0.0">',
    )

    result = check_assets.check(site)

    assert result["ok"] is False
    assert any("site.css" in item and "1.0.0" in item for item in result["issues"]["conflicts"])


def test_a_missing_asset_fails_the_check(tmp_path):
    site = tmp_path
    (site / "a.html").write_text(
        '<script src="/assets/js/gone.js?v=1.0.0"></script>', encoding="utf-8"
    )

    result = check_assets.check(site)

    assert result["ok"] is False
    assert any("gone.js" in item for item in result["issues"]["missing"])


def test_an_unversioned_image_is_only_a_warning(tmp_path):
    site = make_site(tmp_path, '<img src="/assets/css/site.css">')

    result = check_assets.check(site)

    assert result["ok"] is True
    assert len(result["issues"]["unversioned"]) == 1


def test_external_urls_are_not_treated_as_local_assets(tmp_path):
    site = make_site(tmp_path, '<link rel="stylesheet" href="https://cdn.test/a.css?v=1">')

    assert check_assets.scan_assets(site) == []


def test_the_cli_accepts_the_published_site():
    done = subprocess.run([sys.executable, str(TOOL)], capture_output=True, text=True, check=False)

    assert done.returncode == 0
    assert "assets: OK" in done.stdout


def test_the_cli_rejects_a_conflicting_site(tmp_path):
    site = make_site(
        tmp_path,
        '<link rel="stylesheet" href="/assets/css/site.css?v=1">',
        '<link rel="stylesheet" href="/assets/css/site.css?v=2">',
    )

    done = subprocess.run(
        [sys.executable, str(TOOL), "--root", str(site)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert done.returncode == 1
    assert "VERSION CONFLICT" in done.stdout


def test_the_cli_emits_parseable_json(tmp_path):
    site = make_site(tmp_path, '<link rel="stylesheet" href="/assets/css/site.css?v=1">')

    done = subprocess.run(
        [sys.executable, str(TOOL), "--root", str(site), "--json"],
        capture_output=True,
        text=True,
        check=False,
    )

    payload = json.loads(done.stdout)
    assert payload["ok"] is True
    assert set(payload["issues"]) == {"missing", "unversioned", "conflicts"}
