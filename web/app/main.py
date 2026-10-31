"""Dream AI — web service (FastAPI).

The browser talks to this service; the service talks to any OpenAI-compatible
model endpoint. API keys never leave the server.
"""

from __future__ import annotations

import asyncio
import ipaddress
import json
import logging
import re
import socket
import time
from collections import defaultdict, deque
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from html.parser import HTMLParser
from typing import Literal
from urllib.parse import urljoin, urlparse

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from . import llm
from .config import VERSION, WEB_DIR, load_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("dreamai.web")

settings = load_settings()
STARTED_AT = time.time()

MAX_BODY_BYTES = 512 * 1024


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Dream AI web %s starting (free=%s model=%s, byok=%s)",
        VERSION,
        settings.free_configured,
        settings.free_model,
        ",".join(settings.byok_ids),
    )
    if not settings.free_configured:
        logger.warning("DREAMAI_FREE_API_KEY is empty — free chat returns 503 until it is set.")
    yield
    await llm.close_client()


app = FastAPI(
    title="Dream AI",
    version=VERSION,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Rate limiting (per client IP, sliding window, in-memory)
# ---------------------------------------------------------------------------


class RateLimiter:
    def __init__(self, limit: int, window: int) -> None:
        self._limit = limit
        self._window = window
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def hit(self, key: str) -> tuple[bool, int]:
        """Return ``(allowed, retry_after_seconds)``."""
        now = time.monotonic()
        async with self._lock:
            bucket = self._hits[key]
            while bucket and now - bucket[0] > self._window:
                bucket.popleft()
            if len(bucket) >= self._limit:
                retry = int(self._window - (now - bucket[0])) + 1
                return False, max(1, retry)
            bucket.append(now)
            if len(self._hits) > 20000:  # keep memory bounded
                self._hits.clear()
            return True, 0


limiter = RateLimiter(settings.rate_limit, settings.rate_window)
_semaphore = asyncio.Semaphore(settings.max_concurrency)

_daily_lock = asyncio.Lock()
_daily_state = {"date": time.strftime("%Y-%m-%d"), "count": 0}

_stats = {
    "requests": 0,
    "failures": 0,
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "by_model": defaultdict(int),
    "started_at": STARTED_AT,
}


async def consume_daily_budget() -> bool:
    """Global per-process daily request budget (protects the API key)."""
    if settings.daily_limit <= 0:
        return True
    today = time.strftime("%Y-%m-%d")
    async with _daily_lock:
        if _daily_state["date"] != today:
            _daily_state["date"] = today
            _daily_state["count"] = 0
        if _daily_state["count"] >= settings.daily_limit:
            return False
        _daily_state["count"] += 1
        return True


def client_ip(request: Request) -> str:
    real = request.headers.get("x-real-ip")
    if real:
        return real.strip()
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ---------------------------------------------------------------------------
# Safe link reader (SSRF-guarded, text only)
# ---------------------------------------------------------------------------

READER_MAX_BYTES = 2_000_000
READER_MAX_CHARS = 20_000
READER_TYPES = {"text/html", "text/plain", "application/xhtml+xml"}
reader_limiter = RateLimiter(20, 600)


class ReaderError(Exception):
    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status = status


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.title = ""
        self._skip = 0
        self._in_title = False
        self._title_done = False

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"script", "style", "noscript", "svg", "canvas", "iframe", "template"}:
            self._skip += 1
        if tag == "title" and not self._title_done:
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg", "canvas", "iframe", "template"} and self._skip:
            self._skip -= 1
        if tag == "title" and self._in_title:
            self._in_title = False
            self._title_done = True

    def handle_data(self, data: str) -> None:
        if self._skip:
            return
        text = " ".join(data.split())
        if not text:
            return
        if self._in_title and not self._title_done:
            self.title += text
        else:
            self.parts.append(text)


