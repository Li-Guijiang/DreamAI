"""Owner cookie checks must refuse impossible expiries."""

from __future__ import annotations

import sys
import time
from pathlib import Path

WEB = str(Path(__file__).resolve().parent.parent / "web")
if WEB not in sys.path:
    sys.path.insert(0, WEB)

from app import owner_auth  # noqa: E402


def _signed(expires: int) -> str:
    import hashlib
    import hmac

    secret = "test-secret"
    signature = hmac.new(secret.encode(), str(expires).encode(), hashlib.sha256).hexdigest()
    return f"{expires}.{signature}"


def test_a_fresh_cookie_is_accepted(monkeypatch):
    monkeypatch.setenv(owner_auth.SECRET_ENV, "test-secret")
    now = int(time.time())

    assert owner_auth.verify_cookie(owner_auth.issue_cookie(now), now=now)


def test_an_expired_cookie_is_refused(monkeypatch):
    monkeypatch.setenv(owner_auth.SECRET_ENV, "test-secret")
    now = int(time.time())

    assert not owner_auth.verify_cookie(_signed(now - 1), now=now)


def test_a_zero_or_negative_expiry_is_refused(monkeypatch):
    monkeypatch.setenv(owner_auth.SECRET_ENV, "test-secret")

    assert not owner_auth.verify_cookie(_signed(0), now=100)
    assert not owner_auth.verify_cookie(_signed(-1), now=100)


def test_a_forged_signature_is_refused(monkeypatch):
    monkeypatch.setenv(owner_auth.SECRET_ENV, "test-secret")
    far_future = int(time.time()) + 99999

    assert not owner_auth.verify_cookie(f"{far_future}.deadbeef")


def test_a_cookie_without_a_secret_cannot_be_verified(monkeypatch):
    monkeypatch.delenv(owner_auth.SECRET_ENV, raising=False)

    assert not owner_auth.verify_cookie(_signed(9999999999))
