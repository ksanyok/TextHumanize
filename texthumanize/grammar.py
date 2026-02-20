"""Правило-ориентированная проверка грамматики (rule-based grammar checker).

Поддерживает 9 языков. Работает без ML-моделей и внешних API.
Обнаруживаемые ошибки:
    - Двойные слова (the the, is is)
    - Ошибки капитализации (начало предложения)
    - Пробелы перед знаками препинания
    - Множественные пробелы
    - Отсутствие пробела после знаков препинания
    - Двойные знаки препинания
    - Незакрытые скобки/кавычки
    - Общие опечатки (per-language)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class GrammarIssue:
    """Одна найденная грамматическая проблема."""

    rule: str
    message: str
    offset: int
    length: int
    suggestion: str = ""
    severity: str = "warning"  # "error" | "warning" | "info"


@dataclass
class GrammarReport:
    """Результат проверки грамматики."""

    issues: list[GrammarIssue] = field(default_factory=list)
    score: float = 100.0  # 0-100, 100 = perfect

    @property
    def total(self) -> int:
        return len(self.issues)

    @property
    def errors(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warnings(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")


# ── Common typos / misspellings per language ──────────────────────────

_COMMON_TYPOS: dict[str, dict[str, str]] = {
    "en": {
        "teh": "the", "recieve": "receive", "seperate": "separate",
        "occured": "occurred", "definately": "definitely", "occassion": "occasion",
        "accomodate": "accommodate", "acheive": "achieve", "beleive": "believe",
        "calender": "calendar", "committment": "commitment", "concensus": "consensus",
        "existance": "existence", "foriegn": "foreign", "grammer": "grammar",
        "harrass": "harass", "independant": "independent", "millenium": "millennium",
        "neccessary": "necessary", "occurence": "occurrence", "perseverence": "perseverance",
        "publically": "publicly", "recomend": "recommend", "refered": "referred",
        "succesful": "successful", "tommorow": "tomorrow", "wierd": "weird",
    },
    "ru": {
        "агенство": "агентство", "буду щий": "будущий", "в течении": "в течение",
        "искуство": "искусство", "прийти": "прийти", "следущий": "следующий",
        "сдесь": "здесь", "впоследствии": "впоследствии",
        "симпотичный": "симпатичный", "компания": "кампания",
        "инциндент": "инцидент", "прецендент": "прецедент",
    },
    "uk": {
        "їхній": "їхній", "приїжджати": "приїжджати",
        "буд-який": "будь-який", "буд-ласка": "будь ласка",
        "на жаль": "на жаль",
    },
    "de": {
        "das selbe": "dasselbe", "nähmlich": "nämlich",
        "wiederrum": "wiederum", "sympatisch": "sympathisch",
        "Standart": "Standard", "Vorraussetzung": "Voraussetzung",
        "Reperatur": "Reparatur", "agressiv": "aggressiv",
        "Rhytmus": "Rhythmus", "Terasse": "Terrasse",
    },
    "fr": {
        "language": "langage", "parmis": "parmi",
        "malgrés": "malgré", "biensur": "bien sûr",
        "quelque fois": "quelquefois", "apeller": "appeler",
        "déveloper": "développer", "souvant": "souvent",
    },
    "es": {
        "haiga": "haya", "hubieron": "hubo",
        "nadien": "nadie", "habia": "había",
        "mas": "más", "atravez": "a través",
        "enseñes": "enseñes", "preveer": "prever",
    },
    "it": {
        "un'uomo": "un uomo", "qual'è": "qual è",
        "pultroppo": "purtroppo", "propio": "proprio",
        "efficiente": "efficiente", "obbiettivo": "obiettivo",
    },
    "pl": {
        "wziąść": "wziąć", "włanczyć": "włączyć",
        "ponadż": "ponad", "bynajmiej": "bynajmniej",
        "inteligientny": "inteligentny",
    },
    "pt": {
        "concerteza": "com certeza", "agente": "a gente",
        "aonde": "onde", "menas": "menos",
        "mais melhor": "melhor", "hà": "há",
    },
}

# ── Sentence-ending punctuation ───────────────────────────────────────

_SENTENCE_END = re.compile(r"[.!?…]")
_DOUBLE_WORD = re.compile(r"\b(\w{2,})\s+\1\b", re.IGNORECASE)
_MULTI_SPACE = re.compile(r"  +")
_SPACE_BEFORE_PUNCT = re.compile(r"\s+([,.!?;:])")
_NO_SPACE_AFTER_PUNCT = re.compile(r"([,.!?;:])([A-Za-zА-Яа-яЁёЇїІіЄєҐґÀ-ÿÄÖÜäöüß])")
_DOUBLE_PUNCT = re.compile(r"([,.!?;:]){2,}")
_UNCLOSED_PAREN = re.compile(r"\([^)]*$")
_UNCLOSED_BRACKET = re.compile(r"\[[^\]]*$")


def _check_double_words(text: str) -> list[GrammarIssue]:
    """Найти повторяющиеся слова (the the, is is)."""
    issues = []
    for m in _DOUBLE_WORD.finditer(text):
        issues.append(GrammarIssue(
            rule="DOUBLE_WORD",
            message=f"Повторяющееся слово: '{m.group(1)}'",
            offset=m.start(),
            length=len(m.group()),
            suggestion=m.group(1),
            severity="warning",
        ))
    return issues


def _check_capitalization(text: str) -> list[GrammarIssue]:
    """Проверить капитализацию в начале предложений."""
    issues = []
    # Split into sentences by '.', '!', '?'
    sentences = re.split(r"(?<=[.!?…])\s+", text)
    offset = 0
    for sent in sentences:
        sent_stripped = sent.lstrip()
        if sent_stripped and sent_stripped[0].isalpha() and sent_stripped[0].islower():
            real_offset = text.find(sent_stripped, offset)
            if real_offset >= 0:
                issues.append(GrammarIssue(
                    rule="CAPITALIZATION",
                    message="Предложение должно начинаться с заглавной буквы",
                    offset=real_offset,
                    length=1,
                    suggestion=sent_stripped[0].upper(),
                    severity="warning",
                ))
        offset += len(sent) + 1
    return issues


def _check_spacing(text: str) -> list[GrammarIssue]:
    """Проверить пробелы: двойные, перед пунктуацией, после пунктуации."""
    issues = []

    for m in _MULTI_SPACE.finditer(text):
        issues.append(GrammarIssue(
            rule="MULTI_SPACE",
            message="Множественные пробелы",
            offset=m.start(),
            length=len(m.group()),
            suggestion=" ",
            severity="info",
        ))

    for m in _SPACE_BEFORE_PUNCT.finditer(text):
        issues.append(GrammarIssue(
            rule="SPACE_BEFORE_PUNCT",
            message=f"Лишний пробел перед '{m.group(1)}'",
            offset=m.start(),
            length=len(m.group()),
            suggestion=m.group(1),
            severity="warning",
        ))

    for m in _NO_SPACE_AFTER_PUNCT.finditer(text):
        issues.append(GrammarIssue(
            rule="NO_SPACE_AFTER_PUNCT",
            message=f"Отсутствует пробел после '{m.group(1)}'",
            offset=m.start(),
            length=len(m.group()),
            suggestion=f"{m.group(1)} {m.group(2)}",
            severity="warning",
        ))

    return issues


def _check_double_punct(text: str) -> list[GrammarIssue]:
    """Найти дублированные знаки препинания (.. ,,)."""
    issues = []
    for m in _DOUBLE_PUNCT.finditer(text):
        # Allow "..." (ellipsis) and "!!"
        if m.group() in ("...", "!!", "??"):
            continue
        issues.append(GrammarIssue(
            rule="DOUBLE_PUNCT",
            message=f"Двойной знак препинания: '{m.group()}'",
            offset=m.start(),
            length=len(m.group()),
            suggestion=m.group(1),
            severity="warning",
        ))
    return issues


def _check_brackets(text: str) -> list[GrammarIssue]:
    """Проверить незакрытые скобки и кавычки."""
    issues = []
    openers = {"(": ")", "[": "]", "{": "}"}
    stack: list[tuple[str, int]] = []

    for i, ch in enumerate(text):
        if ch in openers:
            stack.append((ch, i))
        elif ch in openers.values():
            if stack and openers.get(stack[-1][0]) == ch:
                stack.pop()

    for opener, pos in stack:
        issues.append(GrammarIssue(
            rule="UNCLOSED_BRACKET",
            message=f"Незакрытая скобка '{opener}'",
            offset=pos,
            length=1,
            suggestion="",
            severity="warning",
        ))

    # Simple quote check
    for q in ('"', "'"):
        cnt = text.count(q)
        if cnt % 2 != 0:
            issues.append(GrammarIssue(
                rule="UNCLOSED_QUOTE",
                message=f"Нечётное количество кавычек '{q}' ({cnt})",
                offset=text.rfind(q),
                length=1,
                suggestion="",
                severity="info",
            ))

    return issues


def _check_typos(text: str, lang: str) -> list[GrammarIssue]:
    """Проверить общие опечатки для конкретного языка."""
    typos = _COMMON_TYPOS.get(lang, {})
    if not typos:
        return []

    issues = []
    lower = text.lower()
    for wrong, correct in typos.items():
        wrong_lower = wrong.lower()
        idx = 0
        while True:
            pos = lower.find(wrong_lower, idx)
            if pos < 0:
                break
            # Verify word boundary
            before_ok = pos == 0 or not text[pos - 1].isalnum()
            after_pos = pos + len(wrong)
            after_ok = after_pos >= len(text) or not text[after_pos].isalnum()
            if before_ok and after_ok:
                issues.append(GrammarIssue(
                    rule="TYPO",
                    message=f"Возможная опечатка: '{text[pos:after_pos]}' → '{correct}'",
                    offset=pos,
                    length=len(wrong),
                    suggestion=correct,
                    severity="error",
                ))
            idx = pos + 1
    return issues


def check_grammar(text: str, lang: str = "en") -> GrammarReport:
    """Проверить грамматику текста.

    Применяет набор правил для обнаружения грамматических ошибок,
    опечаток и проблем с форматированием.

    Args:
        text: Текст для проверки.
        lang: Код языка (en, ru, uk, de, fr, es, it, pl, pt).

    Returns:
        GrammarReport с найденными проблемами и общим баллом.
    """
    if not text or not text.strip():
        return GrammarReport(issues=[], score=100.0)

    issues: list[GrammarIssue] = []
    issues.extend(_check_double_words(text))
    issues.extend(_check_capitalization(text))
    issues.extend(_check_spacing(text))
    issues.extend(_check_double_punct(text))
    issues.extend(_check_brackets(text))
    issues.extend(_check_typos(text, lang))

    # Sort by offset
    issues.sort(key=lambda i: i.offset)

    # Score: start at 100, deduct points per issue
    penalty = {
        "error": 5.0,
        "warning": 2.0,
        "info": 0.5,
    }
    total_penalty = sum(penalty.get(i.severity, 1.0) for i in issues)
    # Normalize by text length to avoid over-penalizing long texts
    word_count = max(len(text.split()), 1)
    penalty_per_word = total_penalty / word_count * 10
    score = max(0.0, min(100.0, 100.0 - penalty_per_word * 10))

    return GrammarReport(issues=issues, score=round(score, 1))


def fix_grammar(text: str, lang: str = "en") -> str:
    """Автоматически исправить найденные грамматические ошибки.

    Применяет все предложения из check_grammar() с severity 'error' и 'warning'.

    Args:
        text: Текст для исправления.
        lang: Код языка.

    Returns:
        Исправленный текст.
    """
    report = check_grammar(text, lang)
    if not report.issues:
        return text

    # Apply fixes from end to start (to preserve offsets)
    result = list(text)
    for issue in sorted(report.issues, key=lambda i: i.offset, reverse=True):
        if issue.suggestion and issue.severity in ("error", "warning"):
            start = issue.offset
            end = start + issue.length
            result[start:end] = list(issue.suggestion)

    return "".join(result)
