"""Тесты для модуля sentence_readability — читабельность предложений."""

from __future__ import annotations

import pytest

from texthumanize.sentence_readability import (
    SentenceReadabilityReport,
    SentenceScore,
    sentence_readability,
)


class TestSentenceReadability:
    """Tests for sentence_readability()."""

    def test_returns_report(self):
        text = "Short sentence. A much longer and more complex sentence with many words."
        report = sentence_readability(text)
        assert isinstance(report, SentenceReadabilityReport)
        assert len(report.sentences) >= 2

    def test_sentence_scores(self):
        """Each sentence should have a score."""
        report = sentence_readability("Hello world. Testing readability.")
        for sent in report.sentences:
            assert isinstance(sent, SentenceScore)
            assert 0 <= sent.difficulty <= 100
            assert sent.grade in ("easy", "medium", "hard", "very_hard")
            assert sent.word_count >= 1

    def test_avg_difficulty(self):
        """Average difficulty should be computed."""
        report = sentence_readability("First. Second. Third.")
        assert 0 <= report.avg_difficulty <= 100

    def test_hardest_index(self):
        """Should identify the index of the hardest sentence."""
        report = sentence_readability(
            "Short. A significantly more elaborate and intricate sentence structure."
        )
        assert isinstance(report.hardest_index, int)
        assert 0 <= report.hardest_index < len(report.sentences)

    def test_short_easy_sentence(self):
        """Short sentences should be classified as easy."""
        report = sentence_readability("Hello.")
        if report.sentences:
            assert report.sentences[0].grade in ("easy", "medium")

    def test_long_complex_sentence(self):
        """Long sentences with big words should be harder."""
        report = sentence_readability(
            "The implementation of sophisticated algorithmic transformations "
            "necessitates comprehensive understanding of computational complexity "
            "and mathematical underpinnings of theoretical frameworks."
        )
        if report.sentences:
            assert report.sentences[0].difficulty >= 30

    def test_empty_text(self):
        """Empty text should return empty report."""
        report = sentence_readability("")
        assert isinstance(report, SentenceReadabilityReport)
        assert len(report.sentences) == 0

    def test_word_count(self):
        """Word count should be correct."""
        report = sentence_readability("One two three four five.")
        if report.sentences:
            assert report.sentences[0].word_count == 5

    def test_avg_word_length(self):
        """Average word length should be positive."""
        report = sentence_readability("Hello world testing.")
        if report.sentences:
            assert report.sentences[0].avg_word_length > 0

    def test_syllable_count(self):
        """Syllable count should be positive for real text."""
        report = sentence_readability("Understanding complexity requires study.")
        if report.sentences:
            assert report.sentences[0].syllable_count >= 1

    def test_count_by_grade(self):
        """Should count sentences by grade via explicit fields."""
        report = sentence_readability("Easy now. Hard implementation of methodological considerations.")
        total = report.easy_count + report.medium_count + report.hard_count + report.very_hard_count
        assert total == len(report.sentences)
