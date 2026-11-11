"""Status codes must map to one retry policy and one readable message."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "web"))

import pytest
from app.errors import (  # noqa: E402
    BYOK_STATUS,
    RETRYABLE_STATUS,
    final_message,
    is_retryable,
    usable_detail,
    user_message,
)


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


def test_a_key_failure_hides_whatever_the_provider_wrote():
    message = final_message(401, "OpenAI", "Incorrect API key provided: sk-abc")

    assert "OpenAI" in message
    assert "sk-abc" not in message


def test_a_parameter_detail_is_kept_when_the_provider_explains_it():
    detail = "maximum context length is 8192 tokens, you sent 9000"

    assert final_message(400, "DeepSeek", detail) == detail


def test_json_and_html_are_never_shown_to_a_visitor():
    assert not usable_detail('{"error": {"message": "bad"}}')
    assert not usable_detail("<html><body>502 Bad Gateway</body></html>")
    assert final_message(400, "x", '{"error": "oops"}') == user_message(400, "x")


def test_a_long_detail_is_replaced_by_our_sentence():
    assert final_message(422, "", "x" * 400) == user_message(422)


def test_a_request_that_never_arrived_keeps_its_own_explanation():
    message = final_message(None, "DeepSeek", "无法连接模型服务，请稍后重试。")

    assert "无法连接" in message


def test_a_missing_status_with_nothing_to_say_still_answers():
    assert final_message(None, "DeepSeek", "") == "请求没有成功，请稍后重试。"


def test_a_retired_model_is_permanent_and_names_the_fix():
    message = user_message(410, "OpenAI")

    assert "OpenAI" in message
    assert "模型" in message
    assert "换" in message
    assert "稍后重试" not in message
    assert not is_retryable(410)


def test_a_retired_model_never_shows_the_provider_wording():
    from app.errors import final_message

    assert final_message(410, "OpenAI", "model deprecated") == user_message(410, "OpenAI")
