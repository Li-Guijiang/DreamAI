"""Reply-quality helpers are pure functions, so they are cheap to pin down."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))

from app.quality import (  # noqa: E402
    build_digest,
    classify_tier,
    close_fences,
    compress_history,
    dedupe_sentences,
    looks_empty,
    needs_context,
    plan_generation,
    tier_params,
)


def test_short_greeting_is_light():
    assert classify_tier("你好") == "light"
    assert classify_tier("在吗？") == "light"


def test_trade_off_question_is_deep():
    assert classify_tier("为什么 Redis 单线程还比多线程快？") == "deep"
    assert classify_tier("对比一下 MySQL 和 PostgreSQL 的索引实现差异") == "deep"


def test_code_question_is_deep():
    assert classify_tier("这段报错怎么修：\n```java\nNPE\n```") == "deep"


def test_ordinary_question_is_standard():
    assert classify_tier("帮我把这段话改得正式一点，用于周报开头") == "standard"


def test_long_message_is_deep():
    assert classify_tier("需求：给一个班级做选课系统，" + "要支持并发、" * 12) == "deep"


def test_empty_is_light():
    assert classify_tier("   ") == "light"


def test_light_tier_caps_the_budget():
    temperature, max_tokens, hint = tier_params("light", 0.9, 4096)

    assert temperature <= 0.4
    assert max_tokens <= 768
    assert "一两句话" in hint


def test_deep_tier_raises_the_budget():
    temperature, max_tokens, hint = tier_params("deep", 0.3, 4096)

    assert temperature >= 0.5
    assert max_tokens > 4096
    assert "先给结论" in hint


def test_standard_tier_leaves_the_budget_alone():
    assert tier_params("standard", 0.7, 4096) == (0.7, 4096, "")


def test_pronoun_follow_up_needs_context():
    assert needs_context("那它呢？")
    assert needs_context("这个怎么改")


def test_standalone_question_needs_no_context():
    assert not needs_context("贵州有哪些二本院校")
    assert not needs_context("")


def test_digest_keeps_both_sides_of_the_conversation():
    digest = build_digest([
        {"role": "user", "content": "我在写一个选课系统"},
        {"role": "assistant", "content": "用 Spring Boot 还是 Django？"},
    ])

    assert "用户" in digest and "助手" in digest
    assert "选课系统" in digest


def test_short_history_is_kept_untouched():
    history = [{"role": "user", "content": "你好"}]
    kept, digest = compress_history(history, max_chars=100)

    assert kept == history
    assert digest == ""


def test_long_history_is_folded_not_deleted():
    history = [
        {"role": "user", "content": "第一轮：我要做选课系统"},
        {"role": "assistant", "content": "第一轮回答：" + "细节" * 200},
        {"role": "user", "content": "第二轮：它要支持并发"},
        {"role": "assistant", "content": "第二轮回答：" + "细节" * 200},
        {"role": "user", "content": "第三轮：怎么加锁"},
        {"role": "assistant", "content": "第三轮回答：" + "细节" * 200},
        {"role": "user", "content": "那它呢？"},
    ]

    kept, digest = compress_history(history, max_chars=120, keep_turns=2)

    assert len(kept) == 2
    assert digest, "dropped turns must leave a digest"
    assert "选课系统" in digest


def test_unclosed_fence_is_closed():
    assert close_fences("看代码：\n```python\nprint(1)").endswith("```")


def test_closed_fence_is_untouched():
    text = "```python\nprint(1)\n```\n好了"

    assert close_fences(text) == text


def test_consecutive_duplicate_sentences_collapse():
    assert dedupe_sentences("先部署。先部署。再验证。") == "先部署。再验证。"


def test_similar_but_different_sentences_survive():
    text = "先部署。再验证。"

    assert dedupe_sentences(text) == text


def test_empty_reply_is_detected():
    assert looks_empty("")
    assert looks_empty("   ")
    assert looks_empty("。")
    assert not looks_empty("答案是 A。")


def test_plan_keeps_every_field_in_range():
    plan = plan_generation("你好", 0.9, 4096)

    assert plan["tier"] == "light"
    assert 0.0 <= plan["temperature"] <= 1.5
    assert 128 <= plan["max_tokens"] <= 8192


def test_plan_for_a_deep_question_raises_the_budget():
    plan = plan_generation("为什么这个查询在数据量大时变慢？", 0.3, 2048)

    assert plan["tier"] == "deep"
    assert plan["max_tokens"] > 2048
    assert plan["hint"]
