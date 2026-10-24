"""Runtime configuration for Dream AI.

Settings are read from environment variables (optionally loaded from a `.env`
file). No secret is ever committed to the repository — see `.env.example`.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_SYSTEM_PROMPT = (
    "You are Dream AI, a helpful, honest, and capable general-purpose "
    "assistant. Think clearly, answer truthfully, and admit when you are unsure."
)

# Values treated as "false" for boolean environment switches.
_FALSE_VALUES = {"", "0", "false", "no", "off", "n"}


@dataclass(frozen=True)
class Settings:
    """Immutable runtime settings for the agent."""

    provider: str
    base_url: str
    api_key: str
    model: str
    system_prompt: str
    data_dir: Path
    persistence_enabled: bool

    @property
    def hosted_configured(self) -> bool:
        """True when a hosted (OpenAI-compatible) provider can be used."""
        return bool(self.api_key.strip())


def _load_dotenv() -> None:
    """Load variables from `.env` if python-dotenv is installed.

    The dependency is optional: if it is missing, environment variables from
    the shell are still used.
    """
    try:
        from dotenv import load_dotenv
    except ImportError:  # pragma: no cover - optional dependency
        return
    load_dotenv()


def _truthy(raw: str) -> bool:
    """Interpret a string as a boolean switch (default: true)."""
    return raw.strip().lower() not in _FALSE_VALUES


def _default_data_dir() -> Path:
    """Per-user directory where sessions and preferences are stored."""
    return Path.home() / ".dream_ai"


def load_settings() -> Settings:
    """Build :class:`Settings` from the environment / `.env` file."""
    _load_dotenv()

    provider = os.getenv("DREAMAI_PROVIDER", "openai_compat").strip()
    if provider not in {"openai_compat", "local"}:
        # Fall back gracefully to the default rather than crashing startup.
        provider = "openai_compat"

    raw_data_dir = os.getenv("DREAMAI_DATA_DIR", "").strip()
    data_dir = Path(raw_data_dir) if raw_data_dir else _default_data_dir()

    return Settings(
        provider=provider,
        base_url=os.getenv("DREAMAI_BASE_URL", "https://api.deepseek.com/v1").strip(),
        api_key=os.getenv("DREAMAI_API_KEY", "").strip(),
        model=os.getenv("DREAMAI_MODEL", "deepseek-chat").strip(),
        system_prompt=os.getenv("DREAMAI_SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT).strip(),
        data_dir=data_dir,
        persistence_enabled=_truthy(os.getenv("DREAMAI_PERSISTENCE", "true")),
    )
