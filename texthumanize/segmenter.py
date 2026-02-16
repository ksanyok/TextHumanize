"""Сегментатор текста — защита блоков, которые не должны изменяться."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class ProtectedSegment:
    """Защищённый сегмент текста."""
    placeholder: str
    original: str
    kind: str  # code_block, inline_code, url, email, html_tag, hashtag, mention, number


@dataclass
class SegmentedText:
    """Текст с защищёнными сегментами."""
    text: str
    segments: list[ProtectedSegment] = field(default_factory=list)

    def restore(self, processed_text: str) -> str:
        """Восстановить защищённые сегменты в обработанном тексте."""
        result = processed_text
        # Восстанавливаем в обратном порядке, чтобы индексы не сбивались
        for seg in reversed(self.segments):
            result = result.replace(seg.placeholder, seg.original)
        return result


# Регулярные выражения для защищаемых элементов
_PATTERNS = {
    "code_block": re.compile(
        r'```[\s\S]*?```'
        r'|'
        r'~~~[\s\S]*?~~~',
        re.MULTILINE,
    ),
    "inline_code": re.compile(r'`[^`\n]+?`'),
    "url": re.compile(
        r'https?://[^\s<>\[\]()\"\']+[^\s<>\[\]()\"\'.,;:!?)]'
        r'|'
        r'www\.[^\s<>\[\]()\"\']+[^\s<>\[\]()\"\'.,;:!?)]',
        re.IGNORECASE,
    ),
    "email": re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}'),
    "html_tag": re.compile(r'</?[a-zA-Z][^>]*?>'),
    "hashtag": re.compile(r'#[a-zA-Zа-яА-ЯёЁіІїЇєЄґҐ0-9_]+'),
    "mention": re.compile(r'@[a-zA-Z0-9_]+'),
    "markdown_link": re.compile(r'\[([^\]]+)\]\(([^)]+)\)'),
    "markdown_image": re.compile(r'!\[([^\]]*)\]\(([^)]+)\)'),
    "markdown_heading": re.compile(r'^#{1,6}\s+', re.MULTILINE),
    "markdown_bold": re.compile(r'\*\*[^*]+?\*\*|__[^_]+?__'),
    "markdown_italic": re.compile(r'(?<!\*)\*[^*]+?\*(?!\*)|(?<!_)_[^_]+?_(?!_)'),
}

# Паттерн для чисел с единицами измерения
_NUMBER_PATTERN = re.compile(
    r'\b\d+(?:[.,]\d+)?(?:\s*(?:руб|грн|USD|EUR|%|°[CF]?'
    r'|кг|г|мг|т|км|м|см|мм|л|мл|шт|чел|раз'
    r'|KB|MB|GB|TB|px|em|rem|pt))?\.?\b',
    re.IGNORECASE,
)


class Segmenter:
    """Сегментатор для защиты неизменяемых частей текста."""

    def __init__(self, preserve: dict | None = None):
        """
        Args:
            preserve: Словарь настроек защиты.
                code_blocks, urls, emails, hashtags, mentions,
                markdown, html, numbers, brand_terms.
        """
        self.preserve = preserve or {
            "code_blocks": True,
            "urls": True,
            "emails": True,
            "hashtags": True,
            "mentions": True,
            "markdown": True,
            "html": True,
            "numbers": False,
            "brand_terms": [],
        }
        self._counter = 0

    def _make_placeholder(self, kind: str) -> str:
        """Создать уникальный placeholder."""
        self._counter += 1
        return f"\x00THZ_{kind.upper()}_{self._counter}\x00"

    def segment(self, text: str) -> SegmentedText:
        """Разобрать текст и защитить неизменяемые части.

        Args:
            text: Исходный текст.

        Returns:
            SegmentedText с placeholders вместо защищённых элементов.
        """
        self._counter = 0
        segments: list[ProtectedSegment] = []
        result = text

        # Порядок важен: сначала крупные блоки, потом мелкие

        # 1. Блоки кода
        if self.preserve.get("code_blocks", True):
            result = self._protect(result, "code_block", segments)

        # 2. Inline-код
        if self.preserve.get("code_blocks", True):
            result = self._protect(result, "inline_code", segments)

        # 3. Markdown-изображения (до ссылок!)
        if self.preserve.get("markdown", True):
            result = self._protect(result, "markdown_image", segments)

        # 4. Markdown-ссылки
        if self.preserve.get("markdown", True):
            result = self._protect(result, "markdown_link", segments)

        # 5. URL
        if self.preserve.get("urls", True):
            result = self._protect(result, "url", segments)

        # 6. Email
        if self.preserve.get("emails", True):
            result = self._protect(result, "email", segments)

        # 7. HTML-теги
        if self.preserve.get("html", True):
            result = self._protect(result, "html_tag", segments)

        # 8. Хэштеги
        if self.preserve.get("hashtags", True):
            result = self._protect(result, "hashtag", segments)

        # 9. Упоминания
        if self.preserve.get("mentions", True):
            result = self._protect(result, "mention", segments)

        # 10. Числа с единицами
        if self.preserve.get("numbers", False):
            result = self._protect_numbers(result, segments)

        # 11. Брендовые термины
        brand_terms = self.preserve.get("brand_terms", [])
        if brand_terms:
            result = self._protect_terms(result, brand_terms, segments)

        # 12. Ключевые слова для SEO
        keep_keywords = self.preserve.get("keep_keywords", [])
        if keep_keywords:
            result = self._protect_terms(result, keep_keywords, segments)

        return SegmentedText(text=result, segments=segments)

    def _protect(
        self,
        text: str,
        kind: str,
        segments: list[ProtectedSegment],
    ) -> str:
        """Защитить все вхождения паттерна."""
        pattern = _PATTERNS.get(kind)
        if not pattern:
            return text

        def replacer(match: re.Match) -> str:
            placeholder = self._make_placeholder(kind)
            segments.append(ProtectedSegment(
                placeholder=placeholder,
                original=match.group(0),
                kind=kind,
            ))
            return placeholder

        return pattern.sub(replacer, text)

    def _protect_numbers(
        self,
        text: str,
        segments: list[ProtectedSegment],
    ) -> str:
        """Защитить числа."""
        def replacer(match: re.Match) -> str:
            placeholder = self._make_placeholder("number")
            segments.append(ProtectedSegment(
                placeholder=placeholder,
                original=match.group(0),
                kind="number",
            ))
            return placeholder

        return _NUMBER_PATTERN.sub(replacer, text)

    def _protect_terms(
        self,
        text: str,
        terms: list[str],
        segments: list[ProtectedSegment],
    ) -> str:
        """Защитить конкретные термины."""
        for term in terms:
            if not term:
                continue
            escaped = re.escape(term)
            pattern = re.compile(r'\b' + escaped + r'\b', re.IGNORECASE)

            def make_replacer(t: str):
                def replacer(match: re.Match) -> str:
                    placeholder = self._make_placeholder("brand_term")
                    segments.append(ProtectedSegment(
                        placeholder=placeholder,
                        original=match.group(0),
                        kind="brand_term",
                    ))
                    return placeholder
                return replacer

            text = pattern.sub(make_replacer(term), text)
        return text
