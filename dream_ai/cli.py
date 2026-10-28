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

from . import __version__
from .agent_factory import build_agent
from .autonomy import PlanStep, TraceEntry
from .config import Settings, load_settings
from .core import DreamAIAgent
from .exceptions import ConfigurationError, ProviderError, ToolConfirmationRequired, ToolError
from .ui import Console, prepare_output

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
  /motion          Toggle the terminal launch / typing / spinner effects
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
    parser.add_argument(
        "--no-animation",
        "--no-motion",
        action="store_true",
        dest="no_animation",
        help="Disable the launch sequence, typing effect, and spinner.",
    )
    return parser.parse_args(argv)


def _apply_overrides(settings: Settings, args: argparse.Namespace) -> Settings:
    updates: dict[str, object] = {}
    if args.provider:
        updates["provider"] = args.provider
    if args.model:
        updates["model"] = args.model
    if args.base_url:
        updates["base_url"] = args.base_url
    if args.api_key:
        updates["api_key"] = args.api_key
    if getattr(args, "no_animation", False):
        updates["animations_enabled"] = False
    return dataclasses.replace(settings, **updates) if updates else settings


def _print_memory_status(agent: DreamAIAgent, settings: Settings, ui: Console) -> None:
    mode = "persistent" if settings.persistence_enabled else "in-memory"
    location = settings.data_dir if settings.persistence_enabled else "session only"
    autonomy = "on" if settings.autonomy_enabled else "off"
    ui.line(f"{ui.muted('memory')}   {mode} {ui.muted(f'({location})')}")
    ui.line(
        f"{ui.muted('autonomy')} {autonomy} "
        f"{ui.muted(f'(max steps: {settings.max_steps}, retries: {settings.max_retries})')}"
    )
    ui.line(f"{ui.muted('tools')}    {len(agent.tool_names)} registered")
    ui.blank()


def _print_tools(agent: DreamAIAgent, ui: Console) -> None:
    schemas = agent.list_tools()
    if not schemas:
        ui.line(ui.muted("No tools registered. Set DREAMAI_TOOLS_ENABLED=true to enable tools."))
        ui.blank()
        return

    ui.line(ui.accent("Registered tools:"))
    for tool in schemas:
        confirmation = " (needs confirmation)" if tool["requires_confirmation"] else ""
        risk = tool["risk"]
        ui.line(f"  {ui.accent('›')} {tool['name']} {ui.muted(f'[{risk}]{confirmation}')}")
        ui.line(f"      {ui.muted(tool['description'])}")
        required = tool["parameters"].get("required", [])
        if required:
            ui.line(f"      {ui.muted('arguments:')} {', '.join(required)}")
    ui.blank()


def _run_tool(agent: DreamAIAgent, rest: str, ui: Console) -> None:
    rest = rest.strip()
    if not rest:
        ui.line('Usage: /tool <name> <json>  e.g. /tool calculator {"expression": "2+3"}')
        ui.blank()
        return

    name, _, args_text = rest.partition(" ")
    name = name.strip()
    args_text = args_text.strip()

    arguments: dict[str, Any] = {}
    if args_text:
        try:
            parsed = json.loads(args_text)
        except json.JSONDecodeError as exc:
            ui.line(ui.error(f"⚠ Invalid tool arguments: {exc}"))
            ui.blank()
            return
        if not isinstance(parsed, dict):
            ui.line(ui.error("⚠ Tool arguments must be a JSON object."))
            ui.blank()
            return
        arguments = parsed

    try:
        with ui.status(f"running tool {ui.accent(name)}"):
            result = agent.execute_tool(name, confirmed=False, **arguments)
    except ToolConfirmationRequired as exc:
        answer = input(f"Tool '{exc.tool_name}' will modify files. Confirm? [y/N] ").strip().lower()
        if answer not in {"y", "yes"}:
            ui.line(ui.muted("Tool call cancelled."))
            ui.blank()
            return
        try:
            with ui.status(f"running tool {ui.accent(name)}"):
                result = agent.execute_tool(name, confirmed=True, **arguments)
        except ToolError as tool_exc:
            ui.line(ui.error(f"⚠ Tool error: {tool_exc}"))
            ui.blank()
            return
    except ToolError as exc:
        ui.line(ui.error(f"⚠ Tool error: {exc}"))
        ui.blank()
        return

    ui.line(f"{ui.success('tool ›')} {result}")
    ui.blank()


