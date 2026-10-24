"""Non-interactive demo: run a small autonomous task through the v0.4 loop.

Run from the repository root:
    python examples/autonomy_demo.py

Uses the offline planner and the safe built-in tools; no API key is required.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running this script directly: python examples/autonomy_demo.py
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dream_ai.agent_factory import build_agent
from dream_ai.autonomy import TraceEntry
from dream_ai.config import load_settings


def _print_event(entry: TraceEntry) -> None:
    """Print one live autonomy trace event."""
    step = f"step {entry.step_index + 1}" if entry.step_index is not None else "plan"
    print(f"  [{entry.phase.value}] {step}: {entry.content}")


def main() -> None:
    agent = build_agent(load_settings())
    objective = "What time is it now, and calculate 12 * 7?"

    print(f"you › /run {objective}\n")
    result = agent.autonomous_task(objective, on_event=_print_event)

    print("\nPlan:")
    for index, step in enumerate(result.steps, start=1):
        print(f"  {index}. [{step.status.value}] {step.title}")
        if step.observation:
            print(f"      observation: {step.observation}")

    print(f"\n{result.final_summary}\n")


if __name__ == "__main__":
    main()
