"""A caller-supplied budget must reach the wire, and nothing must be sent otherwise."""

from __future__ import annotations

from types import SimpleNamespace

from dream_ai.providers.openai_compat import OpenAICompatProvider


class FakeCompletions:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def create(self, **kwargs):  # noqa: ANN003 - mirrors the SDK signature
        self.calls.append(kwargs)
        message = SimpleNamespace(content="好的")
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def _provider() -> tuple[OpenAICompatProvider, FakeCompletions]:
    completions = FakeCompletions()
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    provider = OpenAICompatProvider(model="m", api_key="k", base_url="https://x/v1")
    provider._client = client
    return provider, completions


def test_a_budget_is_forwarded_to_the_provider():
    provider, completions = _provider()

    provider.generate([{"role": "user", "content": "hi"}], max_tokens=256)

    assert completions.calls[0]["max_tokens"] == 256


def test_no_budget_means_no_max_tokens_key():
    provider, completions = _provider()

    provider.generate([{"role": "user", "content": "hi"}])

    assert "max_tokens" not in completions.calls[0]


def test_a_nonsense_budget_is_ignored_rather_than_sent():
    provider, completions = _provider()

    provider.generate([{"role": "user", "content": "hi"}], max_tokens=0)

    assert "max_tokens" not in completions.calls[0]
