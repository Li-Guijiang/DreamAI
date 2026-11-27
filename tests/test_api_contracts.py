"""The browser depends on these response shapes being stable."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

pytest.importorskip("fastapi", reason="web dependencies are not installed")
WEB = str(Path(__file__).resolve().parent.parent / "web")
if WEB not in sys.path:
    sys.path.insert(0, WEB)

from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.syspath_prepend(WEB)
    main = importlib.import_module("app.main")
    return TestClient(main.app)


def test_health_always_reports_the_core_fields(client):
    data = client.get("/api/health").json()

    assert {
        "ok",
        "configured",
        "model",
        "models",
        "byok",
        "version",
        "upstream",
        "breaker",
        "cache",
        "configChecks",
        "configClamped",
    } <= set(data)


def test_health_never_returns_a_key(client):
    body = client.get("/api/health").text

    for marker in ("sk-", "apiKey", "api_key", "DREAMAI_FREE_API_KEY"):
        assert marker not in body


def test_usage_reports_the_daily_budget(client):
    data = client.get("/api/usage").json()

    assert isinstance(data.get("daily"), dict)
    assert isinstance(data.get("dailyLimit"), int)
    assert isinstance(data.get("requests"), int)
    assert isinstance(data.get("usageState"), dict)
    assert "loadStatus" in data["usageState"]


def test_config_reports_client_limits(client):
    data = client.get("/api/config").json()

    limits = data["limits"]
    assert limits["maxInputChars"] >= 500
    assert limits["maxTokens"] >= 256
    assert limits["rateLimit"] >= 1
    assert limits["rateWindow"] >= 30


def test_robots_references_the_sitemap(client):
    body = client.get("/robots.txt").text

    assert "Disallow: /api/" in body
    assert "https://liguijiang.com/sitemap.xml" in body


def test_sitemap_is_valid_xml_with_a_single_urlset(client):
    import xml.etree.ElementTree as ET

    body = client.get("/sitemap.xml").text
    root = ET.fromstring(body)

    assert root.tag.endswith("urlset")
    assert len(root) >= 4
    for url in root:
        assert url.tag.endswith("url")
        assert url.find("{*}loc") is not None


def test_static_pages_are_served(client):
    for path in ("/", "/index.html", "/offline.html", "/sw.js", "/manifest.webmanifest"):
        response = client.get(path)
        assert response.status_code == 200, path


def test_root_index_is_marked_no_cache(client):
    response = client.get("/")

    assert response.headers.get("Cache-Control") == "no-cache"


def test_manifest_is_json(client):
    response = client.get("/manifest.webmanifest")

    data = response.json()
    assert data["display"] == "standalone"
    assert data["start_url"] == "/"


def test_unknown_routes_return_404(client):
    assert client.get("/api/does-not-exist").status_code == 404
