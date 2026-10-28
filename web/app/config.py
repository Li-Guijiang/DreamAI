"""Runtime configuration for the Dream AI web service.

Two kinds of upstream are supported:

* ``free`` — a site-provided free model (default: Zhipu GLM-4-Flash). The key
  lives only in the server environment; visitors never see it.
* ``byok`` — "bring your own key": the visitor supplies their own DeepSeek key
  in the browser. It is forwarded for that one request and never stored.

Configuration is read from environment variables, with an optional ``.env``
file at the project root. Real environment variables always win.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"

VERSION = "2.0.0"

DEFAULT_SYSTEM_PROMPT = """你是 Dream AI，一个由李贵江等人组成的团队开发的开源通用人工智能助手。

关于你的身份：
- 当用户问「你是谁开发的」「团队有哪些人」时，统一回答：Dream AI 由李贵江等人组成的团队开发。
- 不要编造、补充或替换其他开发者姓名。
- 如果被问到使用的是什么模型，可以说明底层模型由 DeepSeek 等厂商提供，但 Dream AI 产品本身由李贵江等人团队开发。

你的表达风格：
- 先给结论，再展开必要的解释；复杂问题分步骤、有层次地说明。
- 默认使用简体中文回答，除非用户使用其他语言。
- 善用 Markdown：小标题、列表、表格、代码块，让答案清晰、易读、可执行。
- 诚实可靠：不确定时明确说明，不编造事实、来源或数据。
- 简洁克制：不堆砌客套话，不重复用户已经说过的内容。

