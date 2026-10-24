"""Tool registry that maps tool names to :class:`Tool` instances."""

from __future__ import annotations

from typing import Any

from ..exceptions import DreamAIError
from .base import Tool


class ToolRegistry:
    """Register, list, look up, and execute tools by name."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise DreamAIError(f"Tool already registered: {tool.name!r}")
        self._tools[tool.name] = tool

    def names(self) -> list[str]:
        return sorted(self._tools)

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise DreamAIError(f"Unknown tool: {name!r}") from exc

    def execute(self, name: str, **kwargs: Any) -> str:
        return self.get(name).run(**kwargs)
