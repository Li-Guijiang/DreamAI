"""Model ids are sent to providers verbatim; reject impossible ones at boot."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))

from app.validation import check_model_id  # noqa: E402


@pytest.mark.parametrize(
    "value",
    ["glm-4-flash", "deepseek-chat", "gpt-4o", "my.gateway/model:v2", "m" * 128],
)
def test_usable_model_ids_have_no_finding(value):
    assert check_model_id(value) is None


@pytest.mark.parametrize(
    ("value", "reason"),
    [
        ("", "empty"),
        ("   ", "empty"),
        ("a b", "whitespace"),
        ("a\tb", "whitespace"),
        ("x" * 129, "128"),
        ("a\x00b", "control"),
        ("a\x7fb", "control"),
    ],
)
def test_impossible_model_ids_name_the_reason(value, reason):
    assert reason in check_model_id(value)


def test_the_reason_does_not_echo_the_id():
    assert "SECRET-ID" not in check_model_id("SECRET-ID with space")
