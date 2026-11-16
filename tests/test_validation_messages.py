"""A rejected body must be readable in the language the site uses."""

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

from app.errors import validation_reason  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        ({"type": "less_than_equal", "msg": "Input should be <= 2"}, "数值超过允许的上限"),
        ({"type": "greater_than_equal", "msg": "Input should be >= 0"}, "数值低于允许的下限"),
        ({"type": "string_too_long", "msg": "String should have at most 128"}, "内容太长"),
        ({"type": "too_long", "msg": "List should have at most 40"}, "条目太多"),
        (
            {"type": "literal_error", "msg": "Input should be 'user' or 'assistant'"},
            "取值不在允许范围内",
        ),
        ({"type": "missing", "msg": "Field required"}, "缺少必填字段"),
    ],
)
def test_pydantic_types_become_short_chinese_phrases(error, expected):
    assert validation_reason(error) == expected


def test_a_custom_validator_message_is_kept_without_the_prefix():
    error = {"type": "value_error", "msg": "Value error, 最后一条消息必须来自用户"}

    assert validation_reason(error) == "最后一条消息必须来自用户"


def test_an_unknown_error_still_has_a_readable_fallback():
    assert validation_reason({}) == "字段不合法"


def _post(body: dict, monkeypatch):
    main = importlib.import_module("app.main")
    monkeypatch.setattr(
        main, "settings", dataclasses.replace(main.settings, free_api_key="test-key")
    )
    return TestClient(main.app).post("/api/chat", json=body)


def test_the_http_error_has_no_pydantic_english(monkeypatch):
    response = _post(
        {"messages": [{"role": "user", "content": "在吗"}], "temperature": 9.0}, monkeypatch
    )

    text = response.json()["error"]
    assert "Value error" not in text
    assert "Input should" not in text
    assert "数值超过允许的上限" in text


def test_the_http_error_explains_a_bad_message_order(monkeypatch):
    response = _post(
        {
            "messages": [
                {"role": "user", "content": "在吗"},
                {"role": "assistant", "content": "你好"},
            ]
        },
        monkeypatch,
    )

    assert "最后一条消息必须来自用户" in response.json()["error"]
