"""The agent shapes a turn by intent, and trims what it forwards."""

from __future__ import annotations

from dream_ai.core.agent import DreamAIAgent
from dream_ai.memory import PreferenceMemory


class Capture:
    def __init__(self) -> None:
        self.seen: list[list[dict]] = []

    def generate(self, messages):  # noqa: ANN001
        self.seen.append(list(messages))
        return "收到。"


def make():
    provider = Capture()
    return DreamAIAgent(provider=provider, preferences=PreferenceMemory(), system_prompt="BASE"), provider


def test_error_turn_adds_the_error_shape():
    agent, provider = make()

    agent.chat("启动报错：端口占用怎么修")

    system = provider.seen[-1][0]["content"]
    assert "现象→最可能的原因→修复步骤→如何验证" in system
    assert system.startswith("BASE")


def test_chat_turn_leaves_the_prompt_alone():
    agent, provider = make()

    agent.chat("你好")

    assert provider.seen[-1][0]["content"] == "BASE"


def test_repeat_turn_asks_for_a_different_angle():
    agent, provider = make()
    agent.chat("为什么这个查询慢")
    agent.chat("这个查询为什么这么慢")

    system = provider.seen[-1][0]["content"]
    assert "重复问了同一件事" in system


def test_long_paste_is_trimmed_before_the_provider():
    agent, provider = make()
    body = "run\n" + ("noise line\n" * 900) + "ERROR: boom\n"

    agent.chat(body)

    sent = provider.seen[-1][-1]["content"]
    assert len(sent) < len(body)
    assert "boom" in sent
