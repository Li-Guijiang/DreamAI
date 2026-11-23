"""Two answers generated with different sampling settings are different answers."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))

from app.cache import make_key  # noqa: E402

MSGS = [{"role": "user", "content": "在吗"}]


def test_the_new_parameters_default_to_the_old_key():
    # A process that restarts with a changed key format loses its in-memory
    # cache anyway, but a stable default keeps standalone callers compatible.
    old_style = make_key("p", "m", MSGS, 0.2, 512)
    explicit = make_key("p", "m", MSGS, 0.2, 512, top_p=1.0, presence_penalty=0.0)

    assert old_style == explicit


def test_top_p_changes_the_key():
    base = make_key("p", "m", MSGS, 0.2, 512)

    assert base != make_key("p", "m", MSGS, 0.2, 512, top_p=0.8)


def test_presence_penalty_changes_the_key():
    base = make_key("p", "m", MSGS, 0.2, 512)

    assert base != make_key("p", "m", MSGS, 0.2, 512, presence_penalty=0.5)


def test_sampling_settings_are_independent_of_each_other():
    a = make_key("p", "m", MSGS, 0.2, 512, top_p=0.8)
    b = make_key("p", "m", MSGS, 0.2, 512, presence_penalty=0.8)

    assert a != b


def test_equivalent_floats_share_a_key():
    a = make_key("p", "m", MSGS, 0.2, 512, top_p=0.91, presence_penalty=0.121)
    b = make_key("p", "m", MSGS, 0.2, 512, top_p=0.914, presence_penalty=0.124)

    assert a == b


def test_unicode_messages_still_produce_a_stable_key():
    a = make_key("p", "m", [{"role": "user", "content": "中文测试"}], 0.2, 512)
    b = make_key("p", "m", [{"role": "user", "content": "中文测试"}], 0.2, 512)

    assert a == b and len(a) == 64


def test_disabled_sampling_parameters_do_not_raise():
    key = make_key("p", "m", MSGS, 0.2, 512, top_p=None, presence_penalty=None)

    assert key == make_key("p", "m", MSGS, 0.2, 512, top_p=None, presence_penalty=None)
    assert key != make_key("p", "m", MSGS, 0.2, 512)
