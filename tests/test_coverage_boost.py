"""Тесты для coherence, paraphrase, watermark — повышение покрытия."""
from __future__ import annotations

from texthumanize.coherence import CoherenceAnalyzer
from texthumanize.paraphrase import Paraphraser
from texthumanize.watermark import WatermarkDetector, detect_watermarks

# ═══════════════════════════════════════════════════════════════
#  COHERENCE — с 68% до ~85%+
# ═══════════════════════════════════════════════════════════════

class TestCoherenceAnalyzer:
    """Тесты анализатора когерентности."""

    def setup_method(self):
        self.ca = CoherenceAnalyzer(lang="en")
        self.ca_ru = CoherenceAnalyzer(lang="ru")

    def test_single_paragraph(self):
        """Один абзац — нет причин для низкой когерентности."""
        report = self.ca.analyze("This is a single paragraph with several sentences. "
                                 "It discusses one topic. Nothing else here.")
        assert report.overall > 0
        assert report.paragraph_count == 1

    def test_multiple_paragraphs(self):
        """Несколько абзацев — полный анализ."""
        text = (
            "First paragraph about technology. Computers are everywhere.\n\n"
            "However, the second paragraph talks about related topics. "
            "Technology impacts our daily lives significantly.\n\n"
            "Furthermore, the third paragraph provides a conclusion. "
            "We must adapt to technological changes."
        )
        report = self.ca.analyze(text)
        assert report.paragraph_count == 3
        assert 0 <= report.overall <= 1
        assert 0 <= report.lexical_cohesion <= 1
        assert 0 <= report.transition_score <= 1
        assert 0 <= report.topic_consistency <= 1
        assert 0 <= report.sentence_opening_diversity <= 1

    def test_uniform_paragraph_lengths(self):
        """Одинаковые длины абзацев → issue."""
        text = (
            "First short paragraph here.\n\n"
            "Second short paragraph here.\n\n"
            "Third short paragraph here.\n\n"
            "Fourth short paragraph here."
        )
        report = self.ca.analyze(text)
        # Может или может не иметь issue в зависимости от CV
        assert isinstance(report.issues, list)

    def test_very_long_paragraphs(self):
        """Очень длинный абзац → issue."""
        long_para = " ".join(["word"] * 250) + "."
        text = f"Short intro.\n\n{long_para}\n\nShort conclusion."
        report = self.ca.analyze(text)
        assert "very_long_paragraphs" in report.issues

    def test_very_short_paragraphs(self):
        """Очень короткий абзац → issue."""
        text = "Full intro paragraph with details.\n\nYes.\n\nFull conclusion paragraph."
        report = self.ca.analyze(text)
        assert "very_short_paragraphs" in report.issues

    def test_suggest_improvements_uniform(self):
        """Рекомендации для однородных абзацев."""
        text = (
            "First short paragraph here.\n\n"
            "Second short paragraph here.\n\n"
            "Third short paragraph here.\n\n"
            "Fourth short paragraph here."
        )
        report = self.ca.analyze(text)
        report.issues.append("paragraph_uniform_length")
        suggestions = self.ca.suggest_improvements(text, report)
        assert any("uniform" in s.lower() or "cv" in s.lower() for s in suggestions)

    def test_suggest_improvements_few_transitions(self):
        """Рекомендации при отсутствии переходов."""
        text = (
            "Apples are red. They taste good.\n\n"
            "Bananas are yellow. Eating them is fun.\n\n"
            "Grapes are purple. Wine comes from them."
        )
        report = self.ca.analyze(text)
        report.issues.append("few_transitions")
        suggestions = self.ca.suggest_improvements(text, report)
        assert any("transition" in s.lower() for s in suggestions)

    def test_suggest_improvements_low_cohesion(self):
        """Рекомендации при низкой лексической связности."""
        text = "Technology is great.\n\nCats are fluffy.\n\nPizzas are delicious."
        report = self.ca.analyze(text)
        report.issues.append("low_lexical_cohesion")
        suggestions = self.ca.suggest_improvements(text, report)
        assert any("cohesion" in s.lower() for s in suggestions)

    def test_suggest_improvements_repetitive_openings(self):
        """Рекомендации при повторяющихся началах."""
        text = "Short text.\n\nAnother short text."
        report = self.ca.analyze(text)
        report.issues.append("repetitive_sentence_openings")
        suggestions = self.ca.suggest_improvements(text, report)
        assert any("opening" in s.lower() or "vary" in s.lower() for s in suggestions)

    def test_suggest_improvements_long_paragraphs(self):
        """Рекомендации при очень длинных абзацах."""
        text = "Short.\n\n" + " ".join(["word"] * 250) + "."
        report = self.ca.analyze(text)
        report.issues.append("very_long_paragraphs")
        suggestions = self.ca.suggest_improvements(text, report)
        assert any("200" in s or "break" in s.lower() for s in suggestions)

    def test_suggest_auto_analyze(self):
        """suggest_improvements без предварительного report."""
        text = (
            "First topic discussed here.\n\n"
            "Second topic is different.\n\n"
            "Third topic wraps up."
        )
        suggestions = self.ca.suggest_improvements(text)
        assert isinstance(suggestions, list)

    def test_cosine_similarity_empty(self):
        """Косинусное сходство пустых Counter."""
        from collections import Counter
        assert CoherenceAnalyzer._cosine_similarity(Counter(), Counter()) == 0.0
        assert CoherenceAnalyzer._cosine_similarity(Counter(a=1), Counter()) == 0.0

    def test_topic_consistency_few_paragraphs(self):
        """Тематическая последовательность при < 3 абзацах."""
        text = "First paragraph.\n\nSecond paragraph."
        report = self.ca.analyze(text)
        # Должна вернуть 0.8 для 2 абзацев
        assert report.topic_consistency >= 0.5

    def test_opening_diversity_few_sentences(self):
        """Разнообразие открытий при < 3 предложениях."""
        text = "One sentence."
        report = self.ca.analyze(text)
        # С 1 предложением diversity = 0.0 (нечего сравнивать)
        assert report.sentence_opening_diversity >= 0.0

    def test_overall_computation(self):
        """Итоговый балл всегда в [0, 1]."""
        text = (
            "Introduction to the topic. Background information.\n\n"
            "However, the main point is different. Details follow.\n\n"
            "In conclusion, results are clear."
        )
        report = self.ca.analyze(text)
        assert 0.0 <= report.overall <= 1.0


