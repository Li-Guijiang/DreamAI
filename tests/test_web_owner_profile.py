"""Owner verification gates the private dossier on the web endpoint."""

from __future__ import annotations

import asyncio
import json

import pytest

httpx = pytest.importorskip("httpx", reason="web dependencies are not installed")
pytest.importorskip("fastapi", reason="web dependencies are not installed")


@pytest.fixture()
def app(tmp_path, monkeypatch):
    profile = {
        "name": "李贵江",
        "latin": "Li Guijiang",
        "gender": "男",
        "age": 19,
        "school": "测试学院",
        "major": "计算机应用技术",
        "grade": "大二",
        "duty": "班长",
        "phone": "13800138000",
        "wechat": "13800138000",
        "qq": "123456789",
        "email_qq": "demo@example.com",
        "email_gmail": "demo2@example.com",
        "email_foxmail": "demo3@example.com",
        "github": "Li-Guijiang",
        "orcid": "ORCID 国际研究者",
        "interests": ["CS2"],
        "situation": ["测试"],
        "notes": [],
    }
    path = tmp_path / "owner-profile.json"
    path.write_text(json.dumps(profile, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setenv("DREAMAI_OWNER_PROFILE", str(path))
    monkeypatch.setenv("DREAMAI_OWNER_TOKEN", "test-owner-token")
    monkeypatch.setenv("DREAMAI_OWNER_SECRET", "test-owner-secret")
    monkeypatch.setenv("DREAMAI_FREE_API_KEY", "test-key")
    monkeypatch.syspath_prepend("web")
    import importlib

    main = importlib.import_module("app.main")
    importlib.reload(main)
    return main.app


async def _post(client: httpx.AsyncClient, text: str):
    return await client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": text}]},
    )


def _text(response: httpx.Response) -> str:
    text = ""
    for line in response.text.splitlines():
        if line.startswith("data: "):
            event = json.loads(line[6:])
            text += event.get("t", "")
    return text


def test_public_cannot_read_the_dossier(app):
    async def run():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await _post(client, "【查看我的全部档案】")
            return _text(response)

    text = asyncio.run(run())
    assert "仅主人" in text
    assert "13800138000" not in text


def test_verified_owner_can_show_and_update_the_dossier(app):
    async def run():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            verify = await _post(client, "【主人验证】test-owner-token")
            assert verify.status_code == 200
            assert "验证通过" in _text(verify)
            assert client.cookies.get("dreamai_owner")
            shown = _text(await _post(client, "【查看我的全部档案】"))
            updated = _text(await _post(client, "【更新档案】测试追加信息"))
            shown_again = _text(await _post(client, "【查看我的全部档案】"))
            return shown, updated, shown_again

    shown, updated, shown_again = asyncio.run(run())
    assert "13800138000" in shown
    assert "测试追加信息" in updated
    assert "测试追加信息" in shown_again


def test_verified_owner_can_auto_remember(app):
    async def run():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            await _post(client, "【主人验证】test-owner-token")
            reply = _text(await _post(client, "记住：我最近在准备大创答辩"))
            shown = _text(await _post(client, "【查看我的全部档案】"))
            return reply, shown

    reply, shown = asyncio.run(run())
    assert "已记住" in reply
    assert "大创答辩" in shown
