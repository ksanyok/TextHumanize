"""Семантическое сравнение текстов (Semantic Similarity).

Оценивает, насколько два текста сохраняют одинаковый смысл,
используя ключевые слова, именованные сущности и N-грамм перекрытие.
Без ML-моделей — 100 % оффлайн.

Использование:
    >>> from texthumanize.semantic import semantic_similarity
    >>> score = semantic_similarity(original, humanized)
    >>> print(score.preservation)  # 0-1, 1 = смысл сохранён полностью
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field


@dataclass
class SemanticReport:
    """Результат семантического сравнения."""

    preservation: float  # 0-1, 1 = полное сохранение смысла
    keyword_overlap: float  # Доля совпадающих ключевых слов
    entity_overlap: float  # Доля совпадающих «сущностей» (capitalized words)
    content_word_overlap: float  # Перекрытие контентных слов
    ngram_overlap: float  # Перекрытие триграмм
    missing_keywords: list[str] = field(default_factory=list)
    added_keywords: list[str] = field(default_factory=list)


# ── Utilities ─────────────────────────────────────────────────────────

_WORD_RE = re.compile(r"\b\w+\b")
_ENTITY_RE = re.compile(r"\b[A-ZА-ЯЁЇІЄҐ][a-zа-яёїіє'ґ]{2,}\b")

# Universal stop words (very common, content-less)
_STOP = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "to", "of", "in", "for",
    "on", "with", "at", "by", "from", "this", "that", "it", "its",
    "and", "or", "but", "not", "no", "if", "so", "as", "than", "then",
    "he", "she", "they", "we", "you", "i", "me", "my", "your", "his",
    "her", "our", "their", "who", "which", "what", "where", "when",
    # Russian / Ukrainian
    "и", "в", "на", "с", "по", "к", "у", "о", "из", "за", "от",
    "не", "но", "это", "что", "как", "для", "же", "он", "она",
    "они", "мы", "вы", "его", "её", "их", "при", "до", "без",
    "та", "те", "той", "ті", "тих", "цей", "ця", "це", "ці",
})


def _content_words(text: str) -> list[str]:
    """Извлечь контентные слова (не стоп-слова), lowercase."""
    words = _WORD_RE.findall(text.lower())
    return [w for w in words if w not in _STOP and len(w) > 2]


def _extract_entities(text: str) -> set[str]:
    """Извлечь «сущности» — слова с заглавной буквы (имена, бренды)."""
    return {m.group().lower() for m in _ENTITY_RE.finditer(text)}


def _extract_keywords(words: list[str], top_n: int = 30) -> set[str]:
    """Выбрать top-N ключевых слов по частоте."""
    counter = Counter(words)
    return {w for w, _ in counter.most_common(top_n)}


def _overlap(set_a: set, set_b: set) -> float:
    """Перекрытие: |A ∩ B| / max(|A|, |B|)."""
    if not set_a and not set_b:
        return 1.0
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / max(len(set_a), len(set_b))


def _ngram_overlap(tokens_a: list[str], tokens_b: list[str], n: int = 3) -> float:
    """Jaccard перекрытие N-грамм."""
    if len(tokens_a) < n or len(tokens_b) < n:
        return 0.0
    grams_a = {tuple(tokens_a[i:i + n]) for i in range(len(tokens_a) - n + 1)}
    grams_b = {tuple(tokens_b[i:i + n]) for i in range(len(tokens_b) - n + 1)}
    if not grams_a and not grams_b:
        return 1.0
    intersection = grams_a & grams_b
    union = grams_a | grams_b
    return len(intersection) / len(union) if union else 0.0


def semantic_similarity(original: str, processed: str) -> SemanticReport:
    """Оценить сохранение смысла между оригиналом и обработанным текстом.

    Сравнивает ключевые слова, именованные сущности,
    контентные слова и N-грамм перекрытие.

    Args:
        original: Исходный текст.
        processed: Обработанный (гуманизированный) текст.

    Returns:
        SemanticReport с метриками сохранения смысла.
    """
    cw_orig = _content_words(original)
    cw_proc = _content_words(processed)

    kw_orig = _extract_keywords(cw_orig)
    kw_proc = _extract_keywords(cw_proc)

    ent_orig = _extract_entities(original)
    ent_proc = _extract_entities(processed)

    cw_set_orig = set(cw_orig)
    cw_set_proc = set(cw_proc)

    kw_overlap = _overlap(kw_orig, kw_proc)
    ent_ovl = _overlap(ent_orig, ent_proc)
    cw_ovl = _overlap(cw_set_orig, cw_set_proc)
    ng_ovl = _ngram_overlap(cw_orig, cw_proc, 3)

    # Weighted preservation score
    preservation = (
        kw_overlap * 0.35
        + ent_ovl * 0.20
        + cw_ovl * 0.25
        + ng_ovl * 0.20
    )

    missing = sorted(kw_orig - kw_proc)
    added = sorted(kw_proc - kw_orig)

    return SemanticReport(
        preservation=round(min(1.0, max(0.0, preservation)), 4),
        keyword_overlap=round(kw_overlap, 4),
        entity_overlap=round(ent_ovl, 4),
        content_word_overlap=round(cw_ovl, 4),
        ngram_overlap=round(ng_ovl, 4),
        missing_keywords=missing,
        added_keywords=added,
    )
