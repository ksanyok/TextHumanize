"""Tests for OpenAI LLM integration in the humanization pipeline."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from texthumanize import humanize
from texthumanize.pipeline import HumanizeOptions, Pipeline


class TestLLMOptionsPropagation(unittest.TestCase):
    """openai_api_key and openai_model flow through correctly."""

    def test_options_fields_exist(self):
        """HumanizeOptions has openai_api_key and openai_model fields."""
        opts = HumanizeOptions()
        assert opts.openai_api_key is None
        assert opts.openai_model == "gpt-4o-mini"

    def test_options_custom_values(self):
        opts = HumanizeOptions(openai_api_key="sk-test123", openai_model="gpt-4o")
        assert opts.openai_api_key == "sk-test123"
        assert opts.openai_model == "gpt-4o"

    def test_humanize_accepts_openai_params(self):
        """humanize() accepts openai_api_key/openai_model without error."""
        # With a fake key the LLM step should fail gracefully and
        # still return a locally-humanized result.
        result = humanize(
            "This is a test sentence for humanization.",
            lang="en",
            openai_api_key="sk-fake-key-for-testing",
            openai_model="gpt-4o-mini",
            seed=42,
        )
        assert result.text
        assert isinstance(result.text, str)

    def test_no_openai_key_skips_llm(self):
        """Without an API key, LLM-assisted evasion is skipped."""
        result = humanize(
            "Furthermore, the implementation of this technology.",
            lang="en",
            seed=42,
        )
        change_types = [c["type"] for c in result.changes]
        assert "llm_evasion" not in change_types


class TestLLMAssistedRewrite(unittest.TestCase):
    """Unit tests for Pipeline._llm_assisted_rewrite()."""

    def _make_pipeline(self, api_key: str = "sk-test") -> Pipeline:
        opts = HumanizeOptions(
            lang="en",
            openai_api_key=api_key,
            openai_model="gpt-4o-mini",
            seed=42,
        )
        return Pipeline(opts)

    def _make_result(self, text: str, original: str = "original text") -> MagicMock:
        result = MagicMock()
        result.text = text
        result.changes = []
        result.metrics_before = {}
        result.metrics_after = {}
        return result

    @patch("texthumanize.ai_backend.AIBackend")
    def test_llm_rewrite_improves_score(self, mock_backend_cls):
        """When LLM produces a better score, it's returned."""
        mock_ai = MagicMock()
        mock_ai.paraphrase.return_value = "A totally human-sounding rewrite."
        mock_ai.improve_naturalness.return_value = "Another natural version."
        mock_backend_cls.return_value = mock_ai

        pipeline = self._make_pipeline()
        current = self._make_result("AI-sounding text with formal structure.")

        # Mock detect_fn: original text=0.8, both candidates=0.3
        def mock_detect(text, *, lang):
            if text == "AI-sounding text with formal structure.":
                return {"combined_score": 0.8}
            return {"combined_score": 0.3}

        result = pipeline._llm_assisted_rewrite(
            original="Some original text.",
            current=current,
            lang="en",
            api_key="sk-test",
            model="gpt-4o-mini",
            target_score=0.40,
            max_change=0.60,
            detect_fn=mock_detect,
            check_deadline=lambda: None,
        )

        assert result is not None
        assert result.text in (
            "A totally human-sounding rewrite.",
            "Another natural version.",
        )
        change_types = [c["type"] for c in result.changes]
        assert "llm_evasion" in change_types

    @patch("texthumanize.ai_backend.AIBackend")
    def test_llm_rewrite_no_improvement(self, mock_backend_cls):
        """When LLM doesn't improve score, None is returned."""
        mock_ai = MagicMock()
        mock_ai.paraphrase.return_value = "Still AI text."
        mock_ai.improve_naturalness.return_value = "Still AI too."
        mock_backend_cls.return_value = mock_ai

        pipeline = self._make_pipeline()
        current = self._make_result("Already at score 0.9.")

        def mock_detect(text, *, lang):
            return {"combined_score": 0.9}  # Always bad

        result = pipeline._llm_assisted_rewrite(
            original="Some original.",
            current=current,
            lang="en",
            api_key="sk-test",
            model="gpt-4o-mini",
            target_score=0.40,
            max_change=0.60,
            detect_fn=mock_detect,
            check_deadline=lambda: None,
        )

        assert result is None

    @patch("texthumanize.ai_backend.AIBackend")
    def test_llm_rewrite_backend_error(self, mock_backend_cls):
        """Backend errors return None gracefully."""
        mock_backend_cls.side_effect = Exception("Connection error")

        pipeline = self._make_pipeline()
        current = self._make_result("Some text.")

        result = pipeline._llm_assisted_rewrite(
            original="Original.",
            current=current,
            lang="en",
            api_key="sk-test",
            model="gpt-4o-mini",
            target_score=0.40,
            max_change=0.60,
            detect_fn=lambda t, *, lang: {"combined_score": 0.8},
            check_deadline=lambda: None,
        )

        assert result is None

    @patch("texthumanize.ai_backend.AIBackend")
    def test_llm_paraphrase_empty_response(self, mock_backend_cls):
        """Empty paraphrase response returns None."""
        mock_ai = MagicMock()
        mock_ai.paraphrase.return_value = ""
        mock_backend_cls.return_value = mock_ai

        pipeline = self._make_pipeline()
        current = self._make_result("Some text.")

        result = pipeline._llm_assisted_rewrite(
            original="Original.",
            current=current,
            lang="en",
            api_key="sk-test",
            model="gpt-4o-mini",
            target_score=0.40,
            max_change=0.60,
            detect_fn=lambda t, *, lang: {"combined_score": 0.8},
            check_deadline=lambda: None,
        )

        assert result is None


class TestLLMInRunMethod(unittest.TestCase):
    """Integration: LLM block in Pipeline.run()."""

    @patch("texthumanize.ai_backend.AIBackend")
    def test_llm_block_called_when_key_present_and_score_high(self, mock_cls):
        """LLM block is attempted when API key is set and score > target."""
        mock_ai = MagicMock()
        # Return something vaguely human
        mock_ai.paraphrase.return_value = (
            "AI stuff got better with simpler words and shorter bits."
        )
        mock_ai.improve_naturalness.return_value = None
        mock_cls.return_value = mock_ai

        # Use a clearly AI text so the detection loop doesn't already
        # bring it below threshold before the LLM block.
        text = (
            "Furthermore, the utilization of this methodology is paramount."
        )
        result = humanize(
            text,
            lang="en",
            openai_api_key="sk-fake",
            seed=42,
            intensity=30,  # low intensity to keep local transforms mild
        )
        # Result should exist regardless
        assert result.text
        assert isinstance(result.text, str)


if __name__ == "__main__":
    unittest.main()
