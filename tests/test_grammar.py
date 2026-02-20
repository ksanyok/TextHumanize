"""Тесты для модуля grammar — проверка и исправление грамматики."""

from __future__ import annotations

import pytest

from texthumanize.grammar import (
    GrammarIssue,
    GrammarReport,
    check_grammar,
    fix_grammar,
)


# ── check_grammar ────────────────────────────────────────────


class TestCheckGrammar:
    """Tests for check_grammar()."""

    def test_clean_text_high_score(self):
        """Clean text should score high."""
        report = check_grammar("This is a perfectly normal sentence.", lang="en")
        assert isinstance(report, GrammarReport)
        assert report.score >= 80

    def test_double_words_detected(self):
        """Repeated adjacent words should be flagged."""
        report = check_grammar("He went to the the store.", lang="en")
        assert report.total > 0
        assert any("double" in i.rule.lower() or "dupl" in i.rule.lower() or "repeat" in i.rule.lower()
                    for i in report.issues)

    def test_missing_capital_detected(self):
        """Sentence starting with lowercase should be flagged."""
        report = check_grammar("hello world. this is a test.", lang="en")
        issues = [i for i in report.issues if "capital" in i.rule.lower() or "upper" in i.rule.lower()]
        assert len(issues) >= 1

    def test_double_punctuation(self):
        """Double periods/commas should be flagged."""
        report = check_grammar("Something happened.. Then more.", lang="en")
        assert any("punct" in i.rule.lower() or "double" in i.rule.lower()
                    for i in report.issues)

    def test_empty_text(self):
        """Empty text should return perfect score."""
        report = check_grammar("", lang="en")
        assert report.score == 100
        assert report.errors == 0

    def test_russian_text(self):
        """Russian text should work."""
        report = check_grammar("Это нормальное предложение.", lang="ru")
        assert isinstance(report, GrammarReport)
        assert report.score >= 70

    def test_german_text(self):
        """German text should work."""
        report = check_grammar("Das ist ein normaler Satz.", lang="de")
        assert isinstance(report, GrammarReport)

    def test_report_properties(self):
        """Report should expose total/errors/warnings."""
        report = check_grammar("Some text.", lang="en")
        assert isinstance(report.total, int)
        assert isinstance(report.errors, int)
        assert isinstance(report.warnings, int)
        assert report.total == report.errors + report.warnings

    def test_issue_fields(self):
        """GrammarIssue should have all required fields."""
        report = check_grammar("He went to the the store.", lang="en")
        if report.issues:
            issue = report.issues[0]
            assert isinstance(issue, GrammarIssue)
            assert hasattr(issue, "rule")
            assert hasattr(issue, "message")
            assert hasattr(issue, "offset")
            assert hasattr(issue, "length")
            assert hasattr(issue, "suggestion")
            assert hasattr(issue, "severity")

    @pytest.mark.parametrize("lang", ["en", "ru", "uk", "de", "fr", "es", "it", "pl", "pt"])
    def test_all_languages(self, lang: str):
        """check_grammar should work for all supported languages."""
        report = check_grammar("Test text. Another sentence.", lang=lang)
        assert isinstance(report, GrammarReport)
        assert 0 <= report.score <= 100


# ── fix_grammar ──────────────────────────────────────────────


class TestFixGrammar:
    """Tests for fix_grammar()."""

    def test_fixes_double_words(self):
        """Should remove doubled words."""
        result = fix_grammar("He went to the the store.", lang="en")
        assert "the the" not in result

    def test_preserves_good_text(self):
        """Clean text should remain unchanged."""
        original = "This is perfectly fine."
        result = fix_grammar(original, lang="en")
        assert result == original

    def test_returns_string(self):
        """Should always return a string."""
        result = fix_grammar("Some text", lang="en")
        assert isinstance(result, str)

    def test_empty_text(self):
        """Empty text should return empty."""
        assert fix_grammar("", lang="en") == ""

    @pytest.mark.parametrize("lang", ["en", "ru", "de", "fr", "es"])
    def test_multiple_languages(self, lang: str):
        """fix_grammar should work for multiple languages."""
        result = fix_grammar("Some text here.", lang=lang)
        assert isinstance(result, str)
