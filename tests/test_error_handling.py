"""Tests for error handling, input validation, and exception hierarchy.

Covers: invalid inputs, boundary conditions, exception types.
"""

from __future__ import annotations

import pytest

from texthumanize.exceptions import (
    ConfigError,
    InputTooLargeError,
    TextHumanizeError,
)


class TestExceptionHierarchy:
    """Verify exception class hierarchy."""

    def test_base_exception(self):
        assert issubclass(TextHumanizeError, Exception)

    def test_config_error_is_value_error(self):
        assert issubclass(ConfigError, ValueError)

    def test_input_too_large_is_config_error(self):
        assert issubclass(InputTooLargeError, ConfigError)

    def test_input_too_large_attrs(self):
        exc = InputTooLargeError(2_000_000, 1_000_000)
        assert exc.size == 2_000_000
        assert exc.max_size == 1_000_000
        assert "2,000,000" in str(exc)

    def test_pipeline_error_hierarchy(self):
        from texthumanize.exceptions import PipelineError, StageError
        assert issubclass(StageError, PipelineError)
        assert issubclass(PipelineError, TextHumanizeError)

    def test_stage_error_attrs(self):
        from texthumanize.exceptions import StageError
        exc = StageError("typography", "bad chars")
        assert exc.stage_name == "typography"
        assert "typography" in str(exc)
        assert "bad chars" in str(exc)

    def test_detection_error(self):
        from texthumanize.exceptions import DetectionError
        assert issubclass(DetectionError, TextHumanizeError)

    def test_unsupported_language_error(self):
        from texthumanize.exceptions import UnsupportedLanguageError
        exc = UnsupportedLanguageError("xx")
        assert exc.lang == "xx"
        assert "xx" in str(exc)

    def test_ai_backend_errors(self):
        from texthumanize.exceptions import (
            AIBackendError,
            AIBackendRateLimitError,
            AIBackendUnavailableError,
        )
        assert issubclass(AIBackendUnavailableError, AIBackendError)
        assert issubclass(AIBackendRateLimitError, AIBackendError)
        assert issubclass(AIBackendError, TextHumanizeError)

    def test_catch_all(self):
        """All custom exceptions should be catchable via TextHumanizeError."""
        from texthumanize.exceptions import (
            AIBackendRateLimitError,
            StageError,
        )
        with pytest.raises(TextHumanizeError):
            raise InputTooLargeError(100, 50)
        with pytest.raises(TextHumanizeError):
            raise StageError("test")
        with pytest.raises(TextHumanizeError):
            raise AIBackendRateLimitError("rate limited")


class TestHumanizeInputValidation:
    """Test input validation in humanize()."""

    def test_none_raises_config_error(self):
        from texthumanize import humanize
        with pytest.raises(ConfigError):
            humanize(None)

    def test_int_raises_config_error(self):
        from texthumanize import humanize
        with pytest.raises(ConfigError):
            humanize(42)

    def test_empty_string_returns_empty(self):
        from texthumanize import humanize
        result = humanize("")
        assert result.text == ""

    def test_whitespace_only_returns_same(self):
        from texthumanize import humanize
        result = humanize("   \t\n  ")
        assert result.text == "   \t\n  "

    def test_oversized_raises_input_too_large(self):
        from texthumanize import humanize
        huge = "a " * 600_000  # ~1.2M chars
        with pytest.raises(InputTooLargeError) as exc_info:
            humanize(huge)
        assert exc_info.value.max_size == 1_000_000

    def test_valid_text_succeeds(self):
        from texthumanize import humanize
        result = humanize("This is a simple test.", lang="en")
        assert isinstance(result.text, str)
        assert len(result.text) > 0


class TestDetectAIInputValidation:
    """Test input validation in detect_ai()."""

    def test_none_raises_config_error(self):
        from texthumanize import detect_ai
        with pytest.raises(ConfigError):
            detect_ai(None)

    def test_int_raises_config_error(self):
        from texthumanize import detect_ai
        with pytest.raises(ConfigError):
            detect_ai(123)

    def test_empty_string_returns_human(self):
        from texthumanize import detect_ai
        result = detect_ai("")
        assert result["verdict"] == "human"
        assert result["score"] == 0.0

    def test_oversized_raises_input_too_large(self):
        from texthumanize import detect_ai
        huge = "word " * 300_000
        with pytest.raises(InputTooLargeError):
            detect_ai(huge)

    def test_valid_text_returns_dict(self):
        from texthumanize import detect_ai
        result = detect_ai("The quick brown fox jumps over the lazy dog.", lang="en")
        assert "score" in result
        assert "verdict" in result
        assert result["verdict"] in ("human", "mixed", "ai", "unknown")


class TestDetectAIBatch:
    """Test detect_ai_batch edge cases."""

    def test_empty_list(self):
        from texthumanize import detect_ai_batch
        result = detect_ai_batch([])
        assert result == []


class TestPipelineValidation:
    """Test Pipeline parameter validation."""

    def test_register_plugin_no_position(self):
        from texthumanize import Pipeline
        with pytest.raises(ValueError, match="before.*after"):
            Pipeline.register_plugin(object())

    def test_register_plugin_unknown_stage(self):
        from texthumanize import Pipeline
        with pytest.raises(ValueError, match="Unknown stage"):
            Pipeline.register_plugin(object(), before="nonexistent_stage")

    def test_register_hook_no_position(self):
        from texthumanize import Pipeline
        with pytest.raises(ValueError, match="before.*after"):
            Pipeline.register_hook(lambda t, l: t)

    def test_register_hook_unknown_stage(self):
        from texthumanize import Pipeline
        with pytest.raises(ValueError, match="Unknown stage"):
            Pipeline.register_hook(lambda t, l: t, after="nonexistent_stage")


class TestAnalyzeEdgeCases:
    """Test analyze() edge cases."""

    def test_empty_text(self):
        from texthumanize import analyze
        result = analyze("")
        assert result is not None

    def test_single_word(self):
        from texthumanize import analyze
        result = analyze("Hello")
        assert result is not None


class TestExplainEdgeCases:
    """Test explain() basic usage."""

    def test_explain_returns_string(self):
        from texthumanize import explain, humanize
        result = humanize("Данный текст является примером.", lang="ru")
        explanation = explain(result)
        assert isinstance(explanation, str)
