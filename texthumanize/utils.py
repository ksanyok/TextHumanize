"""Утилиты TextHumanize."""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any, TypedDict

logger = logging.getLogger(__name__)

@dataclass
class HumanizeOptions:
    """Опции гуманизации текста."""

    lang: str = "auto"
    profile: str = "web"
    intensity: int = 60
    preserve: dict[str, Any] = field(default_factory=lambda: {
        "code_blocks": True,
        "urls": True,
        "emails": True,
        "hashtags": True,
        "mentions": True,
        "markdown": True,
        "html": True,
        "numbers": False,
        "brand_terms": [],
    })
    constraints: dict[str, Any] = field(default_factory=lambda: {
        "max_change_ratio": 0.4,
        "min_sentence_length": 3,
        "keep_keywords": [],
    })
    seed: int | None = None
    # Целевой стилистический отпечаток для имитации авторского стиля
    target_style: Any | None = None  # StylisticFingerprint, preset name (str), or None
    # Пользовательский словарь замен: {"слово": "замена"} или {"слово": ["вар1", "вар2"]}
    custom_dict: dict[str, str | list[str]] | None = None

    def __post_init__(self) -> None:
        if self.intensity < 0:
            self.intensity = 0
        elif self.intensity > 100:
            self.intensity = 100
        _VALID_PROFILES = (
            "chat", "web", "seo", "docs", "formal",
            "academic", "marketing", "social", "email",
        )
        if self.profile not in _VALID_PROFILES:
            raise ValueError(
                f"Неизвестный профиль: {self.profile}. "
                f"Доступны: {', '.join(_VALID_PROFILES)}"
            )


@dataclass
class HumanizeResult:
    """Результат гуманизации текста."""

    original: str
    text: str
    lang: str
    profile: str
    intensity: int
    changes: list[dict[str, str]] = field(default_factory=list)
    metrics_before: dict[str, Any] = field(default_factory=dict)
    metrics_after: dict[str, Any] = field(default_factory=dict)

    @property
    def change_ratio(self) -> float:
        """Доля изменений в тексте (0..1).

        Использует SequenceMatcher для корректного сравнения —
        вставка/удаление одного слова не сдвигает все позиции.
        """
        if not self.original:
            return 0.0
        orig_words = self.original.split()
        new_words = self.text.split()
        if not orig_words:
            return 0.0
        matcher = SequenceMatcher(None, orig_words, new_words)
        return min(1.0 - matcher.ratio(), 1.0)

    @property
    def similarity(self) -> float:
        """Jaccard-подобие оригинала и результата (0..1).

        1.0 = идентичные тексты, 0.0 = полностью разные.
        """
        if not self.original or not self.text:
            return 1.0 if self.original == self.text else 0.0
        orig_set = set(self.original.lower().split())
        new_set = set(self.text.lower().split())
        if not orig_set and not new_set:
            return 1.0
        intersection = orig_set & new_set
        union = orig_set | new_set
        return len(intersection) / len(union) if union else 1.0

    @property
    def quality_score(self) -> float:
        """Общий балл качества обработки (0..1).

        Учитывает баланс между достаточным изменением текста
        и сохранением смысла (similarity). Идеал: ~0.75-0.90.
        """
        sim = self.similarity
        change = self.change_ratio
        # Штраф за слишком малые или слишком большие изменения
        if change < 0.01:
            # Текст не изменился — проверяем, нужны ли были изменения
            # Если similarity = 1.0, значит текст вернулся без изменений;
            # для уже естественных текстов это может быть желательно
            ai_before = self.metrics_before.get("artificiality_score", 50)
            if ai_before < 15:
                return 0.7  # Лёгкий текст — отсутствие изменений ОК
            return 0.3  # AI-текст без изменений — плохо
        if sim < 0.3:
            return 0.2  # Слишком сильно изменён — потеря смысла
        # Оптимальный диапазон change: 3%-35%
        # Центр оптимума: 15%
        change_score = 1.0 - abs(change - 0.15) / 0.35
        change_score = max(0.0, min(1.0, change_score))
        return sim * 0.6 + change_score * 0.4


@dataclass
class AnalysisReport:
    """Отчёт анализа текста."""

    lang: str
    total_chars: int = 0
    total_words: int = 0
    total_sentences: int = 0
    avg_sentence_length: float = 0.0
    sentence_length_variance: float = 0.0
    bureaucratic_ratio: float = 0.0
    connector_ratio: float = 0.0
    repetition_score: float = 0.0
    typography_score: float = 0.0
    burstiness_score: float = 0.5
    artificiality_score: float = 0.0
    # Readability metrics
    flesch_kincaid_grade: float = 0.0
    coleman_liau_index: float = 0.0
    avg_word_length: float = 0.0
    avg_syllables_per_word: float = 0.0
    # N-gram perplexity metrics
    predictability_score: float = 0.0
    char_perplexity: float = 0.0
    vocabulary_richness: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)


# ─── Профили ──────────────────────────────────────────────────

