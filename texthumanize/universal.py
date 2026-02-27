"""Универсальный обработчик текста — работает для ЛЮБОГО языка без словарей.

Использует статистические и структурные методы, не требующие
языковых пакетов. Для языков с полными словарями (RU, UK, EN, DE, FR, ES и др.)
этот модуль дополняет словарную обработку. Для остальных языков
работает как основной обработчик.

Стратегии:
- Вариация длины предложений (burstiness)
- Нормализация типографики (unicode → ASCII)
- Удаление дубликатов слов в скользящем окне
- Пермутация порядка слов в придаточных
- Вариация пунктуации
- Разрыв монотонного ритма
"""

from __future__ import annotations

import logging
import random
import re

from texthumanize.segmenter import has_placeholder, skip_placeholder_sentence
from texthumanize.sentence_split import split_sentences

logger = logging.getLogger(__name__)

class UniversalProcessor:
    """Универсальная обработка текста: работает для любого языка.

    Не зависит от словарей. Использует статистические и структурные
    методы для устранения признаков AI-генерации.
    """

    def __init__(
        self,
        profile: str = "web",
        intensity: int = 60,
        seed: int | None = None,
    ):
        self.profile = profile
        self.intensity = intensity
        self.rng = random.Random(seed)
        self.changes: list[dict[str, str]] = []

    def process(self, text: str) -> str:
        """Универсальная обработка текста.

        Args:
            text: Текст для обработки.

        Returns:
            Обработанный текст.
        """
        self.changes = []

        if not text or len(text.strip()) < 20:
            return text

        prob = self.intensity / 100.0

        # 1. Универсальная нормализация Unicode-символов
        text = self._normalize_unicode(text, prob)

        # 2. Вариация длины предложений (burstiness)
        text = self._vary_sentence_lengths(text, prob)

        # 3. Удаление повторов слов в скользящем окне (без словаря)
        text = self._reduce_adjacent_repeats(text, prob)

        # 4. Вариация пунктуации
        text = self._vary_punctuation(text, prob)

        # 5. Разрыв монотонного ритма абзацев
        text = self._break_paragraph_rhythm(text, prob)

        return text

    def _normalize_unicode(self, text: str, prob: float) -> str:
        """Нормализовать Unicode-символы, типичные для AI."""
        if prob < 0.1:
            return text

        original = text

        # Универсальные замены (работают для любого языка):

        # Разные виды тире → обычный дефис или короткое тире
        if self.profile in ("chat",):
            text = text.replace('\u2014', '-')   # em dash
            text = text.replace('\u2013', '-')   # en dash
        elif self.profile not in ("formal", "docs"):
            text = text.replace('\u2014', '\u2013')  # em dash → en dash

        # Кавычки-ёлочки и кавычки-лапки → простые
        if self.profile not in ("formal",):
            # Кавычки-ёлочки (русские, французские)
            text = text.replace('\u00AB', '"').replace('\u00BB', '"')
            # Немецкие нижние кавычки
            text = text.replace('\u201E', '"')
            # Английские типографские
            text = text.replace('\u201C', '"').replace('\u201D', '"')
            text = text.replace('\u2018', "'").replace('\u2019', "'")
            # Угловые одинарные
            text = text.replace('\u2039', "'").replace('\u203A', "'")

        # Типографское многоточие → три точки
        if self.profile not in ("formal", "docs"):
            text = text.replace('\u2026', '...')

        # Спецпробелы → обычный
        text = text.replace('\u00A0', ' ')   # nbsp
        text = text.replace('\u202F', ' ')   # narrow nbsp
        text = text.replace('\u2009', ' ')   # thin space
        text = text.replace('\u200B', '')    # zero-width space
        text = text.replace('\u200C', '')    # zero-width non-joiner
        text = text.replace('\u200D', '')    # zero-width joiner
        text = text.replace('\uFEFF', '')    # BOM
        text = text.replace('\u2003', ' ')   # em space
        text = text.replace('\u2002', ' ')   # en space

        # Дефис-минус разных видов → обычный
        text = text.replace('\u2010', '-')   # hyphen
        text = text.replace('\u2011', '-')   # non-breaking hyphen
        text = text.replace('\u2012', '-')   # figure dash

        # Bullet-символы → обычные
        text = text.replace('\u2022', '-')   # bullet
        text = text.replace('\u2023', '-')   # triangular bullet
        text = text.replace('\u25E6', '-')   # white bullet

        if text != original:
            self.changes.append({
                "type": "universal_unicode",
                "description": "Нормализация Unicode-символов",
            })

        return text

    def _vary_sentence_lengths(self, text: str, prob: float) -> str:
        """Добавить вариативность длины предложений (burstiness).

        AI генерирует предложения примерно одной длины (10-20 слов).
        Люди пишут с большим разбросом: 3-30+ слов.
        """
        if prob < 0.3:
            return text

        sentences = split_sentences(text)
        if len(sentences) < 4:
            return text

        # Анализируем текущую вариативность
        lengths = [len(s.split()) for s in sentences]
        avg_len = sum(lengths) / len(lengths)
        if avg_len == 0:
            return text

        variance = sum((sl - avg_len) ** 2 for sl in lengths) / len(lengths)
        cv = (variance ** 0.5) / avg_len  # Коэффициент вариации

        # Если уже достаточно вариативно — не трогаем
        if cv > 0.5:
            return text

        result = list(sentences)
        changed = False

        # Стратегия: разбить некоторые длинные предложения
        for i in range(len(result)):
            if skip_placeholder_sentence(result[i]):
                continue
            words = result[i].split()
            wlen = len(words)

            # Разбить предложение длиннее 2x средней
            if wlen > avg_len * 1.8 and wlen > 15 and self.rng.random() < prob * 0.6:
                split = self._universal_split_sentence(result[i])
                if split:
                    result[i] = split
                    changed = True
                    self.changes.append({
                        "type": "universal_burstiness",
                        "description": f"Разбивка длинного предложения ({wlen} слов)",
                    })

        if changed:
            return ' '.join(result)
        return text

    def _universal_split_sentence(self, sentence: str) -> str | None:
        """Универсальная разбивка предложения (без словаря)."""
        if has_placeholder(sentence):
            return None
        words = sentence.split()
        if len(words) < 12:
            return None

        # Ищем позицию для разбивки: запятая, точка с запятой, или
        # союзоподобное слово ближе к середине
        mid = len(sentence) // 2
        best_pos = None
        best_dist = len(sentence)

        # Ищем запятую/; рядом с серединой
        for sep in ['; ', ', ']:
            idx = -1
            while True:
                idx = sentence.find(sep, idx + 1)
                if idx == -1:
                    break

                # Проверяем что каждая часть >= 4 слова
                left_words = len(sentence[:idx].split())
                right_words = len(sentence[idx + len(sep):].split())
                if left_words >= 4 and right_words >= 4:
                    dist = abs(idx - mid)
                    if dist < best_dist:
                        best_dist = dist
                        best_pos = (idx, sep)

        if best_pos:
            idx, sep = best_pos
            part1 = sentence[:idx].rstrip().rstrip(',;') + '.'
            part2 = sentence[idx + len(sep):].strip()
            if part2 and part2[0].islower():
                part2 = part2[0].upper() + part2[1:]
            return f"{part1} {part2}"

        return None

    def _reduce_adjacent_repeats(self, text: str, prob: float) -> str:
        """Убрать повторы слов без словаря (простая дедупликация).

        Удаляет избыточные повторы содержательных слов
        в пределах скользящего окна. Сохраняет структуру абзацев.
        """
        if prob < 0.2:
            return text

        # Split keeping whitespace tokens to preserve paragraph breaks
        tokens = re.split(r'(\s+)', text)
        # tokens: [word, ws, word, ws, ...]
        # Extract just the words (even indices)
        words = [tokens[i] for i in range(0, len(tokens), 2)]
        if len(words) < 10:
            return text

        seen_content: dict[str, int] = {}
        window = 8
        removed_indices: set[int] = set()
        _skip_before = {
            "the", "a", "an", "this", "that", "these", "those",
            "его", "её", "их", "этот", "эта", "это", "эти",
            "der", "die", "das", "ein", "eine", "le", "la",
            "el", "los", "las", "un", "una",
        }

        for i, word in enumerate(words):
            if has_placeholder(word):
                continue
            clean = re.sub(r'[.,;:!?\'"()\[\]{}]', '', word).lower()
            if len(clean) < 4:
                continue

            if clean in seen_content:
                last_pos = seen_content[clean]
                if i - last_pos <= window and self.rng.random() < prob * 0.5:
                    removed_indices.add(i)
                    if i > 0:
                        prev_clean = re.sub(
                            r'[.,;:!?\'"()\[\]{}]', '',
                            words[i - 1],
                        ).lower()
                        if prev_clean in _skip_before:
                            removed_indices.add(i - 1)
                    self.changes.append({
                        "type": "universal_repeat",
                        "description": f"Убран повтор: {clean}",
                    })

            seen_content[clean] = i

        if not removed_indices:
            return text

        # Rebuild preserving original whitespace
        result_parts: list[str] = []
        for i, word in enumerate(words):
            if i in removed_indices:
                continue
            if result_parts:
                # Get the whitespace before this word
                ws_idx = i * 2 - 1
                if 0 < ws_idx < len(tokens):
                    result_parts.append(tokens[ws_idx])
                else:
                    result_parts.append(' ')
            result_parts.append(word)
        return ''.join(result_parts)

    def _vary_punctuation(self, text: str, prob: float) -> str:
        """Добавить вариативность пунктуации."""
        if prob < 0.2:
            return text

        # AI часто использует ; — заменяем часть на .
        if ';' in text and self.rng.random() < prob * 0.5:
            parts = text.split(';')
            if len(parts) >= 2:
                # Заменяем первый ; на .
                idx = text.find(';')
                before = text[:idx].rstrip()
                after = text[idx + 1:].lstrip()
                if after and after[0].islower() and not has_placeholder(after):
                    after = after[0].upper() + after[1:]
                text = before + '. ' + after
                self.changes.append({
                    "type": "universal_punct",
                    "description": "Замена ; на .",
                })

        # AI часто ставит : для пояснений — иногда заменяем на . или —
        if text.count(':') > 2 and self.rng.random() < prob * 0.3:
            # Заменяем один : на . (тот, что не в URL и не в начале строки)
            for m in re.finditer(r'(?<!https)(?<!http):\s', text):
                pos = m.start()
                before = text[:pos]
                after = text[pos + 1:].lstrip()
                if after and after[0].islower() and not has_placeholder(after):
                    after = after[0].upper() + after[1:]
                text = before + '. ' + after
                self.changes.append({
                    "type": "universal_punct",
                    "description": "Замена : на .",
                })
                break

        return text

    def _break_paragraph_rhythm(self, text: str, prob: float) -> str:
        """Разбить монотонный ритм абзацев.

        AI часто генерирует абзацы примерно одного размера.
        """
        if prob < 0.4:
            return text

        paragraphs = text.split('\n\n')
        if len(paragraphs) < 3:
            return text

        # Анализируем размеры абзацев
        sizes = [len(p.split()) for p in paragraphs]
        avg_size = sum(sizes) / len(sizes)
        if avg_size == 0:
            return text

        cv = ((sum((s - avg_size) ** 2 for s in sizes) / len(sizes)) ** 0.5) / avg_size

        # Если абзацы уже разнообразные — не трогаем
        if cv > 0.4:
            return text

        # Стратегия: объединить два самых маленьких соседних абзаца
        modified = False
        result = list(paragraphs)

        for i in range(len(result) - 1):
            if (len(result[i].split()) <= avg_size * 0.7
                    and len(result[i + 1].split()) <= avg_size * 0.7
                    and self.rng.random() < prob * 0.3):
                result[i] = result[i].rstrip() + ' ' + result[i + 1].lstrip()
                result[i + 1] = ''
                modified = True
                self.changes.append({
                    "type": "universal_paragraph",
                    "description": "Объединение маленьких абзацев",
                })
                break

        if modified:
            return '\n\n'.join(p for p in result if p.strip())
        return text
