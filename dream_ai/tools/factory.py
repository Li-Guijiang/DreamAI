"""Assemble the default tool registry from :class:`Settings`.

Safe, read-only tools are registered by default. File and network tools are
registered only when their explicit permission switch is enabled, so the
agent's capability surface stays opt-in.
"""

from __future__ import annotations

from ..config import Settings
from .builtin.calculator import CalculatorTool
from .builtin.clock import ClockTool
from .builtin.files import FileReadTool, FileWriteTool
from .builtin.web_search import WebSearchTool
from .registry import ToolRegistry


def build_tool_registry(settings: Settings) -> ToolRegistry:
    """Return a registry populated according to the tool permission switches."""
    registry = ToolRegistry()
    if not settings.tools_enabled:
        return registry

    registry.register(CalculatorTool())
    registry.register(ClockTool())

    if settings.file_access_enabled:
        registry.register(FileReadTool(settings.workspace_dir))
        registry.register(FileWriteTool(settings.workspace_dir))

    if settings.web_search_enabled:
        registry.register(WebSearchTool())

    return registry
