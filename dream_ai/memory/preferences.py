"""Long-term user preferences remembered across sessions.

Preferences are stored separately from the conversation history so they survive
a cleared session and can be injected into the system prompt for every reply.
"""

from __future__ import annotations

from pathlib import Path

from ..exceptions import DreamAIError
from .storage import read_json, write_json_atomic


class PreferenceMemory:
    """A de-duplicated list of remembered user preferences."""

    def __init__(self, file_path: Path | str | None = None) -> None:
        self._file = Path(file_path) if file_path is not None else None
        self._notes: list[str] = self._load()

    def remember(self, text: str) -> None:
        """Record a preference, ignoring duplicates and blank input."""
        note = " ".join(text.split())
        if not note:
            raise DreamAIError("Preference text cannot be empty.")
        if note in self._notes:
            return
        self._notes.append(note)
        self._save()

    def list(self) -> list[str]:
        """Return a copy of the remembered preferences."""
        return list(self._notes)

    def forget(self) -> None:
        """Clear all remembered preferences."""
        self._notes = []
        self._save()

    def system_context(self) -> str:
        """Render preferences as a system-prompt section, or empty when none."""
        if not self._notes:
            return ""
        lines = "\n".join(f"- {note}" for note in self._notes)
        return (
            "Remember the following user preferences and account for them "
            "naturally in your replies:\n" + lines
        )

    def _load(self) -> list[str]:
        if self._file is None:
            return []
        data = read_json(self._file, {})
        return [str(item) for item in data.get("preferences", []) if str(item).strip()]

    def _save(self) -> None:
        if self._file is None:
            return
        write_json_atomic(self._file, {"preferences": self._notes})
