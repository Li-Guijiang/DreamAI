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


def mask_ip(value: str) -> str:
    """Keep a client's network prefix; drop the host part.

    The rate limiter still keys on the full address - that is its job. Logs are
    read to notice that one network is misbehaving, not to identify a person,
    so the last two IPv4 octets and the tail of an IPv6 address are dropped.
    Unrecognised values (a proxy name, "unknown") pass through unchanged.
    """
    raw = (value or "").strip()
    if not raw:
        return "unknown"
    body = raw[1:].split("]", 1)[0] if raw.startswith("[") else raw
    if body.count(":") > 1:  # IPv6 (one colon means an IPv4 address with a port)
        parts = body.split(":")
        return ":".join(parts[:2]) + "::" if parts and parts[0] else body
    host = body.split(":", 1)[0]  # IPv4 with an optional port
    parts = host.split(".")
    if len(parts) == 4 and all(part.isdigit() and 0 <= int(part) <= 255 for part in parts):
        return ".".join(parts[:2]) + ".x.x"
    return raw


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
    status: int | None = None,
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
        # Last, and only on failures: the status is what distinguishes a slow
        # upstream (408/504) from a bad key (401) in a grep of the log.
        + (f" status={status}" if status is not None else "")
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
