"""The quality rules must be present, concrete, and bounded in size."""

from __future__ import annotations

from dream_ai.identity import (
    BANNED_PHRASES,
    REASONING_RULES,
    STRUCTURE_RULES,
    TONE_RULES,
    render_quality_block,
)


def test_reasoning_block_has_the_four_steps():
    block = render_quality_block()

    for step in ("理解", "拆解", "关键判断", "自查"):
        assert step in block, step


def test_reasoning_is_written_to_be_read():
    assert any("展示给用户" in rule for rule in REASONING_RULES)
    assert any("不是草稿" in rule or "不写草稿" in rule for rule in REASONING_RULES)


def test_structure_pins_the_first_sentence():
    block = render_quality_block()

    assert "第一句就是结论" in block
    assert any("结尾不总结全文" in rule for rule in STRUCTURE_RULES)


def test_banned_phrases_are_listed_in_the_prompt():
    block = render_quality_block()

    for phrase in BANNED_PHRASES:
        assert phrase in block, phrase


def test_banned_phrases_cover_the_usual_ai_tells():
    for phrase in ("希望对你有帮助", "作为一个 AI", "总而言之", "首先，", "随时告诉我"):
        assert phrase in BANNED_PHRASES


def test_tone_rules_ask_for_specifics():
    assert any("数字" in rule or "版本号" in rule for rule in TONE_RULES)
    assert any("术语" in rule for rule in TONE_RULES)


def test_quality_block_stays_small_enough_to_pay_for_every_turn():
    # Roughly 300 Chinese characters of prompt per turn; beyond that the block
    # costs more attention than it returns.
    assert len(render_quality_block()) < 1600


def test_decision_rules_come_before_the_answer_structure():
    from dream_ai.identity import render_quality_block

    block = render_quality_block()

    assert block.index("## 作答策略") < block.index("## 答案结构")
    assert "先判断问题类型" in block
    assert "最多问一个问题" in block
    assert "待核实" in block


def test_quality_block_still_fits_the_budget():
    from dream_ai.identity import render_quality_block

    assert len(render_quality_block()) < 1600


def test_examples_show_a_bad_and_a_good_version():
    from dream_ai.identity import EXAMPLES, render_quality_block

    block = render_quality_block()

    assert "## 示例" in block
    assert len(EXAMPLES) >= 2
    for label, bad, good in EXAMPLES:
        assert bad != good
        assert bad in block and good in block, label


def test_language_rule_is_stated_in_the_persona():
    from dream_ai.identity import render_tone_block

    assert "跟随用户的语言" in render_tone_block()
