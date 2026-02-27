"""Сегментатор текста — защита блоков, которые не должны изменяться."""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ── Placeholder sentinel ──────────────────────────────────────
# Null-byte framing is used to mark protected tokens.
PLACEHOLDER_PREFIX = "\x00THZ_"
PLACEHOLDER_SUFFIX = "\x00"
_PLACEHOLDER_RE = re.compile(r'\x00THZ_[A-Z_]+_\d+\x00')

# ── Placeholder-aware helpers (used by ALL pipeline stages) ───


def has_placeholder(text: str) -> bool:
    """Return True if *text* contains any placeholder token."""
    return "\x00" in text


def is_placeholder_word(word: str) -> bool:
    """Return True if a whitespace-delimited word contains a placeholder."""
    return "\x00" in word


def skip_placeholder_sentence(sentence: str) -> bool:
    """Return True if the sentence contains placeholder(s) and
    should be left untouched by word-level transformations."""
    return "\x00" in sentence


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
        """Восстановить защищённые сегменты в обработанном тексте.

        Handles both exact matches and case-corrupted placeholders
        (e.g. lowercased by sentence-join logic).
        """
        result = processed_text
        # Pass 1: exact match (fast path)
        for seg in reversed(self.segments):
            result = result.replace(seg.placeholder, seg.original)

        # Pass 2: if any \x00 markers remain, try case-insensitive recovery
        if "\x00" in result:
            for seg in reversed(self.segments):
                # Build case-insensitive pattern from exact placeholder
                pat = re.compile(re.escape(seg.placeholder), re.IGNORECASE)
                result = pat.sub(seg.original, result)

        # Pass 3: last resort — strip any orphaned placeholder tokens
        if "\x00" in result:
            result = _PLACEHOLDER_RE.sub("", result)
            # Also handle lower-cased remnants
            result = re.sub(r'\x00thz_[a-z_]+_\d+\x00', '', result, flags=re.IGNORECASE)
            # Remove lone null bytes
            result = result.replace("\x00", "")

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
    # HTML block: protect entire paired tag + content (p, div, ul, ol, li, h1-h6, etc.)
    "html_block": re.compile(
        r'<(ul|ol|table|thead|tbody|tr|pre|code|script|style|blockquote)'
        r'(?:\s[^>]*)?>[\s\S]*?</\1\s*>',
        re.IGNORECASE,
    ),
    # URL: handles multi-level TLDs like .com.ua, .kh.ua, .co.uk
    "url": re.compile(
        r'https?://[^\s<>\[\]()\"\']+[^\s<>\[\]()\"\'.,;:!?)]'
        r'|'
        r'www\.[^\s<>\[\]()\"\']+[^\s<>\[\]()\"\'.,;:!?)]',
        re.IGNORECASE,
    ),
    # Bare domain: site.com, site.com.ua, site.kh.ua (without http prefix)
    "bare_domain": re.compile(
        r'\b[a-zA-Z0-9](?:[a-zA-Z0-9\-]*[a-zA-Z0-9])?'
        r'\.(?:com|net|org|info|biz|io|dev|app|pro|me|ua|ru|de|fr|es|it|pl|pt|uk|eu|us|co|in|br)'
        r'(?:\.(?:ua|uk|br|au|nz|za|ar|mx|jp|kr|cn|tw|hk|sg|my|in|il|tr))?'
        r'(?:/[^\s<>\[\]()\"\']*[^\s<>\[\]()\"\'.,;:!?)])?',
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
    # HTML list items: protect <li>...</li> individually
    "html_list_item": re.compile(r'<li\b[^>]*>[\s\S]*?</li\s*>', re.IGNORECASE),
    # Leader dots (TOC, оглавления): "Глава 1 .......... 5"
    "leader_dots": re.compile(r'^.*\.{4,}.*\d+\s*$', re.MULTILINE),
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

        # 3. HTML blocks (ul, ol, table, pre, etc.) — before individual tags
        if self.preserve.get("html", True):
            result = self._protect(result, "html_block", segments)

        # 4. HTML list items (<li>...</li>) — protect individually
        if self.preserve.get("html", True):
            result = self._protect(result, "html_list_item", segments)

        # 5. Markdown-изображения (до ссылок!)
        if self.preserve.get("markdown", True):
            result = self._protect(result, "markdown_image", segments)

        # 6. Markdown-ссылки
        if self.preserve.get("markdown", True):
            result = self._protect(result, "markdown_link", segments)

        # 7. URL (with http/https/www prefix)
        if self.preserve.get("urls", True):
            result = self._protect(result, "url", segments)

        # 8. Bare domains (site.com.ua, example.kh.ua, etc.)
        if self.preserve.get("urls", True):
            result = self._protect(result, "bare_domain", segments)

        # 9. Email
        if self.preserve.get("emails", True):
            result = self._protect(result, "email", segments)

        # 10. HTML-теги (individual opening/closing tags)
        if self.preserve.get("html", True):
            result = self._protect(result, "html_tag", segments)

        # 8. Хэштеги
        if self.preserve.get("hashtags", True):
            result = self._protect(result, "hashtag", segments)

        # 9. Упоминания
        if self.preserve.get("mentions", True):
            result = self._protect(result, "mention", segments)

        # 10. Leader dots (оглавления, TOC)
        result = self._protect(result, "leader_dots", segments)

        # 11. Числа с единицами
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

            def make_replacer(t: str) -> Callable[[re.Match[str]], str]:
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
