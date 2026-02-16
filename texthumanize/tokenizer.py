"""Токенизатор текста — разбивка на абзацы, предложения, слова."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class TokenizedText:
    """Токенизированный текст."""
    paragraphs: list[Paragraph] = field(default_factory=list)

    def to_text(self) -> str:
        """Собрать текст обратно."""
        return "\n\n".join(p.to_text() for p in self.paragraphs)


@dataclass
class Paragraph:
    """Абзац текста."""
    sentences: list[Sentence] = field(default_factory=list)
    prefix: str = ""  # Markdown-префиксы: "- ", "1. ", "> "

    def to_text(self) -> str:
        """Собрать абзац обратно."""
        text = " ".join(s.to_text() for s in self.sentences)
        if self.prefix:
            return self.prefix + text
        return text


@dataclass
class Sentence:
    """Предложение."""
    words: list[str] = field(default_factory=list)
    ending: str = "."  # Знак в конце: . ! ? ... и т.д.
    prefix: str = ""  # Пробелы/переносы перед предложением

    def to_text(self) -> str:
        """Собрать предложение обратно."""
        text = " ".join(self.words)
        if text and self.ending:
            # Не добавляем точку, если предложение заканчивается placeholder-ом
            if text.endswith("\x00"):
                return self.prefix + text
            return self.prefix + text + self.ending
        return self.prefix + text

    @property
    def word_count(self) -> int:
        """Количество слов (без placeholder-ов)."""
        return sum(1 for w in self.words if "\x00" not in w)


class Tokenizer:
    """Токенизатор текста."""

    def __init__(self, abbreviations: list[str] | None = None):
        self.abbreviations = set(abbreviations or [])
        self._build_patterns()

    def _build_patterns(self):
        """Построить регулярные выражения для разбора."""
        # Паттерн для разделения абзацев
        self._para_split = re.compile(r'\n\s*\n')

        # Markdown-префиксы
        self._md_prefix = re.compile(
            r'^(\s*(?:[-*+]|\d+\.)\s+|>\s*|#{1,6}\s+)'
        )

        # Паттерн для разделения предложений
        # Ищем точку/!/? за которыми следует пробел и заглавная буква или конец строки
        self._sent_end = re.compile(
            r'(?<=[.!?…])'  # После знака препинания
            r'(?:\s+)'  # Один или более пробелов
            r'(?=[A-ZА-ЯЁЇІЄҐa-zA-Z\x00\(«"\'])',  # Перед заглавной буквой или placeholder
            re.UNICODE,
        )

    def tokenize(self, text: str) -> TokenizedText:
        """Разбить текст на абзацы, предложения, слова.

        Args:
            text: Текст для разбора.

        Returns:
            TokenizedText со структурой абзацев/предложений/слов.
        """
        result = TokenizedText()

        # Разбиваем на абзацы
        raw_paragraphs = self._para_split.split(text)

        for raw_para in raw_paragraphs:
            raw_para = raw_para.strip()
            if not raw_para:
                continue

            para = Paragraph()

            # Проверяем markdown-префикс
            md_match = self._md_prefix.match(raw_para)
            if md_match:
                para.prefix = md_match.group(1)
                raw_para = raw_para[md_match.end():]

            # Разбиваем на предложения
            raw_sentences = self._split_sentences(raw_para)

            for raw_sent in raw_sentences:
                raw_sent = raw_sent.strip()
                if not raw_sent:
                    continue

                sentence = self._parse_sentence(raw_sent)
                if sentence.words:
                    para.sentences.append(sentence)

            if para.sentences:
                result.paragraphs.append(para)

        return result

    def _split_sentences(self, text: str) -> list[str]:
        """Разбить текст на предложения."""
        if not text:
            return []

        # Защищаем аббревиатуры: заменяем точки в них на placeholder
        protected = text
        for abbr in sorted(self.abbreviations, key=len, reverse=True):
            # Ищем аббревиатуру с точкой
            pattern = re.compile(r'\b' + re.escape(abbr) + r'\.', re.IGNORECASE)
            protected = pattern.sub(
                lambda m: m.group(0).replace('.', '\x01'),
                protected,
            )

        # Защищаем многоточия
        protected = protected.replace('...', '\x02\x02\x02')
        protected = protected.replace('…', '\x02\x02\x02')

        # Разделяем предложения
        parts = self._sent_end.split(protected)

        # Восстанавливаем точки аббревиатур и многоточия
        result = []
        for part in parts:
            part = part.replace('\x01', '.')
            part = part.replace('\x02\x02\x02', '...')
            part = part.strip()
            if part:
                result.append(part)

        return result

    def _parse_sentence(self, raw: str) -> Sentence:
        """Разобрать предложение на слова и концовку."""
        sentence = Sentence()

        # Определяем окончание
        stripped = raw.rstrip()
        if stripped.endswith('...'):
            sentence.ending = '...'
            stripped = stripped[:-3].rstrip()
        elif stripped.endswith('…'):
            sentence.ending = '…'
            stripped = stripped[:-1].rstrip()
        elif stripped.endswith('?!') or stripped.endswith('!?'):
            sentence.ending = stripped[-2:]
            stripped = stripped[:-2].rstrip()
        elif stripped.endswith(('!', '?', '.')):
            sentence.ending = stripped[-1]
            stripped = stripped[:-1].rstrip()
        else:
            sentence.ending = ""

        # Разбиваем на слова
        if stripped:
            sentence.words = stripped.split()

        return sentence

    def detokenize(self, tokenized: TokenizedText) -> str:
        """Собрать текст из токенизированной структуры."""
        return tokenized.to_text()
