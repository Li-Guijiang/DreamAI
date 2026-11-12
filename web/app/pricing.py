"""Rough cost per million tokens, so a usage number has a unit.

Prices are published per model by each vendor and change without notice; the table
is therefore a small, explicitly dated snapshot, and an unknown model returns None
rather than a fabricated number.

The point is not accounting precision. It is answering "is this model ten times
more expensive than the other one" before a bill arrives.
"""

from __future__ import annotations

import math

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

#: USD per 1M *cached* input tokens, same snapshot. A prompt cache is billed at a
#: fraction of the list input price, and the fraction is not the same everywhere:
#: it is a tenth at Anthropic, a quarter at Google, a half at OpenAI and about a
#: quarter at DeepSeek. A single multiplier would be wrong for three of the four.
#: Models absent from this table are billed at the full input price - an unknown
#: discount is assumed to be no discount, which overstates rather than flatters.
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
    """USD for one turn, or None when the model is not in the table.

    ``cached`` is the part of ``prompt_tokens`` that hit a prompt cache. It is a
    subset, not an addition, so it never makes the prompt larger - only cheaper.
    A count that exceeds the prompt is clamped instead of producing a negative
    line: a provider that reports the two numbers inconsistently should not be
    able to reduce the bill.
    """
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


def _entries(raw: str) -> list[tuple[str, list[str]]]:
    """Split ``model=a,b[,c];model2=…`` into ``(model, fields)`` without judging."""
    entries: list[tuple[str, list[str]]] = []
    for item in (raw or "").split(";"):
        item = item.strip()
        if not item or "=" not in item:
            continue
        model, numbers = item.split("=", 1)
        model = model.strip()
        if not model:
            continue
        entries.append((model, [part.strip() for part in numbers.split(",")]))
    return entries


def _floats(fields: list[str]) -> list[float] | None:
    """The fields as finite non-negative floats, or None if any of them is not."""
    try:
        values = [float(field) for field in fields]
    except ValueError:
        return None
    # nan and inf parse as floats and would quietly make every estimate nan.
    return values if all(math.isfinite(value) and value >= 0 for value in values) else None


def parse_price_overrides(raw: str) -> dict[str, tuple[float, float]]:
    """Parse ``model=input,output[,cached];model2=…`` into a price table.

    A published price list is a dated snapshot. A vendor can change a price or
    add a model without a release, so the operator needs a way to correct one
    entry in an environment variable instead of editing source. Malformed pairs
    are skipped rather than allowed to poison the table.

    The third field is optional and is read by :func:`parse_cache_overrides`;
    it is accepted here so a single variable can carry all three numbers.
    """
    result: dict[str, tuple[float, float]] = {}
    for model, fields in _entries(raw):
        if len(fields) < 2:
            continue
        values = _floats(fields[:2])
        if values is None:
            continue
        result[model] = (values[0], values[1])
    return result


def parse_cache_overrides(raw: str) -> dict[str, float]:
    """The optional third number: USD per 1M cached input tokens.

    Only entries that carry it are returned, so a model can be repriced without
    silently claiming its cache price stayed the same.
    """
    result: dict[str, float] = {}
    for model, fields in _entries(raw):
        if len(fields) < 3:
            continue
        values = _floats(fields[:3])
        if values is None:
            continue
        result[model] = values[2]
    return result


def configure_prices(raw: str) -> dict[str, tuple[float, float]]:
    """Apply operator overrides to the module tables and return what was applied."""
    overrides = parse_price_overrides(raw)
    PRICES.update(overrides)
    CACHE_PRICES.update(parse_cache_overrides(raw))
    return overrides
