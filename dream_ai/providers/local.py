"""Offline local demo provider.

This provider needs no network and no API key. It is used for testing, demos,
and as a fallback when no hosted model is configured. It does not reason —
it simply demonstrates the agent loop, memory history, and CLI flow.
"""

from __future__ import annotations

from typing import Any

from .base import LLMProvider


class LocalEchoProvider(LLMProvider):
    """A lightweight offline stand-in for a real language model."""

    @property
    def name(self) -> str:
        return "local-echo"

    def generate(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        user_messages = [m for m in messages if m["role"] == "user"]
        last_user = user_messages[-1]["content"] if user_messages else ""
        history_turns = len(user_messages)

        if not last_user.strip():
            return "I heard an empty message — please tell me what you need."

        return (
            "[Local demo mode] This reply comes from the offline placeholder "
            "provider, not a real model.\n"
            f"You have sent {history_turns} message(s) in this session.\n"
            f"You said: {last_user}\n"
            "Configure DREAMAI_API_KEY in `.env` to connect a hosted model."
        )
