"""The two copies of the difficulty rule must not drift apart."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

WEB = str(Path(__file__).resolve().parent.parent / "web")
if WEB not in sys.path:
    sys.path.insert(0, WEB)

from app.quality import classify_tier as web_classify  # noqa: E402

from dream_ai.quality import classify_tier as local_classify  # noqa: E402

CORPUS = (
    "",
    "在吗",
    "你好",
    "帮我写一段周报",
    "为什么要把缓存做成两层，架构上怎么权衡",
    "对比一下 Redis 和本地字典的方案",
    "```python\nprint(1)\n```",
    "Traceback (most recent call last): boom",
    "什么是脏读",
    "这个配置怎么改？为什么改完还是不生效？还有别的地方要一起改吗？",
)


@pytest.mark.parametrize("text", CORPUS)
def test_both_surfaces_rate_the_same_question(text):
    assert local_classify(text) == web_classify(text), text
