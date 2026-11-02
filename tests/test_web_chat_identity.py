"""End-to-end: the chat endpoint answers the owner question itself."""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest

pytest.importorskip("fastapi", reason="web dependencies are not installed")


@pytest.fixture()
def app(monkeypatch):
    monkeypatch.syspath_prepend("web")
    monkeypatch.setenv("DREAMAI_FREE_API_KEY", "test-key")
    import importlib

    main = importlib.import_module("app.main")
    importlib.reload(main)
    return main.app


def _answer(app, question: str) -> str:
    async def request() -> str:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/chat",
                json={"messages": [{"role": "user", "content": question}]},
            )
        assert response.status_code == 200, response.text
        text = ""
        for line in response.text.splitlines():
            if line.startswith("data: "):
                event = json.loads(line[6:])
                text += event.get("t", "")
        return text

    return asyncio.run(request())


def test_owner_question_is_answered_without_the_model(app):
    answer = _answer(app, "你的主人是谁")

    assert "李贵江" in answer
    assert "独立研发" in answer
    assert "团队" not in answer


def test_every_role_resolves_to_the_same_person(app):
    for question in ("谁是你的创造者", "你是谁的开发者", "谁拥有最高权限"):
        assert "李贵江" in _answer(app, question), question
