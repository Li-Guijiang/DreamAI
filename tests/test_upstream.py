"""Request routing: which provider, which key, which model."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest.importorskip("fastapi", reason="web dependencies are not installed")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))

from app.main import ChatRequest, UpstreamError, resolve_upstream  # noqa: E402

KEY = "sk-" + "a" * 40


def request(**kwargs) -> ChatRequest:
    payload = {"messages": [{"role": "user", "content": "hi"}]}
    payload.update(kwargs)
    return ChatRequest(**payload)


@pytest.mark.parametrize("provider_id", ["deepseek", "openai", "anthropic", "google", "zhipu"])
def test_each_provider_routes_with_its_own_wire_format(provider_id):
    upstream = resolve_upstream(request(provider=provider_id, apiKey=KEY))

    assert upstream.provider.id == provider_id
    assert upstream.api_key == KEY
    assert upstream.kind in {"openai", "anthropic", "google"}


def test_anthropic_and_google_keep_their_own_kind():
    assert resolve_upstream(request(provider="anthropic", apiKey=KEY)).kind == "anthropic"
    assert resolve_upstream(request(provider="google", apiKey=KEY)).kind == "google"


def test_legacy_byok_alias_still_means_deepseek():
    upstream = resolve_upstream(request(provider="byok", apiKey=KEY))

    assert upstream.provider.id == "deepseek"


def test_missing_key_is_rejected_with_the_provider_name():
    with pytest.raises(UpstreamError) as caught:
        resolve_upstream(request(provider="anthropic"))

    assert caught.value.code == "byok_missing"
    assert "Anthropic" in caught.value.message


def test_key_with_whitespace_is_rejected():
    with pytest.raises(UpstreamError):
        resolve_upstream(request(provider="openai", apiKey="sk-" + "a" * 20 + " b"))


def test_unknown_provider_is_rejected():
    with pytest.raises(UpstreamError) as caught:
        resolve_upstream(request(provider="nope", apiKey=KEY))

    assert caught.value.code == "unknown_provider"
    assert caught.value.status == 400


def test_model_defaults_to_the_provider_list():
    upstream = resolve_upstream(request(provider="openai", apiKey=KEY))

    assert upstream.model == "gpt-4o-mini"


def test_custom_model_is_kept():
    upstream = resolve_upstream(request(provider="openai", apiKey=KEY, model="my-gateway/x"))

    assert upstream.model == "my-gateway/x"
