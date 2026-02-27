"""Тесты для обнаружения водяных знаков (watermark.py)."""

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