# --- Autonomous mode ---------------------------------------------------------


def _confirm_action(step: PlanStep, tool_name: str, arguments: dict[str, Any]) -> bool:
    """Interactive approval gate for protected autonomous actions."""
    print(f"⚠ Protected action '{tool_name}' {arguments}")
    answer = input("Confirm this action? [y/N] ").strip().lower()
    return answer in {"y", "yes"}


def _print_event(entry: TraceEntry, ui: Console) -> None:
    """Print one live autonomy trace event (verbose mode)."""
    step = f"step {entry.step_index + 1}" if entry.step_index is not None else "plan"
    ui.event(entry.phase.value, step, entry.content)


def _print_steps(steps: list[PlanStep], ui: Console) -> None:
    for index, step in enumerate(steps, start=1):
        ui.line(f"  {ui.muted(f'{index:02d}')} {ui.accent(f'[{step.status.value}]')} {step.title}")
        if step.observation:
            ui.line(f"       {ui.muted('observation')}: {step.observation}")
        if step.error:
            ui.line(f"       {ui.error('error')}: {step.error}")


def _run_autonomous(agent: DreamAIAgent, settings: Settings, objective: str, ui: Console) -> None:
    if not settings.autonomy_enabled:
        ui.line(ui.error("⚠ Autonomous mode is disabled (DREAMAI_AUTONOMY_ENABLED=false)."))
        ui.blank()
        return
    if not objective:
        ui.line("Usage: /run <objective>  e.g. /run what time is it and calculate 12 * 7")
        ui.blank()
        return

    on_event = (lambda entry: _print_event(entry, ui)) if settings.autonomy_verbose else None

    try:
        if not settings.autonomy_verbose:
            ui.line(ui.muted("dream-ai is planning the route…"))
        result = agent.autonomous_task(
            objective,
            confirmation_callback=_confirm_action,
            on_event=on_event,
        )
    except ConfigurationError as exc:
        ui.line(ui.error(f"⚠ {exc}"))
        ui.blank()
        return

    if not settings.autonomy_verbose:
        ui.blank()
        ui.line(ui.accent("Plan"))
        _print_steps(result.steps, ui)
        ui.blank()

    ui.reply(result.final_summary)


def _print_trace(agent: DreamAIAgent, ui: Console) -> None:
    result = agent.last_execution
    if result is None:
        ui.line(ui.muted("No autonomous task has run yet. Use /run <objective>."))
        ui.blank()
        return

    ui.line(f"{ui.muted('Last task:')} {result.objective}")
    ui.line(
        f"{ui.muted('Status:')} {result.status.value} "
        f"{ui.muted(f'({len(result.succeeded_steps)}/{result.total_steps} steps succeeded)')}"
    )
    ui.blank()

    ui.line(ui.accent("Plan"))
    _print_steps(result.steps, ui)

    ui.blank()
    ui.line(ui.accent("Trace"))
    for entry in result.trace:
        step = f"step {entry.step_index + 1}" if entry.step_index is not None else "—"
        ui.event(entry.phase.value, step, entry.content)
    ui.blank()


