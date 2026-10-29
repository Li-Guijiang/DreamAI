"""Dream AI — web service (FastAPI).

The browser talks to this service; the service talks to any OpenAI-compatible
model endpoint. API keys never leave the server.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import defaultdict, deque
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Literal

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


async def consume_daily_budget() -> bool:
    """Daily request budget for this worker process (protects the API key).

    The production unit runs two Uvicorn workers, so the effective ceiling is
    roughly ``daily_limit * workers``. Use one worker or shared storage when a
    strict process-independent quota is required.
    """
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
    providerId: str | None = Field(default=None, max_length=40)
    apiKey: str | None = Field(default=None, max_length=200)
    temperature: float | None = None
    maxTokens: int | None = Field(default=None, ge=128, le=8192)
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
    chat = [{"role": m.role, "content": m.content} for m in messages][
        -settings.max_history_messages :
    ]

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
        provider = settings.provider(payload.providerId)
        if provider is None or not provider.models:
            raise UpstreamError("这个模型来源不可用，请重新选择。", "byok_provider", 400)
        model_ids = {model.id for model in provider.models}
        model = payload.model if payload.model in model_ids else provider.models[0].id
        return Upstream(provider.base_url, key, model, "byok")

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
    messages = prepare_messages(payload.messages, system_prompt)
    temperature = payload.temperature if payload.temperature is not None else settings.temperature
    temperature = min(1.5, max(0.0, temperature + STYLE_TEMPERATURE.get(style, 0.0)))

    async def event_stream() -> AsyncIterator[bytes]:
        started = time.monotonic()
        produced = 0
        failed = False
        cancelled = False
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
            if not failed and not cancelled:
                yield sse(
                    "done",
                    {
                        "chars": produced,
                        "elapsed": round(time.monotonic() - started, 2),
                        "model": model,
                    },
                )

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


@app.get("/docs.html")
async def docs() -> FileResponse:
    return FileResponse(WEB_DIR / "docs.html", headers={"Cache-Control": "no-cache"})


@app.get("/download.html")
async def download_page() -> FileResponse:
    return FileResponse(WEB_DIR / "download.html", headers={"Cache-Control": "no-cache"})


@app.get("/favicon.ico")
async def favicon() -> FileResponse:
    return FileResponse(WEB_DIR / "assets" / "img" / "favicon.ico")


@app.get("/manifest.webmanifest")
async def manifest() -> FileResponse:
    return FileResponse(WEB_DIR / "manifest.webmanifest", media_type="application/manifest+json")


@app.get("/robots.txt")
async def robots() -> Response:
    body = "User-agent: *\nAllow: /\nDisallow: /api/\nSitemap: https://liguijiang.com/sitemap.xml\n"
    return Response(body, media_type="text/plain")


@app.get("/sitemap.xml")
async def sitemap() -> FileResponse:
    return FileResponse(
        WEB_DIR / "sitemap.xml",
        media_type="application/xml",
        headers={"Cache-Control": "no-cache"},
    )


app.mount("/assets", StaticFiles(directory=str(WEB_DIR / "assets")), name="assets")


@app.exception_handler(404)
async def not_found(request: Request, exc):  # noqa: ANN001
    if request.url.path.startswith("/api/"):
        return JSONResponse({"error": "接口不存在"}, status_code=404)
    return FileResponse(
        WEB_DIR / "index.html", status_code=404, headers={"Cache-Control": "no-cache"}
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)
