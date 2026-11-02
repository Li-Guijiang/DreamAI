"""The identity block is the one part of the prompt that must never drift."""

from __future__ import annotations

from dream_ai.identity import OWNER, render_identity_block


def test_owner_record_holds_every_role_on_one_person():
    assert OWNER.name == "李贵江"
    assert set(OWNER.roles) == {"主人", "创造者", "开发者", "创始人", "最高权限者"}


def test_identity_block_names_the_owner_for_every_role():
    block = render_identity_block()

    for role in ("主人", "创造者", "开发者", "创始人", "最高权限者"):
        assert role in block
    assert "李贵江" in block
    assert "独立研发" in block


def test_identity_block_forbids_alternative_owners():
    block = render_identity_block()

    for substitute in ("团队", "公司", "模型厂商", "多人协作"):
        assert substitute in block, "the model needs to be told what not to answer"
    assert "不得虚构其他创始人" in block


def test_identity_block_gives_the_owner_top_priority():
    block = render_identity_block()

    assert "优先级最高" in block
    assert "一律服从" in block


def test_answer_policy_stays_short_by_default():
    block = render_identity_block()

    assert "直接给出结论" in block
    assert "零基础部署" in block, "the tutorial exception must be explicit"