def main(argv: list[str] | None = None) -> int:
    prepare_output()
    args = _parse_args(argv)
    settings = _apply_overrides(load_settings(), args)
    ui = Console(enabled=settings.animations_enabled, speed=settings.animation_speed)

    try:
        agent = build_agent(settings)
    except ConfigurationError as exc:
        ui.line(ui.error(f"Configuration error: {exc}"))
        return 2

    ui.intro(
        __version__,
        agent.provider_name,
        settings.model,
        agent.provider_name == "local-echo",
    )
    ui.line(f"Welcome to {ui.accent('Dream AI')} — type /help for commands, /quit to exit.")
    ui.blank()

    if agent.provider_name == "local-echo":
        ui.line(
            ui.warn(
                "ℹ Offline demo mode: no hosted API key was configured, so Dream AI "
                "is running on the local placeholder provider."
            )
        )
        ui.line(
            ui.muted(
                "  Copy `.env.example` to `.env`, set DREAMAI_API_KEY, and restart to "
                "use a real model."
            )
        )
        ui.blank()
    else:
        ui.line(f"{ui.muted('Connected via provider:')} {ui.success(agent.provider_name)}")
        ui.blank()

    _print_memory_status(agent, settings, ui)

    while True:
        try:
            user_input = input(ui.user_prompt()).strip()
        except (EOFError, KeyboardInterrupt):
            ui.blank()
            ui.line(ui.muted("Goodbye — keep dreaming."))
            return 0

        if not user_input:
            continue

        command = user_input.lower()

        if command in {"/quit", "/exit"}:
            ui.line(ui.muted("Goodbye — keep dreaming."))
            return 0

        if command == "/help":
            ui.line(HELP_TEXT)
            continue

        if command == "/motion":
            active = ui.toggle()
            if active:
                ui.line(
                    ui.success("Terminal motion on — typing, spinner, and launch effects enabled.")
                )
            elif sys.stdout.isatty():
                ui.line(ui.muted("Terminal motion off — output is plain text for this session."))
            else:
                ui.line(
                    ui.muted("Terminal motion needs an interactive terminal; output stays plain.")
                )
            ui.blank()
            continue

        if command.startswith("/run"):
            _, _, rest = user_input.partition(" ")
            _run_autonomous(agent, settings, rest.strip(), ui)
            continue

        if command == "/trace":
            _print_trace(agent, ui)
            continue

        if command == "/tools":
            _print_tools(agent, ui)
            continue

        if command.startswith("/tool"):
            _, _, rest = user_input.partition(" ")
            _run_tool(agent, rest, ui)
            continue

        if command.startswith("/remember"):
            _, _, note = user_input.partition(" ")
            note = note.strip()
            if not note:
                ui.line("Usage: /remember <your preference>")
                ui.blank()
                continue
            agent.remember(note)
            ui.line(ui.success("Saved to long-term memory."))
            ui.blank()
            continue

        if command == "/memory":
            notes = agent.preference_notes
            if not notes:
                ui.line(ui.muted("No preferences remembered yet. Use /remember <text>."))
                ui.blank()
                continue
            ui.line(ui.accent("Remembered preferences:"))
            for index, note in enumerate(notes, start=1):
                ui.line(f"  {index}. {note}")
            ui.blank()
            continue

        if command == "/forget":
            agent.forget_preferences()
            ui.line(ui.muted("All remembered preferences cleared."))
            ui.blank()
            continue

        if command in {"/clear", "/reset"}:
            agent.reset()
            ui.line(ui.muted("Conversation history cleared."))
            ui.blank()
            continue

        if command == "/about":
            turns = sum(1 for msg in agent.history if msg["role"] == "user")
            ui.line(f"{ui.muted('Provider:')} {agent.provider_name}")
            ui.line(f"{ui.muted('Model:')} {settings.model}")
            ui.line(
                f"{ui.muted('Tools:')} {len(agent.tool_names)} ({', '.join(agent.tool_names) or 'none'})"
            )
            autonomy = "on" if agent.autonomy_enabled else "off"
            ui.line(
                f"{ui.muted('Autonomy:')} {autonomy} "
                f"{ui.muted(f'(max steps: {settings.max_steps}, retries: {settings.max_retries})')}"
            )
            if agent.last_execution:
                ui.line(f"{ui.muted('Last autonomous task:')} {agent.last_execution.status.value}")
            ui.line(f"{ui.muted('Messages sent this session:')} {turns}")
            ui.line(f"{ui.muted('Preferences remembered:')} {len(agent.preference_notes)}")
            ui.blank()
            continue

        try:
            with ui.status("thinking"):
                reply = agent.chat(user_input)
        except ProviderError as exc:
            ui.line(ui.error(f"⚠ Provider error: {exc}"))
            ui.blank()
            continue

        ui.reply(reply)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