PROFILES = {
    "chat": {
        "description": "Живой разговорный стиль",
        "typography": {"dash": "-", "quotes": '"', "ellipsis": "..."},
        "decancel_intensity": 1.0,
        "structure_intensity": 1.0,
        "repetition_intensity": 0.8,
        "liveliness_intensity": 0.7,
        "target_sentence_len": (8, 18),
    },
    "web": {
        "description": "Нейтральный веб-контент",
        "typography": {"dash": "–", "quotes": '"', "ellipsis": "..."},
        "decancel_intensity": 0.8,
        "structure_intensity": 0.8,
        "repetition_intensity": 0.7,
        "liveliness_intensity": 0.3,
        "target_sentence_len": (10, 22),
    },
    "seo": {
        "description": "SEO-безопасный режим",
        "typography": {"dash": "–", "quotes": '"', "ellipsis": "..."},
        "decancel_intensity": 0.4,
        "structure_intensity": 0.5,
        "repetition_intensity": 0.3,
        "liveliness_intensity": 0.0,
        "target_sentence_len": (12, 25),
    },
    "docs": {
        "description": "Документация, технический стиль",
        "typography": {"dash": "—", "quotes": '"', "ellipsis": "…"},
        "decancel_intensity": 0.3,
        "structure_intensity": 0.4,
        "repetition_intensity": 0.5,
        "liveliness_intensity": 0.0,
        "target_sentence_len": (12, 28),
    },
    "formal": {
        "description": "Формальный стиль",
        "typography": {"dash": "—", "quotes": "«»", "ellipsis": "…"},
        "decancel_intensity": 0.2,
        "structure_intensity": 0.3,
        "repetition_intensity": 0.4,
        "liveliness_intensity": 0.0,
        "target_sentence_len": (15, 30),
    },
    "academic": {
        "description": "Академический / научный стиль",
        "typography": {"dash": "—", "quotes": "«»", "ellipsis": "…"},
        "decancel_intensity": 0.15,
        "structure_intensity": 0.25,
        "repetition_intensity": 0.3,
        "liveliness_intensity": 0.0,
        "target_sentence_len": (18, 35),
    },
    "marketing": {
        "description": "Маркетинговый / рекламный стиль",
        "typography": {"dash": "–", "quotes": '"', "ellipsis": "..."},
        "decancel_intensity": 0.9,
        "structure_intensity": 0.9,
        "repetition_intensity": 0.6,
        "liveliness_intensity": 0.8,
        "target_sentence_len": (6, 16),
    },
    "social": {
        "description": "Социальные сети / посты",
        "typography": {"dash": "-", "quotes": '"', "ellipsis": "..."},
        "decancel_intensity": 1.0,
        "structure_intensity": 1.0,
        "repetition_intensity": 0.7,
        "liveliness_intensity": 0.9,
        "target_sentence_len": (5, 14),
    },
    "email": {
        "description": "Деловая переписка",
        "typography": {"dash": "–", "quotes": '"', "ellipsis": "..."},
        "decancel_intensity": 0.5,
        "structure_intensity": 0.5,
        "repetition_intensity": 0.6,
        "liveliness_intensity": 0.1,
        "target_sentence_len": (10, 22),
    },
}


def get_profile(name: str) -> dict:
    """Получить конфигурацию профиля."""
    if name not in PROFILES:
        raise ValueError(f"Неизвестный профиль: {name}")
    return PROFILES[name]


def should_apply(intensity: int, profile_factor: float, threshold: float = 0.5) -> bool:
    """Решить, применять ли трансформацию на основе интенсивности и профиля.

    Args:
        intensity: Общая интенсивность (0-100).
        profile_factor: Множитель профиля (0.0-1.0).
        threshold: Порог срабатывания (0.0-1.0).

    Returns:
        True если трансформацию нужно применить.
    """
    effective = (intensity / 100.0) * profile_factor
    return effective >= threshold


def coin_flip(probability: float, rng: random.Random | None = None) -> bool:
    """Случайное решение с заданной вероятностью."""
    r = rng or random
    return r.random() < probability


def intensity_probability(intensity: int, profile_factor: float) -> float:
    """Вычислить вероятность применения трансформации."""
    return min((intensity / 100.0) * profile_factor, 1.0)


# ── TypedDicts for structured return types ────────────────


class DetectionMetrics(TypedDict, total=False):
    """Detailed per-metric scores from AI detection."""

    entropy: float
    burstiness: float
    vocabulary: float
    zipf: float
    stylometry: float
    ai_patterns: float
    punctuation: float
    coherence: float
    grammar_perfection: float
    opening_diversity: float
    readability_consistency: float
    rhythm: float
    perplexity: float
    discourse: float
    semantic_repetition: float
    entity_specificity: float
    voice: float
    topic_sentence: float


class DetectionReport(TypedDict, total=False):
    """Structured result of :func:`detect_ai`.

    Using ``total=False`` allows the dict to omit optional keys.
    """

    score: float
    combined_score: float
    stat_probability: float | None
    verdict: str
    confidence: float
    metrics: DetectionMetrics
    explanations: list[str]
    domain: str
    lang: str
