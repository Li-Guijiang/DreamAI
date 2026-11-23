"""A missing snapshot is normal; a corrupt one is an incident."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))

from app.state_store import describe_snapshot, load_snapshot, save_snapshot  # noqa: E402


def test_no_path_is_disabled():
    assert describe_snapshot(None) == "disabled"
    assert describe_snapshot("") == "disabled"


def test_no_file_yet_is_absent(tmp_path):
    assert describe_snapshot(tmp_path / "usage.json") == "absent"


def test_a_valid_file_is_valid(tmp_path):
    path = tmp_path / "usage.json"
    assert save_snapshot(path, {"requests": 7}) is True

    assert describe_snapshot(path) == "valid"


def test_a_truncated_file_is_corrupt(tmp_path):
    path = tmp_path / "usage.json"
    path.write_text('{"version":1,', encoding="utf-8")

    assert describe_snapshot(path) == "corrupt"


def test_a_wrong_version_is_corrupt(tmp_path):
    path = tmp_path / "usage.json"
    path.write_text(json.dumps({"version": 99, "counters": {}}), encoding="utf-8")

    assert describe_snapshot(path) == "corrupt"
    assert load_snapshot(path) is None


def test_a_directory_at_the_path_is_corrupt(tmp_path):
    path = tmp_path / "usage.json"
    path.mkdir()

    assert describe_snapshot(path) == "corrupt"


def test_a_leftover_tmp_file_does_not_count_as_a_snapshot(tmp_path):
    (tmp_path / "usage.json.tmp").write_text("{", encoding="utf-8")

    assert describe_snapshot(tmp_path / "usage.json") == "absent"


def test_an_oversized_file_is_not_parsed(tmp_path):
    from app.state_store import MAX_SNAPSHOT_BYTES

    path = tmp_path / "usage.json"
    path.write_bytes(b"x" * (MAX_SNAPSHOT_BYTES + 1))

    assert describe_snapshot(path) == "oversized"
    assert load_snapshot(path) is None


def test_non_finite_counters_are_not_written(tmp_path):
    import math

    path = tmp_path / "usage.json"

    assert save_snapshot(path, {"cost_usd": math.inf}) is False
    assert not path.exists()


def test_a_valid_file_with_a_huge_padding_is_rejected(tmp_path):
    path = tmp_path / "usage.json"
    valid = '{"version":1,"counters":{}}'
    path.write_text(valid + " " * (9 * 1024 * 1024), encoding="utf-8")

    assert describe_snapshot(path) == "oversized"
