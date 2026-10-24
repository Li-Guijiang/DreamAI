"""Local date and time utility tool."""

from __future__ import annotations

import datetime
from typing import Any

from ..base import Tool


class ClockTool(Tool):
    """Return the current local date, time, and weekday."""

    @property
    def name(self) -> str:
        return "clock"

    @property
    def description(self) -> str:
        return "Return the current local date, time, timezone, and weekday."

    @property
    def parameters(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}, "required": []}

    def run(self, **kwargs: Any) -> str:
        now = datetime.datetime.now().astimezone()
        return (
            f"Current local time: {now.strftime('%Y-%m-%d %H:%M:%S %z')}\n"
            f"Weekday: {now.strftime('%A')}"
        )
