"""Инъекция «живости» — делает текст более разговорным и человечным."""

from __future__ import annotations

import random

from texthumanize.lang import get_lang_pack
from texthumanize.sentence_split import split_sentences
from texthumanize.utils import coin_flip, get_profile, intensity_probability


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
        self.changes: list[dict[str, str | int]] = []

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

        # 1. Вставка разговорных маркеров (split_sentences + join →
        #    обрабатываем построчно для сохранения структуры)
        text = self._per_paragraph(text, self._inject_markers, prob)

        # 2. Вариативность пунктуации (regex — безопасно)
        text = self._vary_punctuation(text, prob)

        return text

    # ─── Paragraph-safe wrapper ────────────────────────────────

    def _per_paragraph(
        self,
        text: str,
        fn: object,
        *args: object,
    ) -> str:
        """Применить *fn* к каждой непустой строке независимо.

        Сохраняет структуру абзацев/списков: строки, разделённые ``\\n``,
        обрабатываются по отдельности и не склеиваются друг с другом.
        """
        lines = text.split('\n')
        result: list[str] = []
        for line in lines:
            if line.strip():
                result.append(fn(line, *args))  # type: ignore[operator]
            else:
                result.append(line)
        return '\n'.join(result)

    def _inject_markers(self, text: str, prob: float) -> str:
        """Вставить разговорные маркеры в некоторые предложения."""
        markers = self.lang_pack.get("colloquial_markers", [])
        if not markers:
            return text

        sentences = split_sentences(text, lang=self.lang)
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
