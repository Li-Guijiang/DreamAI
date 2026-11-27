"""Four versions are independent, but their relationships are not optional."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "web" / "tools" / "check_versions.py"

sys.path.insert(0, str(TOOL.parent))
import check_versions  # noqa: E402


def make_tree(
    root: Path,
    *,
    server="1.5.0",
    worker="1.5.6",
    installer="1.3.0",
    package="1.3.0",
    changelog="1.5.0",
) -> Path:
    (root / "web" / "app").mkdir(parents=True, exist_ok=True)
    (root / "web" / "web" / "downloads").mkdir(parents=True, exist_ok=True)
    (root / "desktop").mkdir(parents=True, exist_ok=True)
    (root / "web" / "app" / "config.py").write_text(f'VERSION = "{server}"\n', encoding="utf-8")
    (root / "web" / "web" / "sw.js").write_text(
        f'const CACHE = "dreamai-shell-v{worker}";\n', encoding="utf-8"
    )
    (root / "web" / "web" / "downloads" / "latest.json").write_text(
        json.dumps({"version": installer}), encoding="utf-8"
    )
    (root / "desktop" / "package.json").write_text(
        json.dumps({"version": package}), encoding="utf-8"
    )
    (root / "web" / "web" / "changelog.html").write_text(
        f"<h2>v{changelog}</h2>\n", encoding="utf-8"
    )
    return root


def test_the_published_versions_are_coherent():
    result = check_versions.check()

    assert result["ok"] is True
    assert set(result["versions"]) >= {
        "server",
        "serviceWorker",
        "installer",
        "desktopPackage",
        "cli",
        "changelog",
    }


def test_a_coherent_tree_passes(tmp_path):
    assert check_versions.check(make_tree(tmp_path))["ok"] is True


def test_a_worker_older_than_the_server_is_reported(tmp_path):
    root = make_tree(tmp_path, server="2.0.0", worker="1.5.6")

    result = check_versions.check(root)

    assert any("older than server" in item for item in result["issues"])


def test_a_worker_equal_to_the_server_is_allowed(tmp_path):
    root = make_tree(tmp_path, server="1.5.0", worker="1.5.0")

    assert check_versions.check(root)["ok"] is True


def test_an_installer_that_disagrees_with_the_package_is_reported(tmp_path):
    root = make_tree(tmp_path, installer="1.3.0", package="1.4.0")

    result = check_versions.check(root)

    assert any("installer manifest" in item for item in result["issues"])


def test_a_changelog_older_than_the_server_is_reported(tmp_path):
    root = make_tree(tmp_path, server="2.0.0", changelog="1.5.0")

    result = check_versions.check(root)

    assert any("changelog latest" in item for item in result["issues"])


def test_a_newer_changelog_is_allowed(tmp_path):
    root = make_tree(tmp_path, server="1.5.0", changelog="1.6.0")

    assert check_versions.check(root)["ok"] is True


def test_a_non_semantic_version_is_reported(tmp_path):
    root = make_tree(tmp_path, server="1.5")

    result = check_versions.check(root)

    assert any("not a semantic version" in item for item in result["issues"])


def test_version_comparison_is_numeric_not_lexical(tmp_path):
    root = make_tree(tmp_path, server="1.10.0", worker="1.9.0")

    result = check_versions.check(root)

    assert any("older than server" in item for item in result["issues"])


def test_a_missing_precache_target_is_reported(tmp_path):
    root = make_tree(tmp_path)
    sw = root / "web" / "web" / "sw.js"
    sw.write_text(
        sw.read_text(encoding="utf-8")
        + 'const SHELL = ["/index.html", "/assets/js/gone.js?v=1.0.0"];\n',
        encoding="utf-8",
    )

    result = check_versions.check(root)

    assert any("gone.js" in item for item in result["issues"])


def test_a_root_entry_is_not_treated_as_a_missing_file(tmp_path):
    root = make_tree(tmp_path)
    sw = root / "web" / "web" / "sw.js"
    sw.write_text(
        sw.read_text(encoding="utf-8") + 'const SHELL = ["/"];\n',
        encoding="utf-8",
    )

    assert check_versions.check(root)["ok"] is True


def test_existing_precache_targets_pass(tmp_path):
    root = make_tree(tmp_path)
    assets = root / "web" / "web" / "assets" / "js"
    assets.mkdir(parents=True)
    (assets / "app.js").write_text("ok", encoding="utf-8")
    sw = root / "web" / "web" / "sw.js"
    sw.write_text(
        sw.read_text(encoding="utf-8") + 'const SHELL = ["/assets/js/app.js?v=1.0.0"];\n',
        encoding="utf-8",
    )

    assert check_versions.check(root)["ok"] is True


def test_a_stale_download_page_fallback_is_reported(tmp_path):
    root = make_tree(tmp_path)
    latest = root / "web" / "web" / "downloads" / "latest.json"
    data = json.loads(latest.read_text(encoding="utf-8"))
    data.update({"sha256": "a" * 64, "date": "2026-10-31", "size": 1048576})
    latest.write_text(json.dumps(data), encoding="utf-8")
    page = root / "web" / "web" / "download.html"
    page.write_text(
        '<a href="/downloads/DreamAI-Setup-9.9.9.exe">v9.9.9</a> 1.0 MB 2020-01-01 deadbeef',
        encoding="utf-8",
    )

    result = check_versions.check(root)

    assert any("fallback link" in item for item in result["issues"])
    assert any("fallback sha256" in item for item in result["issues"])
    assert any("fallback date" in item for item in result["issues"])


def test_a_matching_download_page_fallback_passes(tmp_path):
    root = make_tree(tmp_path)
    latest = root / "web" / "web" / "downloads" / "latest.json"
    data = json.loads(latest.read_text(encoding="utf-8"))
    data.update(
        {
            "file": "DreamAI-Setup-1.3.0.exe",
            "sha256": "a" * 64,
            "date": "2026-10-31",
            "size": 1048576,
        }
    )
    latest.write_text(json.dumps(data), encoding="utf-8")
    (root / "web" / "web" / "download.html").write_text(
        'href="/downloads/DreamAI-Setup-1.3.0.exe" v1.3.0 '
        + "a" * 64
        + " 2026-10-31 1.0 MB",
        encoding="utf-8",
    )

    assert check_versions.check(root)["ok"] is True


def test_an_empty_tree_reports_missing_files_without_crashing(tmp_path):
    result = check_versions.check(tmp_path)

    assert result["ok"] is False
    assert any("missing file" in item for item in result["issues"])


def test_the_cli_passes_for_the_published_tree():
    done = subprocess.run([sys.executable, str(TOOL)], capture_output=True, text=True, check=False)

    assert done.returncode == 0
    assert "versions: OK" in done.stdout


def test_the_cli_emits_parseable_json(tmp_path):
    root = make_tree(tmp_path)

    done = subprocess.run(
        [sys.executable, str(TOOL), "--root", str(root), "--json"],
        capture_output=True,
        text=True,
        check=False,
    )

    payload = json.loads(done.stdout)
    assert done.returncode == 0
    assert payload["versions"]["server"] == "1.5.0"
