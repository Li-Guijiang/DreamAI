"""Status codes must map to one retry policy and one readable message."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))

import pytest
from app.errors import BYOK_STATUS, RETRYABLE_STATUS, is_retryable, user_message  # noqa: E402


@pytest.mark.parametrize("status", [408, 425, 429, 500, 502, 503, 504])
def test_transient_status_is_retryable(status):
    assert is_retryable(status)


@pytest.mark.parametrize("status", [400, 401, 402, 403, 404, 422])
def test_client_status_is_not_retryable(status):
    assert not is_retryable(status)


def test_the_two_sets_do_not_overlap():
    assert not (RETRYABLE_STATUS & BYOK_STATUS)


def test_key_failure_names_the_provider():
    message = user_message(401, "OpenAI")

    assert "OpenAI" in message
    assert "Key" in message


def test_rate_limit_tells_the_user_to_wait():
    assert "稍后" in user_message(429) or "等" in user_message(429)


def test_server_error_does_not_blame_the_user():
    message = user_message(503)

    assert "上游" in message
    assert "Key" not in message


def test_not_found_points_at_the_address_and_the_model_name():
    message = user_message(404, "DeepSeek")

    assert "DeepSeek" in message
    assert "模型" in message
    # The two mistakes that actually produce a 404 here.
    assert "/v1" in message
    assert "稍后重试" not in message


def test_oversized_input_talks_about_length_not_about_keys():
    message = user_message(413)

    assert "长" in message
    assert "Key" not in message
    assert "稍后重试" not in message


def test_a_rejected_payload_names_the_parameters_too():
    for status in (400, 422):
        message = user_message(status)
        assert "参数" in message or "max_tokens" in message, status


def test_a_payload_problem_is_never_worth_retrying():
    from app.errors import PAYLOAD_STATUS

    assert not (PAYLOAD_STATUS & RETRYABLE_STATUS)
    assert not (PAYLOAD_STATUS & BYOK_STATUS)
