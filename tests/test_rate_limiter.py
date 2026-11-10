"""The limiter must enforce its window and never leak the clients it watches."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))

from app.main import RateLimiter  # noqa: E402


def _hit(limiter: RateLimiter, key: str) -> tuple[bool, int]:
    return asyncio.run(limiter.hit(key))


def test_a_limit_is_enforced_inside_the_window():
    limiter = RateLimiter(limit=2, window=60)

    assert _hit(limiter, "1.2.3.4")[0] is True
    assert _hit(limiter, "1.2.3.4")[0] is True
    allowed, retry = _hit(limiter, "1.2.3.4")
    assert allowed is False
    assert retry >= 1


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
    allowed, _ = _hit(limiter, "1.2.3.4")

    assert allowed is True