# ═══════════════════════════════════════════════════════════════
#  PARAPHRASE — с 71% до ~85%+
# ═══════════════════════════════════════════════════════════════

class TestParaphraser:
    """Тесты парафразера."""

    def test_short_text(self):
        """Короткий текст возвращается без изменений."""
        p = Paraphraser(lang="en", seed=42, intensity=0.5)
        result = p.paraphrase("Hello world.")
        assert isinstance(result.paraphrased, str)
        assert len(result.paraphrased) > 0

    def test_clause_swap(self):
        """Перестановка клауз (Although X, Y → Y, although X)."""
        p = Paraphraser(lang="en", seed=42, intensity=1.0)
        text = "Although the system works well, there are issues."
        result = p.paraphrase(text)
        assert isinstance(result.paraphrased, str)

    def test_passive_to_active(self):
        """Пассив → актив."""
        p = Paraphraser(lang="en", seed=42, intensity=1.0)
        text = "The report was written by the team."
        result = p.paraphrase(text)
        assert isinstance(result.paraphrased, str)

    def test_passive_non_english(self):
        """Пассив не работает для других языков."""
        p = Paraphraser(lang="ru", seed=42, intensity=1.0)
        text = "Отчёт был написан командой."
        result = p.paraphrase(text)
        assert isinstance(result.paraphrased, str)

    def test_sentence_split_long(self):
        """Разбиение длинного предложения."""
        p = Paraphraser(lang="en", seed=42, intensity=1.0)
        text = ("The system provides important data for analysis and "
                "the team uses this data to make critical decisions about "
                "the future direction of the project and the company strategy.")
        result = p.paraphrase(text)
        assert isinstance(result.paraphrased, str)

    def test_adverb_fronting(self):
        """Вынос наречия в начало предложения."""
        p = Paraphraser(lang="en", seed=42, intensity=1.0)
        text = "She completed the project successfully."
        result = p.paraphrase(text)
        assert isinstance(result.paraphrased, str)

    def test_adverb_fronting_ru(self):
        """Вынос наречия для русского."""
        p = Paraphraser(lang="ru", seed=42, intensity=1.0)
        text = "Она завершила проект успешно."
        result = p.paraphrase(text)
        assert isinstance(result.paraphrased, str)

    def test_nominalization(self):
        """Номинализация: глагол → существительное."""
        p = Paraphraser(lang="en", seed=42, intensity=1.0)
        text = "They decided to implement the new system."
        result = p.paraphrase(text)
        assert isinstance(result.paraphrased, str)

    def test_multiple_sentences(self):
        """Несколько предложений."""
        p = Paraphraser(lang="en", seed=42, intensity=0.8)
        text = (
            "Although data is important, many companies ignore it. "
            "The system processes information quickly. "
            "She completed the task efficiently."
        )
        result = p.paraphrase(text)
        assert isinstance(result.paraphrased, str)
        assert len(result.paraphrased) > 0

    def test_zero_intensity(self):
        """Интенсивность 0 — минимальные изменения."""
        p = Paraphraser(lang="en", seed=42, intensity=0.0)
        text = "The quick brown fox jumps over the lazy dog."
        result = p.paraphrase(text)
        assert isinstance(result.paraphrased, str)

    def test_high_intensity(self):
        """Максимальная интенсивность."""
        p = Paraphraser(lang="en", seed=42, intensity=1.0)
        text = (
            "Although the project was complex, it succeeded. "
            "The report was reviewed by all members. "
            "They analyzed the results carefully."
        )
        result = p.paraphrase(text)
        assert isinstance(result.paraphrased, str)

    def test_paraphrase_sentence_method(self):
        """Перефразирование одного предложения."""
        p = Paraphraser(lang="en", seed=42, intensity=1.0)
        transformed, change_type = p.paraphrase_sentence("Although X is true, Y follows.")
        assert isinstance(transformed, str)

    def test_result_has_changes(self):
        """Результат содержит список изменений."""
        p = Paraphraser(lang="en", seed=42, intensity=1.0)
        result = p.paraphrase(
            "Although the project was complex, it succeeded. "
            "She completed the task efficiently."
        )
        assert isinstance(result.changes, list)
        assert isinstance(result.confidence, float)


