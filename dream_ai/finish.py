"""Fold a provider's finish reason into four shared words.

The web service does the same in ``web/app/adapters.py``; the two copies exist so
the CLI keeps working when only ``dream_ai`` is installed. A parity test compares
them, the same way the two difficulty rules and the two price tables are kept in
step.

A reply that ended at ``length`` is not a finished answer. The local surfaces
generate whole replies instead of streaming, so this is the only place they can
notice it - and a session view that silently counts it as complete is misleading.
"""

from __future__ import annotations

LENGTH = "length"
STOP = "stop"
FILTER = "filter"
OTHER = "other"

_LENGTH_REASONS = frozenset({"length", "LENGTH", "max_tokens", "MAX_TOKENS"})
_STOP_REASONS = frozenset({"stop", "STOP", "end_turn", "endTurn", "stop_sequence"})
_FILTER_REASONS = frozenset(
    {
        "content_filter",
        "refusal",
        "SAFETY",
        "RECITATION",
        "BLOCKLIST",
        "PROHIBITED_CONTENT",
        "SPII",
    }
)
_UNSPECIFIED_REASONS = frozenset({"", "none", "null", "FINISH_REASON_UNSPECIFIED", "unspecified"})


def normalise_finish(reason: object) -> str | None:
    """One vendor reason, folded into length / stop / filter / other.

    ``None`` means no reason was reported; an unknown reason becomes ``other``
    rather than being dropped, so a new vendor value is visible.
    """
    if not isinstance(reason, str):
        return None
    raw = reason.strip()
    if raw in _UNSPECIFIED_REASONS:
        return None
    if raw in _LENGTH_REASONS:
        return LENGTH
    if raw in _STOP_REASONS:
        return STOP
    if raw in _FILTER_REASONS:
        return FILTER
    return OTHER


def is_truncated(reason: object) -> bool:
    """Whether the model stopped because it ran out of its token budget."""
    return normalise_finish(reason) == LENGTH
