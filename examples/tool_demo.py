"""Non-interactive demo: list tools and run the safe built-in tools.

Run from the repository root:
    python examples/tool_demo.py

File and web tools are disabled until their permission switches are enabled;
this demo only uses the safe, always-registered tools.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running this script directly: python examples/tool_demo.py
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dream_ai.agent_factory import build_agent
from dream_ai.config import load_settings


def main() -> None:
    agent = build_agent(load_settings())

    print("Registered tools:")
    for schema in agent.list_tools():
        confirmation = " (needs confirmation)" if schema["requires_confirmation"] else ""
        print(f"  - {schema['name']} [{schema['risk']}]{confirmation}")
    print()

    expressions = ["2 + 3 * 4", "(12 + 8) / 5", "sqrt(144)"]
    for expression in expressions:
        print(agent.execute_tool("calculator", expression=expression))
    print()
    print(agent.execute_tool("clock"))


if __name__ == "__main__":
    main()
