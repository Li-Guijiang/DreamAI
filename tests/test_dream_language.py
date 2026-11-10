"""The local surfaces must answer in the language the user wrote in."""

from __future__ import annotations

from dream_ai.insight import detect_language, language_prompt


def test_chinese_wins_when_the_message_is_mostly_han():
    assert detect_language("帮我把这段配置改成 yaml") == "zh"


def test_english_wins_when_latin_characters_dominate():
    assert detect_language("how do I reset the cache TTL?") == "en"


def test_code_inside_a_chinese_question_does_not_flip_the_language():
    assert detect_language("这段代码是什么意思 print(sum([1,2,3]))") == "zh"


def test_an_empty_message_defaults_to_chinese():
    assert detect_language("") == "zh"


def test_the_hint_keeps_code_and_identifiers_untouched():
    hint = language_prompt("en")

    assert "English" in hint
    assert "code" in hint


def test_the_chinese_hint_says_the_same_thing_in_chinese():
    assert "代码" in language_prompt("zh")
