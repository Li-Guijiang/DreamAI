"""Local mock of an OpenAI-compatible streaming endpoint.

Used only for development and visual QA — never deployed. Start it, then point
the web app at it:

    python tools/mock_upstream.py
    DREAMAI_BASE_URL=http://127.0.0.1:8799/v1 DREAMAI_API_KEY=test uvicorn app.main:app --port 8787
"""

from __future__ import annotations

import asyncio
import json
import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

app = FastAPI()

SAMPLE = """好的，我们把它拆开来看。

## 一、先给结论

LRU 缓存的核心是 **哈希表 + 双向链表**：哈希表负责 O(1) 定位，双向链表负责 O(1) 调整顺序。

| 操作 | 时间复杂度 | 说明 |
| --- | --- | --- |
| `get` | O(1) | 命中则把节点移到头部 |
| `put` | O(1) | 超容量时淘汰尾部节点 |

> 关键点是：**所有「最近使用」的语义，都由链表顺序承载**，而不是时间戳。

## 二、可运行的实现

```python
from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Generic, TypeVar

K = TypeVar("K")
V = TypeVar("V")


class LRUCache(Generic[K, V]):
    def __init__(self, capacity: int) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self._capacity = capacity
        self._data: OrderedDict[K, V] = OrderedDict()
        self._lock = threading.RLock()

    def get(self, key: K) -> V | None:
        with self._lock:
            if key not in self._data:
                return None
            self._data.move_to_end(key)
            return self._data[key]

    def put(self, key: K, value: V) -> None:
        with self._lock:
            if key in self._data:
                self._data.move_to_end(key)
            self._data[key] = value
            while len(self._data) > self._capacity:
                self._data.popitem(last=False)
```

## 三、几个容易踩的坑

1. `OrderedDict` **不是**线程安全的，多线程场景必须自己加锁；
2. 淘汰发生在写入之后，注意 `while` 而不是 `if`；
3. 如果缓存的值很大，考虑用 `weakref` 或外部存储，避免内存膨胀。

需要我把它改成异步版本（`asyncio.Lock`）或者加上统计指标吗？"""

REASONING = """用户想要一个 LRU 缓存实现，重点在类型注解、线程安全和复杂度分析。
先确认边界：容量必须为正；并发访问需要锁保护 OrderedDict。
实现上用 OrderedDict 的 move_to_end 和 popitem(last=False) 即可同时满足 O(1)。
最后补上三个常见陷阱，让答案更实用。"""


def chunk(text: str, kind: str = "content") -> str:
    delta = {"reasoning_content": text} if kind == "reasoning" else {"content": text}
    payload = {
        "id": "chatcmpl-mock",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": "mock",
        "choices": [{"index": 0, "delta": delta, "finish_reason": None}],
    }
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@app.post("/v1/chat/completions")
async def completions(request: Request):
    body = await request.json()
    if not body.get("messages"):
        return JSONResponse({"error": {"message": "no messages"}}, status_code=400)

    model = str(body.get("model", ""))
    last = str((body.get("messages") or [{}])[-1].get("content", ""))
    if "任务规划器" in last:
        text = '{"title":"准备产品发布会","steps":["梳理目标与受众","撰写开场文案","检查语气与长度"]}'
    elif "最终答复" in last:
        text = "## 最终结果\n\n已完成三步：\n\n1. 明确了目标与受众；\n2. 写出了一版克制、有画面感的开场文案；\n3. 检查了语气与长度，控制在 200 字内。"
    elif "当前步骤" in last:
        text = "这一步的产出：把复杂信息收进一句话，保留画面感，避免形容词堆叠。"
    else:
        text = SAMPLE
    chunks = [text[i : i + 6] for i in range(0, len(text), 6)]
    reasoning = [REASONING[i : i + 8] for i in range(0, len(REASONING), 8)]

    async def stream():
        if "reasoner" in model:
            for part in reasoning:
                yield chunk(part, "reasoning")
                await asyncio.sleep(0.02)
        for part in chunks:
            yield chunk(part)
            await asyncio.sleep(0.012)
        yield "data: [DONE]\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/health")
async def health():
    return {"ok": True}
