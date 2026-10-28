"""Abstract memory interface.

v0.2 will add persistent long-term and vector memory; every backend will
implement this same interface so the agent core does not change.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class Memory(ABC):
    """Stores ordered conversation messages and returns them to the model."""

    @abstractmethod
    def append(self, role: str, content: str) -> None:
        """Append a message. Roles are ``system``, ``user``, ``assistant``."""

    @abstractmethod
    def messages(self) -> list[dict[str, str]]:
        """Return a copy of the stored message history."""

    @abstractmethod
    def clear(self) -> None:
        """Reset memory, keeping the system prompt if one is stored."""

    @abstractmethod
    def set_system_prompt(self, system_prompt: str | None) -> None:
        """Replace the stored system prompt and keep the conversation turns.

        The agent calls this whenever the effective prompt changes (on start-up
        and after a remembered preference is added or cleared), so the prompt
        that reaches the provider is always the current one. Implementations
        must keep the prompt in the position the model expects — first message.
        """
