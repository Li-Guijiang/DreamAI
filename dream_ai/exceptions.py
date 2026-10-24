"""Custom exceptions for Dream AI."""


class DreamAIError(Exception):
    """Base exception for all Dream AI errors."""


class ConfigurationError(DreamAIError):
    """Raised when the project is misconfigured (missing/invalid settings)."""


class ProviderError(DreamAIError):
    """Raised when an LLM provider fails to generate a response."""
