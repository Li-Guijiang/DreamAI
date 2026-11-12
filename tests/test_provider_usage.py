"""A hosted call already reports its own token counts; nothing may drop them."""

from __future__ import annotations

from types import SimpleNamespace

from dream_ai.providers.openai_compat import OpenAICompatProvider, usage_from_response


def test_counts_are_read_from_a_mapping_response():
    response = {
        "usage": {
            "prompt_tokens": 120,
            "completion_tokens": 80,
            "prompt_tokens_details": {"cached_tokens": 64},
        }
    }

    assert usage_from_response(response) == {
        "prompt_tokens": 120,
        "completion_tokens": 80,
        "cached_tokens": 64,
    }


def test_counts_are_read_from_an_sdk_object():
    response = SimpleNamespace(
        usage=SimpleNamespace(
            prompt_tokens=300,
            completion_tokens=40,
            prompt_tokens_details=SimpleNamespace(cached_tokens=256),
        )
    )

    assert usage_from_response(response)["cached_tokens"] == 256


def test_a_silent_provider_reports_nothing_rather_than_zero():
    assert usage_from_response(SimpleNamespace(usage=None)) == {}
    assert usage_from_response({"choices": []}) == {}


def test_details_without_a_cached_count_are_ignored():
    response = {"usage": {"prompt_tokens": 10, "completion_tokens": 2, "prompt_tokens_details": {}}}

    assert "cached_tokens" not in usage_from_response(response)


def test_a_boolean_is_not_a_token_count():
    response = {"usage": {"prompt_tokens": True, "completion_tokens": 5}}

    assert usage_from_response(response) == {"completion_tokens": 5}


def test_negative_counts_cannot_shrink_a_bill():
    response = {"usage": {"prompt_tokens": -10, "completion_tokens": -1}}

    assert usage_from_response(response) == {"prompt_tokens": 0, "completion_tokens": 0}


def test_the_provider_names_its_own_model_for_the_price_table():
    provider = OpenAICompatProvider(model="deepseek-chat", api_key="k", base_url="http://x")

    # name is for humans; model is the key the price table uses.
    assert provider.name == "openai-compat:deepseek-chat"
    assert provider.model == "deepseek-chat"


def test_usage_starts_empty_on_a_fresh_provider():
    provider = OpenAICompatProvider(model="m", api_key="k", base_url="http://x")

    assert provider.last_usage == {}
