"""Tests for conversation flow backed by in-memory session memory."""

from dream_ai.core.conversation import Conversation
from dream_ai.exceptions import DreamAIError
from dream_ai.memory import InMemorySessionMemory


def test_system_prompt_is_first_message():
    memory = InMemorySessionMemory("You are Dream AI.")
    conversation = Conversation(memory)

    history = conversation.history()

    assert history[0] == {"role": "system", "content": "You are Dream AI."}


def test_user_and_assistant_messages_are_recorded():
    conversation = Conversation(InMemorySessionMemory())
    conversation.add_user("Hello")
    conversation.add_assistant("Hi there!")

    history = conversation.history()

    assert history[-2] == {"role": "user", "content": "Hello"}
    assert history[-1] == {"role": "assistant", "content": "Hi there!"}


def test_clear_keeps_system_prompt():
    conversation = Conversation(InMemorySessionMemory("system prompt"))
    conversation.add_user("Temp")
    conversation.clear()

    history = conversation.history()

    assert history == [{"role": "system", "content": "system prompt"}]


def test_empty_message_is_rejected():
    conversation = Conversation(InMemorySessionMemory())

    raised = False
    try:
        conversation.add_user("   ")
    except DreamAIError:
        raised = True

    assert raised
