"""The finish reason must reach the caller as metadata, never as answer text."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

WEB = str(Path(__file__).resolve().parent.parent / "web")
if WEB not in sys.path:
    sys.path.insert(0, WEB)

from app import llm  # noqa: E402

from tests.test_llm_usage import _collect  # noqa: E402


def test_an_openai_length_reason_becomes_one_finish_event():
    lines = [
        'data: {"choices":[{"delta":{"content":"半句话"}}]}',
        "",
        'data: {"choices":[{"delta":{},"finish_reason":"length"}]}',
        "",
        "data: [DONE]",
        "",
    ]

    items, _ = _collect(lines)

    assert items[-1] == ("finish", "length")
    assert ("content", "length") not in items
    assert [text for kind, text in items if kind == "content"] == ["半句话"]


def test_a_normal_finish_still_reaches_the_caller():
    lines = ['data: {"choices":[{"delta":{},"finish_reason":"stop"}]}', "", "data: [DONE]", ""]

    items, _ = _collect(lines)

    assert items == [("finish", "stop")]


def test_anthropic_max_tokens_becomes_length():
    lines = [
        "event: content_block_delta",
        'data: {"delta":{"type":"text_delta","text":"ok"}}',
        "",
        "event: message_delta",
        'data: {"type":"message_delta","delta":{"stop_reason":"max_tokens"}}',
        "",
    ]

    items, _ = _collect(lines, kind="anthropic")

    assert ("finish", "length") in items


def test_google_max_tokens_becomes_length():
    lines = [
        'data: {"candidates":[{"content":{"parts":[{"text":"ok"}]},"finishReason":"MAX_TOKENS"}]}',
        "",
    ]

    items, _ = _collect(lines, kind="google")

    assert ("finish", "length") in items


def test_an_unspecified_reason_produces_no_finish_event():
    lines = [
        'data: {"choices":[{"delta":{"content":"hi"},"finish_reason":null}]}',
        "",
        'data: {"candidates":[]}',
        "",
        "data: [DONE]",
        "",
    ]

    items, _ = _collect(lines)

    assert all(kind != "finish" for kind, _ in items)


def test_the_last_non_empty_reason_wins():
    lines = [
        'data: {"choices":[{"delta":{},"finish_reason":null}]}',
        "",
        'data: {"choices":[{"delta":{"content":"x"},"finish_reason":"stop"}]}',
        "",
        'data: {"choices":[{"delta":{},"finish_reason":"length"}]}',
        "",
        "data: [DONE]",
        "",
    ]

    items, _ = _collect(lines)

    assert [text for kind, text in items if kind == "finish"] == ["length"]


def test_usage_and_finish_arrive_once_each_and_in_order():
    lines = [
        'data: {"choices":[{"delta":{"content":"a"}}]}',
        "",
        'data: {"choices":[{"delta":{},"finish_reason":"length"}]}',
        "",
        'data: {"choices":[],"usage":{"prompt_tokens":3,"completion_tokens":1}}',
        "",
        "data: [DONE]",
        "",
    ]

    items, _ = _collect(lines)
    kinds = [kind for kind, _ in items]

    assert kinds.count("usage") == 1
    assert kinds.count("finish") == 1
    assert kinds.index("usage") < kinds.index("finish")


def test_a_finish_event_never_joins_a_text_run_in_coalesce():
    async def source():
        yield "content", "前半"
        yield "content", "后半"
        yield "finish", "length"
        yield "usage", '{"prompt_tokens": 1}'
        yield "content", "尾巴"

    async def run():
        return [item async for item in llm.coalesce(source())]

    assert asyncio.run(run()) == [
        ("content", "前半后半"),
        ("finish", "length"),
        ("usage", '{"prompt_tokens": 1}'),
        ("content", "尾巴"),
    ]


def test_a_leading_finish_event_does_not_create_an_empty_text_event():
    # The buffer starts with kind=""; a control event must not flush it.
    async def source():
        yield "finish", "stop"
        yield "content", "你好"

    async def run():
        return [item async for item in llm.coalesce(source())]

    assert asyncio.run(run()) == [("finish", "stop"), ("content", "你好")]
