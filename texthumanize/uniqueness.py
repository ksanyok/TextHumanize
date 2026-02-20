"""Метрики уникальности текста (Uniqueness Score).

Вычисляет уникальность текста через N-грамм фингерпринтинг и
самосходство (self-similarity). Полностью оффлайн, без API.

Идея: чем больше уникальных N-грамм в тексте и чем меньше повторов —
тем «уникальнее» контент. Сравнение двух текстов показывает,
насколько один является переработкой другого.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from dataclasses import dataclass


@dataclass
class UniquenessReport:
    """Результат анализа уникальности."""

    score: float  # 0-100, 100 = полностью уникален
    unique_ratio_2gram: float  # Доля уникальных биграмм (0-1)
    unique_ratio_3gram: float  # Доля уникальных триграмм (0-1)
    unique_ratio_4gram: float  # Доля уникальных 4-грамм (0-1)
    repetition_score: float  # Повторяемость (0-1, 0 = нет повторов)
    total_words: int
    unique_words: int
    vocabulary_richness: float  # unique_words / total_words


@dataclass
class SimilarityReport:
    """Результат сравнения двух текстов."""

    similarity: float  # 0-1, 1 = идентичны
    common_ngrams: int
    total_ngrams_a: int
    total_ngrams_b: int
    jaccard_2gram: float
    jaccard_3gram: float
    jaccard_4gram: float


def _tokenize(text: str) -> list[str]:
    """Простая токенизация: lowercase, только слова."""
    return re.findall(r"\b\w+\b", text.lower())


def _ngrams(tokens: list[str], n: int) -> list[tuple[str, ...]]:
    """Получить N-граммы из списка токенов."""
    if len(tokens) < n:
        return []
    return [tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]


def _unique_ratio(grams: list[tuple[str, ...]]) -> float:
    """Доля уникальных N-грамм."""
    if not grams:
        return 1.0
    return len(set(grams)) / len(grams)


def _repetition_score(tokens: list[str]) -> float:
    """Вычислить повторяемость (0 = нет повторов, 1 = всё повторяется)."""
    if not tokens:
        return 0.0
    counter = Counter(tokens)
    repeated = sum(c - 1 for c in counter.values() if c > 1)
    return repeated / len(tokens)


def uniqueness_score(text: str) -> UniquenessReport:
    """Вычислить метрики уникальности текста.

    Анализирует текст через N-грамм фингерпринтинг, вычисляя
    долю уникальных конструкций и лексическое разнообразие.

    Args:
        text: Текст для анализа.

    Returns:
        UniquenessReport с детальными метриками.
    """
    tokens = _tokenize(text)
    total = len(tokens)
    unique = len(set(tokens))

    if total == 0:
        return UniquenessReport(
            score=100.0, unique_ratio_2gram=1.0,
            unique_ratio_3gram=1.0, unique_ratio_4gram=1.0,
            repetition_score=0.0, total_words=0,
            unique_words=0, vocabulary_richness=1.0,
        )

    bg = _ngrams(tokens, 2)
    tg = _ngrams(tokens, 3)
    fg = _ngrams(tokens, 4)

    ur2 = _unique_ratio(bg)
    ur3 = _unique_ratio(tg)
    ur4 = _unique_ratio(fg)
    rep = _repetition_score(tokens)
    vr = unique / total

    # Composite score: weighted average
    score = (
        ur2 * 0.15
        + ur3 * 0.25
        + ur4 * 0.25
        + vr * 0.20
        + (1.0 - rep) * 0.15
    ) * 100

    return UniquenessReport(
        score=round(min(100.0, max(0.0, score)), 1),
        unique_ratio_2gram=round(ur2, 4),
        unique_ratio_3gram=round(ur3, 4),
        unique_ratio_4gram=round(ur4, 4),
        repetition_score=round(rep, 4),
        total_words=total,
        unique_words=unique,
        vocabulary_richness=round(vr, 4),
    )


def _jaccard(set_a: set, set_b: set) -> float:
    """Jaccard similarity."""
    if not set_a and not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)


def compare_texts(text_a: str, text_b: str) -> SimilarityReport:
    """Сравнить два текста на схожесть через N-грамм пересечение.

    Использует Jaccard similarity по биграммам, триграммам и 4-граммам
    для определения степени совпадения текстов.

    Args:
        text_a: Первый текст (обычно оригинал).
        text_b: Второй текст (обычно обработанный).

    Returns:
        SimilarityReport с детальными метриками сходства.
    """
    tokens_a = _tokenize(text_a)
    tokens_b = _tokenize(text_b)

    bg_a = set(_ngrams(tokens_a, 2))
    bg_b = set(_ngrams(tokens_b, 2))
    tg_a = set(_ngrams(tokens_a, 3))
    tg_b = set(_ngrams(tokens_b, 3))
    fg_a = set(_ngrams(tokens_a, 4))
    fg_b = set(_ngrams(tokens_b, 4))

    j2 = _jaccard(bg_a, bg_b)
    j3 = _jaccard(tg_a, tg_b)
    j4 = _jaccard(fg_a, fg_b)

    # Weighted similarity — skip empty n-gram levels for short texts
    weights = []
    values = []
    if bg_a or bg_b:
        weights.append(0.2)
        values.append(j2)
    if tg_a or tg_b:
        weights.append(0.4)
        values.append(j3)
    if fg_a or fg_b:
        weights.append(0.4)
        values.append(j4)

    if weights:
        total_w = sum(weights)
        similarity = sum(v * w for v, w in zip(values, weights)) / total_w
    else:
        # Both texts are empty or trivially short
        similarity = 1.0 if (not tokens_a and not tokens_b) else 0.0

    common = len(tg_a & tg_b)

    return SimilarityReport(
        similarity=round(similarity, 4),
        common_ngrams=common,
        total_ngrams_a=len(tg_a),
        total_ngrams_b=len(tg_b),
        jaccard_2gram=round(j2, 4),
        jaccard_3gram=round(j3, 4),
        jaccard_4gram=round(j4, 4),
    )


def text_fingerprint(text: str, n: int = 3) -> str:
    """Вычислить хеш-фингерпринт текста по N-граммам.

    Создаёт стабильный хеш текста для быстрого сравнения.
    Два одинаковых текста дадут одинаковый фингерпринт.

    Args:
        text: Текст для фингерпринтинга.
        n: Размер N-грамм (по умолчанию 3).

    Returns:
        Hex-строка SHA-256 хеша N-грамм фингерпринта.
    """
    tokens = _tokenize(text)
    grams = _ngrams(tokens, n)
    # Fallback to lower n-grams for short texts, include raw tokens
    if not grams:
        for fallback_n in range(n - 1, 0, -1):
            grams = _ngrams(tokens, fallback_n)
            if grams:
                break
    # Include raw tokens to differentiate short texts
    token_part = "|".join(tokens)
    # Sort n-grams for stability
    canonical = sorted(set(grams))
    blob = token_part + "||" + "|".join(",".join(g) for g in canonical)
    return hashlib.sha256(blob.encode()).hexdigest()
