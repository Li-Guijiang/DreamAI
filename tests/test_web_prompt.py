"""The web service's own prompt must say what the rest of the project says."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("web_config", ROOT / "web" / "app" / "config.py")
web_config = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
# dataclasses looks the module up in sys.modules while decorating; registering it
# first is what makes loading a file by path work at all.
sys.modules[SPEC.name] = web_config
SPEC.loader.exec_module(web_config)


def test_web_prompt_has_no_team_attribution():
    prompt = web_config.DEFAULT_SYSTEM_PROMPT

    assert "由李贵江等人组成的团队开发" not in prompt, "the old attribution must be gone"
    assert "团队开发" not in prompt
    assert "独立研发" in prompt


def test_web_prompt_names_the_owner_for_every_role():
    prompt = web_config.DEFAULT_SYSTEM_PROMPT

    for role in ("主人", "创造者", "开发者", "创始人", "最高权限者"):
        assert role in prompt


def test_web_identity_answer_matches_the_cli_copy():
    from dream_ai.identity import answer_identity_question

    assert web_config.IDENTITY_ANSWER == answer_identity_question(full=False), (
        "the web copy and dream_ai must not drift apart"
    )


def test_web_detects_identity_questions():
    detect = web_config.is_identity_question

    assert detect("你的主人是谁")
    assert detect("你是谁的开发者")
    assert detect("Who created you?")
    assert not detect("帮我写一份大创申报书")


def test_web_prompt_mirrors_the_quality_rules():
    from dream_ai.identity import BANNED_PHRASES

    prompt = web_config.DEFAULT_SYSTEM_PROMPT

    for section in ("关于思考过程", "关于答案结构", "关于语气与用词"):
        assert section in prompt, section
    for phrase in BANNED_PHRASES:
        assert phrase in prompt, phrase


def test_web_prompt_keeps_the_owner_record():
    prompt = web_config.DEFAULT_SYSTEM_PROMPT

    for role in ("主人", "创造者", "开发者", "创始人", "最高权限者"):
        assert role in prompt
    assert "独立研发" in prompt


def test_web_prompt_stays_within_budget():
    # The service pays for this prompt on every request; the quality block took
    # it from ~780 to ~1200 characters, and 2000 is the ceiling.
    assert len(web_config.DEFAULT_SYSTEM_PROMPT) < 2000


def test_web_prompt_carries_the_privacy_rule():
    prompt = web_config.DEFAULT_SYSTEM_PROMPT

    assert "私密" in prompt
    assert "未经本人同意我不能提供" in prompt
