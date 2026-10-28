"""Command-line interface for Dream AI.

Run with:
    python -m dream_ai
or, after installing the package:
    dream-ai
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from typing import Any

from .agent_factory import build_agent
from .autonomy import PlanStep, TraceEntry
from .config import Settings, load_settings
from .core import DreamAIAgent
from .exceptions import ConfigurationError, ProviderError, ToolConfirmationRequired, ToolError

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
  /run <objective> Run an autonomous multi-step task (plan → act → observe → reflect)
  /trace           Show the plan, steps, and trace of the last autonomous task
  /tools           List registered tools and their parameters
  /tool <name> <json>  Run a tool with JSON arguments, e.g.
                   /tool calculator {"expression": "2 * (3 + 4)"}
  /remember <text> Record a preference to long-term memory
  /memory          Show remembered preferences
  /forget          Clear all remembered preferences
  /clear           Clear the conversation history
  /about           Show provider, tools, autonomy, session info, and preferences
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
    print(f"Memory: {mode} ({location})")
    autonomy = "on" if settings.autonomy_enabled else "off"
    print(
        f"Autonomy: {autonomy} (max steps: {settings.max_steps}, retries: {settings.max_retries})"
    )
    print(f"Tools: {len(agent.tool_names)} registered\n")


def _print_tools(agent: DreamAIAgent) -> None:
    schemas = agent.list_tools()
    if not schemas:
        print("No tools registered. Set DREAMAI_TOOLS_ENABLED=true to enable tools.\n")
        return

    print("Registered tools:")
    for tool in schemas:
        confirmation = " (needs confirmation)" if tool["requires_confirmation"] else ""
        print(f"  - {tool['name']} [{tool['risk']}]{confirmation}")
        print(f"      {tool['description']}")
        required = tool["parameters"].get("required", [])
        if required:
            print(f"      arguments: {', '.join(required)}")
    print()


def _run_tool(agent: DreamAIAgent, rest: str) -> None:
    rest = rest.strip()
    if not rest:
        print('Usage: /tool <name> <json>  e.g. /tool calculator {"expression": "2+3"}\n')
        return

    name, _, args_text = rest.partition(" ")
    name = name.strip()
    args_text = args_text.strip()

    arguments: dict[str, Any] = {}
    if args_text:
        try:
            parsed = json.loads(args_text)
        except json.JSONDecodeError as exc:
            print(f"⚠ Invalid tool arguments: {exc}\n")
            return
        if not isinstance(parsed, dict):
            print("⚠ Tool arguments must be a JSON object.\n")
            return
        arguments = parsed

    try:
        result = agent.execute_tool(name, confirmed=False, **arguments)
    except ToolConfirmationRequired as exc:
        answer = input(f"Tool '{exc.tool_name}' will modify files. Confirm? [y/N] ").strip().lower()
        if answer not in {"y", "yes"}:
            print("Tool call cancelled.\n")
            return
        try:
            result = agent.execute_tool(name, confirmed=True, **arguments)
        except ToolError as tool_exc:
            print(f"⚠ Tool error: {tool_exc}\n")
            return
    except ToolError as exc:
        print(f"⚠ Tool error: {exc}\n")
        return

    print(f"tool › {result}\n")


# --- Autonomous mode ---------------------------------------------------------


def _confirm_action(step: PlanStep, tool_name: str, arguments: dict[str, Any]) -> bool:
    """Interactive approval gate for protected autonomous actions."""
    print(f"⚠ Protected action '{tool_name}' {arguments}")
    answer = input("Confirm this action? [y/N] ").strip().lower()
    return answer in {"y", "yes"}


def _print_event(entry: TraceEntry) -> None:
    """Print one live autonomy trace event (verbose mode)."""
    step = f"step {entry.step_index + 1}" if entry.step_index is not None else "plan"
    print(f"  [{entry.phase.value}] {step}: {entry.content}")


def _run_autonomous(agent: DreamAIAgent, settings: Settings, objective: str) -> None:
    if not settings.autonomy_enabled:
        print("⚠ Autonomous mode is disabled (DREAMAI_AUTONOMY_ENABLED=false).\n")
        return
    if not objective:
        print("Usage: /run <objective>  e.g. /run what time is it and calculate 12 * 7\n")
        return

    on_event = _print_event if settings.autonomy_verbose else None

    try:
        result = agent.autonomous_task(
            objective,
            confirmation_callback=_confirm_action,
            on_event=on_event,
        )
    except ConfigurationError as exc:
        print(f"⚠ {exc}\n")
        return

    if not settings.autonomy_verbose:
        print("\nPlan:")
        for index, step in enumerate(result.steps, start=1):
            print(f"  {index}. [{step.status.value}] {step.title}")
            if step.observation:
                print(f"      observation: {step.observation}")
            if step.error:
                print(f"      error: {step.error}")
        print()

    print(result.final_summary)
    print()


def _print_trace(agent: DreamAIAgent) -> None:
    result = agent.last_execution
    if result is None:
        print("No autonomous task has run yet. Use /run <objective>.\n")
        return

    print(f"Last task: {result.objective}")
    print(
        f"Status: {result.status.value} "
        f"({len(result.succeeded_steps)}/{result.total_steps} steps succeeded)\n"
    )

    print("Plan:")
    for index, step in enumerate(result.steps, start=1):
        print(f"  {index}. [{step.status.value}] {step.title}")
        if step.observation:
            print(f"      observation: {step.observation}")
        if step.error:
            print(f"      error: {step.error}")

    print("\nTrace:")
    for entry in result.trace:
        step = f"step {entry.step_index + 1}" if entry.step_index is not None else "—"
        print(f"  [{entry.phase.value}] {step}: {entry.content}")
    print()


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

        if command.startswith("/run"):
            _, _, rest = user_input.partition(" ")
            _run_autonomous(agent, settings, rest.strip())
            continue

        if command == "/trace":
            _print_trace(agent)
            continue

        if command == "/tools":
            _print_tools(agent)
            continue

        if command.startswith("/tool"):
            _, _, rest = user_input.partition(" ")
            _run_tool(agent, rest)
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
            print(f"Tools: {len(agent.tool_names)} ({', '.join(agent.tool_names) or 'none'})")
            autonomy = "on" if agent.autonomy_enabled else "off"
            print(
                f"Autonomy: {autonomy} "
                f"(max steps: {settings.max_steps}, retries: {settings.max_retries})"
            )
            if agent.last_execution:
                print(f"Last autonomous task: {agent.last_execution.status.value}")
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
