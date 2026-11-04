"""Delta coalescing must reduce events without changing the text."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "web"))

from app.llm import coalesce  # noqa: E402


def run(items, max_chars: int = 24):
    async def source():
        for item in items:
            yield item

    async def collect():
        return [item async for item in coalesce(source(), max_chars)]

    return asyncio.run(collect())


def test_tokens_of_one_kind_are_merged():
    items = [("content", "a") for _ in range(24)]

    merged = run(items, max_chars=8)

    assert len(merged) == 3
    assert "".join(text for _, text in merged) == "a" * 24


def test_a_kind_change_flushes_immediately():
    merged = run([("reasoning", "想"), ("reasoning", "一下"), ("content", "答")], max_chars=99)

    assert merged[0][0] == "reasoning"
    assert merged[0][1] == "想一下"
    assert merged[1] == ("content", "答")


def test_the_tail_is_never_lost():
    merged = run([("content", "结尾")], max_chars=99)

    assert merged == [("content", "结尾")]


def test_empty_items_are_dropped():
    merged = run([("content", ""), ("content", "x"), ("content", "")], max_chars=99)

    assert merged == [("content", "x")]


def test_long_single_token_is_flushed_as_is():
    merged = run([("content", "超长的一段内容" * 4)], max_chars=8)

    assert len(merged) == 1
    assert merged[0][1] == "超长的一段内容" * 4
