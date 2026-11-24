"""An unindexed ADR is effectively lost."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "web" / "tools" / "check_docs_index.py"

sys.path.insert(0, str(TOOL.parent))
import check_docs_index  # noqa: E402


def make_tree(tmp_path: Path) -> Path:
    docs = tmp_path / "docs"
    adr = docs / "adr"
    adr.mkdir(parents=True)
    (adr / "0001-first.md").write_text("# first", encoding="utf-8")
    (adr / "README.md").write_text(
        "| ADR | Title |\n|---|---|\n| [0001](./0001-first.md) | First |\n",
        encoding="utf-8",
    )
    (docs / "GUIDE.md").write_text("# guide", encoding="utf-8")
    (docs / "README.md").write_text(
        "| Document | Contents |\n|---|---|\n| [GUIDE.md](./GUIDE.md) | Guide |\n",
        encoding="utf-8",
    )
    return tmp_path


def test_the_published_indexes_are_complete():
    result = check_docs_index.check()

    assert result["ok"] is True
    assert result["adr"]["files"] >= 20
    assert result["docs"]["files"] >= 10


def test_an_unindexed_adr_is_reported(tmp_path):
    root = make_tree(tmp_path)
    (root / "docs" / "adr" / "0002-second.md").write_text("# second", encoding="utf-8")

    result = check_docs_index.check_adr_index(root)

    assert result["ok"] is False
    assert "0002-second.md" in result["missing"]


def test_a_broken_adr_link_is_reported(tmp_path):
    root = make_tree(tmp_path)
    index = root / "docs" / "adr" / "README.md"
    index.write_text(
        index.read_text(encoding="utf-8") + "| [x](./9999-gone.md) | |\n", encoding="utf-8"
    )

    assert "9999-gone.md" in check_docs_index.check_adr_index(root)["broken"]


def test_a_gap_in_adr_numbering_is_reported(tmp_path):
    root = make_tree(tmp_path)
    (root / "docs" / "adr" / "0003-third.md").write_text("# third", encoding="utf-8")

    result = check_docs_index.check_adr_index(root)

    assert 2 in result["gaps"]
    assert result["ok"] is False


def test_duplicate_adr_numbers_are_reported(tmp_path):
    root = make_tree(tmp_path)
    (root / "docs" / "adr" / "0001-also-first.md").write_text("# other", encoding="utf-8")

    result = check_docs_index.check_adr_index(root)

    assert 1 in result["duplicates"]
    assert result["ok"] is False


def test_the_published_adr_sequence_has_no_gaps():
    assert check_docs_index.check_adr_index()["gaps"] == []
    assert check_docs_index.check_adr_index()["duplicates"] == []


def test_an_unindexed_document_is_reported(tmp_path):
    root = make_tree(tmp_path)
    (root / "docs" / "SETUP.md").write_text("# setup", encoding="utf-8")

    result = check_docs_index.check_docs_index(root)

    assert result["ok"] is False
    assert "SETUP.md" in result["missing"]


def test_the_adr_directory_itself_is_not_treated_as_a_document(tmp_path):
    root = make_tree(tmp_path)

    assert check_docs_index.check_docs_index(root)["ok"] is True


def test_a_missing_index_fails_closed(tmp_path):
    root = make_tree(tmp_path)
    (root / "docs" / "README.md").unlink()

    assert check_docs_index.check_docs_index(root)["ok"] is False


def test_the_cli_succeeds_for_the_published_indexes():
    done = subprocess.run([sys.executable, str(TOOL)], capture_output=True, text=True, check=False)

    assert done.returncode == 0
    assert "docs index: OK" in done.stdout


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
    assert set(payload) == {"adr", "docs", "ok"}
