"""One structured line per turn.

Logs are for humans here, not for a pipeline, so the format is a fixed key=value
line that can be grepped and still read: request id first, then the numbers that
explain a slow or truncated answer.

    chat done id=req_1a2b3c4d tier=deep intent=error ttft=0.84s total=6.21s chars=812 model=...

TTFT is the number users feel; total is the number that shows up in a bill. The
optional tail fields are appended in a fixed order so two lines can be compared
by eye without reading the labels.
"""

from __future__ import annotations


def format_turn_log(
    request_id: str,
    *,
    tier: str,
    intent: str,
    ttft: float,
    total: float,
    chars: int,
    model: str,
    outcome: str = "done",
    cost: float | None = None,
    cache: str = "",
    cached_tokens: int = 0,
    finish: str = "",
) -> str:
    """Render the single line written when a turn finishes."""
    return (
        f"chat {outcome} id={request_id} tier={tier} intent={intent} "
        f"ttft={ttft:.2f}s total={total:.2f}s chars={chars} model={model}"
        + (f" cache={cache}" if cache else "")
        # The cached share explains a cost that looks too low for the model;
        # without it the next reader suspects a bug in the price table.
        + (f" cachedTokens={cached_tokens}" if cached_tokens else "")
        + (f" finish={finish}" if finish else "")
        + (f" cost=${cost:.4f}" if cost is not None else "")
    )


def format_breaker_log(stats: dict) -> str:
    """One line when the breaker opens: how bad, how often, and for how long."""
    return (
        f"breaker open state={stats.get('state', 'open')} "
        f"failures={stats.get('failures', 0)} openings={stats.get('openings', 0)} "
        f"cooldown={stats.get('cooldown', 0)}s"
    )


def format_recovery_log(stats: dict) -> str:
    """One line when a half-open probe succeeds and the breaker closes again."""
    return (
        f"breaker recovered state={stats.get('state', 'closed')} "
        f"openings={stats.get('openings', 0)}"
    )
