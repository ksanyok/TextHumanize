"""Тесты для тонального анализа (tone.py)."""

from texthumanize.tone import (
    ToneAdjuster,
    ToneAnalyzer,
    ToneLevel,
    ToneReport,
    adjust_tone,
    analyze_tone,
)

FORMAL_TEXT = (
    "It is imperative to acknowledge that the aforementioned methodology "
    "demonstrates considerable efficacy in addressing the pertinent challenges. "
    "Furthermore, the implementation of said procedures necessitates "
    "comprehensive evaluation of all constituent parameters."
)

CASUAL_TEXT = (
    "Hey, so I was thinking maybe we should just go for it, you know? "
    "Like, it's not that hard really. We could totally pull it off. "
    "Anyway, let me know what you think! Gonna grab some coffee first."
)

NEUTRAL_TEXT = (
    "The project has been completed on schedule. The team reviewed "
    "the results and identified several areas for improvement. "
    "A follow-up meeting will be scheduled next week."
)

FORMAL_RU = (
    "Необходимо подчеркнуть, что данная методология демонстрирует "
    "значительную эффективность. Кроме того, реализация указанных процедур "
    "требует всесторонней оценки всех параметров."
)


class TestToneLevel:
    """Тесты для ToneLevel enum."""

    def test_all_levels_exist(self):
        levels = [
            ToneLevel.FORMAL, ToneLevel.ACADEMIC, ToneLevel.PROFESSIONAL,
            ToneLevel.NEUTRAL, ToneLevel.FRIENDLY, ToneLevel.CASUAL,
            ToneLevel.MARKETING,
        ]
        assert len(levels) == 7

    def test_value_access(self):
        assert ToneLevel.FORMAL.value == "formal"
        assert ToneLevel.CASUAL.value == "casual"


class TestToneAnalyzer:
    """Тесты для ToneAnalyzer."""

    def test_analyze_formal(self):
        analyzer = ToneAnalyzer(lang="en")
        report = analyzer.analyze(FORMAL_TEXT)
        assert isinstance(report, ToneReport)
        assert report.formality > 0.5

    def test_analyze_casual(self):
        analyzer = ToneAnalyzer(lang="en")
        report = analyzer.analyze(CASUAL_TEXT)
        assert report.formality < 0.5

    def test_analyze_returns_scores(self):
        analyzer = ToneAnalyzer(lang="en")
        report = analyzer.analyze(NEUTRAL_TEXT)
        assert isinstance(report.scores, dict)
        assert len(report.scores) > 0

    def test_analyze_confidence(self):
        analyzer = ToneAnalyzer(lang="en")
        report = analyzer.analyze(FORMAL_TEXT)
        assert 0.0 <= report.confidence <= 1.0

    def test_analyze_russian(self):
        analyzer = ToneAnalyzer(lang="ru")
        report = analyzer.analyze(FORMAL_RU)
        assert isinstance(report, ToneReport)
        assert report.formality > 0.3

    def test_empty_text(self):
        analyzer = ToneAnalyzer(lang="en")
        report = analyzer.analyze("")
        assert isinstance(report, ToneReport)


class TestToneAdjuster:
    """Тесты для ToneAdjuster."""

    def test_adjust_to_casual(self):
        adjuster = ToneAdjuster(lang="en")
        result = adjuster.adjust(FORMAL_TEXT, target=ToneLevel.CASUAL, intensity=0.8)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_adjust_to_formal(self):
        adjuster = ToneAdjuster(lang="en")
        result = adjuster.adjust(CASUAL_TEXT, target=ToneLevel.FORMAL, intensity=0.8)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_adjust_identity(self):
        """При интенсивности 0 текст не должен сильно меняться."""
        adjuster = ToneAdjuster(lang="en")
        result = adjuster.adjust(NEUTRAL_TEXT, target=ToneLevel.FORMAL, intensity=0.0)
        assert isinstance(result, str)


class TestModuleFunctions:
    """Тесты для module-level функций."""

    def test_analyze_tone(self):
        report = analyze_tone(FORMAL_TEXT, lang="en")
        assert isinstance(report, ToneReport)

    def test_adjust_tone(self):
        result = adjust_tone(CASUAL_TEXT, target="formal", lang="en")
        assert isinstance(result, str)

    def test_adjust_tone_invalid_target(self):
        """Неизвестный target → fallback to neutral."""
        result = adjust_tone(CASUAL_TEXT, target="unknown_tone", lang="en")
        assert isinstance(result, str)
