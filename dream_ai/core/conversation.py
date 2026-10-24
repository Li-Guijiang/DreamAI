"""Conversation: user/assistant message flow backed by a Memory backend."""

from __future__ import annotations

from ..memory.base import Memory


class Conversation:
    """High-level read/write operations on the current conversation."""

    def __init__(self, memory: Memory) -> None:
        self._memory = memory

    def add_user(self, text: str) -> None:
        self._memory.append("user", text)

    def add_assistant(self, text: str) -> None:
        self._memory.append("assistant", text)

    def history(self) -> list[dict[str, str]]:
        return self._memory.messages()

    def clear(self) -> None:
        self._memory.clear()
