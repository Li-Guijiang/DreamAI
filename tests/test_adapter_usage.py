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


def test_openai_reports_cached_tokens_from_the_nested_details():
    chunk = _data(
        {
            "choices": [],
            "usage": {
                "prompt_tokens": 2000,
                "completion_tokens": 50,
                "prompt_tokens_details": {"cached_tokens": 1792},
            },
        }
    )

    usage = usage_from_chunk("openai", chunk)

    # Cached tokens are a subset of the prompt, not an extra thousand.
    assert usage == {"prompt_tokens": 2000, "completion_tokens": 50, "cached_tokens": 1792}


def test_deepseek_spells_the_cache_hit_at_the_top_level():
    chunk = _data(
        {
            "usage": {
                "prompt_tokens": 900,
                "completion_tokens": 10,
                "prompt_cache_hit_tokens": 768,
            }
        }
    )

    assert usage_from_chunk("openai", chunk)["cached_tokens"] == 768


def test_anthropic_adds_cache_reads_and_writes_to_the_prompt_total():
    # input_tokens counts only the uncached remainder.
    chunk = _data(
        {
            "type": "message_start",
            "message": {
                "usage": {
                    "input_tokens": 30,
                    "cache_read_input_tokens": 1000,
                    "cache_creation_input_tokens": 200,
                    "output_tokens": 1,
                }
            },
        }
    )

    usage = usage_from_chunk("anthropic", chunk)

    assert usage["prompt_tokens"] == 1230
    # Only the read side is the discounted portion; a write is billed above list.
    assert usage["cached_tokens"] == 1000


def test_anthropic_cache_only_turn_still_reports_input():
    chunk = _data(
        {"type": "message_start", "message": {"usage": {"cache_read_input_tokens": 4096}}}
    )

    assert usage_from_chunk("anthropic", chunk) == {
        "prompt_tokens": 4096,
        "cached_tokens": 4096,
    }


def test_google_folds_thinking_tokens_into_the_completion():
    chunk = _data(
        {
            "usageMetadata": {
                "promptTokenCount": 100,
                "candidatesTokenCount": 20,
                "thoughtsTokenCount": 300,
            }
        }
    )

    usage = usage_from_chunk("google", chunk)

    # Thinking is billed as output; candidatesTokenCount leaves it out.
    assert usage["completion_tokens"] == 320


def test_google_cached_content_is_already_inside_the_prompt():
    chunk = _data(
        {
            "usageMetadata": {
                "promptTokenCount": 500,
                "candidatesTokenCount": 5,
                "cachedContentTokenCount": 480,
            }
        }
    )

    usage = usage_from_chunk("google", chunk)

    assert usage["prompt_tokens"] == 500
    assert usage["cached_tokens"] == 480


def test_zero_cached_tokens_are_not_reported():
    chunk = _data(
        {"usage": {"prompt_tokens": 10, "completion_tokens": 2, "prompt_tokens_details": {}}}
    )

    assert "cached_tokens" not in usage_from_chunk("openai", chunk)
