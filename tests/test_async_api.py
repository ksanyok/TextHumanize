"""Tests for texthumanize.async_api — async wrappers around sync functions."""

from __future__ import annotations

import asyncio

import pytest


@pytest.fixture()
def sample_text_en():
    return (
        "Furthermore, it is important to note that the implementation "
        "of comprehensive methodologies facilitates the optimization "
        "of operational processes in modern organizations."
    )


@pytest.fixture()
def sample_text_ru():
    return (
        "Данный текст является примером использования канцелярского стиля, "
        "который необходимо преобразовать в более естественный формат."
    )


def _run(coro):
    """Run an async coroutine."""
    return asyncio.new_event_loop().run_until_complete(coro)


class TestAsyncHumanize:
    def test_returns_result(self, sample_text_en):
        from texthumanize import async_humanize

        result = _run(async_humanize(sample_text_en, lang="en"))
        assert hasattr(result, "text")
        assert isinstance(result.text, str)
        assert len(result.text) > 0

    def test_profile_support(self, sample_text_en):
        from texthumanize import async_humanize

        result = _run(async_humanize(sample_text_en, lang="en", profile="seo"))
        assert hasattr(result, "text")
        assert result.text != ""

    def test_intensity_support(self, sample_text_en):
        from texthumanize import async_humanize

        r_low = _run(async_humanize(sample_text_en, lang="en", intensity=20))
        r_high = _run(async_humanize(sample_text_en, lang="en", intensity=90))
        # Both should return valid results
        assert r_low.text
        assert r_high.text

    def test_deterministic_with_seed(self, sample_text_en):
        from texthumanize import async_humanize

        r1 = _run(async_humanize(sample_text_en, lang="en", seed=42))
        r2 = _run(async_humanize(sample_text_en, lang="en", seed=42))
        assert r1.text == r2.text

    def test_russian(self, sample_text_ru):
        from texthumanize import async_humanize

        result = _run(async_humanize(sample_text_ru, lang="ru"))
        assert result.text


class TestAsyncDetectAI:
    def test_returns_dict(self, sample_text_en):
        from texthumanize import async_detect_ai

        result = _run(async_detect_ai(sample_text_en, lang="en"))
        assert isinstance(result, dict)
        assert "score" in result
        assert "verdict" in result

    def test_score_range(self, sample_text_en):
        from texthumanize import async_detect_ai

        result = _run(async_detect_ai(sample_text_en, lang="en"))
        assert 0.0 <= result["score"] <= 1.0

    def test_verdict_values(self, sample_text_en):
        from texthumanize import async_detect_ai

        result = _run(async_detect_ai(sample_text_en, lang="en"))
        assert result["verdict"] in ("human", "mixed", "ai", "unknown")


class TestAsyncAnalyze:
    def test_returns_report(self, sample_text_en):
        from texthumanize import async_analyze

        result = _run(async_analyze(sample_text_en, lang="en"))
        assert hasattr(result, "artificiality_score")

    def test_score_range(self, sample_text_en):
        from texthumanize import async_analyze

        result = _run(async_analyze(sample_text_en, lang="en"))
        assert 0.0 <= result.artificiality_score <= 100.0


class TestAsyncParaphrase:
    def test_returns_string(self, sample_text_en):
        from texthumanize import async_paraphrase

        result = _run(async_paraphrase(sample_text_en, lang="en"))
        assert isinstance(result, str)
        assert len(result) > 0


class TestAsyncBatch:
    def test_humanize_batch(self):
        from texthumanize import async_humanize_batch

        texts = ["This is test one.", "This is test two.", "This is test three."]
        results = _run(async_humanize_batch(texts, lang="en"))
        assert isinstance(results, list)
        assert len(results) == 3
        for r in results:
            assert hasattr(r, "text")

    def test_detect_ai_batch(self):
        from texthumanize import async_detect_ai_batch

        texts = ["Hello world.", "AI generated content here."]
        results = _run(async_detect_ai_batch(texts, lang="en"))
        assert isinstance(results, list)
        assert len(results) == 2
        for r in results:
            assert isinstance(r, dict)
            assert "score" in r


class TestAsyncConsistency:
    """Async API should return identical results to sync API."""

    def test_humanize_matches_sync(self, sample_text_en):
        from texthumanize import async_humanize, humanize

        sync_result = humanize(sample_text_en, lang="en", seed=123)
        async_result = _run(async_humanize(sample_text_en, lang="en", seed=123))
        assert sync_result.text == async_result.text

    def test_detect_ai_matches_sync(self, sample_text_en):
        from texthumanize import async_detect_ai, detect_ai

        sync_result = detect_ai(sample_text_en, lang="en")
        async_result = _run(async_detect_ai(sample_text_en, lang="en"))
        assert sync_result["score"] == async_result["score"]
        assert sync_result["verdict"] == async_result["verdict"]