async def _public_host(host: str) -> bool:
    name = host.strip().strip("[]").lower().rstrip(".")
    if not name or name == "localhost" or name.endswith((".local", ".internal", ".localhost")):
        return False
    try:
        infos = await asyncio.to_thread(socket.getaddrinfo, name, None, type=socket.SOCK_STREAM)
    except OSError:
        return False
    if not infos:
        return False
    for info in infos:
        try:
            ip = ipaddress.ip_address(info[4][0])
        except ValueError:
            return False
        if (
            not ip.is_global
            or ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
        ):
            return False
    return True


async def _validate_read_url(url: str):
    if not url or len(url) > 2048:
        raise ReaderError("链接无效")
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ReaderError("只支持 http / https 链接")
    if parsed.username or parsed.password:
        raise ReaderError("链接不能包含账号信息")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ReaderError("链接端口无效") from exc
    if port not in (None, 80, 443):
        raise ReaderError("只允许访问 80 / 443 端口")
    host = parsed.hostname
    if not host or not await _public_host(host):
        raise ReaderError("该链接不允许访问（仅支持公网网页）")
    return parsed


async def fetch_readable(url: str) -> dict:
    current = url
    headers = {
        "User-Agent": "DreamAI-Reader/1.0 (+https://liguijiang.com)",
        "Accept": "text/html, text/plain;q=0.9, */*;q=0.1",
    }
    timeout = httpx.Timeout(12.0, connect=6.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False, headers=headers) as client:
        for _ in range(4):
            parsed = await _validate_read_url(current)
            async with client.stream("GET", current) as response:
                if response.status_code in {301, 302, 303, 307, 308}:
                    location = response.headers.get("location")
                    if not location:
                        raise ReaderError("链接跳转无效", 400)
                    current = urljoin(current, location)
                    continue
                if response.status_code != 200:
                    raise ReaderError(f"目标网站返回 HTTP {response.status_code}", 502)
                ctype = (response.headers.get("content-type") or "").split(";")[0].strip().lower()
                if ctype not in READER_TYPES:
                    raise ReaderError("只支持读取网页或纯文本链接", 415)

                chunks: list[bytes] = []
                total = 0
                truncated = False
                async for chunk in response.aiter_bytes():
                    total += len(chunk)
                    if total > READER_MAX_BYTES:
                        truncated = True
                        break
                    chunks.append(chunk)
                raw = b"".join(chunks)
                body = raw.decode(response.encoding or "utf-8", "replace")

                if ctype == "text/plain":
                    title = parsed.hostname or current
                    text = body
                else:
                    extractor = _TextExtractor()
                    extractor.feed(body)
                    extractor.close()
                    title = extractor.title.strip() or (parsed.hostname or current)
                    text = "\n".join(extractor.parts)

                text = re.sub(r"[ \t\r\f\v]+", " ", text)
                text = re.sub(r"\n{3,}", "\n\n", text).strip()
                if not text:
                    raise ReaderError("页面里没有可读文本", 422)
                if len(text) > READER_MAX_CHARS:
                    text = text[:READER_MAX_CHARS]
                    truncated = True
                return {
                    "url": current,
                    "title": title[:200],
                    "text": text,
                    "chars": len(text),
                    "truncated": truncated,
                }
        raise ReaderError("链接跳转次数过多")

# ---------------------------------------------------------------------------
# Middleware: security headers, cache policy, body size guard
# ---------------------------------------------------------------------------


@app.middleware("http")
async def security_headers(request: Request, call_next):
    if request.method in {"POST", "PUT", "PATCH"}:
        length = request.headers.get("content-length")
        if length and length.isdigit() and int(length) > MAX_BODY_BYTES:
            return JSONResponse(
                {"error": "请求内容过大，请精简后再试。", "code": "payload_too_large"},
                status_code=413,
            )

    response = await call_next(request)
    path = request.url.path

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "img-src 'self' data: blob:; "
        "style-src 'self'; "
        "script-src 'self'; "
        "font-src 'self' data:; "
        "connect-src 'self'; "
        "base-uri 'none'; "
        "form-action 'self'; "
        "frame-ancestors 'none'"
    )

    if path.startswith("/assets/"):
        response.headers["Cache-Control"] = "public, max-age=604800"
    elif path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


