"""Exception hierarchy for TextHumanize.

All library-specific exceptions inherit from :class:`TextHumanizeError`,
allowing callers to ``except TextHumanizeError`` for blanket handling.
"""

from __future__ import annotations


class TextHumanizeError(Exception):
    """Base exception for all TextHumanize errors."""


# ── Pipeline errors ───────────────────────────────────────

class PipelineError(TextHumanizeError):
    """Raised when the processing pipeline encounters an unrecoverable error."""


class StageError(PipelineError):
    """Raised when an individual pipeline stage fails.

    Attributes:
        stage_name: Name of the failing stage.
    """

    def __init__(self, stage_name: str, message: str | None = None):
        self.stage_name = stage_name
        msg = f"Stage '{stage_name}' failed"
        if message:
            msg += f": {message}"
        super().__init__(msg)


# ── Detection errors ──────────────────────────────────────

class DetectionError(TextHumanizeError):
    """Raised when AI or watermark detection fails."""


# ── Configuration / validation ────────────────────────────

class ConfigError(TextHumanizeError, ValueError):
    """Raised for invalid options, profiles, or parameters."""


class UnsupportedLanguageError(ConfigError):
    """Raised when the requested language is not supported."""

    def __init__(self, lang: str):
        self.lang = lang
        super().__init__(f"Unsupported language: '{lang}'")


class InputTooLargeError(ConfigError):
    """Raised when input text exceeds the maximum allowed size."""

    def __init__(self, size: int, max_size: int):
        self.size = size
        self.max_size = max_size
        super().__init__(
            f"Input text too large: {size:,} chars (max {max_size:,})"
        )


# ── AI Backend errors ─────────────────────────────────────

class AIBackendError(TextHumanizeError):
    """Raised when the external AI backend encounters an error."""


class AIBackendUnavailableError(AIBackendError):
    """Raised when no AI backend is reachable."""


class AIBackendRateLimitError(AIBackendError):
    """Raised when the AI backend rate limit is exceeded."""
