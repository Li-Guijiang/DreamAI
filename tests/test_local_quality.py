"""Post-processing that only the non-streaming surfaces can do."""

from __future__ import annotations

from dream_ai.core.agent import DreamAIAgent
from dream_ai.memory import PreferenceMemory
from dream_ai.quality import close_fences, dedupe_sentences, looks_empty


def test_open_fence_is_closed():
    assert close_fences("看：\n```python\nprint(1)").endswith("\n```")


def test_closed_fence_survives():
    text = "```bash\nls\n```\n完成"

    assert close_fences(text) == text


def test_back_to_back_repeat_is_removed():
    assert dedupe_sentences("先改配置。先改配置。再重启。") == "先改配置。再重启。"


def test_empty_detection():
    assert looks_empty("  ")
    assert looks_empty("。")
    assert not looks_empty("可以，先改端口。")


class EmptyThenAnswer:
    """First call returns nothing, the retry answers."""

    def __init__(self) -> None:
        self.calls = 0

    def generate(self, messages):  # noqa: ANN001
        self.calls += 1
        return "" if self.calls == 1 else "答案是 B。"


def test_empty_reply_triggers_one_retry():
    provider = EmptyThenAnswer()
    agent = DreamAIAgent(provider=provider, preferences=PreferenceMemory(), system_prompt="base")

    assert agent.chat("选哪个") == "答案是 B。"
    assert provider.calls == 2


class AlwaysEmpty:
    def generate(self, messages):  # noqa: ANN001
        return ""


def test_still_empty_after_retry_is_reported_honestly():
    agent = DreamAIAgent(provider=AlwaysEmpty(), preferences=PreferenceMemory(), system_prompt="base")

    assert "重试" in agent.chat("在吗")


class FencedReply:
    def generate(self, messages):  # noqa: ANN001
        return "代码如下：\n```java\nint a = 1;"


def test_unclosed_fence_is_repaired_on_the_way_out():
    agent = DreamAIAgent(provider=FencedReply(), preferences=PreferenceMemory(), system_prompt="base")

    assert agent.chat("写一行").rstrip().endswith("```")
