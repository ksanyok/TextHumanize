"""N-gram перплексия текста — оценка предсказуемости без ML.

Основная идея: AI-тексты имеют низкую перплексию (высоко предсказуемы),
а тексты человека — более высокую (менее предсказуемые конструкции).

Метрики:
- Символьная перплексия (character-level n-gram)
- Словарная энтропия (word-level entropy)
- Перплексия биграмм (word bigram predictability)
- Общий скор «предсказуемости» (0-100, где 100 = максимально предсказуемый)

Реализация полностью rule-based, без внешних ML-зависимостей.
"""

from __future__ import annotations

import logging
import math
import re
from collections import Counter
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class PerplexityReport:
    """Отчёт перплексии текста."""

    char_perplexity: float = 0.0  # Символьная перплексия (4-gram)
    word_entropy: float = 0.0  # Словарная энтропия (бит/слово)
    bigram_predictability: float = 0.0  # Предсказуемость биграмм (0-1)
    vocabulary_richness: float = 0.0  # TTR — type-token ratio
    hapax_ratio: float = 0.0  # Доля слов, встречающихся один раз
    predictability_score: float = 0.0  # Общий скор (0-100, 100=AI-like)


class PerplexityEstimator:
    """Оценщик перплексии текста на основе n-грамм.

    Работает без обучения: строит модель из самого текста
    и оценивает его «самопредсказуемость».
    """

    def __init__(self, char_n: int = 4, word_n: int = 2):
        """
        Args:
            char_n: Размер символьных n-грамм (по умолчанию 4).
            word_n: Размер словесных n-грамм (по умолчанию 2, биграммы).
        """
        self.char_n = char_n
        self.word_n = word_n

    def analyze(self, text: str) -> PerplexityReport:
        """Полный анализ перплексии текста.

        Args:
            text: Текст для анализа.

        Returns:
            PerplexityReport с метриками.
        """
        report = PerplexityReport()

        if not text or len(text.strip()) < 50:
            return report

        # Нормализуем текст
        clean = self._normalize(text)
        words = self._tokenize(clean)

        if len(words) < 10:
            return report

        # 1. Символьная перплексия
        report.char_perplexity = self._calc_char_perplexity(clean)

        # 2. Словарная энтропия
        report.word_entropy = self._calc_word_entropy(words)

        # 3. Предсказуемость биграмм
        report.bigram_predictability = self._calc_bigram_predictability(words)

        # 4. Vocabulary richness (TTR)
        report.vocabulary_richness = self._calc_ttr(words)

        # 5. Hapax ratio
        report.hapax_ratio = self._calc_hapax_ratio(words)

        # 6. Общий скор предсказуемости (0-100)
        report.predictability_score = self._calc_predictability_score(report)

        return report

    def _normalize(self, text: str) -> str:
        """Нормализовать текст для анализа."""
        # Убираем множественные пробелы, приводим к нижнему регистру
        text = re.sub(r'\s+', ' ', text.lower().strip())
        return text

    def _tokenize(self, text: str) -> list[str]:
        """Токенизировать текст в слова."""
        # Простая токенизация: только буквы и цифры
        return re.findall(r'[a-zа-яёіїєґüöäßàèìòùáéíóúâêîôûãõ\d]+', text)

    def _calc_char_perplexity(self, text: str) -> float:
        """Вычислить символьную перплексию на основе n-грамм.

        Строим модель из самого текста (leave-one-out cross-entropy).
        Низкая перплексия = высокая предсказуемость = AI.
        """
        n = self.char_n
        if len(text) < n + 1:
            return 0.0

        # Строим таблицу частот n-грамм и (n-1)-грамм
        ngram_counts: Counter[str] = Counter()
        context_counts: Counter[str] = Counter()

        for i in range(len(text) - n + 1):
            ngram = text[i:i + n]
            context = text[i:i + n - 1]
            ngram_counts[ngram] += 1
            context_counts[context] += 1

        if not ngram_counts:
            return 0.0

        # Вычисляем cross-entropy
        total_log_prob = 0.0
        count = 0

        for ngram, freq in ngram_counts.items():
            context = ngram[:-1]
            ctx_freq = context_counts[context]
            if ctx_freq > 0:
                # Вероятность с аддитивным сглаживанием (Laplace)
                vocab_size = len(set(text))
                prob = (freq + 1) / (ctx_freq + vocab_size)
                total_log_prob += freq * math.log2(prob)
                count += freq

        if count == 0:
            return 0.0

        # H = -1/N * sum(log2(P))
        entropy = -total_log_prob / count
        # Перплексия = 2^H
        perplexity = 2 ** entropy

        return perplexity

    def _calc_word_entropy(self, words: list[str]) -> float:
        """Вычислить энтропию на уровне слов (бит/слово).

        Высокая энтропия = разнообразный словарь = человек.
        Низкая энтропия = ограниченный словарь = AI.
        """
        if not words:
            return 0.0

        total = len(words)
        freqs = Counter(words)

        entropy = 0.0
        for count in freqs.values():
            p = count / total
            if p > 0:
                entropy -= p * math.log2(p)

        return entropy

    def _calc_bigram_predictability(self, words: list[str]) -> float:
        """Вычислить предсказуемость биграмм.

        0 = каждая биграмма уникальна (непредсказуемо).
        1 = все биграммы повторяются (предсказуемо, AI).
        """
        if len(words) < 3:
            return 0.0

        bigrams = [(words[i], words[i + 1]) for i in range(len(words) - 1)]
        total = len(bigrams)
        unique = len(set(bigrams))

        if total == 0:
            return 0.0

        # Доля повторяющихся биграмм
        repeat_ratio = 1.0 - (unique / total)
        return repeat_ratio

    def _calc_ttr(self, words: list[str]) -> float:
        """Type-Token Ratio — отношение уникальных слов к общему числу.

        Высокий TTR = богатый словарь (человек).
        Низкий TTR = ограниченный словарь (AI).
        """
        if not words:
            return 0.0

        # Используем MSTTR (Mean Segmental TTR) для нормализации по длине
        segment_size = 100
        if len(words) < segment_size:
            return len(set(words)) / len(words)

        ttrs = []
        for i in range(0, len(words) - segment_size + 1, segment_size):
            segment = words[i:i + segment_size]
            ttrs.append(len(set(segment)) / len(segment))

        return sum(ttrs) / len(ttrs) if ttrs else 0.0

    def _calc_hapax_ratio(self, words: list[str]) -> float:
        """Доля слов, встречающихся ровно один раз (hapax legomena).

        Высокая доля hapax = разнообразный текст (человек).
        Низкая доля = повторяющийся (AI).
        """
        if not words:
            return 0.0

        freqs = Counter(words)
        hapax = sum(1 for c in freqs.values() if c == 1)
        return hapax / len(freqs) if freqs else 0.0

    def _calc_predictability_score(self, report: PerplexityReport) -> float:
        """Вычислить общий скор предсказуемости (0-100).

        100 = максимально предсказуемый (AI-like).
        0 = максимально непредсказуемый (человеческий).
        """
        score = 0.0

        # 1. Символьная перплексия: низкая (<5) → AI, высокая (>15) → человек
        if report.char_perplexity > 0:
            if report.char_perplexity < 4:
                score += 25
            elif report.char_perplexity < 7:
                score += 15
            elif report.char_perplexity < 12:
                score += 5

        # 2. Словарная энтропия: низкая (<6) → AI, высокая (>9) → человек
        if report.word_entropy < 5:
            score += 20
        elif report.word_entropy < 7:
            score += 10
        elif report.word_entropy < 8:
            score += 5

        # 3. Предсказуемость биграмм: высокая (>0.3) → AI
        score += report.bigram_predictability * 25

        # 4. TTR: низкий (<0.5) → AI
        if report.vocabulary_richness < 0.4:
            score += 15
        elif report.vocabulary_richness < 0.55:
            score += 8
        elif report.vocabulary_richness < 0.65:
            score += 3

        # 5. Hapax ratio: низкий (<0.5) → AI
        if report.hapax_ratio < 0.4:
            score += 15
        elif report.hapax_ratio < 0.55:
            score += 8
        elif report.hapax_ratio < 0.65:
            score += 3

        return min(score, 100.0)
