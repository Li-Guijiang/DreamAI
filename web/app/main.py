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
import uuid
from collections import defaultdict, deque
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from html.parser import HTMLParser
from typing import Literal
from urllib.parse import urljoin, urlparse

import httpx
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from . import llm, owner_auth, owner_store
from .adapters import FINISH_LENGTH
from .cache import ResponseCache, make_key
from .config import IDENTITY_ANSWER, VERSION, WEB_DIR, is_identity_question, load_settings
from .errors import final_message
from .guard import CircuitBreaker
from .insight import (
    classify_intent,
    detect_language,
    intent_prompt,
    is_repeat,
    language_prompt,
    trim_long_input,
)
from .pricing import configure_prices, estimate_cost, format_cost
from .providers import BYOK_PROVIDERS, get_provider, public_catalog, resolve_model
from .quality import (
    compress_history,
    dedupe_messages,
    needs_context,
    plan_generation,
    respect_cap,
    unclosed_fence,
)
from .routing import choose_model, describe_routing, unknown_targets
from .safety import classify_injection, harden_system_prompt
from .stats import UsageStats
from .telemetry import format_breaker_log, format_recovery_log, format_turn_log

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
    applied = configure_prices(settings.price_overrides)
    if applied:
        logger.info("price overrides: %s", ", ".join(sorted(applied)))
    logger.info(describe_routing(settings.model_by_tier, settings.free_model))
    unknown = unknown_targets(settings.model_by_tier, {m.id for m in settings.models})
    if unknown:
        logger.warning(
            "tier map names models this site does not serve: %s",
            ", ".join(f"{tier}={model}" for tier, model in sorted(unknown.items())),
        )
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
    #: Above this many watched clients, the quiet ones are forgotten. Pruning
    #: beats clearing: emptying the table used to reset the quota of every
    #: client at once, so enough distinct addresses could refill a bucket on
    #: demand.
    MAX_TRACKED = 20000

    def __init__(self, limit: int, window: int) -> None:
        self._limit = limit
        self._window = window
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    def _prune(self, now: float) -> None:
        """Forget clients that have been quiet for a whole window.

        An idle bucket is indistinguishable from one that never existed, so
        dropping it cannot change any decision. Only if the table is still too
        large are the least recently seen clients removed.
        """
        stale = [
            key
            for key, bucket in self._hits.items()
            if not bucket or now - bucket[-1] > self._window
        ]
        for key in stale:
            del self._hits[key]
        excess = len(self._hits) - self.MAX_TRACKED
        if excess > 0:
            quietest = sorted(self._hits, key=lambda key: self._hits[key][-1])
            for key in quietest[:excess]:
                del self._hits[key]

    async def hit(self, key: str) -> tuple[bool, int, int]:
        """Return ``(allowed, retry_after_seconds, remaining_in_window)``.

        The remaining count is what turns a bare limit into a contract: a client
        that can see how many requests it has left slows down before it is told
        to.
        """
        now = time.monotonic()
        async with self._lock:
            if len(self._hits) > self.MAX_TRACKED:
                self._prune(now)
            bucket = self._hits[key]
            while bucket and now - bucket[0] > self._window:
                bucket.popleft()
            if len(bucket) >= self._limit:
                retry = int(self._window - (now - bucket[0])) + 1
                return False, max(1, retry), 0
            bucket.append(now)
            return True, 0, max(0, self._limit - len(bucket))

    def stats(self) -> dict:
        """What the health endpoint reports about the limiter.

        Only a count, never the keys: an IP is personal data, and 'how many
        clients are being watched' is the whole operational question.
        """
        return {
            "tracked": len(self._hits),
            "limit": self._limit,
            "window": self._window,
            "cap": self.MAX_TRACKED,
        }


limiter = RateLimiter(settings.rate_limit, settings.rate_window)
_semaphore = asyncio.Semaphore(settings.max_concurrency)

_daily_lock = asyncio.Lock()
_daily_state = {"date": time.strftime("%Y-%m-%d"), "count": 0}

_breaker = CircuitBreaker(threshold=settings.breaker_threshold, cooldown=settings.breaker_cooldown)
_cache = ResponseCache(max_items=settings.cache_max_items, ttl=settings.cache_ttl)

