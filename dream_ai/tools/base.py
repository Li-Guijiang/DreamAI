"""Abstract tool interface (framework for v0.3).

Tools extend what the agent can do beyond conversation: web search, file
access, calculators, and so on. v0.1 ships the registry contract only; real
tools are wired up in v0.3.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Tool(ABC):
    """A callable capability the agent can invoke."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool name used by the agent to select it."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what the tool does."""

    @abstractmethod
    def run(self, **kwargs: Any) -> str:
        """Execute the tool and return a plain-text result."""
