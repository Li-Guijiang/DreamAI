"""Tests for terminal presentation and motion settings.

Animations must never leak into piped output, and every failure path should
degrade to plain, readable text.
"""

from __future__ import annotations

import io

import pytest

from dream_ai.cli import _apply_overrides, _parse_args
from dream_ai.config import load_settings
from dream_ai.ui import Console, supports_animation
from dream_ai.ui import motion as motion_module


class FakeTTY(io.StringIO):
    """A StringIO that claims to be an interactive terminal."""

    def isatty(self) -> bool:  # noqa: D102 - deliberately minimal test double
        return True


@pytest.fixture(autouse=True)
def _clean_motion_env(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("TERM", "xterm-256color")
    monkeypatch.setenv("DREAMAI_ANIMATIONS", "auto")
    monkeypatch.setattr(motion_module.time, "sleep", lambda _seconds: None)


def test_piped_output_is_plain_text():
    stream = io.StringIO()
    ui = Console(enabled=True, stream=stream)

    assert ui.animate is False
    ui.reply("hello")
    ui.intro("0.4.0", "local-echo", "deepseek-chat", offline=True)

    assert stream.getvalue().startswith("dream-ai › hello")
    assert "\x1b[" not in stream.getvalue()


def test_fake_tty_animates_and_keeps_the_message():
    stream = FakeTTY()
    ui = Console(enabled=True, speed=4, stream=stream)

    assert ui.animate is True
    ui.reply("hello from the universe")

    output = stream.getvalue()
    assert "dream-ai › " in output
    assert "hello from the universe" in output
    assert "\x1b[" in output


def test_no_color_disables_ansi_and_motion(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    stream = FakeTTY()
    ui = Console(enabled=True, stream=stream)

    assert ui.animate is False
    ui.reply("plain")
    assert "plain" in stream.getvalue()
    assert "\x1b[" not in stream.getvalue()


def test_environment_switch_can_disable_motion(monkeypatch):
    monkeypatch.setenv("DREAMAI_ANIMATIONS", "off")
    assert supports_animation(FakeTTY(), requested=True) is False


def test_toggle_switches_animation_state():
    ui = Console(enabled=True, stream=FakeTTY())

    assert ui.toggle() is False
    assert ui.toggle() is True


def test_status_on_non_tty_writes_nothing_extra():
    stream = io.StringIO()
    ui = Console(enabled=True, stream=stream)

    with ui.status("thinking"):
        pass

    assert stream.getvalue() == ""


def test_animation_settings_are_parsed(monkeypatch):
    monkeypatch.setenv("DREAMAI_ANIMATIONS", "false")
    monkeypatch.setenv("DREAMAI_ANIMATION_SPEED", "2.5")

    settings = load_settings()

    assert settings.animations_enabled is False
    assert settings.animation_speed == pytest.approx(2.5)


def test_animation_speed_is_clamped(monkeypatch):
    monkeypatch.setenv("DREAMAI_ANIMATION_SPEED", "99")

    assert load_settings().animation_speed == pytest.approx(4.0)


def test_no_animation_argument_overrides_settings():
    settings = load_settings()
    args = _parse_args(["--no-animation"])

    updated = _apply_overrides(settings, args)

    assert updated.animations_enabled is False
    assert updated.animation_speed == settings.animation_speed
