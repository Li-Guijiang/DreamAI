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
        self._by_model: dict[str, dict[str, float]] = {}

    def _slot(self, model: str) -> dict[str, float]:
        return self._by_model.setdefault(
            model or "unknown",
            {"requests": 0, "failures": 0, "promptTokens": 0, "completionTokens": 0, "costUsd": 0.0},
        )

    def record_turn(self, model: str, *, failed: bool = False) -> None:
        """Count one finished turn, however it ended."""
        self.requests += 1
        slot = self._slot(model)
        slot["requests"] += 1
        if failed:
            self.failures += 1
            slot["failures"] += 1

    def record_usage(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost: float | None = None,
    ) -> None:
        """Add the provider's own token counts for one turn."""
        prompt_tokens = max(0, int(prompt_tokens or 0))
        completion_tokens = max(0, int(completion_tokens or 0))
        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens
        slot = self._slot(model)
        slot["promptTokens"] += prompt_tokens
        slot["completionTokens"] += completion_tokens
        if cost is None:
            # The model has no price here, so its share stays at zero; the
            # per-model table still shows the tokens that were spent.
            self.known_cost = False
        else:
            self.cost_usd += float(cost)
            slot["costUsd"] += float(cost)

    def snapshot(self) -> dict:
        """The numbers `/api/usage` reports, in its own spelling."""
        return {
            "requests": self.requests,
            "failures": self.failures,
            "promptTokens": self.prompt_tokens,
            "completionTokens": self.completion_tokens,
            "costUsd": round(self.cost_usd, 4),
            "costKnown": self.known_cost,
            "byModel": {
                model: {
                    **slot,
                    "costUsd": round(slot["costUsd"], 4),
                }
                for model, slot in self._by_model.items()
            },
        }