# ---------------------------------------------------------------------------
# API models
# ---------------------------------------------------------------------------


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=20000)

    @field_validator("content")
    @classmethod
    def strip_content(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("empty message")
        return value


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=40)
    model: str | None = None
    provider: Literal["free", "byok"] = "free"
    apiKey: str | None = Field(default=None, max_length=200)
    temperature: float | None = None
    maxTokens: int | None = Field(default=None, ge=128, le=8192)
    memory: list[str] | None = Field(default=None, max_length=30)
    context: str | None = Field(default=None, max_length=20000)
    thinking: bool = False
    style: str | None = None


class UpstreamError(Exception):
    def __init__(self, message: str, code: str, status: int) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status


class Upstream:
    __slots__ = ("base_url", "api_key", "model", "kind")

    def __init__(self, base_url: str, api_key: str, model: str, kind: str) -> None:
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.kind = kind


# Optional answer-style presets chosen in the composer. They are short
# instructions appended to the persona, plus a gentle temperature offset.
STYLE_PROMPTS = {
    "precise": "回答风格：严谨。先给结论，再给依据；区分事实与推断；不确定时明确说明。",
    "creative": "回答风格：创意。允许更大胆的联想与比喻，给出有新意的方案，同时保持可执行。",
    "concise": "回答风格：精简。能一句话说清就不写两行；除非用户要求，否则不展开背景。",
}
STYLE_TEMPERATURE = {"precise": -0.3, "creative": 0.25, "concise": -0.15}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def sse(event: str, payload: dict) -> bytes:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n".encode()


def prepare_messages(messages: list[ChatMessage], system_prompt: str) -> list[dict[str, str]]:
    """Trim history (newest-last) by count and size, then prepend the persona."""
    chat = [{"role": m.role, "content": m.content} for m in messages][-settings.max_history_messages :]

    total = 0
    kept: list[dict[str, str]] = []
    for message in reversed(chat):
        total += len(message["content"])
        if kept and total > settings.max_history_chars:
            break
        kept.append(message)
    kept.reverse()

    # A chat must start with a user turn; drop a dangling assistant message.
    while kept and kept[0]["role"] != "user":
        kept.pop(0)

    return [{"role": "system", "content": system_prompt}, *kept]


def resolve_upstream(payload: ChatRequest) -> Upstream:
    """Pick the upstream for this request: site free model or the visitor's key."""
    if payload.provider == "byok":
        key = (payload.apiKey or "").strip()
        if len(key) < 20 or len(key) > 200 or any(char.isspace() for char in key):
            raise UpstreamError(
                "请先在设置中填写自己的 API Key，再使用该模型。",
                "byok_missing",
                401,
            )
        model = payload.model if payload.model in settings.byok_ids else settings.byok_models[0].id
        return Upstream(settings.byok_base_url, key, model, "byok")

    if not settings.free_configured:
        raise UpstreamError(
            "免费模型暂未开放。你可以在设置中填写自己的 API Key 继续使用。",
            "free_not_configured",
            503,
        )
    return Upstream(settings.free_base_url, settings.free_api_key, settings.free_model, "free")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/api/read")
async def read_link(request: Request, url: str = "") -> JSONResponse:
    ip = client_ip(request)
    allowed, retry_after = await reader_limiter.hit(ip)
    if not allowed:
        return JSONResponse(
            {"error": f"读取太频繁了，请 {retry_after} 秒后再试。", "code": "rate_limited"},
            status_code=429,
            headers={"Retry-After": str(retry_after)},
        )
    try:
        data = await fetch_readable(url)
    except ReaderError as exc:
        return JSONResponse({"error": exc.message, "code": "read_failed"}, status_code=exc.status)
    except Exception:  # noqa: BLE001
        logger.exception("reader failed url=%s", url[:200])
        return JSONResponse({"error": "读取失败，请稍后重试。", "code": "read_failed"}, status_code=502)
    return JSONResponse(data)

