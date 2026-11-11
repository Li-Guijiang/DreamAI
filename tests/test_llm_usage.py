"""The streaming client must turn provider counters into one usage event."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace

WEB = str(Path(__file__).resolve().parent.parent / "web")
if WEB not in sys.path:
    sys.path.insert(0, WEB)

from app import llm  # noqa: E402


class FakeResponse:
    def __init__(self, lines: list[str]) -> None:
        self.status_code = 200
        self._lines = lines

    async def aread(self) -> bytes:
        return b""

    async def aiter_lines(self):
        for line in self._lines:
            yield line


class FakeStream:
    def __init__(self, lines: list[str]) -> None:
        self._lines = lines
        self.request: dict | None = None

    async def __aenter__(self):
        return FakeResponse(self._lines)

    async def __aexit__(self, *args):  # noqa: ANN002
        return False


class FakeClient:
    def __init__(self, lines: list[str]) -> None:
        self._lines = lines
        self.payloads: list[dict] = []

    def stream(self, method, url, headers=None, json=None):  # noqa: A002
        self.payloads.append(dict(json or {}))
        return FakeStream(self._lines)


def _provider(kind: str = "openai"):
    return SimpleNamespace(kind=kind, base_url="https://example.test/v1")


def _collect(lines: list[str], kind: str = "openai", include_usage: bool = True):
    client = FakeClient(lines)

    async def run() -> list[tuple[str, str]]:
        original = llm.get_client
        llm.get_client = lambda: client
        try:
            return [
                item
                async for item in llm.stream_completion(
                    _provider(kind),
                    api_key="k",
                    model="m",
                    messages=[{"role": "user", "content": "hi"}],
                    include_usage=include_usage,
                )
            ]
        finally:
            llm.get_client = original

    return asyncio.run(run()), client


def test_an_openai_stream_ends_with_one_usage_event():
    lines = [
        'data: {"choices":[{"delta":{"content":"你好"}}]}',
        "",
        'data: {"choices":[],"usage":{"prompt_tokens":12,"completion_tokens":8}}',
        "",
        "data: [DONE]",
        "",
    ]

    items, _ = _collect(lines)

    assert ("content", "你好") in items
    usage = [json.loads(text) for kind, text in items if kind == "usage"]
    assert usage == [{"prompt_tokens": 12, "completion_tokens": 8}]


def test_anthropic_split_counters_are_accumulated():
    lines = [
        "event: message_start",
        'data: {"type":"message_start","message":{"usage":{"input_tokens":20,"output_tokens":1}}}',
        "",
        "event: content_block_delta",
        'data: {"delta":{"type":"text_delta","text":"ok"}}',
        "",
        "event: message_delta",
        'data: {"type":"message_delta","usage":{"output_tokens":30}}',
        "",
    ]

    items, _ = _collect(lines, kind="anthropic")

    usage = [json.loads(text) for kind, text in items if kind == "usage"]
    assert usage == [{"prompt_tokens": 20, "completion_tokens": 30}]


def test_a_stream_with_no_usage_produces_no_usage_event():
    lines = ['data: {"choices":[{"delta":{"content":"hi"}}]}', "", "data: [DONE]", ""]

    items, _ = _collect(lines)

    assert all(kind != "usage" for kind, _ in items)


def test_the_switch_reaches_the_request_payload():
    lines = ["data: [DONE]", ""]

    _collect(lines, include_usage=False)

    _, client = _collect(lines, include_usage=False)
    assert "stream_options" not in client.payloads[0]

    _, client = _collect(lines, include_usage=True)
    assert client.payloads[0]["stream_options"] == {"include_usage": True}
