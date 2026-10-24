"""Minimal non-interactive example: ask Dream AI one question and print the reply.

Run from the repository root:
    python examples/basic_chat.py

Reads configuration from the environment / `.env`; falls back to the offline
local provider when no API key is configured.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running this script directly: python examples/basic_chat.py
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dream_ai.config import load_settings
from dream_ai.core import DreamAIAgent
from dream_ai.providers import build_provider


def main() -> None:
    settings = load_settings()
    provider = build_provider(settings)
    agent = DreamAIAgent(provider=provider, system_prompt=settings.system_prompt)

    question = "Hello Dream AI, what is a dream?"
    print(f"you › {question}")
    print(f"dream-ai › {agent.chat(question)}")


if __name__ == "__main__":
    main()
