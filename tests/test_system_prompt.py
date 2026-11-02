"""The composed default prompt is what every surface actually sends."""

from __future__ import annotations

import re

from dream_ai.config import DEFAULT_SYSTEM_PROMPT
from dream_ai.identity import OWNER


def test_prompt_names_the_owner_for_every_role():
    for role in OWNER.roles:
        assert role in DEFAULT_SYSTEM_PROMPT


def test_prompt_carries_style_and_privacy():
    assert "回答风格" in DEFAULT_SYSTEM_PROMPT
    assert "信息密度" in DEFAULT_SYSTEM_PROMPT
    assert "隐私与边界" in DEFAULT_SYSTEM_PROMPT


def test_prompt_keeps_the_english_baseline():
    assert "You are Dream AI" in DEFAULT_SYSTEM_PROMPT


def test_prompt_stays_within_a_sane_size():
    # Every turn pays for this prompt; a runaway block would cost tokens on each
    # request, so the ceiling is part of the contract.
    assert len(DEFAULT_SYSTEM_PROMPT) < 2500


def test_prompt_does_not_contain_contact_details():
    # Contacts live in the private dossier, not in the prompt that a public
    # surface sends to a provider on every turn.
    assert not re.search(r"1[3-9]\d{9}", DEFAULT_SYSTEM_PROMPT)
    assert not re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", DEFAULT_SYSTEM_PROMPT)
