"""Smoke tests for the DreamAIAgent using the offline local provider."""

from dream_ai.core import DreamAIAgent
from dream_ai.providers import LocalEchoProvider
from dream_ai.tools import ToolRegistry


def _make_agent() -> DreamAIAgent:
    return DreamAIAgent(provider=LocalEchoProvider(), system_prompt="You are Dream AI.")


def test_chat_returns_nonempty_reply():
    agent = _make_agent()

    reply = agent.chat("Tell me about dreams")

    assert isinstance(reply, str)
    assert reply.strip()


def test_chat_persists_turns_in_history():
    agent = _make_agent()
    agent.chat("First question")

    roles = [msg["role"] for msg in agent.history]

    assert "system" in roles
    assert "user" in roles
    assert "assistant" in roles


def test_reset_clears_turns_but_keeps_system():
    agent = _make_agent()
    agent.chat("A question")
    agent.reset()

    history = agent.history

    assert len(history) == 1
    assert history[0]["role"] == "system"


def test_agent_exposes_empty_tool_registry_by_default():
    agent = _make_agent()

    assert isinstance(agent.tools, ToolRegistry)
    assert agent.tools.names() == []
