"""Тесты для модуля visualize."""
from __future__ import annotations

import pytest

from texthumanize.visualize import (
    TextVisualizer,
    VisualizationResult,
    perplexity_chart,
    detection_heatmap,
    sentence_length_chart,
    lexical_diversity_chart,
    entropy_chart,
    comparison_chart,
    dashboard,
)


_SAMPLE = (
    "Artificial intelligence transforms industries. "
    "These systems analyze data quickly. "
    "Furthermore, they can identify patterns. "
    "The technology continues to evolve rapidly."
)

_SAMPLE_RU = (
    "Искусственный интеллект трансформирует отрасли. "
    "Эти системы анализируют данные быстро. "
    "Кроме того, они могут идентифицировать паттерны."
)


class TestPerplexityChart:
    def test_returns_result(self):
        r = perplexity_chart(_SAMPLE, lang="en")
        assert isinstance(r, VisualizationResult)
        assert r.chart
        assert "ПЕРПЛЕКСИЯ" in r.chart

    def test_data_keys(self):
        r = perplexity_chart(_SAMPLE, lang="en")
        assert "per_sentence_ppl" in r.data
        assert "mean" in r.data
        assert "cv" in r.data

    def test_empty_text(self):
        r = perplexity_chart("", lang="en")
        assert "пустой" in r.chart

    def test_russian(self):
        r = perplexity_chart(_SAMPLE_RU, lang="ru")
        assert r.data.get("sentence_count", 0) >= 2


class TestDetectionHeatmap:
    def test_returns_result(self):
        r = detection_heatmap(_SAMPLE, lang="en")
        assert isinstance(r, VisualizationResult)
        assert "ТЕПЛОВАЯ КАРТА" in r.chart

    def test_data_keys(self):
        r = detection_heatmap(_SAMPLE, lang="en")
        assert "scores" in r.data
        assert "mean_score" in r.data
        assert len(r.data["scores"]) >= 3

    def test_empty_text(self):
        r = detection_heatmap("", lang="en")
        assert "пустой" in r.chart


class TestSentenceLengthChart:
    def test_returns_result(self):
        r = sentence_length_chart(_SAMPLE)
        assert isinstance(r, VisualizationResult)
        assert "ДЛИНЫ" in r.chart

    def test_data_keys(self):
        r = sentence_length_chart(_SAMPLE)
        assert "lengths" in r.data
        assert "cv" in r.data
        assert len(r.data["lengths"]) >= 3


class TestLexicalDiversityChart:
    def test_short_text(self):
        r = lexical_diversity_chart("hello world test", window_size=50)
        assert "короткий" in r.chart.lower() or "TTR" in r.chart

    def test_long_text(self):
        long = " ".join(["word" + str(i) for i in range(200)])
        r = lexical_diversity_chart(long, window_size=30)
        assert "ЛЕКСИЧЕСКОЕ" in r.chart
        assert "mttr_values" in r.data


class TestEntropyChart:
    def test_short_text(self):
        r = entropy_chart("hello", chunk_size=100)
        assert "Энтропия" in r.chart

    def test_long_text(self):
        long = "This is a test. " * 30
        r = entropy_chart(long, chunk_size=50)
        assert "ЭНТРОПИЯ" in r.chart
        assert "entropies" in r.data


class TestComparisonChart:
    def test_comparison(self):
        before = "This system utilizes advanced technology. Furthermore, it demonstrates efficiency."
        after = "This setup uses cool tech. Also, it shows it works."
        r = comparison_chart(before, after, lang="en")
        assert "СРАВНЕНИЕ" in r.chart
        assert "ДО" in r.chart and "ПОСЛЕ" in r.chart


class TestDashboard:
    def test_dashboard(self):
        r = dashboard(_SAMPLE, lang="en")
        assert "ДАШБОРД" in r.chart
        assert "word_count" in r.data
        assert r.data["sentence_count"] >= 3

    def test_dashboard_russian(self):
        r = dashboard(_SAMPLE_RU, lang="ru")
        assert "ДАШБОРД" in r.chart


class TestTextVisualizer:
    def test_all_methods(self):
        viz = TextVisualizer(lang="en")
        assert viz.perplexity(_SAMPLE).chart
        assert viz.detection(_SAMPLE).chart
        assert viz.lengths(_SAMPLE).chart
        assert viz.dashboard(_SAMPLE).chart

    def test_compare(self):
        viz = TextVisualizer(lang="en")
        r = viz.compare(
            "The system utilizes data.",
            "The setup uses data."
        )
        assert "СРАВНЕНИЕ" in r.chart

    def test_full_report(self):
        viz = TextVisualizer(lang="en")
        long = " ".join([
            "AI is powerful.", "Data drives decisions.",
            "The model learns fast.", "We need more tests.",
        ] * 10)
        report = viz.full_report(long)
        assert "ДАШБОРД" in report
        assert "ПЕРПЛЕКСИЯ" in report

    def test_lazy_import(self):
        """TextVisualizer должен быть доступен через __init__."""
        from texthumanize import TextVisualizer as TV
        assert TV is TextVisualizer
