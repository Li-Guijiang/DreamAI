"""The browser may know the shape of the service, never its secrets."""

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

from app.config import ModelOption  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

MARKERS = [
    "SUPERSECRETKEY",
    "https://secret.internal/v1",
    "secret-model-name",
    "/private/path/usage.json",
    "SECRET-SYSTEM-PROMPT",
    "SUPERSECRET-FALLBACK",
]


def patched_settings(main):
    return dataclasses.replace(
        main.settings,
        free_api_key=MARKERS[0],
        byok_base_url=MARKERS[1],
        byok_models=(ModelOption(id="private-key-model", label="label", reasoning=False),),
        usage_state=MARKERS[3],
        system_prompt=MARKERS[4],
        fallback_api_key=MARKERS[5],
        fallback_model=MARKERS[2],
    )


def test_no_secret_marker_reaches_the_public_config(monkeypatch):
    main = importlib.import_module("app.main")
    monkeypatch.setattr(main, "settings", patched_settings(main))

    with TestClient(main.app) as client:
        body = client.get("/api/config").text

    for marker in MARKERS:
        assert marker not in body


def test_no_secret_marker_reaches_the_health_endpoint(monkeypatch):
    main = importlib.import_module("app.main")
    monkeypatch.setattr(main, "settings", patched_settings(main))

    with TestClient(main.app) as client:
        body = client.get("/api/health").text

    for marker in MARKERS:
        assert marker not in body


def test_the_public_config_has_a_stable_top_level_shape():
    main = importlib.import_module("app.main")

    with TestClient(main.app) as client:
        data = client.get("/api/config").json()

    assert set(data) == {
        "configured",
        "defaultModel",
        "defaultProvider",
        "models",
        "free",
        "byok",
        "siteTitle",
        "tagline",
        "repoUrl",
        "version",
        "limits",
        "providers",
    }


def test_public_models_never_carry_credentials():
    main = importlib.import_module("app.main")

    with TestClient(main.app) as client:
        data = client.get("/api/config").json()

    for model in data["models"]:
        assert set(model) <= {"id", "label", "reasoning", "provider", "hint"}
    for provider in data["providers"]:
        assert set(provider) <= {"id", "label", "keyUrl", "hint", "models"}
        for model in provider["models"]:
            assert set(model) <= {"id", "label", "reasoning"}