_stats = UsageStats(started_at=STARTED_AT)


async def consume_daily_budget() -> bool:
    """Global per-process daily request budget (protects the API key)."""
    if settings.daily_limit <= 0:
        return True
    today = time.strftime("%Y-%m-%d")
    async with _daily_lock:
        if _daily_state["date"] != today:
            _daily_state["date"] = today
            _daily_state["count"] = 0
            _daily_state["warned"] = False
        if _daily_state["count"] >= settings.daily_limit:
            # Once per day, not once per refused request: the log is for noticing,
            # not for filling the disk with the same line.
            if not _daily_state.get("warned"):
                _daily_state["warned"] = True
                logger.warning(
                    "daily budget exhausted: %d requests served for %s",
                    settings.daily_limit,
                    today,
                )
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
        if (
            tag in {"script", "style", "noscript", "svg", "canvas", "iframe", "template"}
            and self._skip
        ):
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
    async with httpx.AsyncClient(
        timeout=timeout, follow_redirects=False, headers=headers
    ) as client:
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
    provider: str = "free"
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
    """A resolved request target: which provider, which key, which model."""

    __slots__ = ("provider", "api_key", "model", "kind", "label")

    def __init__(self, provider, api_key: str, model: str, kind: str, label: str) -> None:
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.kind = kind
        self.label = label


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


def prepare_messages(
    messages: list[ChatMessage], system_prompt: str
) -> tuple[list[dict[str, str]], str]:
    """Trim history by count and size, and return what was folded away.

    Truncation used to drop the oldest turns silently, which loses the subject of
    a follow-up. The dropped turns now come back as a short digest so the model
    still knows what the conversation was about.
    """
    chat = [{"role": m.role, "content": m.content} for m in messages][
        -settings.max_history_messages :
    ]

    chat, digest = compress_history(chat, settings.max_history_chars, keep_turns=6)

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

    return [{"role": "system", "content": system_prompt}, *kept], digest


def _valid_key(key: str) -> bool:
    """Shape check only: never call the provider to verify a visitor's key."""
    cleaned = (key or "").strip()
    return 20 <= len(cleaned) <= 200 and not any(char.isspace() for char in cleaned)


def resolve_upstream(payload: ChatRequest) -> Upstream:
    """Pick the upstream: a BYOK provider, the legacy byok alias, or the free model."""
    requested = (payload.provider or "free").strip().lower()

    # "byok" predates the provider registry and always meant DeepSeek; keep it
    # working for browsers that still send it.
    if requested == "byok":
        requested = "deepseek"

    if requested in BYOK_PROVIDERS:
        provider = get_provider(requested)
        assert provider is not None
        key = (payload.apiKey or "").strip()
        if not _valid_key(key):
            raise UpstreamError(
                f"请先在设置中填写 {provider.label} 的 API Key，再使用该模型。",
                "byok_missing",
                401,
            )
        return Upstream(
            provider, key, resolve_model(provider.id, payload.model), provider.kind, provider.label
        )

    if requested != "free":
        raise UpstreamError("不支持的模型提供商。", "unknown_provider", 400)

    if not settings.free_configured:
        raise UpstreamError(
            "免费模型暂未开放。你可以在设置中填写自己的 API Key 继续使用。",
            "free_not_configured",
            503,
        )

    class _Free:
        id = "free"
        label = "免费模型"
        kind = "openai"
        base_url = settings.free_base_url

    return Upstream(
        _Free(),
        settings.free_api_key,
        resolve_model("", payload.model) or settings.free_model,
        "openai",
        "免费模型",
    )


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
        return JSONResponse(
            {"error": "读取失败，请稍后重试。", "code": "read_failed"}, status_code=502
        )
    return JSONResponse(data)


