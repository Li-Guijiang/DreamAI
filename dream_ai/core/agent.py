"""DreamAIAgent: the core that ties provider, memory, conversation, and tools."""

from __future__ import annotations

from ..memory import InMemorySessionMemory
from ..providers.base import LLMProvider
from ..tools import ToolRegistry
from .conversation import Conversation


class DreamAIAgent:
    """The v0.1 assistant: a provider wrapped with session memory and a tool slot."""

    def __init__(
        self,
        provider: LLMProvider,
        system_prompt: str | None = None,
        tools: ToolRegistry | None = None,
    ) -> None:
        self._provider = provider
        self._memory = InMemorySessionMemory(system_prompt)
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

    def chat(self, user_text: str) -> str:
        """Send one user message and return the assistant's reply."""
        self._conversation.add_user(user_text)
        reply = self._provider.generate(self._conversation.history())
        self._conversation.add_assistant(reply)
        return reply

    def reset(self) -> None:
        """Clear the conversation, keeping the system prompt."""
        self._conversation.clear()
