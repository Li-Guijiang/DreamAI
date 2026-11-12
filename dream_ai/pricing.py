"""Rough cost per million tokens, for the surfaces that run on your own machine.

This is the same snapshot the web service uses (``web/app/pricing.py``). The two
copies exist because the CLI and the desktop shell must keep working when only
``dream_ai`` is installed, and a parity test keeps them from drifting apart.

Prices are published per model by each vendor and change without notice; the
table is a small, explicitly dated snapshot, and an unknown model returns None
rather than a fabricated number.
"""

from __future__ import annotations

#: USD per 1M tokens: (input, output). Snapshot 2026-11, list prices.
PRICES: dict[str, tuple[float, float]] = {
    "glm-4-flash": (0.0, 0.0),
    "glm-4-plus": (0.7, 0.7),
    "deepseek-chat": (0.27, 1.1),
    "deepseek-reasoner": (0.55, 2.19),
    "gpt-4o-mini": (0.15, 0.6),
    "gpt-4o": (2.5, 10.0),
    "claude-3-5-haiku-latest": (0.8, 4.0),
    "claude-3-5-sonnet-latest": (3.0, 15.0),
    "gemini-2.0-flash": (0.1, 0.4),
    "gemini-1.5-pro": (1.25, 5.0),
}

#: USD per 1M *cached* input tokens. A prompt cache is billed at a fraction of the
#: list input price, and the fraction differs by vendor; a single multiplier would
#: be wrong for most of them. A model absent here is billed at the full price,
#: which overstates rather than flatters.
CACHE_PRICES: dict[str, float] = {
    "deepseek-chat": 0.07,
    "deepseek-reasoner": 0.14,
    "gpt-4o-mini": 0.075,
    "gpt-4o": 1.25,
    "claude-3-5-haiku-latest": 0.08,
    "claude-3-5-sonnet-latest": 0.3,
    "gemini-2.0-flash": 0.025,
    "gemini-1.5-pro": 0.3125,
}


def estimate_cost(
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    *,
    cached: int = 0,
) -> float | None:
    """USD for one turn, or None when the model is not in the table."""
    price = PRICES.get(model)
    if price is None:
        return None
    input_price, output_price = price
    prompt = max(0, int(prompt_tokens or 0))
    cached = min(max(0, int(cached or 0)), prompt)
    cached_price = CACHE_PRICES.get(model, input_price)
    prompt_cost = (prompt - cached) * input_price + cached * cached_price
    return round(prompt_cost / 1_000_000 + completion_tokens / 1_000_000 * output_price, 6)


def format_cost(total: float | None) -> str:
    """Human form: fractions of a cent are unreadable at full precision."""
    if total is None:
        return "unknown"
    if total == 0:
        return "free"
    if total < 0.01:
        return f"${total:.4f}"
    return f"${total:.2f}"
