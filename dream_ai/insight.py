"""Question shape and input hygiene for the local surfaces.

The web service has its own copy in `web/app/insight.py` because it can be
deployed without this package. Keep the two in step when either changes; the
shared tests are small enough to run against both.
"""

from __future__ import annotations

import re

INTENT_ERROR = "error"
INTENT_DESIGN = "design"
INTENT_CODE = "code"
INTENT_WRITING = "writing"
INTENT_EXPLAIN = "explain"
INTENT_CHAT = "chat"

INTENT_PROMPTS: dict[str, str] = {
    INTENT_ERROR: "本轮是排错：按「现象→最可能的原因→修复步骤→如何验证」回答；给命令要能直接粘贴。",
    INTENT_DESIGN: "本轮是方案设计：先写目标与约束，再给两到三个可选方案与取舍，最后给推荐及理由。",
    INTENT_CODE: "本轮是写代码：先给可运行的最小实现，再说明关键行与边界情况；不要先讲原理。",
    INTENT_WRITING: "本轮是写作：先给成稿，再给一句修改说明；不要逐句解释用词。",
    INTENT_EXPLAIN: "本轮是解释概念：先给一句话定义，再给一个具体例子，最后指出常见误解。",
    INTENT_CHAT: "",
}

_ERROR_WORDS = (
    "报错",
    "错误",
    "异常",
    "exception",
    "traceback",
    "failed",
    "失败",
    "跑不起来",
    "npe",
)
_DESIGN_WORDS = ("方案", "架构", "设计", "选型", "对比", "权衡", "如何实现", "规划")
_WRITE_WORDS = (
    "写一段",
    "写一篇",
    "润色",
    "改写",
    "文案",
    "通知",
    "总结",
    "简历",
    "周报",
    "演讲稿",
)
_EXPLAIN_WORDS = ("是什么", "什么是", "原理", "区别", "为什么", "解释", "含义")

_LOG_LINE = re.compile(
    r"(error|exception|traceback|failed|fatal|caused by|warn|拒绝|失败|异常|错误)", re.I
)


def classify_intent(text: str) -> str:
    """Classify a turn into one of six intents; error beats design on overlap."""
    body = (text or "").strip().lower()
    if not body:
        return INTENT_CHAT
    if "```" in body or any(word in body for word in _ERROR_WORDS):
        return INTENT_ERROR
    if any(word in body for word in _WRITE_WORDS):
        return INTENT_WRITING
    if any(word in body for word in _DESIGN_WORDS):
        return INTENT_DESIGN
    if any(word in body for word in _EXPLAIN_WORDS):
        return INTENT_EXPLAIN
    if re.search(r"\b(def|class|function|select|import|npm|pip|git)\b", body):
        return INTENT_CODE
    return INTENT_CHAT


def intent_prompt(intent: str) -> str:
    return INTENT_PROMPTS.get(intent, "")


def trim_long_input(text: str, max_chars: int = 3000) -> str:
    """Keep the head, the error lines and the tail of a very long paste."""
    body = text or ""
    if len(body) <= max_chars:
        return body

    lines = body.splitlines()
    head = "\n".join(lines[:6])
    tail = "\n".join(lines[-4:])
    hits = [line for line in lines if _LOG_LINE.search(line)][:12]
    parts = [head]
    if hits:
        parts.append("……（中间省略，以下为关键行）……\n" + "\n".join(dict.fromkeys(hits)))
    parts.append("……（末尾）……\n" + tail)
    return "\n".join(parts)[:max_chars]


def _tokens(text: str) -> set[str]:
    body = (text or "").lower()
    latin = set(re.findall(r"[a-z0-9_]{3,}", body))
    chinese = re.sub(r"[^\u4e00-\u9fa5]", "", body)
    return latin | {chinese[i : i + 2] for i in range(len(chinese) - 1)}


def is_repeat(text: str, previous: str, threshold: float = 0.75) -> bool:
    """True when the new question is a rephrasing of the previous one."""
    a, b = _tokens(text), _tokens(previous)
    if not a or not b:
        return False
    return len(a & b) / min(len(a), len(b)) >= threshold


def detect_language(text: str) -> str:
    """Return ``zh`` or ``en`` from the character mix of the message.

    Mirrors ``web/app/insight.py``; the web copy is the reference.
    """
    body = text or ""
    han = len(re.findall(r"[\u4e00-\u9fa5]", body))
    latin = len(re.findall(r"[A-Za-z]", body))
    return "zh" if han >= latin else "en"


def language_prompt(language: str) -> str:
    """Keep the reply in the language the user wrote in."""
    if language == "en":
        return "Reply in English; keep code, commands and identifiers unchanged."
    return "用中文回答；代码、命令、专有名词保持原样。"
