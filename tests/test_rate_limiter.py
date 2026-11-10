"""The limiter must enforce its window and never leak the clients it watches."""

from __future__ import annotations

import asyncio
import importlib
import sys
from pathlib import Path

import pytest

WEB = str(Path(__file__).resolve().parent.parent / "web")
if WEB not in sys.path:
    sys.path.insert(0, WEB)

from app.main import RateLimiter  # noqa: E402


def _hit(limiter: RateLimiter, key: str) -> tuple[bool, int]:
    return asyncio.run(limiter.hit(key))


def test_a_limit_is_enforced_inside_the_window():
    limiter = RateLimiter(limit=2, window=60)

    assert _hit(limiter, "1.2.3.4")[0] is True
    assert _hit(limiter, "1.2.3.4")[0] is True
    allowed, retry, remaining = _hit(limiter, "1.2.3.4")
    assert allowed is False
    assert retry >= 1
    assert remaining == 0


def test_another_client_is_not_punished_for_the_first():
    limiter = RateLimiter(limit=1, window=60)

    _hit(limiter, "1.2.3.4")

    assert _hit(limiter, "5.6.7.8")[0] is True


def test_the_snapshot_counts_clients_without_naming_them():
    limiter = RateLimiter(limit=5, window=60)
    _hit(limiter, "1.2.3.4")
    _hit(limiter, "5.6.7.8")

    snapshot = limiter.stats()

    assert snapshot["tracked"] == 2
    assert snapshot["limit"] == 5
    assert snapshot["window"] == 60
    assert "1.2.3.4" not in str(snapshot)


def test_an_expired_window_frees_the_client():
    limiter = RateLimiter(limit=1, window=10)
    limiter._hits["1.2.3.4"].append(0.0)

    # The limiter's own clock is monotonic, so the stored hit sits far in the
    # past and the window check drops it before enforcing the limit.
    allowed, _, _ = _hit(limiter, "1.2.3.4")

    assert allowed is True


def test_the_remaining_count_falls_as_the_window_fills():
    limiter = RateLimiter(limit=3, window=60)

    assert _hit(limiter, "1.2.3.4")[2] == 2
    assert _hit(limiter, "1.2.3.4")[2] == 1
    assert _hit(limiter, "1.2.3.4")[2] == 0


def test_chat_responses_carry_the_rate_limit_headers():
    pytest.importorskip("fastapi", reason="web dependencies are not installed")

    main = importlib.import_module("app.main")
    from fastapi.testclient import TestClient

    client = TestClient(main.app)
    response = client.post(
        "/api/chat", json={"messages": [{"role": "user", "content": "你的主人是谁"}]}
    )

    assert response.status_code == 200
    assert "X-RateLimit-Limit" in response.headers
    assert "X-RateLimit-Remaining" in response.headers
    assert int(response.headers["X-RateLimit-Remaining"]) >= 0
