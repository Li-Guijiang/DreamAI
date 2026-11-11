"""Each wire format is built and parsed without a network or a key."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))

from app.adapters import build_request, parse_chunk  # noqa: E402
from app.providers import PROVIDERS  # noqa: E402

MESSAGES = [
    {"role": "system", "content": "你是 Dream AI"},
    {"role": "user", "content": "你好"},
]


def build(provider_id: str, **kwargs):
    return build_request(
        PROVIDERS[provider_id],
        api_key=kwargs.pop("api_key", "k" * 40),
        model=kwargs.pop("model", "test-model"),
        messages=kwargs.pop("messages", MESSAGES),
        temperature=0.4,
        max_tokens=512,
    )


def test_openai_compatible_uses_bearer_and_messages():
    url, headers, payload = build("deepseek")

    assert url == "https://api.deepseek.com/v1/chat/completions"
    assert headers["Authorization"] == "Bearer " + "k" * 40
    assert payload["messages"] == MESSAGES
    assert payload["stream"] is True


def test_anthropic_moves_system_out_of_messages():
    url, headers, payload = build("anthropic")

    assert url == "https://api.anthropic.com/v1/messages"
    assert headers["x-api-key"] == "k" * 40
    assert headers["anthropic-version"]
    assert payload["system"] == "你是 Dream AI"
    assert all(m["role"] != "system" for m in payload["messages"])
    assert payload["max_tokens"] == 512, "Anthropic requires max_tokens"


def test_google_uses_contents_and_key_in_query():
    url, headers, payload = build("google")

    assert ":streamGenerateContent" in url
    assert "key=" in url
    assert "systemInstruction" in payload
    assert payload["contents"][0]["parts"][0]["text"] == "你好"
    assert "Authorization" not in headers


def test_openai_chunk_carries_reasoning_and_content():
    data = json.dumps({"choices": [{"delta": {"reasoning_content": "想", "content": "答"}}]})

    assert parse_chunk("openai", "message", data) == [("reasoning", "想"), ("content", "答")]


def test_anthropic_chunk_reads_thinking_delta():
    data = json.dumps({"delta": {"type": "thinking_delta", "thinking": "想"}})

    assert parse_chunk("anthropic", "content_block_delta", data) == [("reasoning", "想")]


def test_anthropic_ignores_other_events():
    assert parse_chunk("anthropic", "message_start", "{}") == []


def test_google_chunk_reads_thought_parts():
    data = json.dumps({"candidates": [{"content": {"parts": [{"text": "想", "thought": True}]}}]})

    assert parse_chunk("google", "message", data) == [("reasoning", "想")]


def test_done_and_garbage_are_ignored():
    assert parse_chunk("openai", "", "[DONE]") == []
    assert parse_chunk("openai", "", "not json") == []


def test_upstream_error_is_raised_for_the_route_to_map():
    data = json.dumps({"error": {"message": "余额不足"}})

    with pytest.raises(ValueError, match="余额不足"):
        parse_chunk("openai", "", data)


def build_with(**extra):
    return build_request(
        PROVIDERS["openai"],
        api_key="k" * 40,
        model="m",
        messages=MESSAGES,
        temperature=0.5,
        max_tokens=256,
        **extra,
    )


def test_sampling_knobs_are_optional():
    _, _, payload = build_with()

    assert "top_p" not in payload
    assert "presence_penalty" not in payload


def test_openai_accepts_both_sampling_knobs():
    _, _, payload = build_with(top_p=0.9, presence_penalty=0.2)

    assert payload["top_p"] == 0.9
    assert payload["presence_penalty"] == 0.2


def test_anthropic_takes_top_p_only():
    url, _, payload = build_request(
        PROVIDERS["anthropic"],
        api_key="k" * 40,
        model="m",
        messages=MESSAGES,
        temperature=0.5,
        max_tokens=256,
        top_p=0.7,
        presence_penalty=0.3,
    )

    assert payload["top_p"] == 0.7
    assert "presence_penalty" not in payload


def test_google_spells_top_p_inside_generation_config():
    _, _, payload = build_request(
        PROVIDERS["google"],
        api_key="k" * 40,
        model="m",
        messages=MESSAGES,
        temperature=0.5,
        max_tokens=256,
        top_p=0.6,
    )

    assert payload["generationConfig"]["topP"] == 0.6


def test_openai_compatible_streams_ask_for_a_usage_chunk():
    _, _, payload = build("deepseek")

    assert payload["stream_options"] == {"include_usage": True}


def test_the_usage_request_can_be_switched_off():
    _, _, payload = build("deepseek", include_usage=False)

    assert "stream_options" not in payload


def test_anthropic_and_google_are_untouched_by_the_switch():
    for provider_id in ("anthropic", "google"):
        _, _, payload = build(provider_id, include_usage=False)
        assert "stream_options" not in payload
