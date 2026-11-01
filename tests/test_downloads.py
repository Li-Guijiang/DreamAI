"""The release manifest must describe the build, not a memory of it."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location(
    "make_downloads", ROOT / "web" / "tools" / "make_downloads.py"
)
make_downloads = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(make_downloads)


def test_manifest_hashes_the_installer(tmp_path: Path) -> None:
    installer = tmp_path / "DreamAI-Setup-9.9.9.exe"
    installer.write_bytes(b"pretend installer payload")

    manifest = make_downloads.build_manifest("9.9.9", installer, "notes")

    assert manifest["version"] == "9.9.9"
    assert manifest["file"] == "DreamAI-Setup-9.9.9.exe"
    assert manifest["size"] == len(b"pretend installer payload")
    assert len(manifest["sha256"]) == 64
    assert manifest["sha512"]
    assert "pending" not in manifest


def test_missing_installer_for_a_known_version_keeps_the_recorded_hashes(tmp_path: Path) -> None:
    previous = {
        "version": "9.9.9",
        "file": "DreamAI-Setup-9.9.9.exe",
        "size": 123,
        "sha256": "a" * 64,
        "date": "2026-10-31",
    }

    manifest = make_downloads.build_manifest("9.9.9", tmp_path / "absent.exe", "", previous)

    assert manifest["sha256"] == "a" * 64
    assert manifest["size"] == 123
    assert manifest["date"] == "2026-10-31"
    assert "pending" not in manifest


def test_missing_installer_for_a_new_version_is_pending(tmp_path: Path) -> None:
    previous = {"version": "1.0.0", "size": 1, "sha256": "b" * 64}

    manifest = make_downloads.build_manifest("9.9.9", tmp_path / "absent.exe", "", previous)

    assert manifest["pending"] is True
    assert manifest["sha256"] == ""


def test_committed_manifest_matches_package_version() -> None:
    version = json.loads((ROOT / "desktop" / "package.json").read_text(encoding="utf-8"))["version"]
    manifest = json.loads(
        (ROOT / "web" / "web" / "downloads" / "latest.json").read_text(encoding="utf-8")
    )

    assert manifest["version"] == version, "latest.json and package.json disagree"
    assert manifest["file"] == f"DreamAI-Setup-{version}.exe"


def test_committed_manifest_is_installable_or_explicitly_pending() -> None:
    manifest = json.loads(
        (ROOT / "web" / "web" / "downloads" / "latest.json").read_text(encoding="utf-8")
    )

    if manifest.get("pending"):
        assert manifest["sha256"] == ""
        return
    assert manifest["size"] > 0
    assert len(manifest["sha256"]) == 64
