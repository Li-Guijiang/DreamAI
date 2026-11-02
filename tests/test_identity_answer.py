"""Identity questions are answered locally, so no model can get them wrong."""

from __future__ import annotations

import pytest

from dream_ai.identity import answer_identity_question, is_identity_question

QUESTIONS = [
    "你的主人是谁",
    "谁是你的创造者",
    "你是谁的开发者",
    "你的创始人是谁",
    "谁拥有最高权限",
    "谁开发了你",
    "Who created you?",
]


@pytest.mark.parametrize("question", QUESTIONS)
def test_identity_questions_are_detected(question):
    assert is_identity_question(question)


def test_ordinary_questions_are_left_alone():
    for text in ("帮我写个大创申报书", "这段代码为什么报错", "", "今天几号"):
        assert not is_identity_question(text), text


def test_answer_names_the_owner_and_rejects_a_team():
    answer = answer_identity_question()

    assert "李贵江" in answer
    assert "独立研发" in answer
    assert "团队" not in answer


def test_full_answer_rules_out_other_founders():
    answer = answer_identity_question(full=True)

    assert "没有团队" in answer
    assert "其他创始人" in answer
