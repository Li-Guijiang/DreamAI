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


class Metered:
    """A provider that reports counts, like a hosted one."""

    name = "metered"
    model = "gpt-4o"

    def __init__(self) -> None:
        self.last_usage: dict[str, int] = {}

    def generate(self, messages, **kwargs):  # noqa: ANN001, ANN003
        self.last_usage = {"prompt_tokens": 2000, "completion_tokens": 100, "cached_tokens": 1500}
        return "好的。"


def test_the_stats_block_reports_turns_tier_and_history():
    agent = DreamAIAgent(provider=Recording(), preferences=PreferenceMemory(), system_prompt="BASE")
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
    agent = DreamAIAgent(provider=Recording(), preferences=PreferenceMemory(), system_prompt="BASE")

    console = PlainConsole()
    _print_stats(agent, console)

    assert "n/a (no model turn yet)" in "\n".join(console.lines)


def test_tokens_and_cost_are_printed_when_the_provider_reports_them():
    agent = DreamAIAgent(provider=Metered(), preferences=PreferenceMemory(), system_prompt="BASE")
    agent.chat("在吗")

    console = PlainConsole()
    _print_stats(agent, console)
    joined = "\n".join(console.lines)

    assert "in 2,000 / out 100 / cached 1,500 (75%)" in joined
    # 500 fresh input at 2.5/M + 1500 cached at 1.25/M + 100 out at 10/M = 0.004125,
    # printed to four decimals because a fraction of a cent is noise.
    assert "$0.0041" in joined


def test_a_provider_that_reports_nothing_says_so_instead_of_showing_zero():
    agent = DreamAIAgent(provider=Recording(), preferences=PreferenceMemory(), system_prompt="BASE")
    agent.chat("在吗")

    console = PlainConsole()
    _print_stats(agent, console)
    joined = "\n".join(console.lines)

    assert "none reported yet" in joined
    assert "unknown (no price for this model" in joined
    assert "$0.00" not in joined


def test_a_free_priced_model_reads_as_free():
    agent = DreamAIAgent(provider=Metered(), preferences=PreferenceMemory(), system_prompt="BASE")
    agent.session_usage.record("glm-4-flash", {"prompt_tokens": 10, "completion_tokens": 10})

    console = PlainConsole()
    _print_stats(agent, console)

    assert "cost            free" in "\n".join(console.lines)


def test_truncated_turns_have_their_own_line():
    agent = DreamAIAgent(provider=Metered(), preferences=PreferenceMemory(), system_prompt="BASE")
    agent.session_usage.record("gpt-4o", {"prompt_tokens": 10, "completion_tokens": 10}, "length")

    console = PlainConsole()
    _print_stats(agent, console)

    assert "truncated       1" in "\n".join(console.lines)
