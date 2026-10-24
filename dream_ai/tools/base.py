"""Abstract tool interface.

Tools extend what the agent can do beyond conversation: web search, file
access, calculators, and so on. Each tool declares a JSON Schema for its
arguments, a risk level, and whether an explicit user confirmation is needed
before it runs.
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

    @property
    def parameters(self) -> dict[str, Any]:
        """JSON Schema (OpenAI function-calling style) for the arguments."""
        return {"type": "object", "properties": {}, "required": []}

    @property
    def risk(self) -> str:
        """Risk level: ``safe`` (read-only, reversible) or ``protected`` (side
        effect, sandbox access, or network access)."""
        return "safe"

    @property
    def requires_confirmation(self) -> bool:
        """Whether an explicit user confirmation is required before execution."""
        return False

    @abstractmethod
    def run(self, **kwargs: Any) -> str:
        """Execute the tool and return a plain-text result."""

    def to_schema(self) -> dict[str, Any]:
        """Return the tool metadata in a serializable schema form."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "risk": self.risk,
            "requires_confirmation": self.requires_confirmation,
        }
