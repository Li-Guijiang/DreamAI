"""The link reader used to return 502 for every request."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

pytest.importorskip("fastapi", reason="web dependencies are not installed")
WEB = str(Path(__file__).resolve().parent.parent / "web")
if WEB not in sys.path:
    sys.path.insert(0, WEB)

from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture()
def main_module(monkeypatch):
    monkeypatch.syspath_prepend(WEB)
    return importlib.import_module("app.main")


def test_an_empty_url_returns_a_validation_error_not_502(main_module):
    with TestClient(main_module.app) as client:
        response = client.get("/api/read", params={"url": ""})

    assert response.status_code == 400
    assert response.json()["code"] == "read_failed"


def test_a_non_http_url_returns_a_validation_error(main_module):
    with TestClient(main_module.app) as client:
        response = client.get("/api/read", params={"url": "file:///etc/passwd"})

    assert response.status_code == 400
    assert "http" in response.json()["error"]


def test_a_private_address_is_refused(main_module):
    with TestClient(main_module.app) as client:
        response = client.get("/api/read", params={"url": "http://127.0.0.1/admin"})

    assert response.status_code == 400
    assert "公网" in response.json()["error"]


def test_a_nonstandard_port_is_refused(main_module):
    with TestClient(main_module.app) as client:
        response = client.get("/api/read", params={"url": "https://example.com:8443/"})

    assert response.status_code == 400
    assert "端口" in response.json()["error"]


def test_a_url_with_credentials_is_refused(main_module):
    with TestClient(main_module.app) as client:
        response = client.get("/api/read", params={"url": "https://user:pass@example.com/"})

    assert response.status_code == 400
    assert "账号" in response.json()["error"]


def test_the_limiter_is_shared_with_nothing_else(main_module):
    assert main_module.reader_limiter is not main_module.limiter
    assert main_module.reader_limiter._limit == 20


def test_a_rate_limited_request_returns_429_with_retry_after(main_module, monkeypatch):
    async def deny(*args, **kwargs):
        return False, 42, 0

    monkeypatch.setattr(main_module.reader_limiter, "hit", deny)

    with TestClient(main_module.app) as client:
        response = client.get("/api/read", params={"url": "https://example.com/"})

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "42"


def test_the_limiter_result_has_three_fields(main_module):
    import asyncio

    async def run():
        return await main_module.reader_limiter.hit("203.0.113.99")

    result = asyncio.run(run())

    assert len(result) == 3
    assert result[0] is True
    assert result[1] == 0
