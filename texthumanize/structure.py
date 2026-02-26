"""Разнообразие структуры предложений и замена ИИ-связок."""

from __future__ import annotations

import random
import re

from texthumanize.lang import get_lang_pack
from texthumanize.segmenter import has_placeholder, skip_placeholder_sentence
from texthumanize.sentence_split import split_sentences
from texthumanize.utils import coin_flip, get_profile, intensity_probability


class StructureDiversifier:
    """Разнообразит структуру текста — убирает однообразие ИИ-генерации.

    - Заменяет повторяющиеся начала предложений
    - Заменяет типичные ИИ-связки
    - Разбивает слишком длинные предложения
    - Склеивает слишком короткие предложения
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
        """Обработать текст: разнообразить структуру.

        Args:
            text: Текст для обработки.

        Returns:
            Текст с разнообразной структурой.
        """
        self.changes = []
        prob = intensity_probability(
            self.intensity,
            self.profile["structure_intensity"],
        )

        if prob < 0.05:
            return text

        # Замена ИИ-связок — работает по regex на всём тексте, безопасно
        text = self._replace_ai_connectors(text, prob)

        # Остальные этапы используют split_sentences + join — нужно
        # обрабатывать каждый параграф/строку отдельно, иначе \n теряются
        text = self._per_paragraph(
            text, self._diversify_sentence_starts, prob,
        )
        text = self._per_paragraph(text, self._split_long_sentences, prob)
        text = self._per_paragraph(text, self._join_short_sentences, prob)

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

    def _replace_ai_connectors(self, text: str, prob: float) -> str:
        """Заменить типичные ИИ-связки."""
        connectors = self.lang_pack.get("ai_connectors", {})
        replaced_count = 0
        max_replacements = max(3, len(connectors) // 2)

        for connector, replacements in connectors.items():
            if replaced_count >= max_replacements:
                break

            # Ищем в начале предложения (после точки/начала текста)
            # Паттерн: начало строки или после .!? и пробела
            pattern = re.compile(
                r'(?:^|(?<=[.!?]\s))' + re.escape(connector) + r'(?=[\s,])',
                re.MULTILINE | re.UNICODE,
            )

            matches = list(pattern.finditer(text))
            if not matches:
                # Попробуем менее строгий паттерн
                pattern = re.compile(
                    r'\b' + re.escape(connector) + r'\b',
                    re.UNICODE,
                )
                matches = list(pattern.finditer(text))

            if not matches:
                continue

            for match in reversed(matches):
                if not coin_flip(prob, self.rng):
                    continue

                if has_placeholder(text[max(0, match.start()-5):match.end()+5]):
                    continue

                original = match.group(0)
                replacement = self.rng.choice(replacements)

                # Пробуем не заменять одинаковым
                attempts = 0
                while replacement.lower() == original.lower() and attempts < 5:
                    replacement = self.rng.choice(replacements)
                    attempts += 1

                # Сохраняем регистр
                if original[0].isupper() and replacement and replacement[0].islower():
                    replacement = replacement[0].upper() + replacement[1:]

                text = text[:match.start()] + replacement + text[match.end():]
                replaced_count += 1

                self.changes.append({
                    "type": "connector_replace",
                    "original": original,
                    "replacement": replacement,
                })
                break  # Одна замена за итерацию для данного коннектора

        return text

    def _diversify_sentence_starts(self, text: str, prob: float) -> str:
        """Разнообразить начала предложений."""
        starters = self.lang_pack.get("sentence_starters", {})
        if not starters:
            return text

        sentences = split_sentences(text, lang=self.lang)
        if len(sentences) < 2:
            return text

        modified = False
        for i in range(1, len(sentences)):
            prev_start = sentences[i - 1].split()[0] if sentences[i - 1].split() else ""
            curr_start = sentences[i].split()[0] if sentences[i].split() else ""

            # Если два предложения подряд начинаются с одного слова
            if (prev_start and curr_start
                    and prev_start.rstrip(',.;:') == curr_start.rstrip(',.;:')
                    and coin_flip(prob, self.rng)):

                # Ищем замену для текущего начала
                clean_start = curr_start.rstrip(',.;:')
                if has_placeholder(clean_start):
                    continue
                alternatives = starters.get(clean_start, [])

                if alternatives:
                    replacement = self.rng.choice(alternatives)
                    words = sentences[i].split()
                    words[0] = replacement
                    sentences[i] = ' '.join(words)
                    modified = True

                    self.changes.append({
                        "type": "sentence_start",
                        "original": curr_start,
                        "replacement": replacement,
                    })

        if modified:
            return ' '.join(sentences)
        return text

    def _split_long_sentences(self, text: str, prob: float) -> str:
        """Разбить слишком длинные предложения."""
        target = self.profile.get("target_sentence_len", (10, 22))
        max_len = target[1] * 2  # Больше двух целевых максимумов

        split_conjs = self.lang_pack.get("split_conjunctions", [])
        if not split_conjs:
            return text

        sentences = split_sentences(text, lang=self.lang)
        result = []

        for sent in sentences:
            word_count = len(sent.split())
            if word_count > max_len and coin_flip(prob, self.rng):
                # Ищем место для разбивки
                split_result = self._try_split_sentence(sent, split_conjs)
                if split_result:
                    result.extend(split_result)
                    self.changes.append({
                        "type": "sentence_split",
                        "original": sent[:50] + "...",
                        "description": f"Предложение из {word_count} слов разбито",
                    })
                    continue
            result.append(sent)

        return ' '.join(result)

    def _try_split_sentence(
        self, sentence: str, split_conjs: list[str]
    ) -> list[str] | None:
        """Попробовать разбить предложение по союзу."""
        if skip_placeholder_sentence(sentence):
            return None
        words = sentence.split()
        mid_point = len(words) // 2
        best_split = None
        best_distance = len(words)

        for conj in split_conjs:
            idx = sentence.find(conj)
            while idx != -1:
                # Считаем позицию в словах
                word_pos = len(sentence[:idx].split())
                distance = abs(word_pos - mid_point)

                # Каждая часть должна быть >= 5 слов
                if (word_pos >= 5
                        and len(words) - word_pos >= 5
                        and distance < best_distance):
                    best_distance = distance
                    best_split = (idx, conj)

                idx = sentence.find(conj, idx + len(conj))

        if best_split:
            idx, conj = best_split
            part1 = sentence[:idx].rstrip().rstrip(',;') + '.'
            part2 = sentence[idx + len(conj):].strip()

            # Делаем первую букву второго предложения заглавной
            if part2 and part2[0].islower():
                part2 = part2[0].upper() + part2[1:]

            return [part1, part2]

        return None

    def _join_short_sentences(self, text: str, prob: float) -> str:
        """Склеить очень короткие предложения."""
        conjunctions = self.lang_pack.get("conjunctions", [])
        if not conjunctions:
            return text

        target = self.profile.get("target_sentence_len", (10, 22))
        min_len = target[0]  # Минимальная целевая длина

        sentences = split_sentences(text, lang=self.lang)
        if len(sentences) < 2:
            return text

        result = []
        i = 0
        while i < len(sentences):
            sent = sentences[i]
            words = sent.split()

            # Если предложение короткое и следующее тоже
            if (i + 1 < len(sentences)
                    and len(words) <= min_len
                    and len(sentences[i + 1].split()) <= min_len
                    and coin_flip(prob * 0.5, self.rng)):

                next_sent = sentences[i + 1]

                # Убираем окончание первого предложения
                first = sent.rstrip()
                if first.endswith(('.', '!', '?')):
                    first = first[:-1]

                # Первая буква второго предложения → строчная
                second = next_sent.strip()
                if second and second[0].isupper() and not has_placeholder(second):
                    second = second[0].lower() + second[1:]

                # Выбираем союз
                conj = self.rng.choice(conjunctions[:4])  # Только простые союзы

                joined = f"{first}, {conj} {second}"
                result.append(joined)

                self.changes.append({
                    "type": "sentence_join",
                    "original": f"{sent} + {next_sent}",
                    "description": "Объединение коротких предложений",
                })
                i += 2
            else:
                result.append(sent)
                i += 1

        return ' '.join(result)
