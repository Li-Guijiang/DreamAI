"""Sandboxed file read/write tools confined to a workspace directory.

Paths are always resolved against the configured workspace root. Absolute paths
and any path that escapes the sandbox (``..`` traversal) are rejected. Writing
is marked ``requires_confirmation`` so the agent core can ask the user before
changing files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ...exceptions import ToolError
from ..base import Tool

_MAX_READ_CHARS = 2000


class _SandboxedFileTool(Tool):
    """Shared sandbox resolution for file tools."""

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()

    def _resolve(self, path: str | None) -> Path:
        if not path or not str(path).strip():
            raise ToolError(f"{self.name} requires a non-empty 'path' argument.")

        candidate = Path(str(path).strip())
        if candidate.is_absolute():
            raise ToolError("Absolute paths are not allowed; use a workspace-relative path.")

        target = (self._root / candidate).resolve()
        if not target.is_relative_to(self._root):
            raise ToolError(f"Path escapes the workspace sandbox: {path!r}")
        return target


class FileReadTool(_SandboxedFileTool):
    """Read a text file from the sandboxed workspace directory."""

    @property
    def name(self) -> str:
        return "file_read"

    @property
    def description(self) -> str:
        return "Read a text file located inside the sandboxed workspace directory."

    @property
    def risk(self) -> str:
        return "protected"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Workspace-relative file path to read.",
                }
            },
            "required": ["path"],
        }

    def run(self, path: str | None = None, **kwargs: Any) -> str:
        target = self._resolve(path)
        if not target.is_file():
            raise ToolError(f"File not found: {path}")

        content = target.read_text(encoding="utf-8", errors="replace")
        if len(content) > _MAX_READ_CHARS:
            content = content[:_MAX_READ_CHARS] + "\n...[truncated]"
        return f"--- {path} ---\n{content}"


class FileWriteTool(_SandboxedFileTool):
    """Write a text file inside the sandboxed workspace directory."""

    @property
    def name(self) -> str:
        return "file_write"

    @property
    def description(self) -> str:
        return "Write text to a file inside the sandboxed workspace directory."

    @property
    def risk(self) -> str:
        return "protected"

    @property
    def requires_confirmation(self) -> bool:
        return True

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Workspace-relative file path to write.",
                },
                "content": {
                    "type": "string",
                    "description": "Text content to write to the file.",
                },
            },
            "required": ["path", "content"],
        }

    def run(self, path: str | None = None, content: str = "", **kwargs: Any) -> str:
        target = self._resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(str(content), encoding="utf-8")
        return f"Wrote {len(str(content))} characters to {path}."
