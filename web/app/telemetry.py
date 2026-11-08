"""One structured line per turn.

Logs are for humans here, not for a pipeline, so the format is a fixed key=value
line that can be grepped and still read: request id first, then the numbers that
explain a slow or truncated answer.

    chat done id=req_1a2b3c4d tier=deep intent=error ttft=0.84s total=6.21s chars=812 model=...

TTFT is the number users feel; total is the number that shows up in a bill.
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
) -> str:
    """Render the single line written when a turn finishes."""
    return (
        f"chat {outcome} id={request_id} tier={tier} intent={intent} "
        f"ttft={ttft:.2f}s total={total:.2f}s chars={chars} model={model}"
        + (f" cost=${cost:.4f}" if cost is not None else "")
    )
