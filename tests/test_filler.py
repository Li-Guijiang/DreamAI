"""Post-processing removes the closing line a prompt ban cannot guarantee."""

from __future__ import annotations

from dream_ai.identity import strip_filler


def test_trailing_filler_without_period_is_removed():
    assert strip_filler("结论是这样。希望对你有帮助") == "结论是这样。"


def test_trailing_filler_with_period_is_removed():
    assert strip_filler("结论是这样。希望对你有帮助。") == "结论是这样。"


def test_comma_joined_filler_is_removed():
    assert strip_filler("答案见上。如有其他问题，随时告诉我。") == "答案见上。"


def test_filler_in_the_middle_is_kept():
    text = "这个例子里写了希望对你有帮助，它是示例文本。"

    assert strip_filler(text) == text


def test_clean_answer_is_untouched():
    assert strip_filler("答案是 A。") == "答案是 A。"


def test_repeated_fillers_collapse():
    assert strip_filler("就这样。希望对你有帮助。随时告诉我") == "就这样。"


def test_empty_and_filler_only_inputs_are_safe():
    assert strip_filler("") == ""
    assert strip_filler("希望对你有帮助") == "希望对你有帮助"
