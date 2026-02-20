"""Тесты для модуля uniqueness — уникальность текста и сравнение."""

from __future__ import annotations

import pytest

from texthumanize.uniqueness import (
    SimilarityReport,
    UniquenessReport,
    compare_texts,
    text_fingerprint,
    uniqueness_score,
)


# ── uniqueness_score ─────────────────────────────────────────


class TestUniquenessScore:
    """Tests for uniqueness_score()."""

    def test_returns_report(self):
        text = "The quick brown fox jumps over the lazy dog near the old bridge."
        report = uniqueness_score(text)
        assert isinstance(report, UniquenessReport)
        assert 0 <= report.score <= 100

    def test_high_uniqueness_for_varied_text(self):
        """Text with diverse vocabulary should score high."""
        text = (
            "Mountains rise majestically. Rivers flow softly through valleys. "
            "Birds sing their morning chorus. Flowers bloom in vibrant colors."
        )
        report = uniqueness_score(text)
        assert report.score >= 60

    def test_low_uniqueness_for_repetitive_text(self):
        """Very repetitive text should score lower."""
        text = "The cat sat. The cat sat. The cat sat. The cat sat. The cat sat."
        report = uniqueness_score(text)
        assert report.score < 60

    def test_vocabulary_richness(self):
        """Vocabulary richness should be between 0 and 1."""
        report = uniqueness_score("Word variety helps quality text creation.")
        assert 0 <= report.vocabulary_richness <= 1

    def test_total_and_unique_words(self):
        """Should count total and unique words."""
        report = uniqueness_score("hello hello world world hello")
        assert report.total_words == 5
        assert report.unique_words == 2

    def test_empty_text(self):
        """Empty text should return score=0 or minimal report."""
        report = uniqueness_score("")
        assert isinstance(report, UniquenessReport)

    def test_short_text(self):
        """Short text should work without errors."""
        report = uniqueness_score("Short.")
        assert isinstance(report, UniquenessReport)


# ── compare_texts ────────────────────────────────────────────


class TestCompareTexts:
    """Tests for compare_texts()."""

    def test_identical_texts(self):
        """Identical texts should have similarity ~1.0."""
        report = compare_texts("Hello world", "Hello world")
        assert isinstance(report, SimilarityReport)
        assert report.similarity >= 0.99

    def test_completely_different(self):
        """Completely different texts should have low similarity."""
        report = compare_texts(
            "The quick brown fox jumps over the lazy dog",
            "Machinery operates under extreme conditions"
        )
        assert report.similarity < 0.5

    def test_partially_similar(self):
        """Partially similar texts should have mid similarity."""
        report = compare_texts(
            "The quick brown cat sat on the soft warm mat near the door",
            "The quick brown cat slept on the soft warm rug near the window"
        )
        assert 0.1 < report.similarity < 0.95

    def test_similarity_range(self):
        """Similarity should be between 0 and 1."""
        report = compare_texts("text one", "text two")
        assert 0 <= report.similarity <= 1

    def test_common_ngrams(self):
        """Should report common n-grams count."""
        report = compare_texts("hello world again", "hello world today")
        assert isinstance(report.common_ngrams, int)


# ── text_fingerprint ─────────────────────────────────────────


class TestTextFingerprint:
    """Tests for text_fingerprint()."""

    def test_returns_hex_string(self):
        fp = text_fingerprint("Hello world")
        assert isinstance(fp, str)
        assert len(fp) == 64  # SHA-256 hex

    def test_deterministic(self):
        """Same text should always produce same fingerprint."""
        fp1 = text_fingerprint("Hello world")
        fp2 = text_fingerprint("Hello world")
        assert fp1 == fp2

    def test_different_texts_different_fingerprints(self):
        fp1 = text_fingerprint("Hello world")
        fp2 = text_fingerprint("Goodbye world")
        assert fp1 != fp2

    def test_custom_n(self):
        """Should work with different n values."""
        fp2 = text_fingerprint("Hello world test", n=2)
        fp4 = text_fingerprint("Hello world test", n=4)
        assert isinstance(fp2, str)
        assert isinstance(fp4, str)
