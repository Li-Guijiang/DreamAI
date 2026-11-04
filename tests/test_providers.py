"""The provider registry is the only place vendors are described."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))

from app.providers import (  # noqa: E402
    BYOK_PROVIDERS,
    PROVIDERS,
    get_provider,
    is_known_model,
    public_catalog,
    resolve_model,
)


def test_the_registry_covers_the_requested_vendors():
    for provider_id in ("deepseek", "openai", "anthropic", "google"):
        assert provider_id in PROVIDERS, provider_id
    assert set(BYOK_PROVIDERS) == set(PROVIDERS)


def test_every_provider_has_a_key_page_and_a_model():
    for provider in PROVIDERS.values():
        assert provider.key_url.startswith("https://"), provider.id
        assert provider.base_url.startswith("https://"), provider.id
        assert provider.models, provider.id
        assert provider.kind in {"openai", "anthropic", "google"}


def test_deepseek_marks_its_reasoning_model():
    provider = get_provider("deepseek")

    assert provider is not None
    reasoning = [m for m in provider.models if m.reasoning]
    assert [m.id for m in reasoning] == ["deepseek-reasoner"]


def test_unknown_provider_is_none():
    assert get_provider("nope") is None


def test_custom_model_ids_pass_through():
    # Gateways expose names we cannot enumerate, so an unknown id is accepted.
    assert resolve_model("openai", "my-gateway/model-x") == "my-gateway/model-x"


def test_empty_model_falls_back_to_the_first_entry():
    assert resolve_model("openai", None) == get_provider("openai").models[0].id


def test_is_known_model_only_accepts_listed_ids():
    assert is_known_model("deepseek", "deepseek-chat")
    assert not is_known_model("deepseek", "gpt-4o")


def test_public_catalog_carries_no_secrets():
    catalog = public_catalog()

    assert {item["id"] for item in catalog} == set(PROVIDERS)
    for item in catalog:
        assert "key" not in str(item).lower() or "keyUrl" in item
        assert all("apiKey" not in model for model in item["models"])