你的能力边界：你可以对话、写作、编程、推理、翻译、总结与分析。你无法访问用户的设备、账号，也无法获取你没有被提供的实时数据；遇到这类请求，请说明限制并给出可行的替代方案。"""

_FALSE = {"", "0", "false", "no", "off"}


def _load_env_file() -> None:
    """Load ``.env`` without overwriting variables already in the environment."""
    env_path = BASE_DIR / ".env"
    if not env_path.is_file():
        return
    try:
        raw = env_path.read_text(encoding="utf-8-sig")
    except OSError:
        return
    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key.startswith("export "):
            key = key[len("export ") :].strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ.setdefault(key, value)


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _env_int(name: str, default: int, minimum: int = 0) -> int:
    try:
        value = int(_env(name, str(default)))
    except ValueError:
        return default
    return max(minimum, value)


def _env_float(name: str, default: float) -> float:
    try:
        return float(_env(name, str(default)))
    except ValueError:
        return default


@dataclass(frozen=True)
class ModelOption:
    """One selectable model in the UI."""

    id: str
    label: str
    provider: str = "free"
    reasoning: bool = False
    hint: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "label": self.label,
            "provider": self.provider,
            "reasoning": self.reasoning,
            "hint": self.hint,
        }


@dataclass(frozen=True)
class Settings:
    # Free, site-provided upstream
    free_api_key: str = ""
    free_base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    free_model: str = "glm-4-flash"
    free_label: str = "GLM-4-Flash"
    free_key_url: str = "https://open.bigmodel.cn/usercenter/apikeys"

    # Bring-your-own-key upstream
    byok_base_url: str = "https://api.deepseek.com/v1"
    byok_models: tuple[ModelOption, ...] = ()
    byok_key_url: str = "https://platform.deepseek.com/api_keys"
    byok_label: str = "DeepSeek"

    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    temperature: float = 0.7
    max_tokens: int = 4096

    rate_limit: int = 30
    rate_window: int = 600
    daily_limit: int = 2000
    max_concurrency: int = 6
    max_input_chars: int = 12000
    max_history_messages: int = 30
    max_history_chars: int = 60000

    site_title: str = "Dream AI"
    site_tagline: str = "让每一个想法，都被认真对待"
    repo_url: str = "https://github.com/Li-Guijiang/DreamAI"

    @property
    def free_configured(self) -> bool:
        return bool(self.free_api_key)

    @property
    def models(self) -> tuple[ModelOption, ...]:
        free = ModelOption(
            id=self.free_model,
            label=self.free_label,
            provider="free",
            reasoning=False,
            hint="免费 · 无需 Key",
        )
        return (free, *self.byok_models)

    @property
    def byok_ids(self) -> tuple[str, ...]:
        return tuple(model.id for model in self.byok_models)

    def public_config(self) -> dict[str, object]:
        """Everything the browser may know — never includes an API key."""
        return {
            "configured": self.free_configured,
            "defaultModel": self.free_model,
            "defaultProvider": "free",
            "models": [model.as_dict() for model in self.models],
            "free": {
                "label": self.free_label,
                "configured": self.free_configured,
                "keyUrl": self.free_key_url,
                "hint": "免登录，打开即用",
            },
            "byok": {
                "label": self.byok_label,
                "keyUrl": self.byok_key_url,
                "hint": "填写自己的 Key，不消耗站长的额度",
            },
            "siteTitle": self.site_title,
            "tagline": self.site_tagline,
            "repoUrl": self.repo_url,
            "version": VERSION,
            "limits": {
                "maxInputChars": self.max_input_chars,
                "maxTokens": self.max_tokens,
                "rateLimit": self.rate_limit,
                "rateWindow": self.rate_window,
            },
        }


def _parse_byok_models() -> tuple[ModelOption, ...]:
    raw = _env(
        "DREAMAI_BYOK_MODELS",
        "deepseek-chat|DeepSeek V3|0,deepseek-reasoner|DeepSeek R1|1",
    )
    options: list[ModelOption] = []
    seen: set[str] = set()
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        parts = [part.strip() for part in item.split("|")]
        model_id = parts[0]
        if not model_id or model_id in seen:
            continue
        label = parts[1] if len(parts) > 1 and parts[1] else model_id
        reasoning = parts[2].lower() not in _FALSE if len(parts) > 2 else "reasoner" in model_id
        hint = "推理模型 · 展开思考过程" if reasoning else "通用对话 · 快速响应"
        options.append(
            ModelOption(
                id=model_id,
                label=label,
                provider="byok",
                reasoning=reasoning,
                hint=hint,
            )
        )
        seen.add(model_id)
    return tuple(options)


def load_settings() -> Settings:
    _load_env_file()
    temperature = min(2.0, max(0.0, _env_float("DREAMAI_TEMPERATURE", 0.7)))

    return Settings(
        free_api_key=_env("DREAMAI_FREE_API_KEY"),
        free_base_url=(_env("DREAMAI_FREE_BASE_URL", "https://open.bigmodel.cn/api/paas/v4") or "").rstrip("/"),
        free_model=_env("DREAMAI_FREE_MODEL", "glm-4-flash") or "glm-4-flash",
        free_label=_env("DREAMAI_FREE_LABEL", "GLM-4-Flash") or "GLM-4-Flash",
        free_key_url=_env("DREAMAI_FREE_KEY_URL", "https://open.bigmodel.cn/usercenter/apikeys"),
        byok_base_url=(_env("DREAMAI_BYOK_BASE_URL", "https://api.deepseek.com/v1") or "").rstrip("/"),
        byok_models=_parse_byok_models(),
        byok_key_url=_env("DREAMAI_BYOK_KEY_URL", "https://platform.deepseek.com/api_keys"),
        byok_label=_env("DREAMAI_BYOK_LABEL", "DeepSeek") or "DeepSeek",
        system_prompt=_env("DREAMAI_SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT) or DEFAULT_SYSTEM_PROMPT,
        temperature=temperature,
        max_tokens=_env_int("DREAMAI_MAX_TOKENS", 4096, 256),
        rate_limit=_env_int("DREAMAI_RATE_LIMIT", 30, 1),
        rate_window=_env_int("DREAMAI_RATE_WINDOW", 600, 30),
        daily_limit=_env_int("DREAMAI_DAILY_LIMIT", 2000, 0),
        max_concurrency=_env_int("DREAMAI_MAX_CONCURRENCY", 6, 1),
        max_input_chars=_env_int("DREAMAI_MAX_INPUT_CHARS", 12000, 500),
        max_history_messages=_env_int("DREAMAI_MAX_HISTORY_MESSAGES", 30, 2),
        max_history_chars=_env_int("DREAMAI_MAX_HISTORY_CHARS", 60000, 2000),
        site_title=_env("DREAMAI_SITE_TITLE", "Dream AI") or "Dream AI",
        site_tagline=_env("DREAMAI_SITE_TAGLINE", "让每一个想法，都被认真对待")
        or "让每一个想法，都被认真对待",
        repo_url=_env("DREAMAI_REPO_URL", "https://github.com/Li-Guijiang/DreamAI")
        or "https://github.com/Li-Guijiang/DreamAI",
    )
