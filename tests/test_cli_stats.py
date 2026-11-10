"""The CLI must be able to show what a session has spent."""

from __future__ import annotations

from dream_ai.cli import _print_stats
from dream_ai.core.agent import DreamAIAgent
from dream_ai.memory import PreferenceMemory
from dream_ai.ui import Console


class PlainConsole(Console):
    """Collect lines instead of writing them."""

    def __init__(self) -> None:
        self.lines: list[str] = []

    def line(self, text: str) -> None:  # noqa: D102 - duck type of the real console
        self.lines.append(text)

    def muted(self, text: str) -> str:  # noqa: D102
        return text


class Recording:
    name = "fake-provider"

    def generate(self, messages, **kwargs):  # noqa: ANN001, ANN003
        return "好的。"


def test_the_stats_block_reports_turns_tier_and_history():
    agent = DreamAIAgent(
        provider=Recording(), preferences=PreferenceMemory(), system_prompt="BASE"
    )
    agent.chat("在吗")
    agent.chat("记住：我喜欢简短的回答")

    console = PlainConsole()
    _print_stats(agent, console)

    joined = "\n".join(console.lines)
    assert "model turns     1" in joined
    assert "last tier       light" in joined
    assert "preferences     1" in joined
    assert "history entries" in joined


def test_a_fresh_session_reports_no_tier_yet():
    agent = DreamAIAgent(
        provider=Recording(), preferences=PreferenceMemory(), system_prompt="BASE"
    )

    console = PlainConsole()
    _print_stats(agent, console)

    assert "n/a (no model turn yet)" in "\n".join(console.lines)
