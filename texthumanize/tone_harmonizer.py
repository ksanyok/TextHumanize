"""Гармонизация тона — этап пайплайна.

Приводит тональность текста к стилю, соответствующему выбранному профилю:
- academic → formal/academic tone
- blog → friendly tone
- default → neutral tone
- seo → professional tone

Использует tone.py для анализа и коррекции.
"""

from __future__ import annotations

from texthumanize.segmenter import has_placeholder, skip_placeholder_sentence
from texthumanize.tone import ToneAdjuster, ToneAnalyzer, ToneLevel


# Маппинг профилей на целевой тон
_PROFILE_TONE_MAP: dict[str, ToneLevel] = {
    "academic": ToneLevel.ACADEMIC,
    "blog": ToneLevel.FRIENDLY,
    "default": ToneLevel.NEUTRAL,
    "seo": ToneLevel.PROFESSIONAL,
    "formal": ToneLevel.FORMAL,
    "casual": ToneLevel.CASUAL,
    "marketing": ToneLevel.MARKETING,
}


class ToneHarmonizer:
    """Гармонизатор тона текста для пайплайна.

    Анализирует текущий тон и приводит его к целевому стилю,
    определённому профилем обработки.

    Работает для: en, ru, uk, de, fr, es (языки с tone_replacements).
    Для остальных языков — только анализ без коррекции.
    """

    def __init__(
        self,
        lang: str = "en",
        profile: str = "default",
        intensity: int = 50,
        seed: int | None = None,
    ):
        self.lang = lang
        self.profile = profile
        self.intensity = intensity
        self.seed = seed
        self.changes: list[dict] = []

    def process(self, text: str) -> str:
        """Скорректировать тон текста согласно профилю.

        Returns:
            Текст с выровненным тоном.
        """
        if not text or not text.strip():
            return text

        # Определяем целевой тон по профилю
        target_tone = _PROFILE_TONE_MAP.get(self.profile, ToneLevel.NEUTRAL)

        # Анализируем текущий тон
        analyzer = ToneAnalyzer(self.lang)
        report_before = analyzer.analyze(text)

        # Если тон уже соответствует — ничего не делаем
        if report_before.primary_tone == target_tone:
            return text

        # Если уверенность в текущем тоне очень низкая — не трогаем
        if report_before.confidence < 0.2:
            return text

        # Корректируем тон
        adjuster = ToneAdjuster(self.lang, seed=self.seed)
        # intensity: от 0.2 (мягко) до 0.7 (сильно) в зависимости от настройки
        adj_intensity = 0.2 + (self.intensity / 100) * 0.5
        result = adjuster.adjust(text, target=target_tone, intensity=adj_intensity)

        if result != text:
            report_after = analyzer.analyze(result)
            self.changes.append({
                "type": "tone_harmonization",
                "description": (
                    f"Тон: {report_before.primary_tone.value}"
                    f"→{report_after.primary_tone.value} "
                    f"(формальность {report_before.formality:.0%}"
                    f"→{report_after.formality:.0%}, "
                    f"цель: {target_tone.value})"
                ),
            })

        return result
