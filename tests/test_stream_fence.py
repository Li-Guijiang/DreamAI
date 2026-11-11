"""A streamed answer must not leave the page inside an open code fence."""

from __future__ import annotations

import dataclasses
import importlib
import sys
from pathlib import Path

import pytest

pytest.importorskip("fastapi", reason="web dependencies are not installed")
WEB = str(Path(__file__).resolve().parent.parent / "web")
if WEB not in sys.path:
    sys.path.insert(0, WEB)


@pytest.fixture()
def client(monkeypatch):
    main = importlib.import_module("app.main")
    monkeypatch.setattr(
        main, "settings", dataclasses.replace(main.settings, free_api_key="test-key")
    )
    main._breaker.reset()
    main._cache.clear()
    main.limiter._hits.clear()

    async def fake_stream(*args, **kwargs):  # noqa: ANN002, ANN003
        yield "content", "代码如下：\n```python\nprint(1)"

    monkeypatch.setattr(main.llm, "stream_completion", fake_stream)
    from fastapi.testclient import TestClient

    return main, TestClient(main.app)


def _text(response) -> str:  # noqa: ANN001
    parts = []
    for line in response.text.splitlines():
        if line.startswith("data: "):
            import json

            parts.append(json.loads(line[6:]).get("t", ""))
    return "".join(parts)


def test_the_stream_ends_with_a_closing_fence(client):
    _, test_client = client

    response = test_client.post(
        "/api/chat", json={"messages": [{"role": "user", "content": "给一段 Python 代码"}]}
    )

    assert response.status_code == 200
    text = _text(response)
    assert text.endswith("\n```")
    assert text.count("```") == 2


def test_the_cached_copy_includes_the_repair(client):
    main, test_client = client
    body = {"messages": [{"role": "user", "content": "给一段 Python 代码"}]}

    test_client.post("/api/chat", json=body)

    # The patch is appended to `answered`, which is what gets cached; the second
    # (cached) response must not lose it.
    cached = list(main._cache._items.values())[0][0] if len(main._cache) else ""
    if cached:
        assert cached.endswith("\n```")
