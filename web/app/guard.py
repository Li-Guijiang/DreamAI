"""A small circuit breaker for the upstream provider.

When a provider is down, every request pays the full timeout before failing. A
breaker turns that into a fast, honest 503 after a few failures, then probes once
in a while to see whether the provider came back.

States follow the usual three-phase model:

    closed --(failures >= threshold)--> open
    open --(cooldown elapsed)--> half-open (one probe allowed)
    half-open --(success)--> closed
    half-open --(failure)--> open
"""

from __future__ import annotations

import time
from collections.abc import Callable

CLOSED = "closed"
OPEN = "open"
HALF_OPEN = "half-open"


class CircuitBreaker:
    """Count failures in a row; open when they cross the threshold."""

    def __init__(
        self,
        threshold: int = 3,
        cooldown: float = 30.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.threshold = max(1, threshold)
        self.cooldown = max(1.0, cooldown)
        self._clock = clock
        self._failures = 0
        self._state = CLOSED
        self._opened_at = 0.0
        self._probe_in_flight = False
        # Counted for the life of the process: a breaker that has opened nine
        # times today is a different situation from one that opened once.
        self.openings = 0
        # Wall-clock timestamp of the most recent opening, for logs and graphs.
        self.last_opened_at: float | None = None

    @property
    def state(self) -> str:
        if self._state == OPEN and self._clock() - self._opened_at >= self.cooldown:
            return HALF_OPEN
        return self._state

    def allow(self) -> bool:
        """Whether a request may go upstream right now."""
        state = self.state
        if state == CLOSED:
            return True
        if state == OPEN:
            return False
        # half-open: exactly one probe, so a recovering provider is not flooded
        if self._probe_in_flight:
            return False
        self._probe_in_flight = True
        return True

    def remaining(self) -> float:
        """Seconds until the breaker will let a probe through; 0 while it is not open."""
        if self._state != OPEN:
            return 0.0
        return max(0.0, self.cooldown - (self._clock() - self._opened_at))

    def record_success(self) -> None:
        self._failures = 0
        self._state = CLOSED
        self._probe_in_flight = False

    def record_failure(self) -> None:
        self._probe_in_flight = False
        self._failures += 1
        if self._state == HALF_OPEN or self._failures >= self.threshold:
            self._state = OPEN
            self._opened_at = self._clock()
            self.openings += 1
            self.last_opened_at = time.time()

    def stats(self) -> dict:
        """Everything an operator needs to read the breaker's current mood."""
        return {
            "state": self.state,
            "threshold": self.threshold,
            "cooldown": self.cooldown,
            "failures": self._failures,
            "retryIn": round(self.remaining(), 1),
            "openings": self.openings,
            "lastOpenedAt": self.last_opened_at,
        }

    def reset(self) -> None:
        self._failures = 0
        self._state = CLOSED
        self._opened_at = 0.0
        self._probe_in_flight = False
