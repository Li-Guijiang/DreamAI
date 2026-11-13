"""The snapshot file must be atomic, versioned and safe to ignore."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

WEB = str(Path(__file__).resolve().parent.parent / "web")
if WEB not in sys.path:
    sys.path.insert(0, WEB)

from app.state_store import SNAPSHOT_VERSION, load_snapshot, save_snapshot  # noqa: E402


def test_a_saved_counter_survives_a_round_trip(tmp_path):
    path = tmp_path / "usage.json"

    assert save_snapshot(path, {"requests": 7, "cost_usd": 0.0123}) is True
    assert load_snapshot(path) == {"requests": 7, "cost_usd": 0.0123}


def test_the_file_is_a_versioned_envelope(tmp_path):
    path = tmp_path / "usage.json"
    save_snapshot(path, {"requests": 1})

    envelope = json.loads(path.read_text(encoding="utf-8"))

    assert envelope["version"] == SNAPSHOT_VERSION
    assert envelope["savedAt"] > 0
    assert envelope["counters"] == {"requests": 1}
    assert not (tmp_path / "usage.json.tmp").exists()


def test_a_second_save_replaces_the_first_atomically(tmp_path):
    path = tmp_path / "usage.json"
    save_snapshot(path, {"requests": 1})
    save_snapshot(path, {"requests": 2})

    assert load_snapshot(path) == {"requests": 2}
    assert list(tmp_path.iterdir()) == [path]


def test_a_missing_file_is_not_an_error(tmp_path):
    assert load_snapshot(tmp_path / "nope.json") is None


def test_no_path_means_no_work():
    assert save_snapshot("", {"requests": 1}) is False
    assert load_snapshot(None) is None


@pytest.mark.parametrize(
    "content",
    [
        "not json",
        "[]",
        "{}",
        '{"version": 999, "counters": {"requests": 1}}',
        '{"version": 1, "counters": []}',
        '{"version": 1}',
    ],
)
def test_a_corrupt_or_old_file_is_ignored(tmp_path, content):
    path = tmp_path / "usage.json"
    path.write_text(content, encoding="utf-8")

    assert load_snapshot(path) is None


def test_a_stale_tmp_file_is_not_read_as_a_snapshot(tmp_path):
    (tmp_path / "usage.json.tmp").write_text("half written", encoding="utf-8")

    assert load_snapshot(tmp_path / "usage.json") is None


def test_a_path_that_cannot_be_written_returns_false(tmp_path):
    # A file used as a parent directory: mkdir fails, and the request must not.
    blocked = tmp_path / "not-a-dir"
    blocked.write_text("x", encoding="utf-8")

    assert save_snapshot(blocked / "usage.json", {"requests": 1}) is False


def test_a_value_that_cannot_be_serialised_does_not_leave_a_tmp_file(tmp_path):
    path = tmp_path / "usage.json"

    assert save_snapshot(path, {"bad": object()}) is False
    assert not path.exists()
    assert not (tmp_path / "usage.json.tmp").exists()


def test_missing_parent_directories_are_created(tmp_path):
    path = tmp_path / "nested" / "deeper" / "usage.json"

    assert save_snapshot(path, {"requests": 3}) is True
    assert load_snapshot(path) == {"requests": 3}
