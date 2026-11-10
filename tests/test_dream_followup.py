"""A follow-up like '那它呢？' must not be sent to the model alone."""

from __future__ import annotations

from dream_ai.quality import needs_context


def test_a_short_pronoun_message_needs_context():
    assert needs_context("那它呢？")
    assert needs_context("这个怎么改")


def test_a_full_question_does_not():
    assert not needs_context("为什么要把缓存做成两层，架构上怎么权衡")


def test_a_bare_fragment_without_punctuation_does():
    assert needs_context("缓存配置")


def test_an_empty_message_does_not():
    assert not needs_context("")