@app.get("/api/health")
async def health() -> JSONResponse:
    return JSONResponse(
        {
            "ok": True,
            "configured": settings.free_configured,
            "model": settings.free_model,
            "models": [m.as_dict() for m in settings.models],
            "byok": list(settings.byok_ids),
            "version": VERSION,
            "uptime": int(time.time() - STARTED_AT),
            "dailyLimit": settings.daily_limit,
            "freeRemaining": max(0, settings.daily_limit - _daily_state["count"]) if settings.daily_limit > 0 else None,
            "rateLimit": settings.rate_limit,
            "rateWindow": settings.rate_window,
            "maxConcurrency": settings.max_concurrency,
            "features": ["memory", "knowledge", "canvas", "reader"],
        }
    )


@app.get("/api/usage")
async def usage() -> JSONResponse:
    return JSONResponse(
        {
            "uptime": int(time.time() - STARTED_AT),
            "version": VERSION,
            "requests": _stats["requests"],
            "failures": _stats["failures"],
            "promptTokens": _stats["prompt_tokens"],
            "completionTokens": _stats["completion_tokens"],
            "byModel": dict(_stats["by_model"]),
            "daily": _daily_state,
            "dailyLimit": settings.daily_limit,
        }
    )


@app.get("/api/config")
async def public_config() -> JSONResponse:
    return JSONResponse(settings.public_config())


@app.post("/api/chat")
async def chat(payload: ChatRequest, request: Request) -> Response:
    try:
        upstream = resolve_upstream(payload)
    except UpstreamError as exc:
        return JSONResponse({"error": exc.message, "code": exc.code}, status_code=exc.status)

    ip = client_ip(request)
    if upstream.kind == "free" and not await consume_daily_budget():
        return JSONResponse(
            {
                "error": "今天的免费额度已经用完啦，明天再来，或在设置中填写自己的 Key。",
                "code": "daily_limit",
            },
            status_code=429,
        )

    allowed, retry_after = await limiter.hit(ip)
    if not allowed:
        return JSONResponse(
            {
                "error": f"发送太频繁了，请 {retry_after} 秒后再试。",
                "code": "rate_limited",
            },
            status_code=429,
            headers={"Retry-After": str(retry_after)},
        )

    total_chars = sum(len(m.content) for m in payload.messages)
    if total_chars > settings.max_history_chars:
        return JSONResponse(
            {"error": "对话上下文太长了，请开启新对话后再试。", "code": "context_too_long"},
            status_code=413,
        )
    if len(payload.messages[-1].content) > settings.max_input_chars:
        return JSONResponse(
            {
                "error": f"单条消息最多 {settings.max_input_chars} 个字符，请分段发送。",
                "code": "input_too_long",
            },
            status_code=413,
        )

    model = upstream.model
    style = payload.style if payload.style in STYLE_PROMPTS else "default"
    system_prompt = settings.system_prompt
    if style in STYLE_PROMPTS:
        system_prompt = f"{system_prompt}\n\n{STYLE_PROMPTS[style]}"
    if payload.memory:
        memories = [" ".join(item.split())[:300] for item in payload.memory if item and item.strip()][:20]
        if memories:
            system_prompt += "\n\n用户长期记忆（请自然遵守，不要逐条复述）：\n" + "\n".join(
                f"- {item}" for item in memories
            )
    if payload.context and payload.context.strip():
        system_prompt += (
            "\n\n以下是本轮参考资料，回答时优先依据它；如果用到请说明来自资料。\n"
            "<资料>\n" + payload.context.strip()[:20000] + "\n</资料>"
        )
    messages = prepare_messages(payload.messages, system_prompt)
    temperature = payload.temperature if payload.temperature is not None else settings.temperature
    temperature = min(1.5, max(0.0, temperature + STYLE_TEMPERATURE.get(style, 0.0)))

    async def event_stream() -> AsyncIterator[bytes]:
        started = time.monotonic()
        produced = 0
        failed = False
        cancelled = False
        usage_payload: dict | None = None
        yield sse("meta", {"model": model, "version": VERSION})
        try:
            async with _semaphore:
                async for kind, text in llm.stream_completion(
                    base_url=upstream.base_url,
                    api_key=upstream.api_key,
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=payload.maxTokens or settings.max_tokens,
                ):
                    if kind == "usage":
                        try:
                            usage_payload = json.loads(text)
                        except ValueError:
                            usage_payload = None
                        if isinstance(usage_payload, dict):
                            yield sse("usage", usage_payload)
                        continue
                    produced += len(text)
                    yield sse("reasoning" if kind == "reasoning" else "delta", {"t": text})
        except llm.LLMError as exc:
            failed = True
            logger.info("chat failed ip=%s kind=%s: %s", ip, upstream.kind, exc)
            message = exc.message
            if upstream.kind == "byok" and exc.status_code in (401, 402, 403):
                message = "你的 API Key 无效、没有权限或余额不足，请在设置中更新后重试。"
            yield sse("error", {"message": message})
        except asyncio.CancelledError:
            cancelled = True
            raise
        except Exception:  # noqa: BLE001 - never leak internals to the client
            failed = True
            logger.exception("unexpected chat error ip=%s", ip)
            yield sse("error", {"message": "服务出现了一点意外，请稍后重试。"})
        finally:
            _stats["requests"] += 1
            _stats["by_model"][model] += 1
            if failed:
                _stats["failures"] += 1
            if isinstance(usage_payload, dict):
                _stats["prompt_tokens"] += int(usage_payload.get("prompt_tokens") or 0)
                _stats["completion_tokens"] += int(usage_payload.get("completion_tokens") or 0)
            if not failed and not cancelled:
                done_payload = {
                    "chars": produced,
                    "elapsed": round(time.monotonic() - started, 2),
                    "model": model,
                }
                if usage_payload:
                    done_payload["usage"] = usage_payload
                yield sse("done", done_payload)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# Static site
