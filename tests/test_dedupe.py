"""A repeated turn must not be sent to the model twice."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))

from app.quality import dedupe_messages  # noqa: E402


def test_consecutive_duplicate_is_dropped():
    messages = [
        {"role": "user", "content": "你好"},
        {"role": "user", "content": "你好"},
    ]

    assert dedupe_messages(messages) == [{"role": "user", "content": "你好"}]


def test_same_text_with_different_roles_survives():
    messages = [
        {"role": "user", "content": "好的"},
        {"role": "assistant", "content": "好的"},
    ]

    assert len(dedupe_messages(messages)) == 2


def test_whitespace_only_difference_counts_as_duplicate():
    messages = [
        {"role": "user", "content": "在吗 "},
        {"role": "user", "content": "在吗"},
    ]

    assert len(dedupe_messages(messages)) == 1


def test_non_consecutive_repeat_survives():
    messages = [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好，有什么可以帮你"},
        {"role": "user", "content": "你好"},
    ]

    assert len(dedupe_messages(messages)) == 3


def test_input_is_not_mutated():
    messages = [{"role": "user", "content": "a"}, {"role": "user", "content": "a"}]
    dedupe_messages(messages)

    assert len(messages) == 2
