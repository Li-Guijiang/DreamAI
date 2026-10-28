"""In-memory session history (v0.1 baseline).

Keeps a single conversation in RAM for the lifetime of the process. Long-term,
cross-session memory arrives in v0.2.
"""

from __future__ import annotations

from ..exceptions import DreamAIError
from .base import Memory

_VALID_ROLES = {"system", "user", "assistant"}


class InMemorySessionMemory(Memory):
    """A simple system-prompt-prefixed conversation buffer."""

    def __init__(self, system_prompt: str | None = None) -> None:
        self._messages: list[dict[str, str]] = []
        self._system_prompt = system_prompt.strip() if system_prompt else ""
        if self._system_prompt:
            self._messages.append({"role": "system", "content": self._system_prompt})

    def append(self, role: str, content: str) -> None:
        if role not in _VALID_ROLES:
            raise DreamAIError(f"Invalid message role: {role!r}")
        if not content.strip():
            raise DreamAIError("Cannot append an empty message.")
        self._messages.append({"role": role, "content": content})

    def messages(self) -> list[dict[str, str]]:
        return [dict(message) for message in self._messages]

    def clear(self) -> None:
        self._messages = []
        if self._system_prompt:
            self._messages.append({"role": "system", "content": self._system_prompt})

    def set_system_prompt(self, system_prompt: str | None) -> None:
        """Replace the system prompt while keeping the conversation turns."""
        self._system_prompt = system_prompt.strip() if system_prompt else ""
        self._messages = [message for message in self._messages if message["role"] != "system"]
        if self._system_prompt:
            self._messages.insert(0, {"role": "system", "content": self._system_prompt})