# ---------------------------------------------------------------------------


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html", headers={"Cache-Control": "no-cache"})


@app.get("/favicon.ico")
async def favicon() -> FileResponse:
    return FileResponse(WEB_DIR / "assets" / "img" / "favicon.ico")


@app.get("/index.html")
async def index_html() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/sw.js")
async def service_worker() -> FileResponse:
    return FileResponse(WEB_DIR / "sw.js", media_type="application/javascript; charset=utf-8")


@app.get("/offline.html")
async def offline_page() -> FileResponse:
    return FileResponse(WEB_DIR / "offline.html")


@app.get("/manifest.webmanifest")
async def manifest() -> FileResponse:
    return FileResponse(WEB_DIR / "manifest.webmanifest", media_type="application/manifest+json")


@app.get("/robots.txt")
async def robots() -> Response:
    body = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /api/\n"
        "Sitemap: https://liguijiang.com/sitemap.xml\n"
    )
    return Response(body, media_type="text/plain")


@app.get("/sitemap.xml")
async def sitemap() -> Response:
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        "  <url><loc>https://liguijiang.com/</loc><changefreq>weekly</changefreq>"
        "<priority>1.0</priority></url>\n"
        "</urlset>\n"
    )
    return Response(body, media_type="application/xml")


app.mount("/assets", StaticFiles(directory=str(WEB_DIR / "assets")), name="assets")


@app.exception_handler(404)
async def not_found(request: Request, exc):  # noqa: ANN001
    if request.url.path.startswith("/api/"):
        return JSONResponse({"error": "接口不存在"}, status_code=404)
    return FileResponse(WEB_DIR / "index.html", status_code=404, headers={"Cache-Control": "no-cache"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)
