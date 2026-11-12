"""The two finish-reason maps must not drift apart."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

WEB = str(Path(__file__).resolve().parent.parent / "web")
if WEB not in sys.path:
    sys.path.insert(0, WEB)

from app.adapters import normalise_finish as web_normalise  # noqa: E402

from dream_ai.finish import normalise_finish as local_normalise  # noqa: E402

CORPUS = (
    "length",
    "LENGTH",
    "max_tokens",
    "MAX_TOKENS",
    "stop",
    "STOP",
    "end_turn",
    "endTurn",
    "stop_sequence",
    "content_filter",
    "refusal",
    "SAFETY",
    "RECITATION",
    "BLOCKLIST",
    "PROHIBITED_CONTENT",
    "SPII",
    "FINISH_REASON_UNSPECIFIED",
    "none",
    "",
    "tool_calls",
    "a-new-vendor-reason",
    None,
    True,
    12,
)


@pytest.mark.parametrize("reason", CORPUS)
def test_both_surfaces_read_a_reason_the_same_way(reason):
    assert local_normalise(reason) == web_normalise(reason)
