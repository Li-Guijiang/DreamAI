"""What kind of question is this, and what does the model need to see?

`quality.py` decides *how much room* a reply gets. This module decides *what kind
of answer* is expected, and cleans the input before it reaches the model.

All functions are pure: no settings, no network.
"""

from __future__ import annotations

import re

INTENT_ERROR = "error"
INTENT_DESIGN = "design"
INTENT_CODE = "code"
INTENT_WRITING = "writing"
INTENT_TRANSLATE = "translate"
INTENT_EXPLAIN = "explain"
INTENT_CHAT = "chat"

#: One short instruction per intent. Written as a shape, not an adjective: a small
#: model can follow "复现→原因→修复→验证" where it cannot follow "answer well".
INTENT_PROMPTS: dict[str, str] = {
    INTENT_ERROR: "本轮是排错：按「现象→最可能的原因→修复步骤→如何验证」回答；给命令要能直接粘贴。",
    INTENT_DESIGN: "本轮是方案设计：先写目标与约束，再给两到三个可选方案与取舍，最后给推荐及理由。",
    INTENT_CODE: "本轮是写代码：先给可运行的最小实现，再说明关键行与边界情况；不要先讲原理。",
    INTENT_WRITING: "本轮是写作：先给成稿，再给一句修改说明；不要逐句解释用词。",
    INTENT_TRANSLATE: "本轮是翻译：先给可直接使用的译文；只在术语或语气需要取舍时补一句说明，不逐句对照。",
    INTENT_EXPLAIN: "本轮是解释概念：先给一句话定义，再给一个具体例子，最后指出常见误解。",
    INTENT_CHAT: "",
}

_ERROR_WORDS = ("报错", "错误", "异常", "exception", "traceback", "failed", "失败", "跑不起来", "启动不了", "npe", "500")
_DESIGN_WORDS = ("方案", "架构", "设计", "选型", "对比", "权衡", "怎么做", "如何实现", "规划")
_WRITE_WORDS = ("写一段", "写一篇", "润色", "改写", "文案", "通知", "总结", "简历", "周报", "演讲稿")
_TRANSLATE_WORDS = ("翻译", "译成", "译为", "translate", "translation")
_EXPLAIN_WORDS = ("是什么", "什么是", "原理", "区别", "为什么", "解释", "含义")


def classify_intent(text: str) -> str:
    """Classify the turn into one of six intents.

    Order matters: an error message often also contains design words ("怎么改"),
    and a fix is more useful than a redesign, so error wins.
    """
    body = (text or "").strip().lower()
    if not body:
        return INTENT_CHAT
    if "```" in body or any(word in body for word in _ERROR_WORDS):
        return INTENT_ERROR
    if any(word in body for word in _WRITE_WORDS):
        return INTENT_WRITING
    if any(word in body for word in _TRANSLATE_WORDS):
        return INTENT_TRANSLATE
    if any(word in body for word in _DESIGN_WORDS):
        return INTENT_DESIGN
    if any(word in body for word in _EXPLAIN_WORDS):
        return INTENT_EXPLAIN
    if re.search(r"\b(def|class|function|select|import|npm|pip|git)\b", body):
        return INTENT_CODE
    return INTENT_CHAT


def intent_prompt(intent: str) -> str:
    """The instruction for an intent, or an empty string for plain chat."""
    return INTENT_PROMPTS.get(intent, "")


_LOG_LINE = re.compile(
    r"(error|exception|traceback|failed|fatal|caused by|warn|拒绝|失败|异常|错误)", re.I
)


def trim_long_input(text: str, max_chars: int = 3000) -> str:
    """Shrink a very long paste while keeping the lines that matter.

    Logs and stack traces are mostly noise; the signal is the error lines plus the
    head (what the user was doing) and the tail (where it stopped).
    """
    body = text or ""
    if len(body) <= max_chars:
        return body

    lines = body.splitlines()
    head = "\n".join(lines[:6])
    tail = "\n".join(lines[-4:])
    hits = [line for line in lines if _LOG_LINE.search(line)][:12]
    picked = "\n".join(dict.fromkeys(hits))

    parts = [head]
    if picked:
        parts.append("……（中间省略，以下为关键行）……\n" + picked)
    parts.append("……（末尾）……\n" + tail)
    compact = "\n".join(parts)
    return compact[:max_chars]


def _tokens(text: str) -> set[str]:
    """Latin words plus overlapping Chinese bigrams.

    ``findall`` on a two-character pattern skips every other pair, which makes two
    rephrasings of the same question look unrelated. Building the bigrams by hand
    keeps the overlap that matters.
    """
    body = (text or "").lower()
    latin = set(re.findall(r"[a-z0-9_]{3,}", body))
    chinese_chars = re.sub(r"[^\u4e00-\u9fa5]", "", body)
    bigrams = {chinese_chars[i : i + 2] for i in range(len(chinese_chars) - 1)}
    return latin | bigrams


def is_repeat(text: str, previous: str, threshold: float = 0.75) -> bool:
    """True when a question is nearly the same as the previous user turn.

    Answers the same question twice verbatim is the most visible sign of a dumb
    assistant; detecting it lets the route ask for a different angle instead.
    """
    a, b = _tokens(text), _tokens(previous)
    if not a or not b:
        return False
    overlap = len(a & b) / min(len(a), len(b))
    return overlap >= threshold


def detect_language(text: str) -> str:
    """Return ``zh`` or ``en`` from the character mix of the message."""
    body = text or ""
    han = len(re.findall(r"[\u4e00-\u9fa5]", body))
    latin = len(re.findall(r"[A-Za-z]", body))
    return "zh" if han >= latin else "en"


def language_prompt(language: str) -> str:
    """Keep the reply in the language the user wrote in."""
    if language == "en":
        return "Reply in English; keep code, commands and identifiers unchanged."
    return "用中文回答；代码、命令、专有名词保持原样。"
