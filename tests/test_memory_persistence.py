"""Tests for persistent session history and long-term preferences (v0.2)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dream_ai.agent_factory import build_agent
from dream_ai.config import Settings
from dream_ai.core import DreamAIAgent
from dream_ai.exceptions import DreamAIError
from dream_ai.memory import PersistentSessionMemory, PreferenceMemory
from dream_ai.providers import LocalEchoProvider
from dream_ai.providers.local import DEMO_PREFIX


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


def test_demo_replies_are_not_persisted(tmp_path: Path) -> None:
    memory = PersistentSessionMemory("sys", tmp_path / "session.json")
    memory.append("user", "Hello")
    memory.append("assistant", f"{DEMO_PREFIX} offline placeholder reply")

    restored = PersistentSessionMemory("sys", tmp_path / "session.json")

    assert [message["role"] for message in restored.messages()] == ["system", "user"]
    assert all(DEMO_PREFIX not in message["content"] for message in restored.messages())


def test_stale_demo_replies_are_filtered_on_restore(tmp_path: Path) -> None:
    file_path = tmp_path / "session.json"
    file_path.write_text(
        json.dumps(
            {
                "messages": [
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": f"{DEMO_PREFIX} old offline reply"},
                    {"role": "user", "content": "Second question"},
                ]
            }
        ),
        encoding="utf-8",
    )

    restored = PersistentSessionMemory("sys", file_path)

    assert [message["content"] for message in restored.messages()] == [
        "sys",
        "Hello",
        "Second question",
    ]


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


def test_remember_reaches_the_prompt_sent_to_the_provider() -> None:
    """The system message — not just the property — must carry the preference."""
    agent = DreamAIAgent(provider=LocalEchoProvider(), system_prompt="Base.")
    agent.chat("First question")

    agent.remember("I like cycling")

    system_messages = [m for m in agent.history if m["role"] == "system"]
    assert len(system_messages) == 1
    assert "I like cycling" in system_messages[0]["content"]
    # Earlier turns must survive the prompt update.
    assert [m["role"] for m in agent.history] == ["system", "user", "assistant"]


def test_forget_preferences_restores_the_base_system_message() -> None:
    agent = DreamAIAgent(provider=LocalEchoProvider(), system_prompt="Base.")
    agent.remember("I like cycling")

    agent.forget_preferences()

    assert agent.history[0] == {"role": "system", "content": "Base."}


def test_persistent_agent_sends_preferences_after_restart(tmp_path: Path) -> None:
    """A preference remembered yesterday must still be in today's payload."""
    settings = _settings(tmp_path, persistence=True)
    first = build_agent(settings)
    first.remember("I drink tea")

    restored = build_agent(settings)

    system_messages = [m for m in restored.history if m["role"] == "system"]
    assert len(system_messages) == 1
    assert "I drink tea" in system_messages[0]["content"]


def test_persistent_set_system_prompt_keeps_saved_turns(tmp_path: Path) -> None:
    file_path = tmp_path / "session.json"
    memory = PersistentSessionMemory("v1", file_path)
    memory.append("user", "Hello")

    memory.set_system_prompt("v2")

    assert memory.messages()[0] == {"role": "system", "content": "v2"}
    # The prompt is never written to disk; only the turns are.
    restored = PersistentSessionMemory("v2", file_path)
    assert [message["role"] for message in restored.messages()] == ["system", "user"]


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