@app.get("/api/health")
async def health() -> JSONResponse:
    breaker = _breaker.stats()
    return JSONResponse(
        {
            "ok": True,
            "configured": settings.free_configured,
            "model": settings.free_model,
            "models": [m.as_dict() for m in settings.models],
            "byok": list(settings.byok_ids),
            "version": VERSION,
            "uptime": int(time.time() - STARTED_AT),
            "upstream": breaker["state"],
            "breaker": breaker,
            "cache": _cache.stats(),
            "dailyLimit": settings.daily_limit,
            "freeRemaining": max(0, settings.daily_limit - _daily_state["count"])
            if settings.daily_limit > 0
            else None,
            "rateLimit": settings.rate_limit,
            "rateWindow": settings.rate_window,
            "limiter": limiter.stats(),
            "maxConcurrency": settings.max_concurrency,
            "features": ["memory", "knowledge", "canvas", "reader"],
        }
    )


@app.get("/api/usage")
async def usage() -> JSONResponse:
    totals = _stats.snapshot()
    cache = _cache.stats()
    breaker = _breaker.stats()
    return JSONResponse(
        {
            "uptime": int(time.time() - STARTED_AT),
            "upstream": breaker["state"],
            "breaker": breaker,
            "cache": cache,
            "version": VERSION,
            "requests": totals["requests"],
            "failures": totals["failures"],
            "promptTokens": totals["promptTokens"],
            "completionTokens": totals["completionTokens"],
            "cachedTokens": totals["cachedTokens"],
            "cachedShare": totals["cachedShare"],
            "costUsd": totals["costUsd"],
            "costKnown": totals["costKnown"],
            "cacheHitRate": cache["hitRate"],
            "avgTtft": totals["avgTtft"],
            "ttftSamples": totals["ttftSamples"],
            "ttftMax": totals["ttftMax"],
            "byTier": totals["byTier"],
            "byIntent": totals["byIntent"],
            "byProvider": totals["byProvider"],
            "byModel": totals["byModel"],
            "local": totals["local"],
            "blocked": totals["blocked"],
            "cancelled": totals["cancelled"],
            "truncated": totals["truncated"],
            "truncationRate": totals["truncationRate"],
            "truncatedByTier": totals["truncatedByTier"],
            "byFinish": totals["byFinish"],
            "daily": _daily_state,
            "dailyLimit": settings.daily_limit,
        }
    )


@app.get("/api/config")
async def public_config() -> JSONResponse:
    config = settings.public_config()
    config["providers"] = public_catalog()
    return JSONResponse(config)


def _local_chat(text: str, *, extra_headers: dict[str, str] | None = None) -> StreamingResponse:
    """Stream a deterministic, model-free answer (identity or owner command)."""
    # A local answer is untraceable without an id: a bug report about the dossier
    # or the verification flow could not be matched to a log line.
    request_id = f"req_{uuid.uuid4().hex[:8]}"

    async def stream() -> AsyncIterator[bytes]:
        started = time.monotonic()
        _stats.record_local()
        logger.info("local reply id=%s chars=%s", request_id, len(text))
        yield sse("meta", {"model": "local", "version": VERSION, "requestId": request_id})
        yield sse("delta", {"t": text})
        yield sse(
            "done",
            {
                "chars": len(text),
                "elapsed": round(time.monotonic() - started, 3),
                "model": "local",
                "local": True,
            },
        )

    headers = {
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
        "X-Request-Id": request_id,
    }
    if extra_headers:
        headers.update(extra_headers)
    return StreamingResponse(
        stream(),
        media_type="text/event-stream; charset=utf-8",
        headers=headers,
    )


def _verification_token(text: str) -> str | None:
    for prefix in ("【主人验证】", "[主人验证]"):
        if text.startswith(prefix):
            return text[len(prefix) :].strip()
    return None


