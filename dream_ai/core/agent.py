"""DreamAIAgent: the core that ties provider, memory, conversation, and tools."""

from __future__ import annotations

from typing import Any

from ..autonomy import (
    AutonomyEngine,
    ConfirmationCallback,
    EventCallback,
    ExecutionResult,
    PlanStep,
)
from ..exceptions import ConfigurationError, ToolConfirmationRequired
from ..memory import InMemorySessionMemory, PreferenceMemory
from ..memory.base import Memory
from ..providers.base import LLMProvider
from ..tools import ToolCall, ToolRegistry, parse_tool_calls
from .conversation import Conversation


class DreamAIAgent:
    """The assistant: a provider wrapped with session memory and a tool slot."""

    def __init__(
        self,
        provider: LLMProvider,
        system_prompt: str | None = None,
        tools: ToolRegistry | None = None,
        memory: Memory | None = None,
        preferences: PreferenceMemory | None = None,
        autonomy_enabled: bool = True,
        autonomy_max_steps: int = 10,
        autonomy_max_retries: int = 2,
    ) -> None:
        self._provider = provider
        self._preferences = preferences or PreferenceMemory()
        self._base_system_prompt = system_prompt or ""
        self._memory = memory or InMemorySessionMemory()
        # The effective prompt (base + remembered preferences) is pushed into the
        # memory backend, so it is the first message the provider receives no
        # matter which backend was injected.
        self._sync_system_prompt()
        self._conversation = Conversation(self._memory)
        self.tools = tools or ToolRegistry()
        self._autonomy_enabled = autonomy_enabled
        self._autonomy_max_steps = max(1, int(autonomy_max_steps))
        self._autonomy_max_retries = max(0, int(autonomy_max_retries))
        self._last_execution: ExecutionResult | None = None

    @property
    def provider_name(self) -> str:
        """Name of the active backend provider."""
        return self._provider.name

    @property
    def history(self) -> list[dict[str, str]]:
        """Current conversation history."""
        return self._conversation.history()

    @property
    def system_prompt(self) -> str:
        """Effective system prompt, including remembered preferences."""
        return self._compose_system_prompt(self._base_system_prompt)

    @property
    def preference_notes(self) -> list[str]:
        """Preferences remembered for later sessions."""
        return self._preferences.list()

    @property
    def tool_names(self) -> list[str]:
        """Names of the currently registered tools."""
        return self.tools.names()

    @property
    def autonomy_enabled(self) -> bool:
        """Whether autonomous multi-step execution is enabled."""
        return self._autonomy_enabled

    @property
    def last_execution(self) -> ExecutionResult | None:
        """Result of the most recent autonomous task, if one ran."""
        return self._last_execution

    def remember(self, text: str) -> None:
        """Record a long-term preference and apply it to the live conversation."""
        self._preferences.remember(text)
        self._sync_system_prompt()

    def forget_preferences(self) -> None:
        """Clear all remembered preferences and restore the base prompt."""
        self._preferences.forget()
        self._sync_system_prompt()

    def chat(self, user_text: str) -> str:
        """Send one user message and return the assistant's reply."""
        self._conversation.add_user(user_text)
        reply = self._provider.generate(self._conversation.history())
        self._conversation.add_assistant(reply)
        return reply

    def reset(self) -> None:
        """Clear the conversation, keeping the system prompt."""
        self._conversation.clear()

    # --- Tools -------------------------------------------------------------

    def list_tools(self) -> list[dict[str, Any]]:
        """Serializable metadata for every registered tool."""
        return self.tools.schemas()

    def execute_tool(self, name: str, confirmed: bool = False, **kwargs: Any) -> str:
        """Run a registered tool, enforcing the confirmation gate for state changes."""
        tool = self.tools.get(name)
        if tool.requires_confirmation and not confirmed:
            raise ToolConfirmationRequired(
                tool_name=name,
                message=f"Tool '{name}' changes state and needs explicit confirmation.",
                arguments=kwargs,
            )
        return self.tools.execute(name, **kwargs)

    def tool_calls_from_text(self, text: str) -> list[ToolCall]:
        """Parse structured tool-call blocks embedded in a model reply."""
        return parse_tool_calls(text)

    def run_tool_calls(
        self, text: str, confirmed: bool = False
    ) -> list[tuple[ToolCall, str]]:
        """Parse and execute every tool call found in ``text``."""
        results: list[tuple[ToolCall, str]] = []
        for call in self.tool_calls_from_text(text):
            result = self.execute_tool(call.name, confirmed=confirmed, **call.arguments)
            results.append((call, result))
        return results

    def provider_tools_schema(self) -> list[dict[str, Any]]:
        """OpenAI function-calling schema for registered tools (future integration)."""
        schema: list[dict[str, Any]] = []
        for tool in self.tools.schemas():
            schema.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool["description"],
                        "parameters": tool["parameters"],
                    },
                }
            )
        return schema

    # --- Autonomy ---------------------------------------------------------

    def autonomous_task(
        self,
        objective: str,
        plan: list[PlanStep] | None = None,
        *,
        max_steps: int | None = None,
        max_retries: int | None = None,
        confirmation_callback: ConfirmationCallback | None = None,
        on_event: EventCallback | None = None,
    ) -> ExecutionResult:
        """Run an autonomous multi-step task and return an explainable result.

        The objective is recorded in session memory, the plan executes through a
        think → act → observe → reflect loop, and the final summary is recorded
        back into the conversation.
        """
        if not self._autonomy_enabled:
            raise ConfigurationError(
                "Autonomous mode is disabled (DREAMAI_AUTONOMY_ENABLED=false)."
            )

        self._conversation.add_user(objective)
        engine = AutonomyEngine(
            self,
            max_steps=max_steps if max_steps is not None else self._autonomy_max_steps,
            max_retries=max_retries if max_retries is not None else self._autonomy_max_retries,
            confirmation_callback=confirmation_callback,
            on_event=on_event,
        )
        result = engine.run(objective, plan)
        self._conversation.add_assistant(result.final_summary)
        self._last_execution = result
        return result

    # --- Internals ---------------------------------------------------------

    def _sync_system_prompt(self) -> None:
        """Push the effective system prompt into the memory backend."""
        self._memory.set_system_prompt(
            self._compose_system_prompt(self._base_system_prompt)
        )

    def _compose_system_prompt(self, base: str | None) -> str:
        """Append remembered preferences to the base system prompt."""
        context = self._preferences.system_context()
        if not context:
            return base or ""
        return f"{base}\n\n{context}" if base else context
