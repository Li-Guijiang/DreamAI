"""Token counts must be readable from all three wire formats."""

from __future__ import annotations

import json
import sys
from pathlib import Path

WEB = str(Path(__file__).resolve().parent.parent / "web")
if WEB not in sys.path:
    sys.path.insert(0, WEB)

from app.adapters import usage_from_chunk  # noqa: E402


def _data(obj: dict) -> str:
    return json.dumps(obj)


def test_openai_compatible_final_chunk():
    chunk = _data({"choices": [], "usage": {"prompt_tokens": 120, "completion_tokens": 80}})

    assert usage_from_chunk("openai", chunk) == {
        "prompt_tokens": 120,
        "completion_tokens": 80,
    }


def test_an_openai_chunk_without_usage_is_not_a_zero():
    assert usage_from_chunk("openai", _data({"choices": [{"delta": {"content": "hi"}}]})) is None


def test_anthropic_input_tokens_live_in_message_start():
    chunk = _data(
        {"type": "message_start", "message": {"usage": {"input_tokens": 42, "output_tokens": 1}}}
    )

    assert usage_from_chunk("anthropic", chunk) == {
        "prompt_tokens": 42,
        "completion_tokens": 1,
    }


def test_anthropic_output_tokens_live_in_message_delta():
    chunk = _data({"type": "message_delta", "usage": {"output_tokens": 77}})

    assert usage_from_chunk("anthropic", chunk) == {"completion_tokens": 77}


def test_google_uses_camel_case_names():
    chunk = _data({"usageMetadata": {"promptTokenCount": 11, "candidatesTokenCount": 9}})

    assert usage_from_chunk("google", chunk) == {
        "prompt_tokens": 11,
        "completion_tokens": 9,
    }


def test_junk_and_done_are_ignored():
    assert usage_from_chunk("openai", "") is None
    assert usage_from_chunk("openai", "[DONE]") is None
    assert usage_from_chunk("openai", "not json") is None
    assert usage_from_chunk("openai", "[1, 2]") is None


def test_a_boolean_is_not_a_token_count():
    assert usage_from_chunk("openai", _data({"usage": {"prompt_tokens": True}})) is None
