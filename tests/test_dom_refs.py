"""A selector with no matching node is a feature that silently stopped working."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "web" / "tools" / "check_dom_refs.py"

sys.path.insert(0, str(TOOL.parent))
import check_dom_refs  # noqa: E402


def make_tree(tmp_path: Path, page_ids: list[str], script_refs: list[str], script_body: str = "") -> Path:
    scripts = tmp_path / "assets" / "js"
    scripts.mkdir(parents=True)
    ids = "".join(f'<div id="{item}"></div>\n' for item in page_ids)
    (tmp_path / "index.html").write_text(f"<body>{ids}</body>", encoding="utf-8")
    refs = "".join(
        f'document.querySelector("#{item}");\n' for item in script_refs
    )
    (scripts / "app.js").write_text(refs + script_body, encoding="utf-8")
    return tmp_path


def test_the_published_scripts_resolve_their_selectors():
    result = check_dom_refs.check()

    assert result["ok"] is True
    assert result["unresolved"] == []


def test_a_selector_with_no_node_is_reported(tmp_path):
    site = make_tree(tmp_path, ["present"], ["missing"])

    result = check_dom_refs.check(site)

    assert result["ok"] is False
    assert any("app.js: #missing" in item for item in result["unresolved"])


def test_a_getelementbyid_reference_is_checked(tmp_path):
    site = make_tree(tmp_path, [], [])
    (site / "assets" / "js" / "app.js").write_text(
        'document.getElementById("gone");', encoding="utf-8"
    )

    result = check_dom_refs.check(site)

    assert any("#gone" in item for item in result["unresolved"])


def test_an_id_created_by_script_is_accepted(tmp_path):
    site = make_tree(
        tmp_path,
        [],
        ["dynamic"],
        'container.innerHTML = \'<div id="dynamic"></div>\';',
    )

    assert check_dom_refs.check(site)["ok"] is True


def test_a_declared_id_satisfies_the_selector(tmp_path):
    site = make_tree(tmp_path, ["ok"], ["ok"])

    assert check_dom_refs.check(site)["ok"] is True


def test_an_allowed_injected_id_is_reported_with_its_reason(tmp_path):
    site = make_tree(tmp_path, [], ["updateGate"])

    result = check_dom_refs.check(site)

    assert result["ok"] is True
    assert "updateGate" in result["allowedInjected"]
    assert "updateGate" in result["reasons"]


def test_extra_allowlist_entries_can_be_supplied(tmp_path):
    site = make_tree(tmp_path, [], ["nativeThing"])

    result = check_dom_refs.check(site, extra={"nativeThing": "native shell"})

    assert result["ok"] is True
    assert result["reasons"]["nativeThing"] == "native shell"


def test_the_cli_passes_for_the_published_site():
    done = subprocess.run(
        [sys.executable, str(TOOL)], capture_output=True, text=True, check=False
    )

    assert done.returncode == 0
    assert "dom refs: OK" in done.stdout


def test_the_cli_emits_parseable_json(tmp_path):
    site = make_tree(tmp_path, ["ok"], ["ok"])

    done = subprocess.run(
        [sys.executable, str(TOOL), "--site", str(site), "--json"],
        capture_output=True,
        text=True,
        check=False,
    )

    payload = json.loads(done.stdout)
    assert done.returncode == 0
    assert payload["ok"] is True
    assert "declaredIds" in payload
