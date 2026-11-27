"""A client must not be able to choose its own rate-limit identity."""

from __future__ import annotations

import dataclasses
import importlib
import sys
from pathlib import Path

import pytest

pytest.importorskip("fastapi", reason="web dependencies are not installed")
WEB = str(Path(__file__).resolve().parent.parent / "web")
if WEB not in sys.path:
    sys.path.insert(0, WEB)

from fastapi import Request  # noqa: E402


def make_request(peer: str, headers: dict[str, str] | None = None) -> Request:
    raw = [(key.lower().encode(), value.encode()) for key, value in (headers or {}).items()]
    scope = {
        "type": "http",
        "client": (peer, 12345) if peer else None,
        "headers": raw,
    }
    return Request(scope)


@pytest.fixture()
def main_module(monkeypatch):
    monkeypatch.syspath_prepend(WEB)
    module = importlib.import_module("app.main")
    monkeypatch.setattr(
        module, "settings", dataclasses.replace(module.settings, trusted_proxies=())
    )
    return module


def test_the_direct_peer_is_used_by_default(main_module):
    request = make_request("203.0.113.7")

    assert main_module.client_ip(request) == "203.0.113.7"


def test_a_forged_real_ip_header_is_ignored(main_module):
    request = make_request("203.0.113.7", {"X-Real-IP": "198.51.100.9"})

    assert main_module.client_ip(request) == "203.0.113.7"


def test_a_forged_forwarded_for_header_is_ignored(main_module):
    request = make_request("203.0.113.7", {"X-Forwarded-For": "198.51.100.9"})

    assert main_module.client_ip(request) == "203.0.113.7"


def test_many_forged_identities_do_not_bypass_the_limiter(main_module):
    seen = {
        main_module.client_ip(make_request("203.0.113.7", {"X-Forwarded-For": f"198.51.100.{n}"}))
        for n in range(1, 40)
    }

    assert seen == {"203.0.113.7"}


def test_a_trusted_proxy_header_is_honoured(main_module, monkeypatch):
    monkeypatch.setattr(
        main_module,
        "settings",
        dataclasses.replace(main_module.settings, trusted_proxies=("127.0.0.1",)),
    )

    request = make_request("127.0.0.1", {"X-Real-IP": "198.51.100.9"})
    assert main_module.client_ip(request) == "198.51.100.9"

    forwarded = make_request("127.0.0.1", {"X-Forwarded-For": "198.51.100.8, 10.0.0.1"})
    assert main_module.client_ip(forwarded) == "198.51.100.8"


def test_an_untrusted_peer_cannot_use_forwarding_headers(main_module, monkeypatch):
    monkeypatch.setattr(
        main_module,
        "settings",
        dataclasses.replace(main_module.settings, trusted_proxies=("127.0.0.1",)),
    )

    request = make_request("203.0.113.7", {"X-Real-IP": "198.51.100.9"})

    assert main_module.client_ip(request) == "203.0.113.7"


def test_a_cidr_range_can_be_trusted(main_module, monkeypatch):
    monkeypatch.setattr(
        main_module,
        "settings",
        dataclasses.replace(main_module.settings, trusted_proxies=("10.0.0.0/8",)),
    )

    request = make_request("10.1.2.3", {"X-Forwarded-For": "198.51.100.9"})

    assert main_module.client_ip(request) == "198.51.100.9"


def test_an_invalid_proxy_entry_does_not_crash(main_module, monkeypatch):
    monkeypatch.setattr(
        main_module,
        "settings",
        dataclasses.replace(main_module.settings, trusted_proxies=("not-an-ip",)),
    )

    assert main_module.client_ip(make_request("203.0.113.7")) == "203.0.113.7"


def test_a_missing_peer_is_reported_as_unknown(main_module):
    assert main_module.client_ip(make_request("")) == "unknown"


def test_the_default_configuration_trusts_no_proxy(monkeypatch):
    monkeypatch.syspath_prepend(WEB)
    import app.config as config

    monkeypatch.delenv("DREAMAI_TRUSTED_PROXIES", raising=False)
    assert config.load_settings().trusted_proxies == ()

    monkeypatch.setenv("DREAMAI_TRUSTED_PROXIES", "127.0.0.1, 10.0.0.0/8")
    assert config.load_settings().trusted_proxies == ("127.0.0.1", "10.0.0.0/8")
