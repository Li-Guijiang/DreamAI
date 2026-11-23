"""docs/API.md is the contract; the code must not drift away from it."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
WEB = str(ROOT / "web")
if WEB not in sys.path:
    sys.path.insert(0, WEB)

from app.errors import error_code  # noqa: E402


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _documented_events() -> set[str]:
    block = re.search(r"<!-- EVENTS\s*\n(.*?)\n-->", _read("docs/API.md"), re.S)
    assert block, "docs/API.md lost its machine-readable event list"
    return {line.strip() for line in block.group(1).splitlines() if line.strip()}


def test_every_sse_event_in_the_code_is_documented():
    used = set(re.findall(r'sse\(\s*"([a-z_]+)"', _read("web/app/main.py")))

    assert used == _documented_events()


def test_every_error_code_in_the_document_is_reachable():
    section = _read("docs/API.md").split("`code` 取值：")[1].split("## 5.")[0]
    documented = set(re.findall(r"^\| `([a-z_]+)` \|", section, re.M))
    statuses = (None, 400, 401, 402, 403, 404, 408, 410, 413, 422, 425, 429, 500, 503, 504)
    reachable = {error_code(status) for status in statuses} | {
        "breaker",
        "concurrency_limit",
    }

    assert documented == reachable


def test_the_error_payload_fields_are_documented():
    section = _read("docs/API.md").split("## 4. error 事件")[1].split("## 5.")[0]

    for field in ("message", "code", "status", "retryable"):
        assert f"`{field}`" in section


def test_the_new_status_fields_are_documented():
    doc = _read("docs/API.md")

    for field in ("configChecks", "usagePersisted", "truncatedByTier", "byFinish"):
        assert f"`{field}`" in doc


def test_the_health_and_usage_endpoints_honour_the_documented_fields():
    pytest.importorskip("fastapi", reason="web dependencies are not installed")
    from fastapi.testclient import TestClient

    main = __import__("app.main", fromlist=["app"])
    client = TestClient(main.app)
    health = client.get("/api/health").json()
    usage = client.get("/api/usage").json()

    assert set(("configChecks",)) <= set(health)
    assert {"usagePersisted", "truncated", "truncatedByTier", "byFinish"} <= set(usage)
    assert {"retries", "retriesByStatus", "fallbacks"} <= set(usage)
    assert {"admissionWaitSamples", "admissionTimeouts"} <= set(usage)
    assert {"enabled", "loadStatus", "lastSaveAt", "saveFailures"} <= set(usage["usageState"])
    assert "pruned" in usage["cache"]
    assert "liveItems" in usage["cache"]
    assert all(set(check) == {"code", "severity", "message"} for check in health["configChecks"])


def test_every_request_field_is_documented():
    from app.main import ChatRequest

    section = _read("docs/API.md").split("### 2.1")[1].split("## 3.")[0]
    documented = set(re.findall(r"^\| `([a-zA-Z]+)` \|", section, re.M))

    assert documented == set(ChatRequest.model_fields)


def test_the_validation_error_shape_matches_the_document():
    import dataclasses

    from fastapi.testclient import TestClient

    main = __import__("app.main", fromlist=["app"])
    original = main.settings
    try:
        main.settings = dataclasses.replace(original, free_api_key="test-key")
        response = TestClient(main.app).post(
            "/api/chat",
            json={"messages": [{"role": "user", "content": "在吗"}], "temperature": 9.0},
        )
    finally:
        main.settings = original

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_body"


def test_every_config_check_code_is_documented(monkeypatch):
    import dataclasses

    from app import pricing
    from app.config import load_settings
    from app.validation import check_settings

    block = re.search(r"<!-- CHECK_CODES\s*\n(.*?)\n-->", _read("docs/API.md"), re.S)
    assert block, "docs/API.md lost its machine-readable check-code list"
    documented = {line.strip() for line in block.group(1).splitlines() if line.strip()}

    broken = dataclasses.replace(
        load_settings(),
        fallback_base_url="https://example.test/v1",
        free_model="bad model",
        byok_base_url="not-a-url",
        breaker_cooldown=1.0,
        upstream_read_timeout=900.0,
        daily_limit=1,
        rate_limit=30,
        system_prompt="",
        max_concurrency=50,
        cache_max_items=2,
        cache_max_bytes=1024,
        max_tracked_models=2,
        rate_window=30,
        heartbeat_seconds=120.0,
        admission_timeout=0.2,
        price_overrides="broken",
        stream_usage=False,
        cache_ttl=300.0,
        usage_state="state.json",
    )
    produced = {check.code for check in check_settings(broken)}
    produced |= {check.code for check in check_settings(dataclasses.replace(broken, cache_ttl=0))}
    produced |= {
        check.code
        for check in check_settings(dataclasses.replace(broken, system_prompt="x" * 8001))
    }
    monkeypatch.setattr(pricing, "CACHE_PRICES", {**pricing.CACHE_PRICES, "ghost": 0.5})
    produced |= {check.code for check in check_settings(broken)}

    assert documented == produced


def test_the_cache_byte_fields_are_published_on_both_status_endpoints():
    pytest.importorskip("fastapi", reason="web dependencies are not installed")
    from fastapi.testclient import TestClient

    main = __import__("app.main", fromlist=["app"])
    client = TestClient(main.app)
    documented = {"maxBytes", "byteEvictions", "byteFull"}
    section = _read("docs/API.md").split("## 6. 状态端点新增字段")[1]

    assert all(f"`cache.{field}`" in section for field in documented)
    for endpoint in ("/api/health", "/api/usage"):
        published = set(client.get(endpoint).json()["cache"])
        assert documented <= published
