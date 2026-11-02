"""Owner commands answered by the agent, without a provider call."""

from __future__ import annotations

from dream_ai.core.agent import DreamAIAgent
from dream_ai.memory import PreferenceMemory


class SpyProvider:
    """Fails if the agent asks a model to answer an owner command."""

    def __init__(self) -> None:
        self.calls = 0

    def generate(self, messages):  # noqa: ANN001 - matches the provider protocol
        self.calls += 1
        return "provider was called"


def make_agent(**kwargs) -> tuple[DreamAIAgent, SpyProvider]:
    provider = SpyProvider()
    preferences = PreferenceMemory()
    agent = DreamAIAgent(
        provider=provider,
        preferences=preferences,
        system_prompt="base",
        **kwargs,
    )
    return agent, provider


def test_show_command_returns_the_dossier_without_calling_the_model():
    agent, provider = make_agent()

    reply = agent.chat("【查看我的全部档案】")

    assert provider.calls == 0
    assert "主人档案" in reply
    assert "李贵江" in reply


def test_update_command_appends_and_persists():
    agent, provider = make_agent()

    assert agent.chat("【更新档案】换了 2K 显示器") == "已追加：换了 2K 显示器"
    assert provider.calls == 0
    assert agent.preference_notes == ["换了 2K 显示器"]

    shown = agent.chat("【查看我的全部档案】")
    assert "换了 2K 显示器" in shown


def test_update_without_text_explains_the_usage():
    agent, _ = make_agent()

    assert "用法" in agent.chat("【更新档案】")
    assert agent.preference_notes == []


def test_clear_command_empties_appended_memory_only():
    agent, _ = make_agent()
    agent.chat("【更新档案】一条记忆")

    reply = agent.chat("【清空档案】")

    assert agent.preference_notes == []
    assert "内置身份记录不可" in reply
    assert "李贵江" in agent.chat("【查看我的全部档案】")


def test_public_surface_masks_contacts_in_model_output():
    class LeakyProvider:
        def generate(self, messages):  # noqa: ANN001
            return "他的手机是 13800138000，邮箱 demo@example.com"

    agent = DreamAIAgent(
        provider=LeakyProvider(),
        preferences=PreferenceMemory(),
        system_prompt="base",
        public_surface=True,
    )

    reply = agent.chat("他是谁")

    assert "13800138000" not in reply
    assert "demo@example.com" not in reply
    assert "已隐藏" in reply


def test_owner_surface_keeps_the_numbers():
    class EchoProvider:
        def generate(self, messages):  # noqa: ANN001
            return "13800138000"

    agent = DreamAIAgent(
        provider=EchoProvider(),
        preferences=PreferenceMemory(),
        system_prompt="base",
        public_surface=False,
    )

    assert agent.chat("我的手机号") == "13800138000"
