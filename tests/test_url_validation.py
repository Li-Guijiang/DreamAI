"""A mistyped base URL must be reported before the first request fails."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))

from app.validation import check_base_url  # noqa: E402


@pytest.mark.parametrize(
    "value",
    [
        "",
        "https://api.example.com/v1",
        "http://localhost:8000",
        "HTTPS://EXAMPLE.COM",
        "https://127.0.0.1:11434/v1/",
    ],
)
def test_usable_urls_have_no_finding(value):
    assert check_base_url(value) is None


@pytest.mark.parametrize(
    ("value", "reason"),
    [
        ("api.example.com/v1", "scheme"),
        ("ftp://api.example.com", "scheme"),
        ("https://", "host"),
        ("https://api example.com/v1", "whitespace"),
        ("https://user:pass@api.example.com/v1", "credentials"),
        ("https://api.example.com/v1?key=x", "query"),
        ("https://api.example.com/v1#frag", "fragment"),
        ("https://[bad", "parsed"),
    ],
)
def test_unusable_urls_name_the_reason(value, reason):
    assert reason in check_base_url(value)


def test_the_reason_never_echoes_a_credential():
    reason = check_base_url("https://user:SUPER-SECRET@host.test/v1")

    assert reason is not None
    assert "SUPER-SECRET" not in reason
    assert "user" not in reason
