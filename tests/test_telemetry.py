"""The turn log line must stay greppable and complete."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))

from app.telemetry import format_turn_log  # noqa: E402


def test_line_carries_every_field_in_a_fixed_order():
    line = format_turn_log(
        "req_abc12345",
        tier="deep",
        intent="error",
        ttft=0.84,
        total=6.21,
        chars=812,
        model="deepseek-chat",
    )

    assert line.startswith("chat done id=req_abc12345 ")
    assert "tier=deep" in line
    assert "intent=error" in line
    assert "ttft=0.84s" in line
    assert "total=6.21s" in line
    assert "chars=812" in line
    assert "model=deepseek-chat" in line


def test_outcome_can_mark_a_failure():
    line = format_turn_log(
        "req_x",
        tier="light",
        intent="chat",
        ttft=0.0,
        total=1.5,
        chars=0,
        model="m",
        outcome="failed",
    )

    assert line.startswith("chat failed ")
    assert "ttft=0.00s" in line