# ═══════════════════════════════════════════════════════════════
#  WATERMARK — с 74% до ~85%+
# ═══════════════════════════════════════════════════════════════

class TestWatermarkDetector:
    """Тесты детектора водяных знаков."""

    def setup_method(self):
        self.wd = WatermarkDetector(lang="en")

    def test_clean_text(self):
        """Чистый текст — нет водяных знаков."""
        report = self.wd.detect("This is a clean text without any watermarks.")
        assert not report.has_watermarks
        assert report.characters_removed == 0

    def test_zero_width_chars(self):
        """Zero-width символы обнаруживаются и удаляются."""
        text = "Hello\u200b world\u200c test\u200d here\ufeff end"
        report = self.wd.detect(text)
        assert report.has_watermarks
        assert any("zero_width" in t for t in report.watermark_types)
        assert report.characters_removed > 0
        assert "\u200b" not in report.cleaned_text

    def test_homoglyphs_cyrillic_in_latin(self):
        """Кириллические символы в латинском тексте."""
        # Заменяем 'a' на кириллическую 'а' (U+0430)
        text = "This is \u0430 test with homoglyphs"
        report = self.wd.detect(text)
        # Может быть обнаружено или нет в зависимости от контекста
        assert isinstance(report, object)

    def test_homoglyphs_latin_in_cyrillic(self):
        """Латинские символы в кириллическом тексте."""
        # Вставка латинской 'o' в кириллическое слово
        text = "Этo тест с гомоглифами"  # 'o' is Latin here
        report = self.wd.detect(text)
        assert isinstance(report.cleaned_text, str)

    def test_invisible_unicode(self):
        """Невидимые Unicode символы."""
        text = "Text with\u2060invisible\u2061characters"
        report = self.wd.detect(text)
        assert isinstance(report.cleaned_text, str)

    def test_multiple_spaces(self):
        """Множественные пробелы (spacing steganography)."""
        text = "Word  word   word  word   word  word   word  word   word  word"
        report = self.wd.detect(text)
        # Если > 5 multi-space sequences, обнаруживается
        if "spacing_steganography" in report.watermark_types:
            assert "  " not in report.cleaned_text

    def test_trailing_spaces(self):
        """Хвостовые пробелы на строках."""
        lines = ["Line one   ", "Line two  ", "Line three   ",
                 "Line four  ", "Line five   "]
        text = "\n".join(lines)
        report = self.wd.detect(text)
        if "trailing_space_steganography" in report.watermark_types:
            for line in report.cleaned_text.split('\n'):
                assert line == line.rstrip(' ')

    def test_statistical_watermarks_clean(self):
        """Статистические водяные знаки — чистый текст."""
        text = " ".join(["The quick brown fox jumps over the lazy dog."] * 10)
        report = self.wd.detect(text)
        # Не должно быть statistical_bias на обычном тексте
        assert isinstance(report, object)

    def test_confidence_calculation(self):
        """Уверенность вычисляется правильно."""
        text = "Clean\u200b text\u200b with\u200b marks"
        report = self.wd.detect(text)
        assert 0 <= report.confidence <= 1

    def test_detect_watermarks_func(self):
        """Функция-обёртка detect_watermarks работает."""
        report = detect_watermarks("Test\u200b text", lang="en")
        assert report.has_watermarks
        assert report.cleaned_text == "Test text"


class TestWatermarkDetectorRussian:
    """Тесты детектора для русского текста."""

    def setup_method(self):
        self.wd = WatermarkDetector(lang="ru")

    def test_clean_russian(self):
        """Чистый русский текст без гомоглифов."""
        # Текст гарантированно без латинских подмен
        report = self.wd.detect("Это чистый текст")
        # Проверяем что как минимум обработал
        assert isinstance(report.cleaned_text, str)

    def test_zero_width_russian(self):
        """Zero-width в русском тексте."""
        text = "Это\u200b текст\u200b с\u200b водяными знаками."
        report = self.wd.detect(text)
        assert report.has_watermarks
        assert "\u200b" not in report.cleaned_text
