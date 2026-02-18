"""Обнаружение и удаление водяных знаков из текста.

Выявляет скрытые маркеры:
- Unicode-стеганография (zero-width characters, homoglyphs)
- AI watermarks (статистические паттерны)
- Скрытые метаданные (невидимые символы)
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field


@dataclass
class WatermarkReport:
    """Результат проверки водяных знаков."""

    has_watermarks: bool = False
    watermark_types: list[str] = field(default_factory=list)
    details: list[str] = field(default_factory=list)
    cleaned_text: str = ""
    characters_removed: int = 0
    homoglyphs_found: list[tuple[str, str, int]] = field(default_factory=list)
    # (original_char, expected_char, position)
    zero_width_count: int = 0
    confidence: float = 0.0


# ═══════════════════════════════════════════════════════════════
#  ZERO-WIDTH CHARACTERS
# ═══════════════════════════════════════════════════════════════

# Все zero-width и невидимые символы Unicode
_ZERO_WIDTH_CHARS = {
    '\u200b',  # Zero Width Space
    '\u200c',  # Zero Width Non-Joiner
    '\u200d',  # Zero Width Joiner
    '\u200e',  # Left-to-Right Mark
    '\u200f',  # Right-to-Left Mark
    '\u2060',  # Word Joiner
    '\u2061',  # Function Application
    '\u2062',  # Invisible Times
    '\u2063',  # Invisible Separator
    '\u2064',  # Invisible Plus
    '\ufeff',  # Zero Width No-Break Space (BOM)
    '\u00ad',  # Soft Hyphen
    '\u034f',  # Combining Grapheme Joiner
    '\u061c',  # Arabic Letter Mark
    '\u180e',  # Mongolian Vowel Separator
}

# Расширенный набор (категории Unicode Cf, Mn в нестандартных позициях)
_INVISIBLE_CATEGORIES = {'Cf', 'Cc'}  # Format chars, Control chars

# ═══════════════════════════════════════════════════════════════
#  HOMOGLYPH DETECTION
# ═══════════════════════════════════════════════════════════════

# Латинские буквы ↔ кириллические (визуально идентичные)
_CYRILLIC_TO_LATIN = {
    'а': 'a', 'с': 'c', 'е': 'e', 'о': 'o', 'р': 'p',
    'х': 'x', 'у': 'y', 'А': 'A', 'В': 'B', 'С': 'C',
    'Е': 'E', 'Н': 'H', 'К': 'K', 'М': 'M', 'О': 'O',
    'Р': 'P', 'Т': 'T', 'Х': 'X',
}

_LATIN_TO_CYRILLIC = {v: k for k, v in _CYRILLIC_TO_LATIN.items()}

# Специальные символы (выглядят как обычные, но из других кодовых блоков)
_SPECIAL_HOMOGLYPHS = {
    # Fullwidth Latin
    '\uff41': 'a', '\uff42': 'b', '\uff43': 'c', '\uff44': 'd',
    '\uff45': 'e', '\uff46': 'f', '\uff47': 'g',
    # Mathematical symbols that look like letters
    '\u2202': 'd',  # Partial Differential → d
    '\u0435': 'e',  # Cyrillic е → Latin e
    '\u03b1': 'a',  # Greek alpha → a
    '\u03bf': 'o',  # Greek omicron → o
    '\u0456': 'i',  # Ukrainian і → Latin i
    '\u0430': 'a',  # Cyrillic а → Latin a
    # Subscript/superscript numbers
    '\u00b2': '2', '\u00b3': '3', '\u00b9': '1',
    '\u2070': '0', '\u2071': 'i',
    # Confusable punctuation
    '\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"',
    '\u2012': '-', '\u2013': '-', '\u2014': '-',
    '\u2212': '-',  # minus sign vs hyphen
    '\u00a0': ' ',  # Non-breaking space
    '\u2003': ' ',  # Em space
    '\u2002': ' ',  # En space
    '\u2009': ' ',  # Thin space
    '\u200a': ' ',  # Hair space
    '\u205f': ' ',  # Medium Mathematical Space
    '\u3000': ' ',  # Ideographic Space
}


class WatermarkDetector:
    """Обнаружение и удаление водяных знаков."""

    def __init__(self, lang: str = "en"):
        self.lang = lang

    def detect(self, text: str) -> WatermarkReport:
        """Обнаружить водяные знаки в тексте.

        Args:
            text: Текст для проверки.

        Returns:
            WatermarkReport с обнаруженными маркерами.
        """
        report = WatermarkReport()
        report.cleaned_text = text

        # 1. Zero-width characters
        self._detect_zero_width(text, report)

        # 2. Homoglyphs
        self._detect_homoglyphs(text, report)

        # 3. Invisible Unicode characters
        self._detect_invisible(text, report)

        # 4. Unusual spacing patterns
        self._detect_spacing_anomalies(text, report)

        # 5. Statistical watermark patterns
        self._detect_statistical_watermarks(text, report)

        # Determine overall result
        report.has_watermarks = len(report.watermark_types) > 0
        if report.has_watermarks:
            report.confidence = min(
                0.3 + 0.15 * len(report.watermark_types) +
                0.01 * report.characters_removed +
                0.05 * len(report.homoglyphs_found),
                1.0
            )

        return report

    def clean(self, text: str) -> str:
        """Удалить все обнаруженные водяные знаки.

        Args:
            text: Текст для очистки.

        Returns:
            Очищенный текст.
        """
        report = self.detect(text)
        return report.cleaned_text

    # ───────────────────────────────────────────────────────────
    #  ZERO-WIDTH
    # ───────────────────────────────────────────────────────────

    def _detect_zero_width(self, text: str, report: WatermarkReport) -> None:
        count = 0
        cleaned = []

        for ch in text:
            if ch in _ZERO_WIDTH_CHARS:
                count += 1
            else:
                cleaned.append(ch)

        if count > 0:
            report.watermark_types.append("zero_width_characters")
            report.details.append(
                f"Found {count} zero-width/invisible characters"
            )
            report.zero_width_count = count
            report.characters_removed += count
            report.cleaned_text = "".join(cleaned)

    # ───────────────────────────────────────────────────────────
    #  HOMOGLYPHS
    # ───────────────────────────────────────────────────────────

    def _detect_homoglyphs(self, text: str, report: WatermarkReport) -> None:
        # Determine expected script
        is_cyrillic = self.lang in ("ru", "uk")

        homoglyphs: list[tuple[str, str, int]] = []
        chars = list(report.cleaned_text)

        for i, ch in enumerate(chars):
            if is_cyrillic:
                # В кириллическом тексте ищем латинские подмены
                if ch in _LATIN_TO_CYRILLIC:
                    # Проверяем контекст: если соседи — кириллица, то это подмена
                    left = chars[i - 1] if i > 0 else ' '
                    right = chars[i + 1] if i < len(chars) - 1 else ' '
                    if self._is_cyrillic(left) or self._is_cyrillic(right):
                        expected = _LATIN_TO_CYRILLIC[ch]
                        homoglyphs.append((ch, expected, i))
                        chars[i] = expected
            else:
                # В латинском тексте ищем кириллические подмены
                if ch in _CYRILLIC_TO_LATIN:
                    left = chars[i - 1] if i > 0 else ' '
                    right = chars[i + 1] if i < len(chars) - 1 else ' '
                    if self._is_latin(left) or self._is_latin(right):
                        expected = _CYRILLIC_TO_LATIN[ch]
                        homoglyphs.append((ch, expected, i))
                        chars[i] = expected

            # Проверяем специальные гомоглифы
            if ch in _SPECIAL_HOMOGLYPHS:
                expected = _SPECIAL_HOMOGLYPHS[ch]
                if ch != expected:
                    homoglyphs.append((ch, expected, i))
                    chars[i] = expected

        if homoglyphs:
            report.watermark_types.append("homoglyph_substitution")
            report.homoglyphs_found = homoglyphs
            report.details.append(
                f"Found {len(homoglyphs)} homoglyph substitutions"
            )
            report.characters_removed += len(homoglyphs)
            report.cleaned_text = "".join(chars)

    # ───────────────────────────────────────────────────────────
    #  INVISIBLE UNICODE
    # ───────────────────────────────────────────────────────────

    def _detect_invisible(self, text: str, report: WatermarkReport) -> None:
        """Detect invisible Unicode characters by category."""
        count = 0
        cleaned = []

        for ch in report.cleaned_text:
            cat = unicodedata.category(ch)
            # Allow normal whitespace and newlines
            if ch in ('\n', '\r', '\t', ' '):
                cleaned.append(ch)
                continue
            # Detect format characters (Cf) that aren't zero-width (already handled)
            if cat in ('Cf',) and ch not in _ZERO_WIDTH_CHARS:
                count += 1
            else:
                cleaned.append(ch)

        if count > 0:
            report.watermark_types.append("invisible_unicode")
            report.details.append(
                f"Found {count} invisible Unicode format characters"
            )
            report.characters_removed += count
            report.cleaned_text = "".join(cleaned)

    # ───────────────────────────────────────────────────────────
    #  SPACING ANOMALIES
    # ───────────────────────────────────────────────────────────

    def _detect_spacing_anomalies(self, text: str, report: WatermarkReport) -> None:
        """Detect unusual spacing patterns that could encode information."""
        cleaned = report.cleaned_text

        # Multiple consecutive spaces (could encode binary data)
        multi_space = re.findall(r' {2,}', cleaned)
        if len(multi_space) > 5:
            report.watermark_types.append("spacing_steganography")
            report.details.append(
                f"Found {len(multi_space)} unusual multi-space sequences"
            )
            # Normalize to single spaces
            cleaned = re.sub(r' {2,}', ' ', cleaned)
            report.cleaned_text = cleaned

        # Trailing spaces on lines (could encode bits)
        lines = cleaned.split('\n')
        trailing_count = sum(1 for line in lines if line != line.rstrip(' '))
        if trailing_count > 3:
            report.watermark_types.append("trailing_space_steganography")
            report.details.append(
                f"Found {trailing_count} lines with trailing spaces"
            )
            cleaned = '\n'.join(line.rstrip(' ') for line in lines)
            report.cleaned_text = cleaned

    # ───────────────────────────────────────────────────────────
    #  STATISTICAL WATERMARKS
    # ───────────────────────────────────────────────────────────

    def _detect_statistical_watermarks(
        self, text: str, report: WatermarkReport
    ) -> None:
        """Detect statistical watermark patterns used by AI systems.

        Some AI watermarking schemes bias token selection toward
        "green list" tokens. This manifests as unusual bigram distributions.
        """
        words = re.findall(r'\b\w+\b', text.lower())
        if len(words) < 50:
            return

        # Check for unusually biased word choices
        # AI watermarks often create slight biases in synonym selection
        # that make word distribution slightly non-natural

        # 1. Check if word endings are suspiciously uniform
        endings_2 = [w[-2:] for w in words if len(w) > 3]
        if endings_2:
            from collections import Counter
            ending_counts = Counter(endings_2)
            total = len(endings_2)
            # If any 2-char ending appears in >15% of words (unusual)
            for ending, count in ending_counts.most_common(3):
                ratio = count / total
                if ratio > 0.15 and ending not in ("ed", "ly", "ng", "er", "on",
                                                    "al", "le", "es", "ts", "ть",
                                                    "ий", "ый", "ет", "на"):
                    report.watermark_types.append("statistical_bias")
                    report.details.append(
                        f"Suspicious word ending bias: '{ending}' appears "
                        f"in {ratio:.1%} of words"
                    )
                    break

    # ───────────────────────────────────────────────────────────
    #  HELPERS
    # ───────────────────────────────────────────────────────────

    @staticmethod
    def _is_cyrillic(ch: str) -> bool:
        """Check if character is Cyrillic."""
        if not ch or ch.isspace():
            return False
        try:
            name = unicodedata.name(ch, '')
            return 'CYRILLIC' in name
        except (ValueError, TypeError):
            return False

    @staticmethod
    def _is_latin(ch: str) -> bool:
        """Check if character is Latin."""
        if not ch or ch.isspace():
            return False
        try:
            name = unicodedata.name(ch, '')
            return 'LATIN' in name
        except (ValueError, TypeError):
            return False


# ═══════════════════════════════════════════════════════════════
#  УДОБНЫЕ ФУНКЦИИ
# ═══════════════════════════════════════════════════════════════

def detect_watermarks(text: str, lang: str = "en") -> WatermarkReport:
    """Обнаружить водяные знаки в тексте."""
    return WatermarkDetector(lang).detect(text)


def clean_watermarks(text: str, lang: str = "en") -> str:
    """Очистить текст от водяных знаков."""
    return WatermarkDetector(lang).clean(text)
