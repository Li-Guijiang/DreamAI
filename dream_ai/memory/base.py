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
