"""Tests for persistent session history and long-term preferences (v0.2)."""

from __future__ import annotations

from pathlib import Path

import pytest

from dream_ai.agent_factory import build_agent
from dream_ai.config import Settings
from dream_ai.core import DreamAIAgent
from dream_ai.exceptions import DreamAIError
from dream_ai.memory import PersistentSessionMemory, PreferenceMemory
from dream_ai.providers import LocalEchoProvider


def _settings(data_dir: Path, persistence: bool) -> Settings:
    return Settings(
        provider="local",
        base_url="",
        api_key="",
        model="local",
        system_prompt="You are Dream AI.",
        data_dir=data_dir,
        persistence_enabled=persistence,
        tools_enabled=True,
        file_access_enabled=False,
        web_search_enabled=False,
        workspace_dir=data_dir / "workspace",
    )


# --- Persistent session history -------------------------------------------


def test_persistent_session_restored_across_instances(tmp_path: Path) -> None:
    memory = PersistentSessionMemory("You are Dream AI.", tmp_path / "session.json")
    memory.append("user", "Hello")
    memory.append("assistant", "Hi there")

    restored = PersistentSessionMemory("You are Dream AI.", tmp_path / "session.json")
    history = restored.messages()

    assert [message["role"] for message in history] == ["system", "user", "assistant"]
    assert history[1]["content"] == "Hello"
    assert history[2]["content"] == "Hi there"


def test_clear_persists_empty_history(tmp_path: Path) -> None:
    memory = PersistentSessionMemory("sys", tmp_path / "session.json")
    memory.append("user", "Temporary")
    memory.clear()

    restored = PersistentSessionMemory("sys", tmp_path / "session.json")

    assert restored.messages() == [{"role": "system", "content": "sys"}]


# --- Preference memory -----------------------------------------------------


def test_preference_memory_remembers_lists_and_forgets(tmp_path: Path) -> None:
    preferences = PreferenceMemory(tmp_path / "preferences.json")
    preferences.remember("I like cycling")
    preferences.remember("I like cycling")  # duplicate ignored
    preferences.remember("I drink tea")

    assert preferences.list() == ["I like cycling", "I drink tea"]
    assert "I like cycling" in preferences.system_context()

    preferences.forget()
    assert preferences.list() == []
    assert preferences.system_context() == ""


def test_empty_preference_is_rejected() -> None:
    preferences = PreferenceMemory()

    with pytest.raises(DreamAIError):
        preferences.remember("   ")


def test_preferences_persist_across_instances(tmp_path: Path) -> None:
    first = PreferenceMemory(tmp_path / "preferences.json")
    first.remember("I like cycling")

    restored = PreferenceMemory(tmp_path / "preferences.json")

    assert restored.list() == ["I like cycling"]


# --- Agent composition ------------------------------------------------------


def test_agent_injects_preferences_into_system_prompt() -> None:
    preferences = PreferenceMemory()
    preferences.remember("I like cycling")
    agent = DreamAIAgent(
        provider=LocalEchoProvider(),
        system_prompt="Base.",
        preferences=preferences,
    )

    assert "Base." in agent.system_prompt
    assert "I like cycling" in agent.system_prompt


def test_forget_preferences_removes_them_from_system_prompt() -> None:
    agent = DreamAIAgent(provider=LocalEchoProvider(), system_prompt="Base.")
    agent.remember("I like cycling")

    assert "I like cycling" in agent.system_prompt

    agent.forget_preferences()

    assert "I like cycling" not in agent.system_prompt
    assert "Base." in agent.system_prompt


# --- Factory wiring ---------------------------------------------------------


def test_factory_restores_session_and_preferences(tmp_path: Path) -> None:
    settings = _settings(tmp_path, persistence=True)

    first = build_agent(settings)
    first.chat("First question")
    first.remember("I like cycling")

    restored = build_agent(settings)
    roles = [message["role"] for message in restored.history]

    assert "user" in roles
    assert "I like cycling" in restored.preference_notes
    assert "I like cycling" in restored.system_prompt


def test_factory_without_persistence_writes_nothing_to_disk(tmp_path: Path) -> None:
    settings = _settings(tmp_path, persistence=False)
    agent = build_agent(settings)
    agent.chat("Hello")

    assert not (tmp_path / "session.json").exists()
    assert not (tmp_path / "preferences.json").exists()
