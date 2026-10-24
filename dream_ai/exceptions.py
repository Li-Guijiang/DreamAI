"""Custom exceptions for Dream AI."""


class DreamAIError(Exception):
    """Base exception for all Dream AI errors."""


class ConfigurationError(DreamAIError):
    """Raised when the project is misconfigured (missing/invalid settings)."""


class ProviderError(DreamAIError):
    """Raised when an LLM provider fails to generate a response."""


class ToolError(DreamAIError):
    """Raised when a tool receives invalid arguments or fails to execute."""


class ToolConfirmationRequired(DreamAIError):
    """Raised when a protected tool needs explicit user confirmation before running."""

    def __init__(self, tool_name: str, message: str, arguments: dict[str, object]) -> None:
        super().__init__(message)
        self.tool_name = tool_name
        self.arguments = arguments
