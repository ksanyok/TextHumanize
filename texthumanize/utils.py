"""Утилиты TextHumanize."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any


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

    def __post_init__(self):
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
        """Доля изменений в тексте (0..1)."""
        if not self.original:
            return 0.0
        orig_words = self.original.split()
        new_words = self.text.split()
        if not orig_words:
            return 0.0
        diff = sum(1 for a, b in zip(orig_words, new_words) if a != b)
        diff += abs(len(orig_words) - len(new_words))
        return min(diff / len(orig_words), 1.0)


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
