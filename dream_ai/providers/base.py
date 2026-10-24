"""Abstract interface for an LLM provider.

The agent core depends only on :class:`LLMProvider`, so any backend — hosted
API, local open-source model, or a future custom model — can be swapped in
without rewriting the agent.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    """A backend that turns a conversation into a reply."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider identifier."""

    @abstractmethod
    def generate(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        """Produce a reply from the given message history.

        Args:
            messages: Ordered list of ``{"role": ..., "content": ...}``.
            **kwargs: Provider-specific generation options (temperature, etc.).

        Returns:
            The assistant's reply as plain text.
        """
