"""One place that decides what an upstream status means.

The retry policy and the message a visitor reads were both derived from raw status
codes in two different files, which is how a 402 ends up retried three times and a
429 tells the user their key is invalid.

`is_retryable` answers the first question; `user_message` answers the second, in the
words the visitor needs rather than the words the provider used.
"""

from __future__ import annotations

RETRYABLE_STATUS = frozenset({408, 425, 429, 500, 502, 503, 504})

BYOK_STATUS = frozenset({401, 402, 403})


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
    return "请求没有成功，请稍后重试。"
