"""Parse structured tool-call blocks out of plain model text.

A model (or a future provider that emits native ``tool_calls``) may embed one
or more blocks in its reply::

    <<TOOL {"name": "calculator", "arguments": {"expression": "12 * (3 + 4)"}}>>

The parser only extracts the call; it does not run the tool. The agent checks
the name against its registry before executing anything. This convention works
offline and with any OpenAI-compatible model.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from ..exceptions import ToolError

_BLOCK_PATTERN = re.compile(r"<<TOOL\s*(\{.*?\})\s*>>", re.DOTALL)


@dataclass(frozen=True)
class ToolCall:
    """A single parsed tool invocation."""

    name: str
    arguments: dict[str, Any]
    raw: str


def parse_tool_calls(text: str) -> list[ToolCall]:
    """Return every tool-call block found in ``text``; empty list when none."""
    calls: list[ToolCall] = []
    for match in _BLOCK_PATTERN.finditer(text or ""):
        raw = match.group(0)
        payload = match.group(1)
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise ToolError(f"Invalid tool-call JSON: {raw}") from exc
        if not isinstance(data, dict):
            raise ToolError(f"Tool call must be a JSON object: {raw}")

        name = data.get("name")
        arguments = data.get("arguments", {})
        if not isinstance(name, str) or not name.strip():
            raise ToolError(f"Tool call missing a valid name: {raw}")
        if not isinstance(arguments, dict):
            raise ToolError(f"Tool arguments must be an object: {raw}")

        calls.append(ToolCall(name=name.strip(), arguments=arguments, raw=raw))
    return calls
