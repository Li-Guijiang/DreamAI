"""DREAMAI_MODEL_BY_TIER must reach the settings object intact."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))

from app.config import load_settings  # noqa: E402


def test_map_is_parsed_from_env(monkeypatch):
    monkeypatch.setenv("DREAMAI_MODEL_BY_TIER", "light=glm-4-flash,deep=deepseek-reasoner")

    assert load_settings().model_by_tier == {
        "light": "glm-4-flash",
        "deep": "deepseek-reasoner",
    }


def test_absent_map_is_empty(monkeypatch):
    monkeypatch.delenv("DREAMAI_MODEL_BY_TIER", raising=False)

    assert load_settings().model_by_tier == {}
