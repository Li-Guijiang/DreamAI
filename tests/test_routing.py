"""Model-per-tier mapping must be forgiving about bad configuration."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))

from app.routing import choose_model, parse_tier_map  # noqa: E402


def test_parses_pairs_and_trims():
    assert parse_tier_map(" light=glm-4-flash , deep=deepseek-reasoner ") == {
        "light": "glm-4-flash",
        "deep": "deepseek-reasoner",
    }


def test_ignores_malformed_entries():
    # 空模型、空键、缺等号全部丢弃，只留合法的一对。
    assert parse_tier_map("light=,=x,,deep") == {}
    assert parse_tier_map("light=cheap,broken,deep=") == {"light": "cheap"}


def test_empty_config_is_empty_map():
    assert parse_tier_map("") == {}


def test_unknown_tier_uses_the_default():
    mapping = {"light": "cheap"}

    assert choose_model("deep", "default", mapping) == "default"
    assert choose_model("light", "default", mapping) == "cheap"


def test_empty_default_never_returns_none():
    assert choose_model("deep", "", {}) == ""


def test_a_default_entry_catches_every_unmapped_tier():
    from app.routing import choose_model

    mapping = {"light": "cheap", "default": "steady"}

    assert choose_model("light", "site", mapping) == "cheap"
    assert choose_model("deep", "site", mapping) == "steady"
    assert choose_model("", "site", mapping) == "steady"


def test_a_mapping_without_a_default_leaves_the_site_model_alone():
    from app.routing import choose_model

    assert choose_model("deep", "site", {"light": "cheap"}) == "site"


def test_a_tier_is_matched_regardless_of_capitalisation():
    from app.routing import choose_model

    assert choose_model("DEEP", "site", {"deep": "expensive"}) == "expensive"
