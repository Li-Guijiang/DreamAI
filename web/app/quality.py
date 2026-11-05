"""Cheap, deterministic helpers that make a reply smarter before the model runs.

Everything here is a pure function over text or message lists: no settings, no
network, no I/O. That keeps the behaviour testable and lets the route compose the
pieces it needs.

Three ideas drive the module:

* **Match the budget to the question.** A greeting does not need 4096 tokens and
  a architecture question should not run at temperature 0.9. ``classify_tier``
  rates the question and ``tier_params`` turns that into generation settings.
* **Repair broken context.** Truncating history at a byte count silently drops the
  turn a pronoun refers to; ``compress_history`` keeps the newest turns and folds
  the older ones into a short digest instead of deleting them outright.
* **Do not lose the subject of a follow-up.** "那它呢？" cannot be answered from a
  three-word message; ``needs_context`` detects that shape and
  ``build_digest`` supplies the missing subject.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

TIER_LIGHT = "light"
TIER_STANDARD = "standard"
TIER_DEEP = "deep"

#: Words that usually mean the answer has to weigh trade-offs rather than recall
#: a fact. Kept short on purpose: a long list starts matching ordinary questions.
_DEEP_WORDS = (
    "为什么",
    "对比",
    "比较",
    "权衡",
    "架构",
    "设计一个",
    "方案",
    "实现",
    "重构",
    "优化",
    "分析",
    "原理",
    "推导",
    "证明",
    "排查",
    "调试",
    "部署",
    "报错",
    "性能",
)

_LIGHT_MAX_CHARS = 12
_DEEP_MIN_CHARS = 80

#: A single one of these is enough on its own: each asks for reasoning, not recall.
_STRONG_DEEP = ("为什么", "对比", "比较", "怎么实现", "如何设计", "架构", "原理")


def classify_tier(text: str) -> str:
    """Rate a question as ``light``, ``standard`` or ``deep``.

    The rating only needs to be roughly right: it decides temperature and token
    budget, not correctness. Length, code, and the vocabulary of trade-off
    questions are enough signal for that.
    """
    body = (text or "").strip()
    if not body:
        return TIER_LIGHT

    # Code or logs almost always need room and precision.
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


def tier_params(tier: str, base_temperature: float, base_max_tokens: int) -> tuple[float, int, str]:
    """Return ``(temperature, max_tokens, prompt_hint)`` for a tier.

    The hint is appended to the system prompt: it tells the model how much room it
    has, which matters more than the raw numbers for a small model.
    """
    if tier == TIER_LIGHT:
        return (
            min(base_temperature, 0.4),
            min(base_max_tokens, 768),
            "本轮问题很直接：一两句话答完，不展开背景，不列清单。",
        )
    if tier == TIER_DEEP:
        return (
            max(base_temperature, 0.5),
            min(base_max_tokens + 1024, 8192),
            "本轮问题需要推演：先给结论，再给依据与取舍；复杂处用分步或表格，避免大段散文。",
        )
    return base_temperature, base_max_tokens, ""


_PRONOUNS = ("它", "他", "她", "这个", "那个", "上面", "前面", "刚才", "这样", "上述", "此")


def needs_context(text: str) -> bool:
    """True when the message is a follow-up that cannot stand on its own.

    Short messages with a pronoun, or fragments with no verb, are the two shapes
    that fail without the previous turn; both are cheap to detect.
    """
    body = (text or "").strip()
    if not body:
        return False
    if len(body) <= 20 and any(word in body for word in _PRONOUNS):
        return True
    return len(body) <= 6 and not re.search(r"[，。！？,.!?]", body)


def build_digest(messages: Sequence[dict[str, str]], max_chars: int = 600) -> str:
    """Fold earlier turns into a short labelled digest, newest last.

    Only role, order and a clipped opening of each message survive, which is what
    a follow-up needs in order to know what "it" refers to.
    """
    lines: list[str] = []
    budget = max_chars
    for message in messages:
        if budget <= 0:
            break
        role = "用户" if message.get("role") == "user" else "助手"
        content = re.sub(r"\s+", " ", message.get("content") or "").strip()
        if not content:
            continue
        clip = content[: max(40, min(120, budget // 2))]
        line = f"- {role}：{clip}"
        lines.append(line)
        budget -= len(line)
    return "\n".join(lines)


def compress_history(
    messages: Sequence[dict[str, str]], max_chars: int, keep_turns: int = 6
) -> tuple[list[dict[str, str]], str]:
    """Keep the newest ``keep_turns`` messages, digest the rest.

    Returns the kept messages and a digest of what was folded away. The digest is
    empty when nothing was dropped.
    """
    if len(messages) <= keep_turns:
        return list(messages), ""

    tail = list(messages)[-keep_turns:]
    head = list(messages)[: -keep_turns]
    total = sum(len(m.get("content") or "") for m in tail)
    if total <= max_chars:
        return list(messages), ""
    return tail, build_digest(head)


_FENCE = "```"


def close_fences(text: str) -> str:
    """Close a code fence the model left open, so the rest of the answer renders."""
    if not text:
        return text
    if text.count(_FENCE) % 2 == 1:
        return text.rstrip() + "\n```"
    return text


def dedupe_sentences(text: str) -> str:
    """Drop an immediately repeated sentence.

    Small models loop on the same line under long prompts; removing only
    consecutive duplicates never changes meaning.
    """
    if not text:
        return text
    parts = re.split(r"(?<=[。！？!?])\s*", text)
    result: list[str] = []
    for part in parts:
        if part and result and part.strip() == result[-1].strip():
            continue
        result.append(part)
    return "".join(result)


def looks_empty(text: str) -> bool:
    """True when a reply carries no usable content."""
    body = (text or "").strip()
    if len(body) < 2:
        return True
    return body in {"。", "…", "...", "抱歉，我无法回答。", "我无法回答这个问题。"}
