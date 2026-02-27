"""Тесты основного API."""

import pytest

from texthumanize import AnalysisReport, HumanizeResult, analyze, explain, humanize


class TestHumanize:
    """Тесты функции humanize()."""

    def test_basic_russian(self):
        """Базовая обработка русского текста."""
        text = (
            "Данный текст является примером использования библиотеки. "
            "Однако необходимо отметить, что осуществление обработки "
            "текста представляет собой сложный процесс."
        )
        result = humanize(text, lang="ru", profile="web", intensity=80, seed=42)
        assert isinstance(result, HumanizeResult)
        assert result.text != text  # Текст должен измениться
        assert result.lang == "ru"
        assert result.profile == "web"
        assert len(result.text) > 0

    def test_basic_ukrainian(self):
        """Базовая обработка украинского текста."""
        text = (
            "Даний текст є прикладом використання бібліотеки. "
            "Однак необхідно зазначити, що здійснення обробки "
            "тексту являє собою складний процес."
        )
        result = humanize(text, lang="uk", profile="web", intensity=80, seed=42)
        assert isinstance(result, HumanizeResult)
        assert result.lang == "uk"

    def test_basic_english(self):
        """Базовая обработка английского текста."""
        text = (
            "This text utilizes a comprehensive methodology for the "
            "implementation of text processing. Furthermore, it is "
            "important to note that the facilitation of this process "
            "necessitates considerable effort."
        )
        result = humanize(text, lang="en", profile="web", intensity=80, seed=42)
        assert isinstance(result, HumanizeResult)
        assert result.lang == "en"

    def test_auto_detect_russian(self):
        """Автоматическое определение русского языка."""
        text = "Этот текст написан на русском языке и содержит много слов."
        result = humanize(text, lang="auto")
        assert result.lang == "ru"

    def test_auto_detect_ukrainian(self):
        """Автоматическое определение украинского языка."""
        text = "Цей текст написаний українською мовою і містить багато слів."
        result = humanize(text, lang="auto")
        assert result.lang == "uk"

    def test_auto_detect_english(self):
        """Автоматическое определение английского языка."""
        text = "This text is written in English and contains many words."
        result = humanize(text, lang="auto")
        assert result.lang == "en"

    def test_empty_text(self):
        """Пустой текст не вызывает ошибку."""
        result = humanize("")
        assert result.text == ""

    def test_short_text(self):
        """Короткий текст обрабатывается без ошибок."""
        result = humanize("Привет.")
        assert len(result.text) > 0

    def test_intensity_zero(self):
        """Интенсивность 0 — минимум изменений."""
        text = "Данный текст является примером. Однако он содержит канцеляризмы."
        result = humanize(text, lang="ru", intensity=0, seed=42)
        # При нулевой интенсивности типографика всё равно нормализуется,
        # но лексические замены минимальны
        assert isinstance(result, HumanizeResult)

    def test_intensity_max(self):
        """Интенсивность 100 — максимум изменений."""
        text = (
            "Данный текст является примером. Однако необходимо "
            "отметить, что осуществление обработки является сложным."
        )
        result = humanize(text, lang="ru", intensity=100, seed=42)
        assert isinstance(result, HumanizeResult)

    def test_profiles(self):
        """Все профили работают без ошибок."""
        text = "Данный текст является примером обработки текста."
        for profile in ("chat", "web", "seo", "docs", "formal"):
            result = humanize(text, lang="ru", profile=profile, seed=42)
            assert isinstance(result, HumanizeResult), f"Ошибка в профиле {profile}"

    def test_invalid_profile(self):
        """Невалидный профиль вызывает ошибку."""
        with pytest.raises(ValueError):
            humanize("текст", profile="invalid")

    def test_seed_reproducibility(self):
        """Один и тот же seed даёт одинаковый результат."""
        text = (
            "Данный текст является примером. Однако необходимо "
            "осуществить обработку данного текста."
        )
        result1 = humanize(text, lang="ru", seed=42)
        result2 = humanize(text, lang="ru", seed=42)
        assert result1.text == result2.text

    def test_change_ratio(self):
        """change_ratio вычисляется корректно."""
        text = "Слово один два три четыре."
        result = humanize(text, lang="ru", seed=42)
        assert isinstance(result.change_ratio, float)
        assert 0.0 <= result.change_ratio <= 1.0

    def test_metrics(self):
        """Метрики заполняются."""
        text = (
            "Данный текст является примером. Однако необходимо "
            "отметить важность данной обработки."
        )
        result = humanize(text, lang="ru", seed=42)
        assert "artificiality_score" in result.metrics_before
        assert "artificiality_score" in result.metrics_after

    def test_keep_keywords(self):
        """Ключевые слова сохраняются."""
        text = "Продукт RankBot AI осуществляет обработку текста."
        result = humanize(
            text,
            lang="ru",
            constraints={"keep_keywords": ["RankBot AI"]},
            seed=42,
        )
        assert "RankBot AI" in result.text

    def test_brand_terms(self):
        """Брендовые термины защищены."""
        text = "Продукт Promopilot осуществляет обработку текста."
        result = humanize(
            text,
            lang="ru",
            preserve={"brand_terms": ["Promopilot"]},
            seed=42,
        )
        assert "Promopilot" in result.text


class TestAnalyze:
    """Тесты функции analyze()."""

    def test_basic_analysis(self):
        """Базовый анализ текста."""
        text = (
            "Данный текст является примером. Однако необходимо отметить "
            "важность обработки. Таким образом, данный подход является оптимальным."
        )
        report = analyze(text, lang="ru")
        assert isinstance(report, AnalysisReport)
        assert report.total_words > 0
        assert report.total_sentences > 0
        assert report.avg_sentence_length > 0
        assert 0 <= report.artificiality_score <= 100

    def test_bureaucratic_detection(self):
        """Обнаружение канцеляризмов."""
        text = (
            "Данный документ осуществляет описание процесса функционирования "
            "посредством предоставления соответствующей информации."
        )
        report = analyze(text, lang="ru")
        assert report.bureaucratic_ratio > 0
        assert len(report.details.get("found_bureaucratic", [])) > 0

    def test_connector_detection(self):
        """Обнаружение ИИ-связок."""
        text = (
            "Однако это важно. Тем не менее стоит учесть. "
            "Кроме того есть нюанс. Таким образом всё ясно."
        )
        report = analyze(text, lang="ru")
        assert report.connector_ratio > 0
        assert len(report.details.get("found_connectors", [])) > 0

    def test_typography_detection(self):
        """Обнаружение «идеальной» типографики."""
        text = "Текст — с длинным тире, «кавычками» и многоточием…"
        report = analyze(text, lang="ru")
        assert report.typography_score > 0
        assert len(report.details.get("typography_issues", [])) > 0

    def test_empty_text(self):
        """Анализ пустого текста."""
        report = analyze("")
        assert report.artificiality_score == 0


class TestExplain:
    """Тесты функции explain()."""

    def test_explain_output(self):
        """explain() возвращает читаемый отчёт."""
        text = "Данный текст является примером обработки."
        result = humanize(text, lang="ru", seed=42)
        report = explain(result)
        assert isinstance(report, str)
        assert "TextHumanize" in report
        assert "Язык" in report

    def test_explain_with_changes(self):
        """explain() показывает изменения."""
        text = (
            "Данный текст является примером. Однако необходимо "
            "осуществить обработку данного текста."
        )
        result = humanize(text, lang="ru", intensity=80, seed=42)
        report = explain(result)
        assert "Метрики" in report or "Изменения" in report or "Изменений нет" in report
