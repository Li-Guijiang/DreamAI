"""One place that decides what an upstream status means.

The retry policy and the message a visitor reads were both derived from raw status
codes in two different files, which is how a 402 ends up retried three times and a
429 tells the user their key is invalid.

`is_retryable` answers the first question; `user_message` answers the second, in the
words the visitor needs rather than the words the provider used.

`final_message` is the one the chat pipeline calls. It has to choose between our
sentence and the provider's: ours is better for everything the visitor can fix
(the key, the quota, the address), the provider's is better for a parameter that
only it knows about - and never better when it is a wall of JSON or an HTML page.
"""

from __future__ import annotations

RETRYABLE_STATUS = frozenset({408, 425, 429, 500, 502, 503, 504})

BYOK_STATUS = frozenset({401, 402, 403})

# The request itself is the problem: no retry will fix it, and the visitor can.
PAYLOAD_STATUS = frozenset({400, 413, 422})


GENERIC = "请求没有成功，请稍后重试。"

# Statuses where our sentence beats anything the provider could say. 400 and 422
# are deliberately absent: there the provider knows which parameter it rejected,
# and that detail is the whole answer.
CURATED_STATUS = BYOK_STATUS | {404, 408, 413, 429}


def is_retryable(status: int) -> bool:
    """Transient failures worth one more attempt before giving up."""
    return status in RETRYABLE_STATUS


def user_message(status: int, label: str = "") -> str:
    """A message that says what to do next, not what the provider returned."""
    who = f"{label} " if label else ""
    if status in BYOK_STATUS:
        return f"{who}拒绝了这次请求：Key 无效、无权限或余额不足，请在设置中更新后重试。"
    if status == 429:
        return "请求太频繁了，等十几秒再试，或换一个模型。"
    if status >= 500:
        return "上游服务暂时不可用，稍后重试；已经生成的回答不会重复计费。"
    if status == 408:
        return "等上游响应超时了，请重试或把问题缩短一些。"
    if status == 413:
        return "这次请求的内容太长了，上游拒绝接收：请缩短问题，或开启一个新对话。"
    if status in PAYLOAD_STATUS:
        return (
            "上游认为请求的格式不对：多半是这个模型不支持某个参数，"
            "或 max_tokens 超过了它的上限。"
        )
    if status == 404:
        # A 404 from an OpenAI-compatible endpoint is almost never a missing
        # page: it is a wrong path (a base_url without /v1) or a wrong model.
        return f"{who}没有找到这个接口或模型：请检查 base_url 是否需要以 /v1 结尾，以及模型名是否拼写正确。"
    return "请求没有成功，请稍后重试。"


def usable_detail(raw: str, limit: int = 160) -> bool:
    """Whether the provider's own words are worth repeating to a visitor."""
    body = (raw or "").strip()
    if not body or len(body) > limit:
        return False
    if body[:1] in "{<[":
        # JSON errors and HTML error pages are for the log, not the chat bubble.
        return False
    return "Traceback" not in body


def final_message(status: int | None, label: str = "", raw: str = "") -> str:
    """The sentence a visitor sees, given what the upstream returned."""
    if status is None:
        # No status at all: the request never reached a server (DNS, TCP, TLS).
        # llm.py already wrote a sentence worth showing for those cases.
        return raw.strip() if usable_detail(raw) else GENERIC
    if status >= 500 or status in CURATED_STATUS:
        return user_message(status, label)
    if usable_detail(raw):
        return raw.strip()
    return user_message(status, label)
