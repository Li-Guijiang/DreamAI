"""Persistent session history backed by a JSON file.

The system prompt stays in memory (it is recomposed on startup); only the
user/assistant turns are written to disk so the conversation can be restored
after the process exits.
"""

from __future__ import annotations

from pathlib import Path

from ..providers.local import DEMO_PREFIX
from .base import Memory
from .session_memory import InMemorySessionMemory
from .storage import read_json, write_json_atomic


def _is_demo_reply(message: dict[str, str]) -> bool:
    """True for an offline placeholder assistant reply that must not persist."""
    return message.get("role") == "assistant" and (message.get("content") or "").strip().startswith(
        DEMO_PREFIX
    )


class PersistentSessionMemory(Memory):
    """Session history that survives restarts through a JSON file."""

    def __init__(
        self,
        system_prompt: str | None = None,
        file_path: Path | str | None = None,
    ) -> None:
        self._core = InMemorySessionMemory(system_prompt)
        self._file = Path(file_path) if file_path is not None else None
        self._restore()

    def append(self, role: str, content: str) -> None:
        self._core.append(role, content)
        self._persist()

    def messages(self) -> list[dict[str, str]]:
        return self._core.messages()

    def clear(self) -> None:
        self._core.clear()
        self._persist()

    def set_system_prompt(self, system_prompt: str | None) -> None:
        """Replace the system prompt; it is only held in memory, never on disk."""
        self._core.set_system_prompt(system_prompt)

    def _restore(self) -> None:
        """Load previously saved user/assistant turns from disk."""
        if self._file is None:
            return
        data = read_json(self._file, {})
        for message in data.get("messages", []):
            role = message.get("role")
            content = (message.get("content") or "").strip()
            if role in {"user", "assistant"} and content and not _is_demo_reply(message):
                self._core.append(role, content)

    def _persist(self) -> None:
        """Write the saved turns (excluding the system prompt) to disk."""
        if self._file is None:
            return
        history = [
            message
            for message in self.messages()
            if message["role"] != "system" and not _is_demo_reply(message)
        ]
        write_json_atomic(self._file, {"messages": history})
