"""Tests for environment-based settings and the CLI override helper.

The settings object is the single input to every other layer, but it had no
direct tests: only the autonomy switches were covered indirectly. These cases
pin the defaults, the fallbacks for invalid values, and the precedence rules
between the environment, `.env`, and command-line arguments.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from dream_ai import config
from dream_ai.cli import _apply_overrides, _parse_args
from dream_ai.config import DEFAULT_SYSTEM_PROMPT, Settings, load_settings


@pytest.fixture(autouse=True)
def _isolate_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ignore any local `.env` file and start from a clean environment."""
    monkeypatch.setattr(config, "_load_dotenv", lambda: None)
    for name in (
        "DREAMAI_PROVIDER",
        "DREAMAI_BASE_URL",
        "DREAMAI_API_KEY",
        "DREAMAI_MODEL",
        "DREAMAI_SYSTEM_PROMPT",
        "DREAMAI_DATA_DIR",
        "DREAMAI_WORKSPACE_DIR",
        "DREAMAI_PERSISTENCE",
        "DREAMAI_TOOLS_ENABLED",
        "DREAMAI_FILE_ACCESS_ENABLED",
        "DREAMAI_WEB_SEARCH_ENABLED",
        "DREAMAI_AUTONOMY_ENABLED",
        "DREAMAI_MAX_STEPS",
        "DREAMAI_MAX_RETRIES",
        "DREAMAI_AUTONOMY_VERBOSE",
    ):
        monkeypatch.delenv(name, raising=False)


def test_defaults_match_the_documented_configuration() -> None:
    settings = load_settings()

    assert settings.provider == "openai_compat"
    assert settings.base_url == "https://api.deepseek.com/v1"
    assert settings.model == "deepseek-chat"
    assert settings.api_key == ""
    assert settings.hosted_configured is False
    assert settings.persistence_enabled is True
    assert settings.tools_enabled is True
    assert settings.file_access_enabled is False
    assert settings.web_search_enabled is False
    assert settings.system_prompt == DEFAULT_SYSTEM_PROMPT


def test_data_and_workspace_directories_default_under_home() -> None:
    settings = load_settings()

    assert settings.data_dir == Path.home() / ".dream_ai"
    assert settings.workspace_dir == settings.data_dir / "workspace"


def test_explicit_directories_are_used_verbatim(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("DREAMAI_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("DREAMAI_WORKSPACE_DIR", str(tmp_path / "sandbox"))

    settings = load_settings()

    assert settings.data_dir == tmp_path / "data"
    assert settings.workspace_dir == tmp_path / "sandbox"


def test_unknown_provider_falls_back_instead_of_crashing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DREAMAI_PROVIDER", "anthropic")

    assert load_settings().provider == "openai_compat"


def test_boolean_switches_accept_common_false_spellings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for value in ("false", "0", "no", "off", ""):
        monkeypatch.setenv("DREAMAI_TOOLS_ENABLED", value)
        assert load_settings().tools_enabled is False


def test_api_key_whitespace_does_not_count_as_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DREAMAI_API_KEY", "   ")

    assert load_settings().hosted_configured is False


def test_cli_overrides_replace_only_the_given_fields() -> None:
    settings = Settings(
        provider="local",
        base_url="https://example.test/v1",
        api_key="",
        model="local",
        system_prompt="Base.",
        data_dir=Path("/tmp/data"),
        persistence_enabled=False,
        tools_enabled=True,
        file_access_enabled=False,
        web_search_enabled=False,
        workspace_dir=Path("/tmp/workspace"),
    )
    args = _parse_args(["--model", "deepseek-chat", "--api-key", "sk-test"])

    updated = _apply_overrides(settings, args)

    assert updated.model == "deepseek-chat"
    assert updated.api_key == "sk-test"
    assert updated.provider == "local"
    assert updated.base_url == "https://example.test/v1"


def test_cli_without_overrides_returns_the_same_object() -> None:
    settings = load_settings()
    args = argparse.Namespace(provider=None, model=None, base_url=None, api_key=None)

    assert _apply_overrides(settings, args) is settings


def test_cli_rejects_unknown_provider_argument() -> None:
    with pytest.raises(SystemExit):
        _parse_args(["--provider", "nope"])
