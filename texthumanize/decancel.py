"""Деканцеляризация — замена тяжёлых бюрократических слов и выражений."""

from __future__ import annotations

import random
import re

from texthumanize.lang import get_lang_pack
from texthumanize.utils import get_profile, intensity_probability, coin_flip


class Debureaucratizer:
    """Заменяет канцеляризмы на простые и естественные выражения.

    Работает по словарям: однословные канцеляризмы и фразовые выражения.
    Интенсивность зависит от профиля и параметра intensity.
    """

    def __init__(
        self,
        lang: str = "ru",
        profile: str = "web",
        intensity: int = 60,
        seed: int | None = None,
    ):
        self.lang = lang
        self.lang_pack = get_lang_pack(lang)
        self.profile_name = profile
        self.profile = get_profile(profile)
        self.intensity = intensity
        self.rng = random.Random(seed)
        self.changes: list[dict[str, str]] = []

    def process(self, text: str) -> str:
        """Деканцеляризация текста.

        Args:
            text: Текст для обработки.

        Returns:
            Текст с заменёнными канцеляризмами.
        """
        self.changes = []
        prob = intensity_probability(
            self.intensity,
            self.profile["decancel_intensity"],
        )

        if prob < 0.05:
            return text

        # 1. Сначала фразовые замены (более специфичные)
        text = self._replace_phrases(text, prob)

        # 2. Затем однословные замены
        text = self._replace_words(text, prob)

        return text

    def _replace_phrases(self, text: str, prob: float) -> str:
        """Заменить фразовые канцеляризмы."""
        phrases = self.lang_pack.get("bureaucratic_phrases", {})

        # Сортируем по длине (длинные фразы первыми)
        sorted_phrases = sorted(phrases.items(), key=lambda x: len(x[0]), reverse=True)

        for phrase, replacements in sorted_phrases:
            if not coin_flip(prob, self.rng):
                continue

            # Ищем фразу с учётом регистра первой буквы
            pattern = re.compile(re.escape(phrase), re.IGNORECASE)
            matches = list(pattern.finditer(text))

            for match in matches:
                original = match.group(0)
                replacement = self.rng.choice(replacements)

                # Сохраняем регистр первой буквы
                if original[0].isupper() and replacement[0].islower():
                    replacement = replacement[0].upper() + replacement[1:]
                elif original[0].islower() and replacement[0].isupper():
                    replacement = replacement[0].lower() + replacement[1:]

                text = text[:match.start()] + replacement + text[match.end():]

                self.changes.append({
                    "type": "decancel_phrase",
                    "original": original,
                    "replacement": replacement,
                })

                # После замены нужно пересобрать matches
                break  # Обрабатываем одну замену за раз, чтобы не сбить индексы

        return text

    def _replace_words(self, text: str, prob: float) -> str:
        """Заменить однословные канцеляризмы."""
        words = self.lang_pack.get("bureaucratic", {})

        for word, replacements in words.items():
            if not coin_flip(prob, self.rng):
                continue

            # Паттерн: целое слово, с учётом регистра
            pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
            matches = list(pattern.finditer(text))

            for match in reversed(matches):  # Обратный порядок, чтобы не сбить индексы
                if not coin_flip(prob, self.rng):
                    continue

                original = match.group(0)
                replacement = self.rng.choice(replacements)

                # Сохраняем регистр
                if original[0].isupper():
                    replacement = replacement[0].upper() + replacement[1:]
                elif original.isupper():
                    replacement = replacement.upper()

                text = text[:match.start()] + replacement + text[match.end():]

                self.changes.append({
                    "type": "decancel_word",
                    "original": original,
                    "replacement": replacement,
                })

        return text
