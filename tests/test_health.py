"""Тесты для модуля health_score — комплексная оценка качества контента."""

from __future__ import annotations

import pytest

from texthumanize.health_score import (
    ContentHealthReport,
    HealthComponent,
    content_health,
)


class TestContentHealth:
    """Tests for content_health()."""

    def test_returns_report(self):
        text = (
            "The quick brown fox jumps over the lazy dog. "
            "Mountains rise in the distance. Rivers flow gently."
        )
        report = content_health(text, lang="en")
        assert isinstance(report, ContentHealthReport)
        assert 0 <= report.score <= 100
        assert report.grade in ("A+", "A", "B", "C", "D", "F")

    def test_components_present(self):
        """Report should have multiple health components."""
        report = content_health(
            "This is a test sentence. Here is another one. And a third.",
            lang="en",
        )
        assert isinstance(report.components, list)
        assert len(report.components) >= 1
        for comp in report.components:
            assert isinstance(comp, HealthComponent)
            assert hasattr(comp, "name")
            assert hasattr(comp, "score")
            assert hasattr(comp, "weight")

    def test_grade_mapping(self):
        """Grade should be derived from score."""
        report = content_health("Normal text with reasonable quality.", lang="en")
        if report.score >= 90:
            assert report.grade in ("A+", "A")
        elif report.score >= 80:
            assert report.grade in ("A", "B")

    def test_include_flags(self):
        """Disabling components should still work."""
        report = content_health(
            "Test text for health.",
            lang="en",
            include_ai=False,
            include_grammar=False,
            include_uniqueness=False,
        )
        assert isinstance(report, ContentHealthReport)

    def test_empty_text(self):
        """Empty text should not crash."""
        report = content_health("", lang="en")
        assert isinstance(report, ContentHealthReport)

    @pytest.mark.parametrize("lang", ["en", "ru", "de", "fr", "es"])
    def test_multiple_languages(self, lang: str):
        """Should work for multiple languages."""
        report = content_health("Some test text here. Another sentence.", lang=lang)
        assert isinstance(report, ContentHealthReport)
        assert 0 <= report.score <= 100

    def test_high_quality_text(self):
        """Well-written text should score reasonably."""
        text = (
            "Natural language processing has evolved significantly. "
            "Modern approaches combine statistical methods with deep learning. "
            "Researchers continue exploring novel architectures. "
            "Applications range from translation to summarization."
        )
        report = content_health(text, lang="en")
        assert report.score >= 30  # At least not terrible

    def test_component_weights_sum(self):
        """Component weights should be positive."""
        report = content_health("Test sentence here.", lang="en")
        for comp in report.components:
            assert comp.weight > 0
