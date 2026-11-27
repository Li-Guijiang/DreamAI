"""Trust is decided by the peer, never by the header itself."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))

from app.peer import forwarded_ip, forwarded_proto, peer_is_trusted  # noqa: E402


def test_no_allowlist_means_no_trust():
    assert peer_is_trusted("127.0.0.1", ()) is False


def test_an_exact_ip_can_be_trusted():
    assert peer_is_trusted("127.0.0.1", ("127.0.0.1",)) is True


def test_a_cidr_range_can_be_trusted():
    assert peer_is_trusted("10.2.3.4", ("10.0.0.0/8",)) is True


def test_an_address_outside_the_range_is_not_trusted():
    assert peer_is_trusted("192.168.1.1", ("10.0.0.0/8",)) is False


def test_an_ipv6_peer_can_be_trusted():
    assert peer_is_trusted("::1", ("::1",)) is True


def test_an_invalid_peer_is_not_trusted():
    assert peer_is_trusted("not-an-ip", ("127.0.0.1",)) is False


def test_an_invalid_range_does_not_trust_anything():
    assert peer_is_trusted("127.0.0.1", ("garbage",)) is False


def test_forwarded_ip_is_none_for_an_untrusted_peer():
    headers = {"x-real-ip": "198.51.100.9"}

    assert forwarded_ip("203.0.113.7", headers, ("127.0.0.1",)) is None


def test_forwarded_ip_uses_real_ip_header_first():
    headers = {"x-real-ip": "198.51.100.9", "x-forwarded-for": "198.51.100.8"}

    assert forwarded_ip("127.0.0.1", headers, ("127.0.0.1",)) == "198.51.100.9"


def test_forwarded_ip_takes_the_first_chain_entry():
    headers = {"x-forwarded-for": "198.51.100.8, 10.0.0.1, 10.0.0.2"}

    assert forwarded_ip("127.0.0.1", headers, ("127.0.0.1",)) == "198.51.100.8"


def test_forwarded_ip_strips_whitespace():
    headers = {"x-forwarded-for": "  198.51.100.8  , 10.0.0.1"}

    assert forwarded_ip("127.0.0.1", headers, ("127.0.0.1",)) == "198.51.100.8"


def test_forwarded_ip_is_none_without_headers_from_a_trusted_peer():
    assert forwarded_ip("127.0.0.1", {}, ("127.0.0.1",)) is None


def test_forwarded_proto_is_none_for_an_untrusted_peer():
    headers = {"x-forwarded-proto": "http"}

    assert forwarded_proto("203.0.113.7", headers, ("127.0.0.1",)) is None


def test_forwarded_proto_from_a_trusted_peer():
    headers = {"x-forwarded-proto": "https"}

    assert forwarded_proto("127.0.0.1", headers, ("127.0.0.1",)) == "https"


def test_header_names_are_expected_in_lowercase():
    headers = {"X-Real-IP": "198.51.100.9"}

    # Callers normalise header names; documented by this test.
    assert forwarded_ip("127.0.0.1", headers, ("127.0.0.1",)) is None
