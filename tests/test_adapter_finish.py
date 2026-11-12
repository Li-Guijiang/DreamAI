"""A truncated answer must be distinguishable from a finished one."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

WEB = str(Path(__file__).resolve().parent.parent / "web")
if WEB not in sys.path:
    sys.path.insert(0, WEB)

from app.adapters import finish_from_chunk, normalise_finish  # noqa: E402


def _data(obj: dict) -> str:
    return json.dumps(obj)


@pytest.mark.parametrize(
    ("reason", "expected"),
    [
        ("length", "length"),
        ("stop", "stop"),
        ("content_filter", "filter"),
        ("tool_calls", "other"),
        (None, None),
    ],
)
def test_openai_finish_reasons(reason, expected):
    data = _data({"choices": [{"delta": {}, "finish_reason": reason}]})

    assert finish_from_chunk("openai", "", data) == expected


def test_openai_chunks_without_a_choice_are_ignored():
    assert finish_from_chunk("openai", "", _data({"choices": []})) is None
    assert finish_from_chunk("openai", "", _data({"usage": {"prompt_tokens": 1}})) is None


def test_anthropic_stop_reason_lives_on_message_delta():
    data = _data({"type": "message_delta", "delta": {"stop_reason": "max_tokens"}})

    assert finish_from_chunk("anthropic", "message_delta", data) == "length"


def test_anthropic_other_events_are_not_a_finish():
    data = _data({"type": "message_delta", "delta": {"stop_reason": "end_turn"}})

    assert finish_from_chunk("anthropic", "content_block_delta", data) is None
    assert finish_from_chunk("anthropic", "message_stop", _data({})) is None


def test_anthropic_an_empty_stop_reason_is_not_a_finish():
    data = _data({"type": "message_delta", "delta": {"stop_reason": None}})

    assert finish_from_chunk("anthropic", "message_delta", data) is None


@pytest.mark.parametrize(
    ("reason", "expected"),
    [
        ("MAX_TOKENS", "length"),
        ("STOP", "stop"),
        ("SAFETY", "filter"),
        ("RECITATION", "filter"),
        ("FINISH_REASON_UNSPECIFIED", None),
        ("SOMETHING_NEW", "other"),
    ],
)
def test_google_finish_reasons(reason, expected):
    data = _data({"candidates": [{"finishReason": reason}]})

    assert finish_from_chunk("google", "", data) == expected


def test_google_chunks_without_candidates_are_ignored():
    assert finish_from_chunk("google", "", _data({"usageMetadata": {}})) is None


def test_junk_done_and_booleans_are_not_reasons():
    assert finish_from_chunk("openai", "", "") is None
    assert finish_from_chunk("openai", "", "[DONE]") is None
    assert finish_from_chunk("openai", "", "not json") is None
    assert finish_from_chunk("openai", "", "[1, 2]") is None
    assert normalise_finish(True) is None
    assert normalise_finish(12) is None
    assert normalise_finish("  length  ") == "length"


def test_an_unknown_reason_is_visible_rather_than_silent():
    assert normalise_finish("a-new-vendor-reason") == "other"
