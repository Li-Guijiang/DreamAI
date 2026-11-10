"""A long session must be folded, not truncated."""

from __future__ import annotations

from dream_ai.quality import build_digest, compress_history


def _turn(index: int, size: int = 40) -> list[dict[str, str]]:
    role = "user" if index % 2 == 0 else "assistant"
    return [{"role": role, "content": f"第{index}轮：" + "内容" * size}]


def test_a_short_session_is_untouched():
    messages = [_turn(i) for i in range(4)]

    kept, digest = compress_history([m for t in messages for m in t], 4000)

    assert len(kept) == 4
    assert digest == ""


def test_a_long_session_keeps_the_tail_and_folds_the_head():
    messages = [m for i in range(10) for m in _turn(i)]

    kept, digest = compress_history(messages, 500, keep_turns=6)

    assert len(kept) == 6
    assert kept[0]["content"].startswith("第4轮")
    assert "第0轮" in digest
    assert "第3轮" in digest
    assert digest.startswith("- 用户：")


def test_a_big_tail_that_still_fits_is_kept_whole():
    messages = [m for i in range(10) for m in _turn(i, size=5)]

    kept, digest = compress_history(messages, 6000, keep_turns=6)

    assert len(kept) == 10
    assert digest == ""


def test_the_digest_is_bounded_and_labels_the_speaker():
    messages = [{"role": "user", "content": "很长的一段话，" * 200}]

    digest = build_digest(messages, max_chars=100)

    assert digest.startswith("- 用户：")
    assert len(digest) <= 100
