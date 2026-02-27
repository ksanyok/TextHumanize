"""Умный сплиттер предложений — корректная сегментация с учётом аббревиатур.

Решает проблемы наивного regex-подхода:
- Аббревиатуры (т.д., Mr., Inc.)
- Десятичные числа (3.14)
- Инициалы (А.С. Пушкин)
- Прямая речь ("Привет!" — сказал он.)
- URL и email внутри предложений
- Многоточие (...)
- Вложенные кавычки и скобки
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from functools import lru_cache

from texthumanize.lang import get_lang_pack

logger = logging.getLogger(__name__)

@dataclass
class SentenceSpan:
    """Предложение с позициями в исходном тексте."""
    text: str
    start: int
    end: int
    index: int = 0


class SentenceSplitter:
    """Умный сплиттер предложений с учётом контекста.

    Учитывает:
    - Аббревиатуры из lang pack
    - Десятичные числа
    - Инициалы
    - Прямую речь
    - URL/email (уже защищены segmenter-ом)
    - Многоточие
    - Стэк кавычек/скобок
    """

    # Универсальные аббревиатуры (все языки)
    _UNIVERSAL_ABBREVS = {
        "mr", "mrs", "ms", "dr", "prof", "sr", "jr", "inc", "ltd",
        "corp", "etc", "vs", "approx", "dept", "est", "govt",
        "intl", "no", "nos", "vol", "vols", "rev", "fig", "misc",
        "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep",
        "oct", "nov", "dec",
        "www", "http", "https", "ftp",
    }

    def __init__(self, lang: str = "en"):
        self.lang = lang
        lang_pack = get_lang_pack(lang)
        # Собираем все аббревиатуры: из lang pack + универсальные
        pack_abbrevs = lang_pack.get("abbreviations", [])
        self._abbreviations = (
            {a.lower().rstrip('.') for a in pack_abbrevs}
            | self._UNIVERSAL_ABBREVS
        )

    def split(self, text: str) -> list[str]:
        """Разбить текст на предложения.

        Args:
            text: Текст для разбиения.

        Returns:
            Список предложений.
        """
        if not text or not text.strip():
            return []

        spans = self.split_spans(text)
        return [s.text for s in spans]

    def split_spans(self, text: str) -> list[SentenceSpan]:
        """Разбить текст на предложения с позициями.

        Args:
            text: Текст для разбиения.

        Returns:
            Список SentenceSpan с позициями.
        """
        if not text or not text.strip():
            return []

        # Шаг 1: Находим все потенциальные точки разрыва
        breaks = self._find_breaks(text)

        # Шаг 2: Разбиваем текст по точкам разрыва
        sentences: list[SentenceSpan] = []
        start = 0
        for brk in breaks:
            sent_text = text[start:brk].strip()
            if sent_text:
                sentences.append(SentenceSpan(
                    text=sent_text,
                    start=start,
                    end=brk,
                    index=len(sentences),
                ))
            start = brk

        # Последнее предложение
        last = text[start:].strip()
        if last:
            sentences.append(SentenceSpan(
                text=last,
                start=start,
                end=len(text),
                index=len(sentences),
            ))

        return sentences

    def _find_breaks(self, text: str) -> list[int]:
        """Найти позиции разрыва предложений."""
        breaks = []

        # Размечаем «защищённые» зоны (не-разрыв)
        protected = self._build_protected_zones(text)

        # Находим все потенциальные концы предложений
        # Паттерн: .!? + опциональные закрывающие + пробел + Заглавная
        for m in re.finditer(
            r'([.!?…][\"\'\»\"\)\]]*)\s+',
            text,
        ):
            pos = m.end()  # Позиция начала следующего предложения
            dot_pos = m.start()  # Позиция пунктуации

            # Проверяем, не в защищённой зоне ли
            if self._in_protected(dot_pos, protected):
                continue

            # Проверяем, что после пробела идёт заглавная или кавычка
            if pos < len(text):
                next_char = text[pos]
                if not (next_char.isupper() or next_char in '"\'«"(—\x00'):
                    continue

            # Проверяем, что это не аббревиатура
            if text[dot_pos] == '.':
                word_before = self._get_word_before_dot(text, dot_pos)
                if word_before and word_before.lower() in self._abbreviations:
                    continue

                # Проверяем инициалы (одна буква перед точкой)
                if word_before and len(word_before) == 1 and word_before.isalpha():
                    continue

            breaks.append(pos)

        return sorted(set(breaks))

    def _build_protected_zones(self, text: str) -> list[tuple[int, int]]:
        """Построить список «защищённых» зон (не разбивать внутри)."""
        zones: list[tuple[int, int]] = []

        # Placeholders от segmenter (\x00THZ_...\x00)
        for m in re.finditer(r'\x00THZ_[A-Z_]+_\d+\x00', text):
            zones.append((m.start(), m.end()))

        # Кавычки-блоки (прямая речь)
        for m in re.finditer(r'"[^"]*"', text):
            if len(m.group()) < 500:  # Не слишком длинные
                zones.append((m.start(), m.end()))
        for m in re.finditer(r'«[^»]*»', text):
            if len(m.group()) < 500:
                zones.append((m.start(), m.end()))

        # Скобки
        for m in re.finditer(r'\([^)]*\)', text):
            if len(m.group()) < 300:
                zones.append((m.start(), m.end()))

        # Многоточие как часть предложения (не конец)
        for m in re.finditer(r'\.\.\.(?!\s+[A-ZА-ЯЁІЇЄҐ])', text):
            zones.append((m.start(), m.end()))

        # Десятичные числа (3.14, 2.5, 0.001)
        for m in re.finditer(r'\d+\.\d+', text):
            zones.append((m.start(), m.end()))

        # Числа с единицами (3.5 млн, 1.2 тыс., $1.5M, 2.0x)
        for m in re.finditer(
            r'\d+\.\d+\s*(?:млн|млрд|тыс|мільйонів|тис|Mio|Mrd|'
            r'M|B|K|x|%|km|m|kg|g|l|ml|GB|MB|TB)\b',
            text, re.IGNORECASE,
        ):
            zones.append((m.start(), m.end()))

        # Порядковые числительные с точкой (нем/пл: 1., 2., 15.)
        for m in re.finditer(r'\b\d{1,4}\.(?=\s+[a-zа-яёіїєґüöäß])', text):
            zones.append((m.start(), m.end()))

        # IP-адреса (192.168.0.1)
        for m in re.finditer(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', text):
            zones.append((m.start(), m.end()))

        # Версии (v2.3.1, 3.11.0)
        for m in re.finditer(r'\b[vV]?\d+\.\d+(?:\.\d+)*\b', text):
            zones.append((m.start(), m.end()))

        # Сокращения с точками: т.д., т.п., т.е., etc.
        for m in re.finditer(
            r'(?:т\.д|т\.п|т\.е|и т\.д|и т\.п|т\.к|т\.н|т\.ін|і т\.д|і т\.п'
            r'|e\.g|i\.e|a\.m|p\.m|vs|p\.s|P\.S'
            r'|к\.т\.н|д\.т\.н|Ph\.D|M\.D|B\.A|M\.A'
            r'|St\.|Mt\.|Ft\.|Ltd\.|Corp\.|Bros'
            r'|тис\.|грн\.|руб\.|коп\.|млн\.|млрд'
            r'|r\.r\.|n\.e\.|p\.n\.e'
            r'|S\.p\.A|S\.r\.l|S\.A|S\.L'
            r'|z\.B|d\.h|u\.a|bzw|ggf|inkl|bzgl)\.',
            text, re.IGNORECASE,
        ):
            zones.append((m.start(), m.end()))

        return zones

    def _in_protected(self, pos: int, zones: list[tuple[int, int]]) -> bool:
        """Проверить, попадает ли позиция в защищённую зону."""
        for start, end in zones:
            if start <= pos < end:
                return True
        return False

    def _get_word_before_dot(self, text: str, dot_pos: int) -> str:
        """Извлечь слово перед точкой."""
        if dot_pos <= 0:
            return ""
        end = dot_pos
        start = end - 1
        while start > 0 and text[start - 1].isalpha():
            start -= 1
        # Проверяем: может это сокращение с точками (т.д.)
        word = text[start:end]
        # Расширяем: ищем сокращение с дополнительной точкой перед ним
        if start > 1 and text[start - 1] == '.' and start > 2 and text[start - 2].isalpha():
            wider_start = start - 2
            while wider_start > 0 and (
                text[wider_start - 1].isalpha() or text[wider_start - 1] == '.'
            ):
                wider_start -= 1
            wider = text[wider_start:end]
            if wider.count('.') >= 1:
                return wider.replace('.', '')
        return word

    def repair(self, sentences: list[str]) -> list[str]:
        """Восстановить ошибочно разбитые предложения.

        Объединяет предложения, если:
        - Первое оканчивается строчной буквой
        - Второе начинается со строчной буквы
        - Слишком короткие фрагменты
        """
        if len(sentences) < 2:
            return sentences

        result = [sentences[0]]

        for i in range(1, len(sentences)):
            prev = result[-1]
            curr = sentences[i]

            should_merge = False

            # Если предыдущее не заканчивается .!?
            if prev and prev[-1] not in '.!?…':
                should_merge = True

            # Если текущее начинается со строчной
            if curr and curr[0].islower():
                should_merge = True

            # Если предыдущее слишком короткое (1-2 слова) и не восклицание
            if prev and len(prev.split()) <= 2 and prev[-1] not in '.!?…':
                should_merge = True

            if should_merge:
                result[-1] = prev + ' ' + curr
            else:
                result.append(curr)

        return result


# ─── Кэш для сплиттеров по языкам ────────────────────────────
_splitter_cache: dict[str, SentenceSplitter] = {}


def _get_splitter(lang: str) -> SentenceSplitter:
    """Получить или создать кэшированный сплиттер для языка."""
    if lang not in _splitter_cache:
        _splitter_cache[lang] = SentenceSplitter(lang=lang)
    return _splitter_cache[lang]


# LRU-кэш для результатов split_sentences (до 256 уникальных текстов)
@lru_cache(maxsize=256)
def _cached_split(text: str, lang: str) -> tuple[str, ...]:
    """Кэшированная версия split для одинаковых текстов."""
    splitter = _get_splitter(lang)
    return tuple(splitter.split(text))


def split_sentences(text: str, lang: str = "en") -> list[str]:
    """Удобная функция для разбивки текста на предложения.

    Результаты кэшируются — повторный вызов с тем же текстом
    не пересчитывает разбивку.

    Args:
        text: Текст для разбиения.
        lang: Код языка.

    Returns:
        Список предложений.
    """
    return list(_cached_split(text, lang))


def split_sentences_with_spans(text: str, lang: str = "en") -> list[SentenceSpan]:
    """Разбить текст с позициями.

    Args:
        text: Текст.
        lang: Код языка.

    Returns:
        Список SentenceSpan.
    """
    splitter = _get_splitter(lang)
    return splitter.split_spans(text)