@app.post("/api/chat")
async def chat(payload: ChatRequest, request: Request) -> Response:
    ip = client_ip(request)
    allowed, retry_after, remaining = await limiter.hit(ip)
    rate_headers = {
        "X-RateLimit-Limit": str(limiter._limit),
        "X-RateLimit-Remaining": str(remaining),
    }

    def _local(text: str, extra: dict[str, str] | None = None) -> StreamingResponse:
        # Local replies consume rate budget too, so they carry the same headers.
        return _local_chat(text, extra_headers={**rate_headers, **(extra or {})})

    if not allowed:
        return JSONResponse(
            {
                "error": f"发送太频繁了，请 {retry_after} 秒后再试。",
                "code": "rate_limited",
            },
            status_code=429,
            headers={"Retry-After": str(retry_after), **rate_headers},
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

    last_text = payload.messages[-1].content.strip()
    owner = owner_auth.is_owner(request)

    token = _verification_token(last_text)
    if token is not None:
        if not owner_auth.configured():
            return _local("主人验证尚未启用。请在服务器配置私有验证口令后重试。")
        if not owner_auth.verify_token(token):
            return _local("验证失败。")
        cookie = owner_auth.cookie_header(request)
        return _local(
            "主人验证通过。私有档案已解锁 30 天，可以发送【查看我的全部档案】。",
            extra={"Set-Cookie": cookie} if cookie else None,
        )

    if owner and last_text.startswith(("记住：", "记住:", "请记住：", "请记住:")):
        fact = last_text.split("：", 1)[-1] if "：" in last_text else last_text.split(":", 1)[-1]
        _, stored = owner_store.append_note(fact)
        return _local("已记住并写入私有档案：" + stored if stored else "内容为空，未写入。")

    command = owner_store.parse_command(last_text)
    if command is not None:
        if not owner:
            return _local("该指令仅主人可用。请先完成主人验证。")
        kind, argument = command
        if kind == "show":
            return _local(owner_store.render_profile(owner_store.load_profile()))
        if kind == "update":
            if not argument:
                return _local("用法：【更新档案】要追加的内容")
            _, fact = owner_store.append_note(argument)
            if not fact:
                return _local("内容为空，未追加。")
            return _local(f"已追加档案：{fact}")
        owner_store.clear_profile()
        return _local("已清空私有档案；公开身份规则不会被删除。")

    # Identity questions and owner commands are handled before the provider
    # call: a weak model must not be able to paraphrase the owner away.
    if is_identity_question(last_text):
        return _local(IDENTITY_ANSWER)

    try:
        upstream = resolve_upstream(payload)
    except UpstreamError as exc:
        return JSONResponse({"error": exc.message, "code": exc.code}, status_code=exc.status)

    if upstream.kind == "free" and not await consume_daily_budget():
        return JSONResponse(
            {
                "error": "今天的免费额度已经用完啦，明天再来，或在设置中填写自己的 Key。",
                "code": "daily_limit",
            },
            status_code=429,
        )

    model = upstream.model
    style = payload.style if payload.style in STYLE_PROMPTS else "default"
    system_prompt = settings.system_prompt
    if style in STYLE_PROMPTS:
        system_prompt = f"{system_prompt}\n\n{STYLE_PROMPTS[style]}"
    if payload.memory:
        memories = [
            " ".join(item.split())[:300] for item in payload.memory if item and item.strip()
        ][:20]
        if memories:
            system_prompt += "\n\n用户长期记忆（请自然遵守，不要逐条复述）：\n" + "\n".join(
                f"- {item}" for item in memories
            )
    if payload.context and payload.context.strip():
        system_prompt += (
            "\n\n以下是本轮参考资料，回答时优先依据它；如果用到请说明来自资料。\n"
            "<资料>\n" + payload.context.strip()[:20000] + "\n</资料>"
        )
    if owner:
        profile = owner_store.load_profile()
        if profile:
            system_prompt += "\n\n" + owner_store.render_profile(profile, include_contacts=True)

    # Never forward a verification token or a dossier block to a public model
    # prompt. Owner history is scoped to the owner cookie; if that cookie has
    # expired, the browser may still hold the profile reply in localStorage.
    safe_history: list[ChatMessage] = []
    for message in payload.messages:
        content = message.content
        if _verification_token(content.strip()) is not None:
            continue
        if not owner:
            if "## 主人档案" in content or "## 追加记忆" in content:
                continue
            content = owner_store.mask_contacts(content)
        # A pasted log can be thousands of lines of noise; keep the head, the
        # error lines and the tail.
        content = trim_long_input(content)
        safe_history.append(ChatMessage(role=message.role, content=content))
    safe_history = [
        ChatMessage(role=m["role"], content=m["content"])
        for m in dedupe_messages([{"role": m.role, "content": m.content} for m in safe_history])
    ]
    messages, dropped = prepare_messages(safe_history, system_prompt)
    temperature = payload.temperature if payload.temperature is not None else settings.temperature
    temperature = min(1.5, max(0.0, temperature + STYLE_TEMPERATURE.get(style, 0.0)))

    # Size the reply to the question: a greeting does not need 4k tokens, and a
    # design question should not be cut off at 768.
    last_user = next((m.content for m in reversed(payload.messages) if m.role == "user"), "")
    plan = plan_generation(last_user, temperature, payload.maxTokens or settings.max_tokens)
    tier, temperature, budget, tier_hint = (
        plan["tier"],
        plan["temperature"],
        respect_cap(plan["max_tokens"], payload.maxTokens),
        plan["hint"],
    )
    model = choose_model(tier, model, settings.model_by_tier)
    if tier_hint:
        system_prompt = f"{system_prompt}\n\n{tier_hint}"
        messages[0] = {"role": "system", "content": system_prompt}
    if dropped and needs_context(last_user):
        system_prompt += "\n这句话是追问，指代对象在上面的摘要里；先确认对象，再回答。"
        messages[0] = {"role": "system", "content": system_prompt}

    # Shape the answer to the kind of question, and notice a repeated one.
    intent = classify_intent(last_user)
    hints = [intent_prompt(intent)]
    if detect_language(last_user) == "en":
        hints.append(language_prompt("en"))
    user_turns = [m.content for m in payload.messages if m.role == "user"]
    if len(user_turns) >= 2 and is_repeat(user_turns[-1], user_turns[-2]):
        hints.append("用户重复问了同一件事：换一个角度或给出更具体的一步，不要原样复述上次的答案。")
    hints = [hint for hint in hints if hint]
    if hints:
        system_prompt += "\n\n" + "\n".join(hints)
        messages[0] = {"role": "system", "content": system_prompt}

    request_id = f"req_{uuid.uuid4().hex[:8]}"
    injection, severity = classify_injection(last_user)
    if injection:
        system_prompt = harden_system_prompt(system_prompt)
        messages[0] = {"role": "system", "content": system_prompt}
        log = logger.warning if severity == "high" else logger.info
        log(
            "possible injection id=%s severity=%s hit=%r",
            request_id,
            severity,
            injection[:40],
        )
    cache_key = None
    cached_text: str | None = None
    # A turn that tripped the guard is answered with a hardened prompt. It is
    # cheap to keep such answers out of the cache entirely: they are rare, and a
    # security-sensitive reply should never be replayed to a later visitor.
    if _cache.enabled and injection is None and temperature <= 0.3:
        cache_key = make_key(upstream.provider.id, model, messages, temperature, budget)
        cached_text = _cache.get(cache_key)

    class _FallbackProvider:
        id = "fallback"
        label = "备用模型"
        kind = "openai"
        base_url = settings.fallback_base_url

    async def event_stream() -> AsyncIterator[bytes]:
        started = time.monotonic()
        produced = 0
        failed = False
        cancelled = False
        usage_payload: dict | None = None
        # Empty means the provider never said why it stopped. "length" means the
        # answer was cut off at the token budget; both are reported, never mixed
        # into the answer text.
        finish_reason = ""
        answered: list[str] = []
        first_token_at = 0.0
        yield sse(
            "meta",
            {
                "model": model,
                "version": VERSION,
                "tier": tier,
                "intent": intent,
                "requestId": request_id,
                "cache": "hit" if cached_text else "miss",
            },
        )
        if cached_text:
            for index in range(0, len(cached_text), 48):
                yield sse("delta", {"t": cached_text[index : index + 48]})
            yield sse(
                "done",
                {
                    "tier": tier,
                    "intent": intent,
                    "requestId": request_id,
                    "chars": len(cached_text),
                    "elapsed": 0.0,
                    "model": model,
                    "cache": "hit",
                },
            )
            # A hit costs no tokens, but it is still a request the service
            # answered. Filing it under the real provider would inflate that
            # vendor's turn count; leaving the fields blank made byProvider and
            # byIntent stop adding up to `requests`.
            _stats.record_turn(model, tier=tier, intent=intent, provider="cache")
            logger.info(
                "chat cache id=%s tier=%s intent=%s chars=%s",
                request_id,
                tier,
                intent,
                len(cached_text),
            )
            return
        if not _breaker.allow():
            logger.warning("circuit open, rejecting ip=%s id=%s", ip, request_id)
            _stats.record_blocked()
            yield sse("error", {"message": "上游连续失败，已暂停约 30 秒，请稍后再试。"})
            yield sse(
                "done",
                {
                    "tier": tier,
                    "intent": intent,
                    "chars": 0,
                    "elapsed": 0.0,
                    "model": model,
                    "blocked": True,
                },
            )
            return
        try:
            async with _semaphore:

                async def _primary() -> AsyncIterator[tuple[str, str]]:
                    async for item in llm.stream_completion(
                        upstream.provider,
                        api_key=upstream.api_key,
                        model=model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=budget,
                        top_p=settings.top_p,
                        presence_penalty=settings.presence_penalty,
                        include_usage=settings.stream_usage,
                        prompt_cache=settings.prompt_cache,
                    ):
                        yield item

                # A queue and a pump, so a silent upstream can be covered by a
                # comment line every few seconds instead of leaving the browser
                # staring at a stalled connection behind a proxy.
                queue: asyncio.Queue = asyncio.Queue()

                async def _secondary() -> AsyncIterator[tuple[str, str]]:
                    async for item in llm.stream_completion(
                        _FallbackProvider(),
                        api_key=settings.fallback_api_key,
                        model=settings.fallback_model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=budget,
                        include_usage=settings.stream_usage,
                        prompt_cache=settings.prompt_cache,
                    ):
                        yield item

                def _chain():
                    if settings.fallback_configured:
                        return llm.stream_with_fallback(_primary, _secondary)
                    return llm.stream_with_retry(_primary)

                async def _pump() -> None:
                    try:
                        async for item in _chain():
                            await queue.put(item)
                    finally:
                        await queue.put(None)

                pump = asyncio.create_task(_pump())
                try:
                    while True:
                        try:
                            item = await asyncio.wait_for(queue.get(), timeout=12)
                        except TimeoutError:
                            yield b": ping\n\n"
                            continue
                        if item is None:
                            break
                        kind, text = item
                        if kind == "usage":
                            try:
                                usage_payload = json.loads(text)
                            except ValueError:
                                usage_payload = None
                            if isinstance(usage_payload, dict):
                                yield sse("usage", usage_payload)
                            continue
                        if kind == "finish":
                            # Metadata, not a delta: a client that rendered this
                            # would see the word "length" appended to the answer.
                            finish_reason = text
                            continue
                        if not first_token_at:
                            first_token_at = time.monotonic()
                        produced += len(text)
                        if kind != "reasoning":
                            answered.append(text)
                        yield sse("reasoning" if kind == "reasoning" else "delta", {"t": text})
                finally:
                    pump.cancel()
                # The last chance to repair the answer: after this point the
                # stream is closed and the text is already rendered. Appending a
                # delta keeps the cached copy and the client's copy identical.
                if not failed and unclosed_fence("".join(answered)):
                    patch = "\n```"
                    answered.append(patch)
                    produced += len(patch)
                    yield sse("delta", {"t": patch})
        except llm.LLMError as exc:
            failed = True
            openings_before = _breaker.openings
            _breaker.record_failure()
            if _breaker.openings > openings_before:
                logger.warning(format_breaker_log(_breaker.stats()))
            logger.info("chat failed ip=%s kind=%s: %s", ip, upstream.kind, exc)
            logger.info(
                format_turn_log(
                    request_id,
                    tier=tier,
                    intent=intent,
                    ttft=(first_token_at - started) if first_token_at else 0.0,
                    total=time.monotonic() - started,
                    chars=produced,
                    model=model,
                    outcome="failed",
                )
            )
            # status_code is None when the request never reached a server, so
            # this comparison used to raise and turn a network failure into a
            # 500 with no explanation.
            message = final_message(exc.status_code, upstream.label, exc.message)
            yield sse("error", {"message": message})
        except asyncio.CancelledError:
            cancelled = True
            raise
        except Exception:  # noqa: BLE001 - never leak internals to the client
            failed = True
            logger.exception("unexpected chat error ip=%s", ip)
            yield sse("error", {"message": "服务出现了一点意外，请稍后重试。"})
        finally:
            # One estimate for the whole turn: the counters, the done event and
            # the log all read the same number. Passing cost=None here would mark
            # the total unknown even for a free model whose price is known (0).
            cost: float | None = None
            cached_tokens = 0
            truncated = finish_reason == FINISH_LENGTH
            if isinstance(usage_payload, dict):
                prompt_tokens = int(usage_payload.get("prompt_tokens") or 0)
                completion_tokens = int(usage_payload.get("completion_tokens") or 0)
                # Part of the prompt that the provider served from its own cache;
                # it is billed at a lower rate, so it is passed to both calls.
                cached_tokens = int(usage_payload.get("cached_tokens") or 0)
                cost = estimate_cost(model, prompt_tokens, completion_tokens, cached=cached_tokens)
                _stats.record_usage(
                    model, prompt_tokens, completion_tokens, cost, cached=cached_tokens
                )
            if cancelled:
                _stats.record_cancelled(model)
            else:
                _stats.record_turn(
                    model,
                    tier=tier,
                    intent=intent,
                    provider=upstream.provider.id,
                    failed=failed,
                    ttft=(first_token_at - started) if first_token_at else 0.0,
                    truncated=truncated,
                    finish=finish_reason,
                )
            if not failed and not cancelled:
                # Only a half-open probe can close an open breaker; that is the
                # moment an incident actually ends.
                recovering = _breaker.state == "half-open"
                _breaker.record_success()
                if recovering:
                    logger.info(format_recovery_log(_breaker.stats()))
                # A reply cut off at the token budget must never be cached: the
                # exact same question would then replay a half answer until the
                # TTL expired, with no way for the visitor to get the rest.
                if cache_key and answered and not truncated:
                    _cache.put(cache_key, "".join(answered))
                done_payload = {
                    "tier": tier,
                    "intent": intent,
                    "requestId": request_id,
                    "chars": produced,
                    "elapsed": round(time.monotonic() - started, 2),
                    "model": model,
                    "truncated": truncated,
                }
                if finish_reason:
                    done_payload["finish"] = finish_reason
                if usage_payload:
                    done_payload["usage"] = usage_payload
                    if cost is not None:
                        done_payload["cost"] = {"usd": cost, "text": format_cost(cost)}
                logger.info(
                    format_turn_log(
                        request_id,
                        tier=tier,
                        intent=intent,
                        ttft=(first_token_at - started) if first_token_at else 0.0,
                        total=time.monotonic() - started,
                        chars=produced,
                        model=model,
                        cache="miss",
                        cached_tokens=cached_tokens,
                        finish=finish_reason,
                        cost=cost,
                    )
                )
                yield sse("done", done_payload)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream; charset=utf-8",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "X-Request-Id": request_id,
            "X-Cache": "HIT" if cached_text else "MISS",
            **rate_headers,
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
    body = "User-agent: *\nAllow: /\nDisallow: /api/\nSitemap: https://liguijiang.com/sitemap.xml\n"
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


@app.exception_handler(RequestValidationError)
async def bad_request(request: Request, exc: RequestValidationError) -> JSONResponse:
    """A body that failed validation, answered in the site's own words.

    FastAPI's default response is a 422 whose body is a list of pydantic
    dictionaries - correct, and unreadable to the person who sent it. One
    sentence with the field's location is all a client needs.
    """
    first = exc.errors()[0] if exc.errors() else {}
    where = ".".join(str(part) for part in first.get("loc", ()) if part != "body")
    reason = first.get("msg") or "字段不合法"
    detail = f"{where}: {reason}" if where else reason
    return JSONResponse(
        {"error": f"请求体不符合要求（{detail}）", "code": "invalid_body"},
        status_code=400,
    )


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
