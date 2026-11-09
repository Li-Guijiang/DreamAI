"""The local surfaces must size a reply to the question, like the web service does."""

from __future__ import annotations

from dream_ai.quality import (
    TIER_DEEP,
    TIER_LIGHT,
    TIER_STANDARD,
    classify_tier,
    reply_budget,
    tier_hint,
)


def test_a_greeting_is_light():
    assert classify_tier("在吗") == TIER_LIGHT
    assert classify_tier("") == TIER_LIGHT


def test_an_ordinary_question_is_standard():
    assert classify_tier("帮我把这段配置改成 yaml 格式，字段名保持不变") == TIER_STANDARD


def test_a_trade_off_question_is_deep():
    assert classify_tier("为什么要把缓存做成两层，架构上怎么权衡") == TIER_DEEP


def test_pasted_code_or_a_traceback_is_deep():
    assert classify_tier("```java\nint a = 1;\n```") == TIER_DEEP
    assert classify_tier("Traceback (most recent call last): boom") == TIER_DEEP


def test_a_light_turn_is_capped_hard():
    assert reply_budget(TIER_LIGHT, 4096) == 768


def test_a_deep_turn_gets_more_room_but_not_unlimited():
    assert reply_budget(TIER_DEEP, 4096) == 4096 + 1024
    assert reply_budget(TIER_DEEP, 8000) == 8192


def test_a_standard_turn_keeps_the_configured_budget():
    assert reply_budget(TIER_STANDARD, 2048) == 2048


def test_a_missing_budget_still_produces_a_number():
    assert reply_budget(TIER_STANDARD, 0) == 1024


def test_only_the_interesting_tiers_carry_a_hint():
    assert "一两句话" in tier_hint(TIER_LIGHT)
    assert "推演" in tier_hint(TIER_DEEP)
    assert tier_hint(TIER_STANDARD) == ""
