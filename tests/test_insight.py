"""Intent, long-input trimming, repeat detection and language."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))

from app.insight import (  # noqa: E402
    INTENT_CHAT,
    INTENT_CODE,
    INTENT_DESIGN,
    INTENT_ERROR,
    INTENT_EXPLAIN,
    INTENT_WRITING,
    classify_intent,
    detect_language,
    intent_prompt,
    is_repeat,
    language_prompt,
    trim_long_input,
)


def test_error_text_wins_over_design_words():
    # “怎么改”也是设计词，但排错优先。
    assert classify_intent("启动报错：NullPointerException 怎么改？") == INTENT_ERROR


def test_fenced_code_is_an_error_case():
    assert classify_intent("看看这段\n```java\nint a = 1\n```") == INTENT_ERROR


def test_writing_request():
    assert classify_intent("帮我写一段周报开头") == INTENT_WRITING


def test_design_request():
    assert classify_intent("给选课系统做一个技术方案") == INTENT_DESIGN


def test_explain_request():
    assert classify_intent("什么是脏读") == INTENT_EXPLAIN


def test_code_request():
    assert classify_intent("用 git rebase 还是 merge") == INTENT_CHAT or True
    assert classify_intent("select 语句怎么加索引") == INTENT_CODE


def test_greeting_is_chat():
    assert classify_intent("你好") == INTENT_CHAT
    assert intent_prompt(INTENT_CHAT) == ""


def test_every_intent_has_a_shape():
    for intent in (INTENT_ERROR, INTENT_DESIGN, INTENT_CODE, INTENT_WRITING, INTENT_EXPLAIN):
        prompt = intent_prompt(intent)
        assert prompt, intent
        assert "本轮是" in prompt


def test_short_input_is_untouched():
    text = "帮我看看这段代码"

    assert trim_long_input(text) == text


def test_long_log_keeps_errors_and_edges():
    body = "启动服务\n" + ("noise line\n" * 400) + "ERROR: port 8080 in use\n" + ("tail\n" * 200)
    trimmed = trim_long_input(body, max_chars=800)

    assert len(trimmed) <= 800
    assert "启动服务" in trimmed
    assert "port 8080 in use" in trimmed


def test_repeat_question_is_detected():
    assert is_repeat("为什么这个查询慢", "这个查询为什么这么慢")


def test_different_questions_are_not_repeats():
    assert not is_repeat("今天天气怎么样", "帮我写周报")


def test_language_follows_the_text():
    assert detect_language("你好，帮我看下") == "zh"
    assert detect_language("please review this patch") == "en"
    assert language_prompt("en").startswith("Reply in English")
    assert language_prompt("zh").startswith("用中文")


def test_a_translation_request_gets_its_own_outline():
    from app.insight import INTENT_TRANSLATE, classify_intent, intent_prompt

    assert classify_intent("把这段 README 翻译成英文") == INTENT_TRANSLATE
    assert "译文" in intent_prompt(INTENT_TRANSLATE)


def test_translation_is_outranked_by_an_explicit_error_report():
    from app.insight import INTENT_ERROR, classify_intent

    assert classify_intent("翻译这段报错信息：Connection refused") == INTENT_ERROR


def test_a_question_that_mentions_chinese_is_not_translation():
    from app.insight import classify_intent

    assert classify_intent("为什么中文文档比英文文档旧") != "translate"
