"""What one session has spent.

The web service reports tokens and cost per turn through ``/api/usage``. The CLI
and the desktop shell only ever printed a turn counter, even though a hosted call
already returns its own token counts - the numbers were being thrown away by the
provider layer.

This module keeps the running total and, more importantly, keeps track of what it
could not measure: a provider that reports nothing, and a model with no published
price, both make the total a lower bound, and a session view that quietly shows
"$0.00" for either is worse than one that says so.
"""

from __future__ import annotations

from collections.abc import Mapping

from .pricing import estimate_cost


def _counts(usage: Mapping[str, int] | None) -> dict[str, int] | None:
    """Normalise one turn's counts, or None when the provider said nothing."""
    if not usage:
        return None
    prompt = max(0, int(usage.get("prompt_tokens") or 0))
    completion = max(0, int(usage.get("completion_tokens") or 0))
    # A cached count is a subset of the prompt; a provider that reports it larger
    # than the prompt is clamped rather than believed.
    cached = min(max(0, int(usage.get("cached_tokens") or 0)), prompt)
    return {"prompt": prompt, "completion": completion, "cached": cached}


class SessionUsage:
    """Running totals for one process, from import to exit."""

    def __init__(self) -> None:
        self.turns = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.cached_tokens = 0
        self.cost_usd = 0.0
        # Turns the provider answered without reporting counts.
        self.unmeasured = 0
        # Turns whose model is not in the price table.
        self.unpriced = 0
        self.models: dict[str, int] = {}

    @property
    def known_cost(self) -> bool:
        """Whether the total accounts for every turn, rather than a subset."""
        return self.unmeasured == 0 and self.unpriced == 0

    def record(self, model: str, usage: Mapping[str, int] | None) -> None:
        """Add one model turn, priced if the model is known."""
        self.turns += 1
        self.models[model] = self.models.get(model, 0) + 1
        counts = _counts(usage)
        if counts is None:
            self.unmeasured += 1
            return
        self.prompt_tokens += counts["prompt"]
        self.completion_tokens += counts["completion"]
        self.cached_tokens += counts["cached"]
        cost = estimate_cost(
            model, counts["prompt"], counts["completion"], cached=counts["cached"]
        )
        if cost is None:
            self.unpriced += 1
        else:
            self.cost_usd += cost

    def snapshot(self) -> dict:
        """The totals, in the spelling the CLI prints."""
        return {
            "turns": self.turns,
            "promptTokens": self.prompt_tokens,
            "completionTokens": self.completion_tokens,
            "cachedTokens": self.cached_tokens,
            "costUsd": round(self.cost_usd, 6),
            "costKnown": self.known_cost,
            "unmeasured": self.unmeasured,
            "unpriced": self.unpriced,
            "models": dict(self.models),
        }

    def reset(self) -> None:
        """Start counting again, e.g. after /clear."""
        self.__init__()
