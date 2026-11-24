"""A new environment variable must arrive with its documentation."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "web" / "tools" / "check_env_docs.py"

sys.path.insert(0, str(TOOL.parent))
import check_env_docs  # noqa: E402

HEADER = "# Reference\n\n## 1. Settings\n\n"


def make_files(tmp_path: Path, config: str, document: str):
    config_path = tmp_path / "config.py"
    doc_path = tmp_path / "CONFIGURATION.md"
    config_path.write_text(config, encoding="utf-8")
    doc_path.write_text(document, encoding="utf-8")
    return config_path, doc_path


def test_the_published_reference_covers_every_server_variable():
    result = check_env_docs.check()

    assert result["ok"] is True
    assert result["variables"] >= 40
    assert result["missing"] == []
    assert result["misplaced"] == []


def test_a_new_variable_without_docs_is_reported(tmp_path):
    config, doc = make_files(
        tmp_path,
        'DREAMAI_FREE_API_KEY = _env("DREAMAI_FREE_API_KEY")\n'
        'DREAMAI_BRAND_NEW = _env("DREAMAI_BRAND_NEW")\n',
        HEADER + "`DREAMAI_FREE_API_KEY`\n",
    )

    result = check_env_docs.check(config, doc)

    assert result["ok"] is False
    assert result["missing"] == ["DREAMAI_BRAND_NEW"]


def test_an_unknown_variable_in_the_main_section_is_reported(tmp_path):
    config, doc = make_files(
        tmp_path,
        'DREAMAI_FREE_API_KEY = _env("DREAMAI_FREE_API_KEY")\n',
        HEADER + "`DREAMAI_FREE_API_KEY` and `DREAMAI_CLIENT_ONLY`\n",
    )

    result = check_env_docs.check(config, doc)

    assert "DREAMAI_CLIENT_ONLY" in result["misplaced"]


def test_client_variables_are_allowed_in_the_final_section(tmp_path):
    config, doc = make_files(
        tmp_path,
        'DREAMAI_FREE_API_KEY = _env("DREAMAI_FREE_API_KEY")\n',
        HEADER
        + "`DREAMAI_FREE_API_KEY`\n\n"
        + check_env_docs.OUT_OF_SCOPE
        + "\n\n`DREAMAI_CLIENT_ONLY`\n",
    )

    assert check_env_docs.check(config, doc)["ok"] is True


def test_a_server_variable_only_in_the_final_section_is_reported(tmp_path):
    config, doc = make_files(
        tmp_path,
        'DREAMAI_FREE_API_KEY = _env("DREAMAI_FREE_API_KEY")\n',
        HEADER + check_env_docs.OUT_OF_SCOPE + "\n\n`DREAMAI_FREE_API_KEY`\n",
    )

    assert "DREAMAI_FREE_API_KEY" in check_env_docs.check(config, doc)["misplaced"]


def test_a_changed_default_is_reported(tmp_path):
    config, doc = make_files(
        tmp_path,
        'DREAMAI_CACHE_TTL = _env_float("DREAMAI_CACHE_TTL", 300.0)\n',
        HEADER + "| `DREAMAI_CACHE_TTL` | `120` 秒 | old value |\n",
    )

    result = check_env_docs.check(config, doc)

    assert result["ok"] is False
    assert any("DREAMAI_CACHE_TTL" in item for item in result["defaultDrift"])


def test_a_multiplication_default_matches_its_expanded_value(tmp_path):
    config, doc = make_files(
        tmp_path,
        'DREAMAI_CACHE_MAX_BYTES = _env_int("DREAMAI_CACHE_MAX_BYTES", 4 * 1024 * 1024)\n',
        HEADER + "| `DREAMAI_CACHE_MAX_BYTES` | `4194304` | bytes |\n",
    )

    assert check_env_docs.check(config, doc)["ok"] is True


def test_missing_files_fail_closed(tmp_path):
    result = check_env_docs.check(tmp_path / "none.py", tmp_path / "none.md")

    assert result["ok"] is False
    assert result["variables"] == 0


def test_the_cli_succeeds_for_the_published_reference():
    done = subprocess.run([sys.executable, str(TOOL)], capture_output=True, text=True, check=False)

    assert done.returncode == 0
    assert "env docs: OK" in done.stdout


def test_the_cli_emits_parseable_json(tmp_path):
    config, doc = make_files(tmp_path, 'DREAMAI_A = _env("DREAMAI_A")\n', HEADER + "`DREAMAI_A`\n")

    done = subprocess.run(
        [sys.executable, str(TOOL), "--config", str(config), "--document", str(doc), "--json"],
        capture_output=True,
        text=True,
        check=False,
    )

    payload = json.loads(done.stdout)
    assert done.returncode == 0
    assert payload["variables"] == 1
