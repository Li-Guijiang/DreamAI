"""The CLI copy of the intent helpers must behave like the web copy."""

from __future__ import annotations

from dream_ai.insight import classify_intent, intent_prompt, is_repeat, trim_long_input


def test_same_classification_as_the_web_copy():
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))
    from app.insight import classify_intent as web_classify

    for text in (
        "启动报错：NPE",
        "帮我写一段周报",
        "给选课系统做方案",
        "什么是脏读",
        "把这段 README 翻译成英文",
        "翻译这段报错信息：Connection refused",
        "你好",
    ):
        assert classify_intent(text) == web_classify(text), text


def test_intent_prompt_is_empty_for_chat():
    assert intent_prompt(classify_intent("你好")) == ""
    assert intent_prompt(classify_intent("启动报错")) != ""


def test_long_paste_is_trimmed_around_the_error_lines():
    body = "run\n" + ("noise\n" * 300) + "ERROR: port in use\n" + ("tail\n" * 100)

    trimmed = trim_long_input(body, max_chars=400)

    assert len(trimmed) <= 400
    assert "port in use" in trimmed


def test_repeat_detection_matches_the_web_copy():
    assert is_repeat("为什么这个查询慢", "这个查询为什么这么慢")
    assert not is_repeat("今天天气", "帮我写周报")
