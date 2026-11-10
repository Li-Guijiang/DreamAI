"""A long local session must reach the provider folded, with its subject intact."""

from __future__ import annotations

from dream_ai.core.agent import DreamAIAgent
from dream_ai.memory import PreferenceMemory


class Capture:
    def __init__(self) -> None:
        self.seen: list[list[dict]] = []

    def generate(self, messages, **kwargs):  # noqa: ANN001, ANN003
        self.seen.append(list(messages))
        return "收到。"


def _agent(**kwargs) -> tuple[DreamAIAgent, Capture]:
    provider = Capture()
    agent = DreamAIAgent(
        provider=provider, preferences=PreferenceMemory(), system_prompt="BASE", **kwargs
    )
    return agent, provider


def _long(text: str, size: int = 900) -> str:
    return text + ("细节。 " * size)


def test_a_short_session_sends_every_turn_without_a_digest():
    agent, provider = _agent()
    agent.chat("第一问：Python 列表怎么去重")
    agent.chat("第二问：元组呢")

    sent = provider.seen[-1]

    assert len(sent) == 4  # system + first exchange + the new user turn
    assert not any("摘要" in m["content"] for m in sent)


def test_a_long_session_is_folded_and_the_digest_travels():
    agent, provider = _agent(max_history_chars=800)
    for i in range(8):
        agent.chat(_long(f"第{i}轮：贴一段很长的日志"))

    sent = provider.seen[-1]
    notes = [m for m in sent if "摘要" in m.get("content", "")]

    assert len(notes) == 1
    assert "第0轮" in notes[0]["content"]
    # The tail is still there, newest last.
    assert sent[-1]["content"].startswith("第7轮")


def test_a_followup_after_folding_tells_the_model_where_to_look():
    agent, provider = _agent(max_history_chars=800)
    for i in range(8):
        agent.chat(_long(f"第{i}轮：贴一段很长的日志"))

    agent.chat("那它呢")

    sent = provider.seen[-1]
    system = sent[0]["content"]

    assert "指代对象在上面的摘要里" in system


def test_folding_does_not_change_what_is_stored():
    agent, _ = _agent(max_history_chars=800)
    agent.chat(_long("第一轮"))
    agent.chat(_long("第二轮"))

    assert len(agent.history) == 5  # system + 2 turns x 2
