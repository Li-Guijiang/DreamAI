"""The agent's reply path applies the quality post-processing."""

from __future__ import annotations

from dream_ai.core.agent import DreamAIAgent
from dream_ai.memory import PreferenceMemory


class ScriptedProvider:
    def __init__(self, reply: str) -> None:
        self.reply = reply

    def generate(self, messages):  # noqa: ANN001
        return self.reply


def make(reply: str, **kwargs) -> DreamAIAgent:
    return DreamAIAgent(
        provider=ScriptedProvider(reply),
        preferences=PreferenceMemory(),
        system_prompt="base",
        **kwargs,
    )


def test_trailing_filler_is_removed_from_the_reply():
    agent = make("结论是 A。希望对你有帮助", public_surface=False)

    assert agent.chat("选哪个") == "结论是 A。"


def test_clean_reply_is_unchanged():
    agent = make("结论是 A。", public_surface=False)

    assert agent.chat("选哪个") == "结论是 A。"


def test_mask_still_applies_after_stripping():
    agent = make("手机 19110734460。希望对你有帮助", public_surface=True)

    reply = agent.chat("他的手机")

    assert "19110734460" not in reply
    assert "希望" not in reply
