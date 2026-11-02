"""The prompt is paid for on every request, so the note list is bounded."""

from __future__ import annotations

import pytest

from dream_ai.exceptions import DreamAIError
from dream_ai.memory import PreferenceMemory


def test_notes_are_deduplicated():
    memory = PreferenceMemory()
    memory.remember("主用 VSCode")
    memory.remember("主用 VSCode ")

    assert memory.list() == ["主用 VSCode"]


def test_the_cap_refuses_rather_than_truncates():
    memory = PreferenceMemory()
    for index in range(PreferenceMemory.MAX_NOTES):
        memory.remember(f"事实 {index}")

    with pytest.raises(DreamAIError, match="记忆已满"):
        memory.remember("第 201 条")

    assert len(memory.list()) == PreferenceMemory.MAX_NOTES
    assert "第 201 条" not in memory.list()


def test_duplicate_at_the_cap_is_still_a_no_op():
    memory = PreferenceMemory()
    for index in range(PreferenceMemory.MAX_NOTES):
        memory.remember(f"事实 {index}")

    memory.remember("事实 0")  # already present, must not raise
    assert len(memory.list()) == PreferenceMemory.MAX_NOTES


def test_clearing_frees_room_again():
    memory = PreferenceMemory()
    for index in range(PreferenceMemory.MAX_NOTES):
        memory.remember(f"事实 {index}")

    memory.forget()
    memory.remember("清理后新增")

    assert memory.list() == ["清理后新增"]
