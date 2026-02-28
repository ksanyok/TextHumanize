"""Нормализация типографики — приведение к «человеческому» виду."""

from __future__ import annotations

import logging
import re

from texthumanize.utils import get_profile

logger = logging.getLogger(__name__)

# Patterns for email/URL protection during typography normalization
_EMAIL_RE = re.compile(
    r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}'
)
_URL_RE = re.compile(
    r'https?://[^\s<>\"\']+|www\.[^\s<>\"\']+',
)
_DOMAIN_RE = re.compile(
    r'\b[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)+\b',
)

class TypographyNormalizer:
    """Нормализует типографику текста под выбранный профиль.

    Заменяет «идеальные» типографские символы на более естественные:
    - Длинные тире → дефис/короткое тире
    - Типографские кавычки → простые
    - Типографское многоточие → три точки
    - Неразрывные пробелы → обычные
    - Двойные пробелы → одинарные
    """

    def __init__(self, profile: str = "web", lang: str = "ru"):
        self.profile_name = profile
        self.profile = get_profile(profile)
        self.lang = lang
        self.changes: list[dict[str, str]] = []

    def normalize(self, text: str) -> str:
        """Нормализовать типографику текста.

        Args:
            text: Текст для обработки.

        Returns:
            Текст с нормализованной типографикой.
        """
        self.changes = []
        original = text

        # 1. Тире
        text = self._normalize_dashes(text)

        # 2. Кавычки
        text = self._normalize_quotes(text)

        # 3. Многоточие
        text = self._normalize_ellipsis(text)

        # 4. Неразрывные пробелы
        text = self._normalize_spaces(text)

        # 5. Пробелы вокруг знаков
        text = self._fix_punctuation_spaces(text)

        # 6. Множественные пробелы
        text = self._fix_multiple_spaces(text)

        if text != original:
            self.changes.append({
                "type": "typography",
                "description": "Нормализация типографики",
            })

        return text

    def _normalize_dashes(self, text: str) -> str:
        """Нормализовать тире."""
        target = self.profile["typography"]["dash"]

        # Длинное тире (—) → целевое
        if target != "—":
            # Тире между словами: слово — слово
            text = re.sub(r'(?<=\S)\s*—\s*(?=\S)', f' {target} ', text)
            # Тире в начале строки (прямая речь) — оставляем
            # text = re.sub(r'^—\s', f'{target} ', text, flags=re.MULTILINE)

        # Длинное тире (—) без пробелов → с пробелами
        text = re.sub(r'(\w)—(\w)', rf'\1 {target} \2', text)

        return text

    def _normalize_quotes(self, text: str) -> str:
        """Нормализовать кавычки."""
        target = self.profile["typography"]["quotes"]

        if target == '"':
            # Замена типографских кавычек на простые
            text = text.replace('«', '"').replace('»', '"')
            text = text.replace('„', '"').replace('"', '"').replace('"', '"')
            text = text.replace('‹', "'").replace('›', "'")
            text = text.replace('\u201E', '"')  # „
            text = text.replace('\u201C', '"')  # "
            text = text.replace('\u201D', '"')  # "
        elif target == '«»':
            # Замена простых кавычек на типографские (RU/UK)
            text = text.replace('„', '«').replace('"', '»')
            # Простые кавычки заменяем только парами
            text = self._replace_paired_quotes(text, '"', '«', '»')

        return text

    def _replace_paired_quotes(
        self, text: str, char: str, open_q: str, close_q: str
    ) -> str:
        """Заменить парные кавычки."""
        result = []
        in_quote = False
        for c in text:
            if c == char:
                if not in_quote:
                    result.append(open_q)
                    in_quote = True
                else:
                    result.append(close_q)
                    in_quote = False
            else:
                result.append(c)
        return ''.join(result)

    def _normalize_ellipsis(self, text: str) -> str:
        """Нормализовать многоточие (но не leader dots)."""
        target = self.profile["typography"]["ellipsis"]

        if target == "...":
            text = text.replace('\u2026', '...')
        elif target == "\u2026":
            # Только ровно 3 точки → многоточие; ≥4 подряд — это leader dots, не трогаем
            text = re.sub(r'(?<!\.)\.{3}(?!\.)', '\u2026', text)

        return text

    def _normalize_spaces(self, text: str) -> str:
        """Убрать неразрывные пробелы и другие спецпробелы."""
        if self.profile_name in ("formal",):
            return text

        # Неразрывный пробел → обычный
        text = text.replace('\u00A0', ' ')
        # Узкий неразрывный пробел
        text = text.replace('\u202F', ' ')
        # Тонкий пробел
        text = text.replace('\u2009', ' ')
        # Em space, en space
        text = text.replace('\u2003', ' ')
        text = text.replace('\u2002', ' ')

        return text

    def _fix_punctuation_spaces(self, text: str) -> str:
        """Исправить пробелы вокруг знаков препинания."""
        # Protect emails, URLs and domain-like strings
        protected: list[tuple[str, str]] = []
        counter = 0
        for pat in (_EMAIL_RE, _URL_RE, _DOMAIN_RE):
            for m in pat.finditer(text):
                placeholder = f"\x00TYPO{counter}\x00"
                protected.append((placeholder, m.group()))
                text = text.replace(m.group(), placeholder, 1)
                counter += 1

        # Убрать пробел перед , . : ; ! ?  (но НЕ перед leader dots: 4+ точек подряд)
        text = re.sub(r'\s+([,:;!?])', r'\1', text)
        # Пробел перед одиночной точкой (но не перед .... leader dots)
        text = re.sub(r'\s+(\.(?!\.{3}))', r'\1', text)

        # Добавить пробел после , . : ; ! ? если его нет (кроме конца строки)
        text = re.sub(r'([,.:;!?])(?=[A-Za-zА-Яа-яёЁіІїЇєЄґҐ])', r'\1 ', text)

        # Restore protected tokens
        for placeholder, original in reversed(protected):
            text = text.replace(placeholder, original)

        return text

    def _fix_multiple_spaces(self, text: str) -> str:
        """Убрать множественные пробелы."""
        # Не трогаем начало строк (могут быть отступы для кода)
        lines = text.split('\n')
        result = []
        for line in lines:
            # Сохраняем ведущие пробелы
            stripped = line.lstrip()
            leading = line[:len(line) - len(stripped)]
            # Убираем множественные пробелы в содержимом
            stripped = re.sub(r'  +', ' ', stripped)
            result.append(leading + stripped)
        return '\n'.join(result)
