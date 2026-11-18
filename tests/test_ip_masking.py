"""Log lines identify a network, not a machine."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

WEB = str(Path(__file__).resolve().parent.parent / "web")
if WEB not in sys.path:
    sys.path.insert(0, WEB)

from app.telemetry import mask_ip  # noqa: E402


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1.2.3.4", "1.2.x.x"),
        ("192.168.1.77", "192.168.x.x"),
        ("1.2.3.4:5678", "1.2.x.x"),
        ("  8.8.8.8  ", "8.8.x.x"),
        ("2001:db8:85a3::1", "2001:db8::"),
        ("[2001:db8::1]:8080", "2001:db8::"),
        ("unknown", "unknown"),
        ("", "unknown"),
        ("example.com", "example.com"),
    ],
)
def test_ip_masking(raw, expected):
    assert mask_ip(raw) == expected


def test_two_hosts_on_one_network_share_a_log_label():
    assert mask_ip("10.20.30.40") == mask_ip("10.20.99.1")


def test_an_invalid_octet_is_not_treated_as_an_ip():
    assert mask_ip("999.1.2.3") == "999.1.2.3"
