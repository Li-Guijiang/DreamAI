"""Every local turn must carry a budget, and older providers must still work."""

from __future__ import annotations

import pytest

from dream_ai.core.agent import DreamAIAgent
from dream_ai.memory import PreferenceMemory


class RecordingProvider:
    """Remembers the kwargs it was called with."""

    def __init__(self, reply: str = "好的") -> None:
        self.reply = reply
        self.calls: list[dict] = []

    def generate(self, messages, **kwargs):  # noqa: ANN001, ANN003
        self.calls.append(kwargs)
        return self.reply


class LegacyProvider:
    """A provider written before the budget existed."""

    def __init__(self) -> None:
        self.calls = 0

    def generate(self, messages):  # noqa: ANN001
        self.calls += 1
        return "旧接口也能用"


class BrokenProvider:
    """Raises TypeError for its own reasons, which must not be swallowed."""

    def generate(self, messages, **kwargs):  # noqa: ANN001, ANN003
        raise TypeError("internal mapping failure")


def _agent(provider, **kwargs) -> DreamAIAgent:  # noqa: ANN001
    return DreamAIAgent(
        provider=provider,
        preferences=PreferenceMemory(),
        system_prompt="base",
        **kwargs,
    )


def test_a_short_question_gets_a_small_budget():
    provider = RecordingProvider()

    _agent(provider).chat("在吗")

    assert provider.calls[0]["max_tokens"] == 768


def test_a_deep_question_gets_more_room_than_the_configured_maximum():
    provider = RecordingProvider()

    _agent(provider, max_tokens=4096).chat("为什么要把缓存做成两层，架构上怎么权衡")

    assert provider.calls[0]["max_tokens"] == 4096 + 1024


def test_the_configured_budget_can_be_lowered():
    provider = RecordingProvider()

    _agent(provider, max_tokens=512).chat("帮我把这段配置改成 yaml 格式，字段名保持不变")

    assert provider.calls[0]["max_tokens"] == 512


def test_a_provider_with_the_old_signature_is_still_usable():
    provider = LegacyProvider()

    assert _agent(provider).chat("在吗") == "旧接口也能用"
    assert provider.calls == 1


def test_an_unrelated_type_error_is_not_swallowed():
    with pytest.raises(TypeError):
        _agent(BrokenProvider()).chat("在吗")
