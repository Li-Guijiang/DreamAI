"""Optional on-disk snapshot for the usage counters.

`/api/usage` is a process-lifetime view: restart the service and every number
goes back to zero, which makes a daily or weekly total impossible to read. This
module writes the counters to a file so a restart can pick up where it left off.

Four rules keep it from becoming a second database:

1. Off by default. No path, no file, no behaviour change.
2. Atomic replace. A reader never sees a half-written file, and a crash leaves
   the previous snapshot intact.
3. No personal data. Only aggregate counters - never an IP, a message, a model
   prompt, or a request id.
4. Failures are quiet and non-fatal. A full disk is an operational warning, not
   a reason to refuse a chat request.

The counters themselves are validated by `stats.UsageStats.import_counters`;
this module only guarantees that the file is a versioned JSON envelope.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

SNAPSHOT_VERSION = 1


def save_snapshot(path: str | os.PathLike[str] | None, counters: dict[str, Any]) -> bool:
    """Write ``counters`` atomically; return whether it worked."""
    if not path:
        return False
    target = Path(path)
    payload = {
        "version": SNAPSHOT_VERSION,
        "savedAt": round(time.time(), 3),
        "counters": counters,
    }
    temporary = target.with_name(target.name + ".tmp")
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        os.replace(temporary, target)
        return True
    except (OSError, TypeError, ValueError):
        # A stale .tmp must not be mistaken for a snapshot on the next start.
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        return False


def load_snapshot(path: str | os.PathLike[str] | None) -> dict[str, Any] | None:
    """The stored counters, or None when the file is absent, old or corrupt."""
    if not path:
        return None
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    if payload.get("version") != SNAPSHOT_VERSION:
        return None
    counters = payload.get("counters")
    return counters if isinstance(counters, dict) else None
