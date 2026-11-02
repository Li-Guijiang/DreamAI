"""Owner commands must be recognised exactly, and never guessed at."""

from __future__ import annotations

from dream_ai.identity import parse_owner_command


def test_show_command():
    command = parse_owner_command("【查看我的全部档案】")

    assert command is not None
    assert command.kind == "show"


def test_update_command_carries_the_fact():
    command = parse_owner_command("【更新档案】最近在准备大创答辩")

    assert command is not None
    assert command.kind == "update"
    assert command.payload == "最近在准备大创答辩"


def test_update_without_text_is_still_a_command():
    command = parse_owner_command("【更新档案】")

    assert command is not None
    assert command.kind == "update"
    assert command.payload == ""


def test_clear_command():
    assert parse_owner_command("【清空档案】").kind == "clear"


def test_half_width_brackets_are_accepted():
    assert parse_owner_command("[更新档案] 换了显示器").payload == "换了显示器"


def test_ordinary_messages_are_not_commands():
    for text in ("你好", "帮我看看这段代码", "【不是命令】", "", "   "):
        assert parse_owner_command(text) is None, text


def test_unknown_bracket_content_is_not_swallowed():
    assert parse_owner_command("【查看全部档案】") is None
    assert parse_owner_command("【档案】") is None
