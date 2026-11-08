"""Rough cost per million tokens, so a usage number has a unit.

Prices are published per model by each vendor and change without notice; the table
is therefore a small, explicitly dated snapshot, and an unknown model returns None
rather than a fabricated number.

The point is not accounting precision. It is answering "is this model ten times
more expensive than the other one" before a bill arrives.
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


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float | None:
    """USD for one turn, or None when the model is not in the table."""
    price = PRICES.get(model)
    if price is None:
        return None
    input_price, output_price = price
    return round(
        prompt_tokens / 1_000_000 * input_price + completion_tokens / 1_000_000 * output_price,
        6,
    )


def format_cost(total: float | None) -> str:
    """Human form: fractions of a cent are unreadable at full precision."""
    if total is None:
        return "unknown"
    if total == 0:
        return "free"
    if total < 0.01:
        return f"${total:.4f}"
    return f"${total:.2f}"
