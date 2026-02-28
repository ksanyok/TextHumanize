"""Анализатор текста — метрики «искусственности»."""

from __future__ import annotations

import logging
import re
from collections import Counter

from texthumanize.lang import get_lang_pack
from texthumanize.perplexity import PerplexityEstimator
from texthumanize.sentence_split import split_sentences
from texthumanize.utils import AnalysisReport

logger = logging.getLogger(__name__)

class TextAnalyzer:
    """Анализирует текст и вычисляет метрики «искусственности».

    Метрики:
    - Средняя длина предложения
    - Дисперсия длины предложений (низкая = ИИ)
    - Доля канцеляризмов
    - Частота ИИ-связок
    - Повторяемость биграмм/триграмм
    - Типографика (идеальная = ИИ)
    - Общий балл «искусственности» (0-100)
    """

    def __init__(self, lang: str = "ru"):
        self.lang = lang
        self.lang_pack = get_lang_pack(lang)

    def analyze(self, text: str) -> AnalysisReport:
        """Анализировать текст.

        Args:
            text: Текст для анализа.

        Returns:
            AnalysisReport с метриками.
        """
        report = AnalysisReport(lang=self.lang)

        if not text or len(text.strip()) < 10:
            return report

        report.total_chars = len(text)
        words = text.split()
        report.total_words = len(words)

        # Разбиваем на предложения
        sentences = self._split_sentences(text)
        report.total_sentences = len(sentences)

        if not sentences:
            return report

        # 1. Длина предложений
        sentence_lengths = [len(s.split()) for s in sentences]
        report.avg_sentence_length = (
            sum(sentence_lengths) / len(sentence_lengths)
        )

        if len(sentence_lengths) > 1:
            mean = report.avg_sentence_length
            variance = sum((sl - mean) ** 2 for sl in sentence_lengths) / len(sentence_lengths)
            report.sentence_length_variance = variance
        else:
            report.sentence_length_variance = 0.0

        # 2. Канцеляризмы
        report.bureaucratic_ratio = self._calc_bureaucratic_ratio(text, words)

        # 3. ИИ-связки
        report.connector_ratio = self._calc_connector_ratio(text, sentences)

        # 4. Повторяемость
        report.repetition_score = self._calc_repetition_score(text, words)

        # 5. Типографика
        report.typography_score = self._calc_typography_score(text)

        # 6. Burstiness (вариативность длины предложений)
        report.burstiness_score = self._calc_burstiness_score(sentence_lengths)

        # 7. Readability metrics
        avg_word_len = (
            sum(len(w) for w in words) / len(words) if words else 0.0
        )
        report.avg_word_length = avg_word_len
        avg_syllables = self._calc_avg_syllables(words)
        report.avg_syllables_per_word = avg_syllables
        report.flesch_kincaid_grade = self._calc_flesch_kincaid(
            len(sentences), len(words), avg_syllables,
        )
        report.coleman_liau_index = self._calc_coleman_liau(
            text, words, sentences,
        )

        # 8. Общий балл искусственности
        report.artificiality_score = self._calc_artificiality_score(report)

        # 9. N-gram перплексия (предсказуемость текста)
        perplexity_est = PerplexityEstimator()
        perp_report = perplexity_est.analyze(text)
        report.predictability_score = perp_report.predictability_score
        report.char_perplexity = perp_report.char_perplexity
        report.vocabulary_richness = perp_report.vocabulary_richness

        # Детали
        report.details = {
            "sentence_lengths": sentence_lengths,
            "found_bureaucratic": self._find_bureaucratic_words(text),
            "found_connectors": self._find_ai_connectors(text),
            "typography_issues": self._find_typography_issues(text),
            "burstiness_cv": self._calc_burstiness_cv(sentence_lengths),
        }

        return report

    def _split_sentences(self, text: str) -> list[str]:
        """Разбить текст на предложения."""
        sentences = split_sentences(text, self.lang)
        return [s.strip() for s in sentences if s.strip() and len(s.split()) > 1]

    def _calc_bureaucratic_ratio(self, text: str, words: list[str]) -> float:
        """Вычислить долю канцеляризмов."""
        if not words:
            return 0.0

        bureaucratic = self.lang_pack.get("bureaucratic", {})
        phrases = self.lang_pack.get("bureaucratic_phrases", {})
        text_lower = text.lower()

        hits = 0

        # Фразовые канцеляризмы
        for phrase in phrases:
            count = text_lower.count(phrase.lower())
            hits += count * len(phrase.split())

        # Однословные канцеляризмы
        for word in bureaucratic:
            pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
            matches = pattern.findall(text)
            hits += len(matches)

        return min(hits / len(words), 1.0) if words else 0.0

    def _calc_connector_ratio(self, text: str, sentences: list[str]) -> float:
        """Вычислить долю ИИ-связок."""
        if not sentences:
            return 0.0

        connectors = self.lang_pack.get("ai_connectors", {})
        hits = 0

        for connector in connectors:
            pattern = re.compile(r'\b' + re.escape(connector) + r'\b', re.IGNORECASE)
            hits += len(pattern.findall(text))

        return min(hits / len(sentences), 1.0)

    def _calc_repetition_score(self, text: str, words: list[str]) -> float:
        """Вычислить показатель повторяемости."""
        if len(words) < 10:
            return 0.0

        stop_words = self.lang_pack.get("stop_words", set())

        # Считаем повторение контентных слов
        content_words = [
            w.lower().strip('.,;:!?\"\'()[]{}')
            for w in words
            if w.lower().strip('.,;:!?\"\'()[]{}') not in stop_words
            and len(w) > 2
        ]

        if not content_words:
            return 0.0

        word_counts = Counter(content_words)
        total = len(content_words)
        unique = len(word_counts)

        # Lexical diversity (обратная метрика)
        diversity = unique / total if total > 0 else 1.0

        # Биграммы
        bigrams = []
        for i in range(len(content_words) - 1):
            bigrams.append((content_words[i], content_words[i + 1]))

        bigram_counts = Counter(bigrams)
        repeated_bigrams = sum(1 for c in bigram_counts.values() if c > 1)
        bigram_ratio = repeated_bigrams / len(bigrams) if bigrams else 0.0

        # Чем ниже diversity и больше повторов — тем выше score
        score = (1.0 - diversity) * 0.5 + bigram_ratio * 0.5
        return min(score, 1.0)

    def _calc_typography_score(self, text: str) -> float:
        """Вычислить «идеальность» типографики (ИИ = идеальная)."""
        if not text:
            return 0.0

        score = 0.0
        total_checks = 6

        # Длинные тире
        if '—' in text:
            score += 1.0

        # Типографские кавычки
        if '«' in text or '»' in text or '"' in text or '"' in text:
            score += 1.0

        # Типографское многоточие
        if '…' in text:
            score += 1.0

        # Неразрывные пробелы
        if '\u00A0' in text or '\u202F' in text:
            score += 1.0

        # Избыток точек с запятой
        semicolons = text.count(';')
        sentences = len(re.findall(r'[.!?]', text))
        if sentences > 0 and semicolons / sentences > 0.2:
            score += 1.0

        # Избыток двоеточий
        colons = text.count(':')
        if sentences > 0 and colons / sentences > 0.3:
            score += 1.0

        return score / total_checks

    def _calc_artificiality_score(self, report: AnalysisReport) -> float:
        """Вычислить общий балл искусственности (0-100)."""
        score = 0.0

        # 1. Низкая дисперсия длины предложений (ИИ пишет равномерно)
        if report.avg_sentence_length > 0:
            cv = (report.sentence_length_variance ** 0.5) / report.avg_sentence_length
            if cv < 0.3:
                score += 20  # Очень равномерные предложения
            elif cv < 0.5:
                score += 10

        # 2. Канцеляризмы
        score += report.bureaucratic_ratio * 25

        # 3. ИИ-связки
        score += report.connector_ratio * 20

        # 4. Повторяемость
        score += report.repetition_score * 15

        # 5. Типографика
        score += report.typography_score * 20

        # 6. Burstiness (низкий burstiness = AI)
        if report.burstiness_score < 0.3:
            score += 15  # Низкая вариативность — признак AI
        elif report.burstiness_score < 0.5:
            score += 5

        # 7. Предсказуемость (из n-gram перплексии)
        if report.predictability_score > 60:
            score += 10
        elif report.predictability_score > 40:
            score += 5

        return min(score, 100.0)

    def _calc_burstiness_score(self, sentence_lengths: list[int]) -> float:
        """Вычислить показатель burstiness (0-1).

        0 = все предложения одинаковой длины (AI).
        1 = большой разброс длин (человек).
        """
        if len(sentence_lengths) < 3:
            return 0.5

        mean = sum(sentence_lengths) / len(sentence_lengths)
        if mean == 0:
            return 0.0

        variance = sum((sl - mean) ** 2 for sl in sentence_lengths) / len(sentence_lengths)
        cv = (variance ** 0.5) / mean

        # Нормализуем: cv=0.7+ это хорошо (человечески), cv<0.3 это плохо (AI)
        return float(min(cv / 0.7, 1.0))

    def _calc_burstiness_cv(self, sentence_lengths: list[int]) -> float:
        """Вычислить коэффициент вариации для длины предложений."""
        if len(sentence_lengths) < 2:
            return 0.0
        mean = sum(sentence_lengths) / len(sentence_lengths)
        if mean == 0:
            return 0.0
        variance = sum((sl - mean) ** 2 for sl in sentence_lengths) / len(sentence_lengths)
        return float((variance ** 0.5) / mean)

    def _find_bureaucratic_words(self, text: str) -> list[str]:
        """Найти все канцеляризмы в тексте."""
        result = []
        bureaucratic = self.lang_pack.get("bureaucratic", {})
        phrases = self.lang_pack.get("bureaucratic_phrases", {})

        for phrase in phrases:
            if phrase.lower() in text.lower():
                result.append(phrase)

        for word in bureaucratic:
            pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
            if pattern.search(text):
                result.append(word)

        return result

    def _find_ai_connectors(self, text: str) -> list[str]:
        """Найти все ИИ-связки в тексте."""
        result = []
        connectors = self.lang_pack.get("ai_connectors", {})

        for connector in connectors:
            if connector.lower() in text.lower():
                result.append(connector)

        return result

    # ─── Readability metrics ──────────────────────────────────

    @staticmethod
    def _count_syllables(word: str) -> int:
        """Estimate syllable count for a word (English-centric heuristic)."""
        word = word.lower().strip(".,!?;:\"'()-")
        if not word:
            return 1
        vowels = "aeiouyаеёиоуыэюяіїєґáéíóúàèìòùâêîôûäëïöüãõ"
        count = 0
        prev_vowel = False
        for ch in word:
            is_vowel = ch in vowels
            if is_vowel and not prev_vowel:
                count += 1
            prev_vowel = is_vowel
        # Handle silent trailing 'e' for English
        if word.endswith("e") and count > 1:
            count -= 1
        return max(count, 1)

    def _calc_avg_syllables(self, words: list[str]) -> float:
        """Average syllables per word."""
        if not words:
            return 0.0
        total = sum(self._count_syllables(w) for w in words)
        return total / len(words)

    @staticmethod
    def _calc_flesch_kincaid(
        num_sentences: int, num_words: int, avg_syllables: float,
    ) -> float:
        """Flesch-Kincaid Grade Level.

        Lower values mean easier readability.
        Typical range: 1-18+  (US school grade equivalent).
        """
        if num_sentences == 0 or num_words == 0:
            return 0.0
        asl = num_words / num_sentences  # avg sentence length
        return 0.39 * asl + 11.8 * avg_syllables - 15.59

    @staticmethod
    def _calc_coleman_liau(
        text: str, words: list[str], sentences: list[str],
    ) -> float:
        """Coleman-Liau Index.

        Uses characters per word and sentences per word.
        """
        if not words or not sentences:
            return 0.0
        num_letters = sum(1 for ch in text if ch.isalpha())
        l_val = (num_letters / len(words)) * 100  # letters per 100 words
        s_val = (len(sentences) / len(words)) * 100  # sentences per 100 words
        return 0.0588 * l_val - 0.296 * s_val - 15.8

    def _find_typography_issues(self, text: str) -> list[str]:
        """Найти типографские признаки ИИ."""
        issues = []
        if '—' in text:
            issues.append("Длинные тире (—)")
        if '«' in text or '»' in text:
            issues.append("Типографские кавычки (« »)")
        if '…' in text:
            issues.append("Типографское многоточие (…)")
        if '\u00A0' in text:
            issues.append("Неразрывные пробелы")
        return issues

    # ─── Additional readability metrics ───────────────────────

    @staticmethod
    def calc_ari(text: str, words: list[str], sentences: list[str]) -> float:
        """Automated Readability Index (ARI).

        Uses character counts vs word/sentence counts.
        Typical range: 1-14+ (US grade level).
        """
        if not words or not sentences:
            return 0.0
        num_chars = sum(1 for ch in text if ch.isalnum())
        asl = len(words) / len(sentences)
        awl = num_chars / len(words)
        return 4.71 * awl + 0.5 * asl - 21.43

    def calc_smog_index(self, words: list[str], sentences: list[str]) -> float:
        """SMOG (Simple Measure of Gobbledygook) Index.

        Estimates years of education needed.
        Requires 30+ sentences for accuracy.
        """
        import math
        if not words or not sentences:
            return 0.0
        polysyllables: float = sum(
            1 for w in words if self._count_syllables(w) >= 3
        )
        n_sentences = len(sentences)
        # Adjust for small samples
        if n_sentences < 30:
            polysyllables = polysyllables * (30 / n_sentences)
        return 1.0430 * math.sqrt(polysyllables * (30 / max(n_sentences, 1))) + 3.1291

    def calc_gunning_fog(
        self, words: list[str], sentences: list[str]
    ) -> float:
        """Gunning Fog Index.

        Typical range: 6-17+ (US grade level).
        Higher = harder to read.
        """
        if not words or not sentences:
            return 0.0
        complex_words = sum(
            1 for w in words
            if self._count_syllables(w) >= 3
            and not w[0].isupper()  # не имена
        )
        asl = len(words) / len(sentences)
        pct_complex = (complex_words / len(words)) * 100
        return 0.4 * (asl + pct_complex)

    @staticmethod
    def calc_dale_chall(
        text: str, words: list[str], sentences: list[str]
    ) -> float:
        """Dale-Chall Readability Score (simplified).

        Uses proportion of 'difficult' words (>6 chars as proxy
        since full Dale-Chall word list is copyrighted).
        """
        if not words or not sentences:
            return 0.0
        # Approximate: words > 6 chars as "difficult"
        difficult = sum(
            1 for w in words
            if len(w.strip('.,;:!?"\'()')) > 6
        )
        pct_diff = (difficult / len(words)) * 100
        asl = len(words) / len(sentences)
        raw = 0.1579 * pct_diff + 0.0496 * asl
        if pct_diff > 5:
            raw += 3.6365
        return raw

    def full_readability(self, text: str) -> dict[str, float]:
        """Calculate all readability metrics at once.

        Returns:
            Dictionary with all readability scores.
        """
        words = text.split()
        sentences = self._split_sentences(text)
        avg_syl = self._calc_avg_syllables(words)

        return {
            "flesch_kincaid_grade": self._calc_flesch_kincaid(
                len(sentences), len(words), avg_syl
            ),
            "coleman_liau_index": self._calc_coleman_liau(text, words, sentences),
            "ari": self.calc_ari(text, words, sentences),
            "smog_index": self.calc_smog_index(words, sentences),
            "gunning_fog": self.calc_gunning_fog(words, sentences),
            "dale_chall": self.calc_dale_chall(text, words, sentences),
            "avg_word_length": (
                sum(len(w) for w in words) / len(words) if words else 0
            ),
            "avg_syllables_per_word": avg_syl,
            "avg_sentence_length": (
                len(words) / len(sentences) if sentences else 0
            ),
        }
