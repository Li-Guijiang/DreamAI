"""Small JSON persistence helpers shared by memory backends.

Writes are atomic (temp file + replace) so an interrupted save cannot corrupt
an existing memory file.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def ensure_parent(path: Path) -> None:
    """Create the parent directory of ``path`` if it does not exist."""
    path.parent.mkdir(parents=True, exist_ok=True)


def read_json(path: Path, default: Any) -> Any:
    """Read JSON from ``path``; return ``default`` when missing or malformed."""
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default


def write_json_atomic(path: Path, payload: Any) -> None:
    """Write ``payload`` as UTF-8 JSON atomically via a temporary file."""
    ensure_parent(path)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    os.replace(temporary, path)
