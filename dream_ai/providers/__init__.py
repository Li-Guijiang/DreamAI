"""Provider factory: build an LLM backend from :class:`Settings`."""

from __future__ import annotations

from ..config import Settings
from ..exceptions import ConfigurationError
from .base import LLMProvider
from .local import LocalEchoProvider
from .openai_compat import OpenAICompatProvider


def build_provider(settings: Settings) -> LLMProvider:
    """Return a configured provider, falling back to offline demo mode.

    If a hosted provider was selected but no API key is present, the offline
    :class:`LocalEchoProvider` is returned so the agent still starts and can
    be explored.
    """
    if settings.provider == "local" or not settings.hosted_configured:
        return LocalEchoProvider()

    if settings.provider == "openai_compat":
        return OpenAICompatProvider(
            model=settings.model,
            api_key=settings.api_key,
            base_url=settings.base_url,
            system_prompt=settings.system_prompt,
        )

    raise ConfigurationError(f"Unknown provider: {settings.provider!r}")


__all__ = ["LLMProvider", "LocalEchoProvider", "OpenAICompatProvider", "build_provider"]
