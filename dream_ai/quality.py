"""Reply post-processing shared by the CLI and the desktop shell.

The web service streams, so it cannot rewrite text after sending it; the local
surfaces generate whole replies and can. These helpers are deliberately tiny and
pure so they stay cheap to call on every turn.
"""

from __future__ import annotations

import re

_FENCE = "```"


def close_fences(text: str) -> str:
    """Close a code fence the model left open, so the rest renders as code."""
    if not text:
        return text
    if text.count(_FENCE) % 2 == 1:
        return text.rstrip() + "\n```"
    return text


def dedupe_sentences(text: str) -> str:
    """Drop sentences repeated back to back, a common small-model loop."""
    if not text:
        return text
    parts = re.split(r"(?<=[。！？!?])\s*", text)
    kept: list[str] = []
    for part in parts:
        if part and kept and part.strip() == kept[-1].strip():
            continue
        kept.append(part)
    return "".join(kept)


def looks_empty(text: str) -> bool:
    """True when a reply carries no usable content."""
    body = (text or "").strip()
    if len(body) < 2:
        return True
    return body in {"。", "…", "...", "抱歉，我无法回答。", "我无法回答这个问题。"}


# --- Reply sizing ---------------------------------------------------------
#
# The web service sizes every turn to its question (see web/app/quality.py). The
# local surfaces never did: a one-line greeting and a design review both asked the
# provider for its maximum. The thresholds below are the same ones, kept here so
# this package can be installed without the web app.

TIER_LIGHT = "light"
TIER_STANDARD = "standard"
TIER_DEEP = "deep"

#: Each of these asks for reasoning rather than recall; one is enough.
_STRONG_DEEP = ("为什么", "对比", "比较", "怎么实现", "如何设计", "架构", "原理")
_DEEP_WORDS = (
    "权衡",
    "设计",
    "实现",
    "重构",
    "优化",
    "分析",
    "推导",
    "排查",
    "调试",
    "部署",
    "报错",
)

_LIGHT_MAX_CHARS = 12
_DEEP_MIN_CHARS = 80

#: (light, deep) caps, applied on top of whatever the caller configured.
_LIGHT_CAP = 768
_DEEP_ALLOWANCE = 1024
_DEEP_CAP = 8192


def classify_tier(text: str) -> str:
    """Rate a question as light, standard or deep.

    The rating decides how much room the model gets, so it only has to be roughly
    right. Length, pasted code and the vocabulary of trade-off questions are
    enough signal for that.
    """
    body = (text or "").strip()
    if not body:
        return TIER_LIGHT
    if "```" in body or re.search(r"\b(traceback|exception|error|stack trace)\b", body, re.I):
        return TIER_DEEP

    questions = body.count("?") + body.count("？")
    if len(body) <= _LIGHT_MAX_CHARS and questions <= 1:
        return TIER_LIGHT
    if any(word in body for word in _STRONG_DEEP) and len(body) >= 12:
        return TIER_DEEP

    deep_hits = sum(1 for word in _DEEP_WORDS if word in body)
    if len(body) >= _DEEP_MIN_CHARS or deep_hits >= 2 or questions >= 3:
        return TIER_DEEP
    return TIER_STANDARD


def reply_budget(tier: str, base: int) -> int:
    """Token budget for a tier, given the caller's configured maximum."""
    base = max(1, int(base or 0)) if base else 1024
    if tier == TIER_LIGHT:
        return min(base, _LIGHT_CAP)
    if tier == TIER_DEEP:
        return min(base + _DEEP_ALLOWANCE, _DEEP_CAP)
    return base


def tier_hint(tier: str) -> str:
    """One line telling the model how much room it has."""
    if tier == TIER_LIGHT:
        return "本轮问题很直接：一两句话答完，不展开背景，不列清单。"
    if tier == TIER_DEEP:
        return "本轮问题需要推演：先给结论，再给依据与取舍；复杂处用分步或表格，避免大段散文。"
    return ""


#: Short fragments built around one of these cannot be answered on their own;
#: the subject lives in an earlier turn.
_PRONOUNS = ("它", "他", "她", "这个", "那个", "上面", "前面", "刚才", "这样", "上述", "此")


def needs_context(text: str) -> bool:
    """True when the message is a follow-up that cannot stand on its own.

    Short messages with a pronoun, or fragments with no punctuation and no verb,
    are the two shapes that fail without the previous turn; both are cheap to
    detect. Mirrors ``web/app/quality.py``.
    """
    body = (text or "").strip()
    if not body:
        return False
    if len(body) <= 20 and any(word in body for word in _PRONOUNS):
        return True
    return len(body) <= 6 and not re.search(r"[，。！？,.!?]", body)
