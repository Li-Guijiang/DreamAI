"""Auto-capture keeps the owner's mid-sentence facts without a command."""

from __future__ import annotations

from dream_ai.core.agent import DreamAIAgent
from dream_ai.memory import PreferenceMemory


class CountingProvider:
    def __init__(self) -> None:
        self.calls = 0

    def generate(self, messages):  # noqa: ANN001
        self.calls += 1
        return "model reply"


def make_agent() -> tuple[DreamAIAgent, CountingProvider]:
    provider = CountingProvider()
    agent = DreamAIAgent(
        provider=provider,
        preferences=PreferenceMemory(),
        system_prompt="base",
        public_surface=False,
    )
    return agent, provider


def test_capture_stores_the_fact_and_skips_the_model():
    agent, provider = make_agent()

    reply = agent.chat("记住：每周三晚上有班会")

    assert reply == "已记住：每周三晚上有班会"
    assert agent.preference_notes == ["每周三晚上有班会"]
    assert provider.calls == 0


def test_capture_accepts_a_half_width_colon():
    agent, _ = make_agent()

    agent.chat("记住: 习惯用中文回答")

    assert agent.preference_notes == ["习惯用中文回答"]


def test_empty_capture_explains_the_usage():
    agent, provider = make_agent()

    assert "用法" in agent.chat("记住：")
    assert provider.calls == 0
    assert agent.preference_notes == []


def test_capture_survives_reload(tmp_path):
    store = tmp_path / "preferences.json"
    agent = DreamAIAgent(
        provider=CountingProvider(),
        preferences=PreferenceMemory(store),
        system_prompt="base",
    )
    agent.chat("记住：主用 VSCode")

    reopened = PreferenceMemory(store)
    assert "主用 VSCode" in reopened.list(), "a captured fact must outlive the process"
