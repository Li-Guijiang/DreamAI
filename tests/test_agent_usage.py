"""Every model call must reach the session ledger, and no other call may."""

from __future__ import annotations

from dream_ai.core.agent import DreamAIAgent
from dream_ai.memory import PreferenceMemory


class Metered:
    """A provider that reports its own counts, like a hosted one."""

    name = "metered"
    model = "deepseek-chat"

    def __init__(self, reply: str = "好的。") -> None:
        self.reply = reply
        self.calls = 0
        self.last_usage: dict[str, int] = {}

    def generate(self, messages, **kwargs):  # noqa: ANN001, ANN003
        self.calls += 1
        self.last_usage = {"prompt_tokens": 1000, "completion_tokens": 500, "cached_tokens": 768}
        return self.reply


class Silent:
    """A provider that reports nothing at all."""

    name = "silent"

    def generate(self, messages, **kwargs):  # noqa: ANN001, ANN003
        return "好的。"


def _agent(provider) -> DreamAIAgent:
    return DreamAIAgent(provider=provider, preferences=PreferenceMemory(), system_prompt="BASE")


def test_a_turn_is_counted_priced_and_attributed():
    agent = _agent(Metered())

    agent.chat("在吗")

    snapshot = agent.session_usage.snapshot()
    assert snapshot["turns"] == 1
    assert snapshot["promptTokens"] == 1000
    assert snapshot["completionTokens"] == 500
    assert snapshot["cachedTokens"] == 768
    assert snapshot["models"] == {"deepseek-chat": 1}
    assert snapshot["costKnown"] is True
    assert snapshot["costUsd"] > 0


def test_the_turn_counter_is_the_ledger():
    agent = _agent(Metered())

    agent.chat("在吗")
    agent.chat("你好")

    assert agent.turn_count == agent.session_usage.snapshot()["turns"] == 2


def test_a_remembered_preference_costs_nothing():
    agent = _agent(Metered())

    agent.chat("记住：回答要短")

    assert agent.session_usage.snapshot()["turns"] == 0


def test_an_owner_command_costs_nothing():
    agent = _agent(Metered())

    agent.chat("【查看我的全部档案】")

    assert agent.session_usage.snapshot()["turns"] == 0


def test_the_retry_after_an_empty_answer_is_counted_too():
    agent = _agent(Metered(reply="…"))

    agent.chat("在吗")

    # Two calls were made and paid for, even though the visitor saw one reply.
    assert agent.session_usage.snapshot()["turns"] == 2


def test_a_provider_that_reports_nothing_makes_the_total_a_lower_bound():
    agent = _agent(Silent())

    agent.chat("在吗")

    snapshot = agent.session_usage.snapshot()
    assert snapshot["turns"] == 1
    assert snapshot["unmeasured"] == 1
    assert snapshot["costKnown"] is False
    assert snapshot["promptTokens"] == 0


def test_the_agent_passes_the_finish_reason_to_the_ledger():
    class CutOff(Metered):
        def generate(self, messages, **kwargs):  # noqa: ANN001, ANN003
            reply = super().generate(messages, **kwargs)
            self.last_finish = "max_tokens"
            return reply

    agent = _agent(CutOff())

    agent.chat("写一篇长文")

    assert agent.session_usage.snapshot()["truncated"] == 1
