"""Tool registry that maps tool names to :class:`Tool` instances."""

from __future__ import annotations

from typing import Any

from ..exceptions import ToolError
from .base import Tool


class ToolRegistry:
    """Register, list, look up, and execute tools by name."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ToolError(f"Tool already registered: {tool.name!r}")
        self._tools[tool.name] = tool

    def names(self) -> list[str]:
        return sorted(self._tools)

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise ToolError(f"Unknown tool: {name!r}") from exc

    def schemas(self) -> list[dict[str, Any]]:
        """Serializable metadata for every registered tool."""
        return [tool.to_schema() for tool in self._tools.values()]

    def execute(self, name: str, **kwargs: Any) -> str:
        tool = self.get(name)
        try:
            return tool.run(**kwargs)
        except ToolError:
            raise
        except Exception as exc:  # normalize unexpected tool failures
            raise ToolError(f"Tool {name!r} failed: {exc}") from exc
