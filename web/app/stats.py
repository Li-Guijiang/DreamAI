"""Counters for the numbers the service reports about itself.

`/api/usage` used to read a dict of bare integers kept in `main.py`, which meant
the endpoint and the chat pipeline both had to agree on a set of string keys and
nothing could be added without touching both. This module owns the counters and
the shape of the snapshot; the endpoint stays a formatting layer.

Everything here is plain synchronous code on purpose. The web service runs one
event loop, each counter update happens between two `await` points, and a lock
would only add a scheduling point where a half-updated number could be read.
"""

from __future__ import annotations

import time


class UsageStats:
    """Process-lifetime totals, reset by a restart and by nothing else."""

    def __init__(self, started_at: float | None = None) -> None:
        self.started_at = started_at if started_at is not None else time.time()
        self.requests = 0
        self.failures = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.cost_usd = 0.0
        # A price list goes stale; when a model is not in it, the total is a
        # lower bound and `/api/usage` has to say so instead of rounding to 0.
        self.known_cost = True

    def record_turn(self, *, failed: bool = False) -> None:
        """Count one finished turn, however it ended."""
        self.requests += 1
        if failed:
            self.failures += 1

    def record_usage(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        cost: float | None = None,
    ) -> None:
        """Add the provider's own token counts for one turn."""
        self.prompt_tokens += max(0, int(prompt_tokens or 0))
        self.completion_tokens += max(0, int(completion_tokens or 0))
        if cost is None:
            self.known_cost = False
        else:
            self.cost_usd += float(cost)

    def snapshot(self) -> dict:
        """The numbers `/api/usage` reports, in its own spelling."""
        return {
            "requests": self.requests,
            "failures": self.failures,
            "promptTokens": self.prompt_tokens,
            "completionTokens": self.completion_tokens,
            "costUsd": round(self.cost_usd, 4),
            "costKnown": self.known_cost,
        }
