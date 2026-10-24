"""Assemble a configured :class:`DreamAIAgent` from :class:`Settings`.

This keeps file-system choices out of the agent core: given settings, it picks
the in-memory or persistent backends and wires them together.
"""

from __future__ import annotations

from .config import Settings
from .core.agent import DreamAIAgent
from .memory import InMemorySessionMemory, PersistentSessionMemory, PreferenceMemory
from .providers import build_provider


def build_agent(settings: Settings) -> DreamAIAgent:
    """Return an agent backed by the configured memory and provider."""
    provider = build_provider(settings)

    if settings.persistence_enabled:
        memory = PersistentSessionMemory(
            settings.system_prompt,
            settings.data_dir / "session.json",
        )
        preferences = PreferenceMemory(settings.data_dir / "preferences.json")
    else:
        memory = InMemorySessionMemory(settings.system_prompt)
        preferences = PreferenceMemory()

    return DreamAIAgent(
        provider=provider,
        system_prompt=settings.system_prompt,
        memory=memory,
        preferences=preferences,
    )
