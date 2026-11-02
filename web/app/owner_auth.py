"""Owner-session cookie for the private dossier commands.

There is no account system on the public chat. The owner proves possession of a
high-entropy token once by sending ``【主人验证】<token>``; the server then sets a
signed, HttpOnly, SameSite=Lax cookie. The token and signing secret come from
the server environment and are never committed.

The cookie only unlocks the private dossier. It does not change the model,
identity rules, or public quota. The public chat never receives the dossier.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time

COOKIE_NAME = "dreamai_owner"
TOKEN_ENV = "DREAMAI_OWNER_TOKEN"
SECRET_ENV = "DREAMAI_OWNER_SECRET"
MAX_AGE = 30 * 24 * 60 * 60


def _token() -> str:
    return os.environ.get(TOKEN_ENV, "").strip()


def _secret() -> str:
    return os.environ.get(SECRET_ENV, "").strip()


def configured() -> bool:
    return bool(_token() and _secret())


def verify_token(value: str) -> bool:
    expected = _token()
    if not expected or not value:
        return False
    return hmac.compare_digest(expected, value.strip())


def issue_cookie(now: int | None = None) -> str | None:
    secret = _secret()
    if not secret:
        return None
    expires = int(now if now is not None else time.time()) + MAX_AGE
    payload = str(expires)
    signature = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def verify_cookie(value: str, now: int | None = None) -> bool:
    secret = _secret()
    if not secret or not value or "." not in value:
        return False
    raw_expires, signature = value.rsplit(".", 1)
    try:
        expires = int(raw_expires)
    except ValueError:
        return False
    if expires < (now if now is not None else time.time()):
        return False
    payload = str(expires)
    expected = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def is_owner(request) -> bool:
    """True when a request carries a valid signed owner cookie."""
    value = request.cookies.get(COOKIE_NAME, "")
    return verify_cookie(value)


def cookie_header(request) -> str | None:
    value = issue_cookie()
    if not value:
        return None
    secure = request.headers.get("x-forwarded-proto", request.url.scheme) == "https"
    parts = [
        f"{COOKIE_NAME}={value}",
        "Path=/",
        f"Max-Age={MAX_AGE}",
        "HttpOnly",
        "SameSite=Lax",
    ]
    if secure:
        parts.append("Secure")
    return "; ".join(parts)
