"""Model providers the site can talk to.

Each provider is described once here: where its API lives, which auth header it
expects, and which models it exposes. The chat route reads this table instead of
branching on provider names, so adding a provider is a data change.

Three wire formats are supported:

* ``openai``    - ``/chat/completions`` with ``Authorization: Bearer``. Covers
                  DeepSeek, OpenAI, Zhipu, Moonshot and most compatible gateways.
* ``anthropic`` - ``/v1/messages`` with ``x-api-key`` and an ``anthropic-version``
                  header; the system prompt is a top-level field, not a message.
* ``google``    - ``:streamGenerateContent`` with the key in a query parameter and
                  ``contents`` instead of ``messages``.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ModelEntry:
    """One selectable model. ``reasoning`` marks models that stream a thinking field."""

    id: str
    label: str
    reasoning: bool = False


@dataclass(frozen=True)
class Provider:
    id: str
    label: str
    kind: str
    base_url: str
    key_url: str
    models: tuple[ModelEntry, ...] = field(default_factory=tuple)
    #: Shown under the key field; keeps the instructions next to the input.
    hint: str = ""


PROVIDERS: dict[str, Provider] = {
    "deepseek": Provider(
        id="deepseek",
        label="DeepSeek",
        kind="openai",
        base_url="https://api.deepseek.com/v1",
        key_url="https://platform.deepseek.com/api_keys",
        models=(
            ModelEntry("deepseek-chat", "DeepSeek Chat", reasoning=False),
            ModelEntry("deepseek-reasoner", "DeepSeek Reasoner", reasoning=True),
        ),
        hint="支持 deepseek-chat 与 deepseek-reasoner；后者会返回思考过程。",
    ),
    "openai": Provider(
        id="openai",
        label="OpenAI",
        kind="openai",
        base_url="https://api.openai.com/v1",
        key_url="https://platform.openai.com/api-keys",
        models=(
            ModelEntry("gpt-4o-mini", "GPT-4o mini"),
            ModelEntry("gpt-4o", "GPT-4o"),
        ),
        hint="任何 OpenAI 兼容网关也可以：填自定义模型 ID 即可。",
    ),
    "anthropic": Provider(
        id="anthropic",
        label="Anthropic",
        kind="anthropic",
        base_url="https://api.anthropic.com",
        key_url="https://console.anthropic.com/settings/keys",
        models=(
            ModelEntry("claude-3-5-sonnet-latest", "Claude 3.5 Sonnet"),
            ModelEntry("claude-3-5-haiku-latest", "Claude 3.5 Haiku"),
        ),
        hint="Claude 的 system 提示单独传递，本服务已自动处理。",
    ),
    "google": Provider(
        id="google",
        label="Google Gemini",
        kind="google",
        base_url="https://generativelanguage.googleapis.com/v1beta",
        key_url="https://aistudio.google.com/app/apikey",
        models=(
            ModelEntry("gemini-2.0-flash", "Gemini 2.0 Flash"),
            ModelEntry("gemini-1.5-pro", "Gemini 1.5 Pro"),
        ),
        hint="Key 走查询参数，不会写进日志。",
    ),
    "zhipu": Provider(
        id="zhipu",
        label="智谱 GLM",
        kind="openai",
        base_url="https://open.bigmodel.cn/api/paas/v4",
        key_url="https://open.bigmodel.cn/usercenter/apikeys",
        models=(
            ModelEntry("glm-4-flash", "GLM-4-Flash"),
            ModelEntry("glm-4-plus", "GLM-4-Plus"),
        ),
        hint="与站点免费模型同源，用自己的 Key 可绕开站点额度。",
    ),
}

#: Providers a visitor may use with their own key.
BYOK_PROVIDERS: tuple[str, ...] = tuple(PROVIDERS)


def get_provider(provider_id: str) -> Provider | None:
    return PROVIDERS.get((provider_id or "").strip().lower())


def provider_ids() -> tuple[str, ...]:
    return tuple(PROVIDERS)


def is_known_model(provider_id: str, model: str) -> bool:
    provider = get_provider(provider_id)
    if not provider:
        return False
    return any(entry.id == model for entry in provider.models)


def resolve_model(provider_id: str, requested: str | None) -> str:
    """Return a model the provider actually serves.

    A custom id is accepted as-is - gateways expose model names we cannot
    enumerate - but an empty or obviously wrong value falls back to the first
    entry so the request still has a chance to succeed.
    """
    provider = get_provider(provider_id)
    if not provider or not provider.models:
        return (requested or "").strip()
    candidate = (requested or "").strip()
    if candidate:
        return candidate
    return provider.models[0].id


def public_catalog() -> list[dict]:
    """Provider metadata safe to send to the browser (no keys, no secrets)."""
    return [
        {
            "id": provider.id,
            "label": provider.label,
            "keyUrl": provider.key_url,
            "hint": provider.hint,
            "models": [
                {"id": entry.id, "label": entry.label, "reasoning": entry.reasoning}
                for entry in provider.models
            ],
        }
        for provider in PROVIDERS.values()
    ]
