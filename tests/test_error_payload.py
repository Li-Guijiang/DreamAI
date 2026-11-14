"""The SSE error contract must survive a reworded sentence."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

WEB = str(Path(__file__).resolve().parent.parent / "web")
if WEB not in sys.path:
    sys.path.insert(0, WEB)

from app.errors import error_code, error_payload, is_retryable  # noqa: E402


@pytest.mark.parametrize(
    ("status", "code"),
    [
        (None, "internal"),
        (401, "auth"),
        (402, "auth"),
        (403, "auth"),
        (400, "payload"),
        (413, "payload"),
        (422, "payload"),
        (429, "rate_limit"),
        (404, "address"),
        (410, "address"),
        (408, "upstream"),
        (425, "upstream"),
        (500, "upstream"),
        (503, "upstream"),
        (504, "upstream"),
        (418, "upstream"),
    ],
)
def test_status_categories(status, code):
    assert error_code(status) == code


def test_the_sentence_is_untouched():
    sentence = "上游服务暂时不可用，稍后重试。"

    assert error_payload(sentence, status=503)["message"] == sentence


def test_an_empty_sentence_falls_back_to_a_readable_one():
    assert error_payload("", status=503)["message"]
    assert error_payload("   ", status=503)["message"]


def test_every_event_has_the_same_four_fields():
    payload = error_payload("msg", status=401)

    assert set(payload) == {"message", "code", "status", "retryable"}


def test_retryable_defaults_to_the_status_policy():
    assert error_payload("msg", status=503)["retryable"] is True
    assert error_payload("msg", status=401)["retryable"] is False
    assert error_payload("msg")["retryable"] is False


def test_a_statusless_failure_carries_a_null_status():
    payload = error_payload("msg")

    assert payload["status"] is None
    assert payload["code"] == "internal"


def test_a_breaker_can_override_both_fields():
    payload = error_payload("msg", code="breaker", retryable=True)

    assert payload["code"] == "breaker"
    assert payload["retryable"] is True
    assert payload["status"] is None


def test_the_payload_never_disagrees_with_the_retry_policy():
    for status in (None, 400, 401, 408, 425, 429, 500, 502, 503, 504):
        assert error_payload("msg", status=status)["retryable"] is is_retryable(status)
