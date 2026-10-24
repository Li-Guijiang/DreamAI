"""Command-line interface for Dream AI.

Run with:
    python -m dream_ai
or, after installing the package:
    dream-ai
"""

from __future__ import annotations

import argparse
import dataclasses
import sys

from .agent_factory import build_agent
from .config import Settings, load_settings
from .core import DreamAIAgent
from .exceptions import ConfigurationError, ProviderError

BANNER = r"""
  ____  ____  __  __    _    __  __ _____
 |  _ \|  _ \|  \/  |  / \  |  \/  | ____|
 | |  \ | |_) | |\/| | / _ \ | |\/| |  _|
 | |__| |  _ <| |  | |/ ___ \| |  | | |___
 |_____/|_| \_\_|  |_/_/   \_\_|  |_|_____|
"""

HELP_TEXT = """\
Available commands:
  /help            Show this help message
  /remember <text> Record a preference to long-term memory
  /memory          Show remembered preferences
  /forget          Clear all remembered preferences
  /clear           Clear the conversation history
  /about           Show the active provider and session info
  /quit | /exit    Leave Dream AI
Type anything else to chat with Dream AI.
"""


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="dream-ai",
        description="Dream AI — a general-purpose AI assistant built around one shared dream.",
    )
    parser.add_argument(
        "--provider",
        choices=["openai_compat", "local"],
        default=None,
        help="Override the LLM provider.",
    )
    parser.add_argument("--model", default=None, help="Override the model name.")
    parser.add_argument("--base-url", default=None, help="Override the API base URL.")
    parser.add_argument("--api-key", default=None, help="Override the API key.")
    return parser.parse_args(argv)


def _apply_overrides(settings: Settings, args: argparse.Namespace) -> Settings:
    updates: dict[str, str] = {}
    if args.provider:
        updates["provider"] = args.provider
    if args.model:
        updates["model"] = args.model
    if args.base_url:
        updates["base_url"] = args.base_url
    if args.api_key:
        updates["api_key"] = args.api_key
    return dataclasses.replace(settings, **updates) if updates else settings


def _print_memory_status(agent: DreamAIAgent, settings: Settings) -> None:
    mode = "persistent" if settings.persistence_enabled else "in-memory"
    location = settings.data_dir if settings.persistence_enabled else "session only"
    print(f"Memory: {mode} ({location})\n")


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    settings = _apply_overrides(load_settings(), args)

    try:
        agent = build_agent(settings)
    except ConfigurationError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    print(BANNER)
    print("Welcome to Dream AI — type /help for commands, /quit to exit.\n")

    if agent.provider_name == "local-echo":
        print(
            "ℹ Offline demo mode: no hosted API key was configured, so Dream AI "
            "is running on the local placeholder provider.\n"
            "  Copy `.env.example` to `.env`, set DREAMAI_API_KEY, and restart to "
            "use a real model.\n"
        )
    else:
        print(f"Connected via provider: {agent.provider_name}\n")

    _print_memory_status(agent, settings)

    while True:
        try:
            user_input = input("you › ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye — keep dreaming.")
            return 0

        if not user_input:
            continue

        command = user_input.lower()

        if command in {"/quit", "/exit"}:
            print("Goodbye — keep dreaming.")
            return 0

        if command == "/help":
            print(HELP_TEXT)
            continue

        if command.startswith("/remember"):
            _, _, note = user_input.partition(" ")
            note = note.strip()
            if not note:
                print("Usage: /remember <your preference>\n")
                continue
            agent.remember(note)
            print("Saved to long-term memory.\n")
            continue

        if command == "/memory":
            notes = agent.preference_notes
            if not notes:
                print("No preferences remembered yet. Use /remember <text>.\n")
                continue
            print("Remembered preferences:")
            for index, note in enumerate(notes, start=1):
                print(f"  {index}. {note}")
            print()
            continue

        if command == "/forget":
            agent.forget_preferences()
            print("All remembered preferences cleared.\n")
            continue

        if command in {"/clear", "/reset"}:
            agent.reset()
            print("Conversation history cleared.\n")
            continue

        if command == "/about":
            turns = sum(1 for msg in agent.history if msg["role"] == "user")
            print(f"Provider: {agent.provider_name}")
            print(f"Model: {settings.model}")
            print(f"Messages sent this session: {turns}")
            print(f"Preferences remembered: {len(agent.preference_notes)}\n")
            continue

        try:
            reply = agent.chat(user_input)
        except ProviderError as exc:
            print(f"⚠ Provider error: {exc}\n")
            continue

        print(f"dream-ai › {reply}\n")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
