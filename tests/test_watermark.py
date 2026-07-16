"""Тесты для обнаружения водяных знаков (watermark.py)."""

import pytest

from texthumanize.core import watermark_report
from texthumanize.watermark import (
    WatermarkDetector,
    WatermarkReport,
    clean_watermarks,
    detect_watermarks,
)

CLEAN_TEXT = "This is a perfectly normal text without any hidden characters."

# Zero-width character insertion
ZW_TEXT = "Hello\u200bWorld\u200cTest\u200dHere\ufeffMore"

# Homoglyph substitution (Cyrillic 'а' instead of Latin 'a')
HOMOGLYPH_TEXT = "This is \u0430 test with \u0441yrilli\u0441 letters"


class TestWatermarkDetector:
    """Тесты для WatermarkDetector."""

    def test_clean_text_no_watermarks(self):
        detector = WatermarkDetector(lang="en")
        report = detector.detect(CLEAN_TEXT)
        assert isinstance(report, WatermarkReport)
        assert not report.has_watermarks

    def test_zero_width_detection(self):
        detector = WatermarkDetector(lang="en")
        report = detector.detect(ZW_TEXT)
        assert report.has_watermarks
        assert "zero_width_characters" in report.watermark_types
        assert report.zero_width_count > 0

    def test_zero_width_cleaning(self):
        detector = WatermarkDetector(lang="en")
        report = detector.detect(ZW_TEXT)
        # Очищенный текст не должен содержать zero-width символов
        assert "\u200b" not in report.cleaned_text
        assert "\u200c" not in report.cleaned_text
        assert "\u200d" not in report.cleaned_text
        assert "\ufeff" not in report.cleaned_text

    def test_homoglyph_detection(self):
        detector = WatermarkDetector(lang="en")
        report = detector.detect(HOMOGLYPH_TEXT)
        assert report.has_watermarks
        assert any("homoglyph" in t for t in report.watermark_types)

    def test_empty_text(self):
        detector = WatermarkDetector(lang="en")
        report = detector.detect("")
        assert isinstance(report, WatermarkReport)
        assert not report.has_watermarks

    def test_confidence_range(self):
        detector = WatermarkDetector(lang="en")
        report = detector.detect(ZW_TEXT)
        assert 0.0 <= report.confidence <= 1.0

    def test_characters_removed_count(self):
        detector = WatermarkDetector(lang="en")
        report = detector.detect(ZW_TEXT)
        assert report.characters_removed > 0

    def test_details_populated(self):
        detector = WatermarkDetector(lang="en")
        report = detector.detect(ZW_TEXT)
        assert isinstance(report.details, list)
        assert len(report.details) > 0


class TestModuleFunctions:
    """Тесты для module-level функций."""

    def test_detect_watermarks(self):
        report = detect_watermarks(ZW_TEXT, lang="en")
        assert report.has_watermarks

    def test_clean_watermarks(self):
        cleaned = clean_watermarks(ZW_TEXT, lang="en")
        assert isinstance(cleaned, str)
        assert "\u200b" not in cleaned

    def test_clean_watermarks_clean_text(self):
        """Чистый текст не должен меняться."""
        cleaned = clean_watermarks(CLEAN_TEXT, lang="en")
        assert cleaned == CLEAN_TEXT

    def test_multiple_watermark_types(self):
        """Текст с несколькими типами водяных знаков."""
        text = "H\u200bello \u0430nd test"  # zero-width + homoglyph
        report = detect_watermarks(text, lang="en")
        assert report.has_watermarks
        assert len(report.watermark_types) >= 1

    def test_real_unicode_cases_in_report(self):
        """Report catches soft hyphen, fullwidth, math and mixed-script cases."""
        text = "So\u00adft \uff41lpha \u2202ata with \u0441yrillic mark"
        report = watermark_report(text, lang="en")
        kinds = {span["kind"] for span in report["highlighted_spans"]}
        assert "zero_width_character" in kinds
        assert "homoglyph_substitution" in kinds
        assert report["clean_safe"]["changed"] is True


class TestStatisticalWatermarkCalibration:
    """Regression for the statistical false-positive fix and long-text cap."""

    def test_clean_prose_not_flagged(self) -> None:
        import texthumanize as th
        clean = (
            "The team reviewed the quarterly report on Monday and agreed on the "
            "next steps before lunch, then shared a short summary with everyone "
            "in the office."
        )
        report = th.watermark_report(clean, lang="en", include_statistical=True)
        # A marginal z (1.5-2.0) must not flip has_watermarks on clean prose.
        assert report["has_watermarks"] is False

    @pytest.mark.perf
    def test_long_text_is_bounded(self) -> None:
        import time

        import texthumanize as th
        sentences = [
            "The team reviewed the report on Monday.",
            "She fixed the bug before lunch and shipped it.",
            "Our revenue grew last quarter across regions.",
            "The cache updates overnight so check tomorrow.",
        ]
        big = " ".join(sentences[i % len(sentences)] for i in range(2600))
        assert len(big) > 90_000
        started = time.perf_counter()
        th.watermark_report(big, lang="en", include_statistical=True)
        # Token cap + diff short-circuit keep this well under the old ~44s.
        assert time.perf_counter() - started < 10.0
