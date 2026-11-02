"""The web service must inherit the identity without a parallel copy of it."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_web_service_builds_its_prompt_from_settings():
    source = (ROOT / "web" / "app" / "main.py").read_text(encoding="utf-8")

    assert "system_prompt = settings.system_prompt" in source, (
        "the web service must take the prompt from settings, or it will drift "
        "away from the identity block the CLI uses"
    )


def test_web_service_does_not_hardcode_an_owner_name():
    source = (ROOT / "web" / "app" / "main.py").read_text(encoding="utf-8")

    # A second copy of the name is a second place to forget to update.
    assert not re.search(r"李贵江|Li Guijiang", source), (
        "the owner name belongs in dream_ai/identity.py only"
    )


def test_settings_default_prompt_is_the_identity_prompt():
    from dream_ai.config import DEFAULT_SYSTEM_PROMPT, load_settings

    settings = load_settings()

    assert settings.system_prompt == DEFAULT_SYSTEM_PROMPT
    assert "李贵江" in settings.system_prompt
