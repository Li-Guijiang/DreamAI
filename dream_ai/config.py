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
    tools_enabled: bool
    file_access_enabled: bool
    web_search_enabled: bool
    workspace_dir: Path
    autonomy_enabled: bool = True
    max_steps: int = 10
    max_retries: int = 2
    autonomy_verbose: bool = False
    animations_enabled: bool = True
    animation_speed: float = 1.0

    @property
    def hosted_configured(self) -> bool:
        """True when a hosted (OpenAI-compatible) provider can be used."""
        return bool(self.api_key.strip())


def _load_dotenv() -> None:
    """Load variables from `.env` if python-dotenv is installed.

    The project-root `.env` is loaded first so configuration works regardless
    of the current working directory. A `.env` in the current directory is
    loaded afterwards as a fallback only: both loads use ``override=False``, so
    a variable that already exists (in the shell, or from the project-root
    file) is never overwritten. The dependency is optional: if it is missing,
    environment variables from the shell are still used.
    """
    try:
        from dotenv import load_dotenv
    except ImportError:  # pragma: no cover - optional dependency
        return

    project_root = Path(__file__).resolve().parents[1]
    project_env = project_root / ".env"
    if project_env.is_file():
        load_dotenv(project_env, override=False)

    # Working-directory `.env` fills gaps only; existing shell environment
    # variables and the project-root file are never overwritten.
    load_dotenv(override=False)


def _truthy(raw: str) -> bool:
    """Interpret a string as a boolean switch (default: true)."""
    return raw.strip().lower() not in _FALSE_VALUES


def _positive_int(raw: str, default: int) -> int:
    """Parse a positive integer, falling back to ``default`` when invalid."""
    try:
        value = int(raw.strip())
    except ValueError:
        return default
    return value if value > 0 else default


def _nonnegative_int(raw: str, default: int) -> int:
    """Parse a non-negative integer, falling back to ``default`` when invalid."""
    try:
        value = int(raw.strip())
    except ValueError:
        return default
    return value if value >= 0 else default


def _animation_speed(raw: str, default: float = 1.0) -> float:
    """Parse a positive animation-speed multiplier, clamped to 0.25–4.0."""
    try:
        value = float(raw.strip())
    except ValueError:
        return default
    if value <= 0:
        return default
    return max(0.25, min(4.0, value))


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

    raw_workspace = os.getenv("DREAMAI_WORKSPACE_DIR", "").strip()
    workspace_dir = Path(raw_workspace) if raw_workspace else data_dir / "workspace"

    return Settings(
        provider=provider,
        base_url=os.getenv("DREAMAI_BASE_URL", "https://api.deepseek.com/v1").strip(),
        api_key=os.getenv("DREAMAI_API_KEY", "").strip(),
        model=os.getenv("DREAMAI_MODEL", "deepseek-chat").strip(),
        system_prompt=os.getenv("DREAMAI_SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT).strip(),
        data_dir=data_dir,
        persistence_enabled=_truthy(os.getenv("DREAMAI_PERSISTENCE", "true")),
        tools_enabled=_truthy(os.getenv("DREAMAI_TOOLS_ENABLED", "true")),
        file_access_enabled=_truthy(os.getenv("DREAMAI_FILE_ACCESS_ENABLED", "false")),
        web_search_enabled=_truthy(os.getenv("DREAMAI_WEB_SEARCH_ENABLED", "false")),
        workspace_dir=workspace_dir,
        autonomy_enabled=_truthy(os.getenv("DREAMAI_AUTONOMY_ENABLED", "true")),
        max_steps=_positive_int(os.getenv("DREAMAI_MAX_STEPS", "10"), 10),
        max_retries=_nonnegative_int(os.getenv("DREAMAI_MAX_RETRIES", "2"), 2),
        autonomy_verbose=_truthy(os.getenv("DREAMAI_AUTONOMY_VERBOSE", "false")),
        animations_enabled=_truthy(os.getenv("DREAMAI_ANIMATIONS", "auto")),
        animation_speed=_animation_speed(os.getenv("DREAMAI_ANIMATION_SPEED", "1.0")),
    )
