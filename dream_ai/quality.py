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
