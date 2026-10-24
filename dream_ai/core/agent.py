"""DreamAIAgent: the core that ties provider, memory, conversation, and tools."""

from __future__ import annotations

from ..memory import InMemorySessionMemory, PreferenceMemory
from ..memory.base import Memory
from ..providers.base import LLMProvider
from ..tools import ToolRegistry
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
    ) -> None:
        self._provider = provider
        self._preferences = preferences or PreferenceMemory()
        self._base_system_prompt = system_prompt or ""
        composed = self._compose_system_prompt(self._base_system_prompt)
        self._memory = memory or InMemorySessionMemory(composed)
        self._conversation = Conversation(self._memory)
        self.tools = tools or ToolRegistry()

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

    def remember(self, text: str) -> None:
        """Record a long-term preference."""
        self._preferences.remember(text)

    def forget_preferences(self) -> None:
        """Clear all remembered preferences."""
        self._preferences.forget()

    def chat(self, user_text: str) -> str:
        """Send one user message and return the assistant's reply."""
        self._conversation.add_user(user_text)
        reply = self._provider.generate(self._conversation.history())
        self._conversation.add_assistant(reply)
        return reply

    def reset(self) -> None:
        """Clear the conversation, keeping the system prompt."""
        self._conversation.clear()

    def _compose_system_prompt(self, base: str | None) -> str:
        """Append remembered preferences to the base system prompt."""
        context = self._preferences.system_context()
        if not context:
            return base or ""
        return f"{base}\n\n{context}" if base else context
