"""Emoji are allowed, counted, and capped - including around code."""

from __future__ import annotations

from dream_ai.identity import MAX_EMOJI, limit_emoji


def test_reply_within_budget_is_untouched():
    text = "搞定了 😊 下一步跑测试。"

    assert limit_emoji(text) == text


def test_surplus_is_dropped():
    marks = "👋🚀🔥✨🎉"
    text = "你好 👋 我是 Dream AI 🚀 随时开工 🔥 现在开始 ✨ 结束 🎉"

    result = limit_emoji(text)

    kept = [ch for ch in result if ch in marks]
    assert len(kept) == MAX_EMOJI
    assert "你好" in result and "结束" in result


def test_code_fences_are_never_touched():
    text = "看这段：\n```bash\necho 😀😀😀😀\n```\n就这些 😄😄😄😄"

    result = limit_emoji(text)

    assert "echo 😀😀😀😀" in result, "a script that prints emoji must survive"
    assert result.count("😄") == MAX_EMOJI


def test_inline_code_is_protected():
    text = "变量 `emoji = '😀'` 即可。"

    assert "`emoji = '😀'`" in limit_emoji(text)


def test_empty_input_is_safe():
    assert limit_emoji("") == ""


def test_budget_can_be_zero():
    assert "😀" not in limit_emoji("完成 😀", max_emoji=0)


def test_no_double_space_is_left_behind():
    result = limit_emoji("完成 😀😀😀😀 收工", max_emoji=1)

    assert "  " not in result
