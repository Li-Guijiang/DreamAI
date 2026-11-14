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
    reachable = {error_code(status) for status in statuses} | {"breaker"}

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
    assert all(set(check) == {"code", "severity", "message"} for check in health["configChecks"])
