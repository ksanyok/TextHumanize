"""Тесты для модуля semantic — семантическое сходство текстов."""

from __future__ import annotations

import pytest

from texthumanize.semantic import SemanticReport, semantic_similarity


class TestSemanticSimilarity:
    """Tests for semantic_similarity()."""

    def test_returns_report(self):
        report = semantic_similarity(
            "The cat sat on the mat",
            "The cat was sitting on the rug",
        )
        assert isinstance(report, SemanticReport)
        assert 0 <= report.preservation <= 1

    def test_identical_texts(self):
        """Identical texts should have preservation ~1.0."""
        text = "The quick brown fox jumps over the lazy dog."
        report = semantic_similarity(text, text)
        assert report.preservation >= 0.99

    def test_completely_different(self):
        """Different texts should have low preservation."""
        report = semantic_similarity(
            "Mountains and rivers dominate the landscape",
            "Quantum mechanics explains subatomic behavior",
        )
        assert report.preservation < 0.5

    def test_paraphrased_text(self):
        """Paraphrased text should retain high semantic similarity."""
        report = semantic_similarity(
            "The implementation of the project was successful.",
            "The project was implemented successfully.",
        )
        assert report.preservation >= 0.3

    def test_overlap_fields(self):
        """Report should have overlap metrics."""
        report = semantic_similarity("Hello world test", "Hello world check")
        assert 0 <= report.keyword_overlap <= 1
        assert 0 <= report.content_word_overlap <= 1
        assert 0 <= report.ngram_overlap <= 1

    def test_missing_and_added_keywords(self):
        """Should track missing and added keywords."""
        report = semantic_similarity(
            "Alpha Beta Gamma Delta",
            "Alpha Beta Epsilon Zeta",
        )
        assert isinstance(report.missing_keywords, list)
        assert isinstance(report.added_keywords, list)

    def test_empty_original(self):
        """Empty original should not crash."""
        report = semantic_similarity("", "Some text")
        assert isinstance(report, SemanticReport)

    def test_empty_processed(self):
        """Empty processed should not crash."""
        report = semantic_similarity("Some text", "")
        assert isinstance(report, SemanticReport)

    def test_both_empty(self):
        """Both empty should return high preservation."""
        report = semantic_similarity("", "")
        assert isinstance(report, SemanticReport)
