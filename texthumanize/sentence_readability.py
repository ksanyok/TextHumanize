"""Sentence-level Readability — оценка читабельности на уровне предложений.

В отличие от документарной читабельности, этот модуль оценивает
каждое предложение отдельно, выявляя «трудные» участки текста.

Использование:
    >>> from texthumanize.sentence_readability import sentence_readability
    >>> report = sentence_readability("Long complex sentence. Short one.")
    >>> for s in report.sentences:
    ...     print(s.text[:40], s.difficulty, s.grade)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class SentenceScore:
    """Оценка одного предложения."""

    text: str
    word_count: int
    avg_word_length: float
    syllable_count: int
    difficulty: float  # 0-100, 100 = очень трудно
    grade: str  # "easy" | "medium" | "hard" | "very_hard"
    index: int = 0


@dataclass
class SentenceReadabilityReport:
    """Полный отчёт о читабельности по предложениям."""

    sentences: list[SentenceScore] = field(default_factory=list)
    avg_difficulty: float = 0.0
    hardest_index: int = -1
    easy_count: int = 0
    medium_count: int = 0
    hard_count: int = 0
    very_hard_count: int = 0


# ── Syllable counter ─────────────────────────────────────────────────

def _count_syllables_en(word: str) -> int:
    """Приблизительный подсчёт слогов (английский + универсальный)."""
    word = word.lower().strip()
    if not word:
        return 0
    if len(word) <= 3:
        return 1

    # Remove trailing 'e'
    w = word
    if w.endswith("e") and len(w) > 3:
        w = w[:-1]

    vowels = "aeiouyаеёиоуыэюяіїєґ"
    count = 0
    prev_vowel = False
    for ch in w:
        is_vowel = ch in vowels
        if is_vowel and not prev_vowel:
            count += 1
        prev_vowel = is_vowel

    return max(1, count)


# ── Sentence splitting ───────────────────────────────────────────────

_SENT_SPLIT = re.compile(
    r"(?<=[.!?…])\s+(?=[A-ZА-ЯЁЇІЄҐÀ-ÿÄÖÜ])"
)


def _split_sentences(text: str) -> list[str]:
    """Разбить текст на предложения."""
    parts = _SENT_SPLIT.split(text.strip())
    return [s.strip() for s in parts if s.strip()]


# ── Difficulty scoring ───────────────────────────────────────────────

def _sentence_difficulty(word_count: int, avg_word_len: float, syllable_count: int) -> float:
    """Вычислить сложность предложения (0-100).

    Факторы:
        - Количество слов (длиннее = сложнее)
        - Средняя длина слова (длиннее = сложнее)
        - Среднее количество слогов на слово
    """
    if word_count == 0:
        return 0.0

    avg_syllables = syllable_count / word_count

    # Length factor: 0-40 based on word count
    if word_count <= 10:
        len_factor = word_count * 1.0
    elif word_count <= 20:
        len_factor = 10 + (word_count - 10) * 2.0
    elif word_count <= 35:
        len_factor = 30 + (word_count - 20) * 0.7
    else:
        len_factor = 40.0

    # Word complexity: 0-30 based on avg word length
    word_factor = min(30.0, max(0.0, (avg_word_len - 3) * 6))

    # Syllable factor: 0-30
    syl_factor = min(30.0, max(0.0, (avg_syllables - 1.2) * 15))

    return min(100.0, len_factor + word_factor + syl_factor)


def _grade_from_difficulty(difficulty: float) -> str:
    """Присвоить грейд сложности."""
    if difficulty < 25:
        return "easy"
    if difficulty < 50:
        return "medium"
    if difficulty < 75:
        return "hard"
    return "very_hard"


def sentence_readability(text: str) -> SentenceReadabilityReport:
    """Оценить читабельность на уровне предложений.

    Каждое предложение получает балл сложности (0-100)
    и грейд (easy/medium/hard/very_hard).

    Args:
        text: Текст для анализа.

    Returns:
        SentenceReadabilityReport со списком оценённых предложений.
    """
    sentences = _split_sentences(text)
    if not sentences:
        return SentenceReadabilityReport()

    scored: list[SentenceScore] = []
    max_diff = -1.0
    max_idx = -1
    easy = medium = hard = very_hard = 0

    for i, sent in enumerate(sentences):
        words = re.findall(r"\b\w+\b", sent)
        wc = len(words)
        if wc == 0:
            continue

        avg_wl = sum(len(w) for w in words) / wc
        syl = sum(_count_syllables_en(w) for w in words)
        diff = _sentence_difficulty(wc, avg_wl, syl)
        gr = _grade_from_difficulty(diff)

        ss = SentenceScore(
            text=sent, word_count=wc,
            avg_word_length=round(avg_wl, 2),
            syllable_count=syl,
            difficulty=round(diff, 1),
            grade=gr, index=i,
        )
        scored.append(ss)

        if diff > max_diff:
            max_diff = diff
            max_idx = i

        if gr == "easy":
            easy += 1
        elif gr == "medium":
            medium += 1
        elif gr == "hard":
            hard += 1
        else:
            very_hard += 1

    avg_diff = sum(s.difficulty for s in scored) / len(scored) if scored else 0.0

    return SentenceReadabilityReport(
        sentences=scored,
        avg_difficulty=round(avg_diff, 1),
        hardest_index=max_idx,
        easy_count=easy,
        medium_count=medium,
        hard_count=hard,
        very_hard_count=very_hard,
    )
