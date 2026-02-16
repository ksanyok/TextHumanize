"""Инъекция «живости» — делает текст более разговорным и человечным."""

from __future__ import annotations

import random
import re

from texthumanize.lang import get_lang_pack
from texthumanize.utils import get_profile, intensity_probability, coin_flip


class LivelinessInjector:
    """Добавляет разговорные маркеры и вариативность пунктуации.

    Контролируемо — работает только для chat/web профилей
    с ограниченной частотой, без повторов маркеров.
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
        """Добавить живость тексту.

        Args:
            text: Текст для обработки.

        Returns:
            Текст с добавленными маркерами живости.
        """
        self.changes = []
        liveliness = self.profile.get("liveliness_intensity", 0.0)
        prob = intensity_probability(self.intensity, liveliness)

        if prob < 0.1:
            return text

        # 1. Вставка разговорных маркеров (очень ограниченно)
        text = self._inject_markers(text, prob)

        # 2. Вариативность пунктуации
        text = self._vary_punctuation(text, prob)

        return text

    def _inject_markers(self, text: str, prob: float) -> str:
        """Вставить разговорные маркеры в некоторые предложения."""
        markers = self.lang_pack.get("colloquial_markers", [])
        if not markers:
            return text

        sentences = re.split(r'(?<=[.!?])\s+', text)
        if len(sentences) < 4:
            return text

        used_markers: set[str] = set()
        max_insertions = max(1, len(sentences) // 8)  # Максимум 1 на 8 предложений
        insertions = 0

        for i in range(len(sentences)):
            if insertions >= max_insertions:
                break

            # Не вставляем в первое предложение и не в каждое
            if i < 2:
                continue

            if not coin_flip(prob * 0.2, self.rng):
                continue

            sent = sentences[i]
            words = sent.split()
            if len(words) < 5:
                continue

            # Выбираем неиспользованный маркер
            available = [m for m in markers if m not in used_markers]
            if not available:
                break

            marker = self.rng.choice(available)
            used_markers.add(marker)

            # Вставляем маркер в начало предложения (после первого слова)
            if len(words) > 2:
                first_word = words[0]
                rest = ' '.join(words[1:])

                # Маркер-вставка: "Слово, маркер, ..."
                if first_word[-1] not in ',.;:':
                    modified = f"{first_word}, {marker}, {rest}"
                else:
                    modified = f"{first_word} {marker}, {rest}"

                sentences[i] = modified
                insertions += 1

                self.changes.append({
                    "type": "liveliness_marker",
                    "marker": marker,
                    "sentence_index": i,
                })

        if insertions > 0:
            return ' '.join(sentences)
        return text

    def _vary_punctuation(self, text: str, prob: float) -> str:
        """Добавить вариативность пунктуации.

        Иногда заменяем точку с запятой на точку,
        или убираем лишние точки с запятой.
        """
        # Заменяем некоторые ; на .  (ИИ часто ставит ;)
        if ';' in text and coin_flip(prob * 0.3, self.rng):
            # Заменяем первую ;
            idx = text.find(';')
            if idx > 0:
                # Проверяем, что после ; идёт пробел и текст
                after = text[idx + 1:].lstrip()
                if after and after[0].islower():
                    after = after[0].upper() + after[1:]

                text = text[:idx] + '.' + ' ' + after
                self.changes.append({
                    "type": "liveliness_punctuation",
                    "description": "Замена ; на .",
                })

        return text
