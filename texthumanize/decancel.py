"""Деканцеляризация — замена тяжёлых бюрократических слов и выражений."""

from __future__ import annotations

import random
import re

from texthumanize.lang import get_lang_pack
from texthumanize.morphology import get_morphology
from texthumanize.utils import coin_flip, get_profile, intensity_probability


# ═══════════════════════════════════════════════════════════════
#  Context guards — запрещаем замену слова, если рядом стоят
#  слова, меняющие его семантику.
#
#  Формат:  word → [(compiled_regex, ...)]
#  Если любой regex находит совпадение в окне ±60 символов —
#  замена блокируется.
# ═══════════════════════════════════════════════════════════════

def _build_context_guards() -> dict[str, list[re.Pattern[str]]]:
    """Build pre-compiled context guard patterns per word."""
    raw: dict[str, list[str]] = {
        # ── Russian ─────────────────────────────────────────
        # «данный» = "this" (bureaucratic) → keep in legal/formal quotes
        "данный": [
            r"\b(?:на\s+данный\s+момент)\b",  # temporal, keep as is
        ],
        "является": [
            r"\b(?:что\s+является|которая\s+является)\b",  # linking verb ok
        ],
        "обеспечение": [
            r"\b(?:программное\s+обеспечение|социальное\s+обеспечение)\b",
        ],
        "реализация": [
            r"\b(?:реализация\s+товар|реализация\s+продукц)\b",
        ],

        # ── Ukrainian ───────────────────────────────────────
        # «даний» = "this" (bureaucratic) → keep in legal/formal quotes
        "даний": [
            r"\b(?:на\s+даний\s+момент)\b",  # temporal, keep as is
        ],
        "забезпечення": [
            r"\b(?:програмне\s+забезпечення|соціальне\s+забезпечення)\b",
        ],

        # ── English ─────────────────────────────────────────
        # «implement» in programming context → keep
        "implement": [
            r"\b(?:function|class|interface|method|module|def|void|return|"
            r"abstract|override|extends|implements)\b",
        ],
        "implementation": [
            r"\b(?:function|class|interface|method|module|def|void|return|"
            r"abstract|override|API|SDK|library|framework)\b",
        ],
        # «utilize» near code/infra → keep
        "utilize": [
            r"\b(?:function|class|def|API|SDK|CLI|library|framework)\b",
        ],
        # «leverage» in tech context
        "leverage": [
            r"\b(?:function|class|API|SDK|library|framework)\b",
        ],
        # «comprehensive» in compound terms → keep
        "comprehensive": [
            r"\b(?:comprehensive\s+exam|comprehensive\s+insurance)\b",
        ],
        # «significant» in statistics context → keep
        "significant": [
            r"\b(?:statistically\s+significant|p\s*[<>=]|confidence\s+interval)\b",
        ],
        # «robust» in statistics/ML context → keep
        "robust": [
            r"\b(?:robust\s+regression|robust\s+estimat|robust\s+standard)\b",
        ],
        # «enhance» in image/photo context → keep
        "enhance": [
            r"\b(?:image\s+enhance|photo\s+enhance|video\s+enhance)\b",
        ],

        # ── German ──────────────────────────────────────────
        "Implementierung": [
            r"\b(?:Software|API|SDK|Bibliothek|Modul|Klasse|Funktion)\b",
        ],
        "implementieren": [
            r"\b(?:Software|API|SDK|Bibliothek|Modul|Klasse|Funktion)\b",
        ],
        "Berücksichtigung": [
            r"\b(?:unter\s+besonderer\s+Berücksichtigung)\b",
        ],
        "Optimierung": [
            r"\b(?:Compiler|Datenbank|SQL|Performance|Laufzeit)\b",
        ],
    }
    result: dict[str, list[re.Pattern[str]]] = {}
    for word, patterns in raw.items():
        result[word] = [re.compile(p, re.IGNORECASE) for p in patterns]
    return result


_CONTEXT_GUARDS = _build_context_guards()

# Context window: how many characters left/right to inspect
_CONTEXT_WINDOW = 80


def _is_replacement_safe(
    word: str,
    text: str,
    match_start: int,
    match_end: int,
    replacement: str | None = None,
) -> bool:
    """Check if replacing *word* at given position is safe.

    Returns False if:
    1. A context guard pattern matches within ±_CONTEXT_WINDOW chars.
    2. The *replacement* word already appears in the same sentence
       (duplicate / echo check).

    Args:
        word: The word being replaced.
        text: Full text.
        match_start: Start index of the match.
        match_end: End index of the match.
        replacement: Optional replacement string for echo check.
    """
    guards = _CONTEXT_GUARDS.get(word.lower())
    if guards:
        window_start = max(0, match_start - _CONTEXT_WINDOW)
        window_end = min(len(text), match_end + _CONTEXT_WINDOW)
        window = text[window_start:window_end]
        for guard in guards:
            if guard.search(window):
                return False

    # Echo check: avoid introducing a word that already exists nearby
    if replacement:
        repl_lower = replacement.lower().split()[0] if replacement.strip() else ""
        if repl_lower and len(repl_lower) > 3:
            # Find sentence boundaries around the match
            sent_start = text.rfind(".", 0, match_start)
            sent_start = 0 if sent_start == -1 else sent_start + 1
            sent_end = text.find(".", match_end)
            sent_end = len(text) if sent_end == -1 else sent_end
            sentence = text[sent_start:sent_end].lower()
            # If the replacement word already exists in the sentence, skip
            if repl_lower in sentence.split():
                return False

    return True


class Debureaucratizer:
    """Заменяет канцеляризмы на простые и естественные выражения.

    Работает по словарям: однословные канцеляризмы и фразовые выражения.
    Интенсивность зависит от профиля и параметра intensity.
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
        self._morph = get_morphology(lang)
        self._max_changes = 100  # will be recalculated in process()
        self._changes_made = 0

    def process(self, text: str) -> str:
        """Деканцеляризация текста.

        Args:
            text: Текст для обработки.

        Returns:
            Текст с заменёнными канцеляризмами.
        """
        self.changes = []
        prob = intensity_probability(
            self.intensity,
            self.profile["decancel_intensity"],
        )

        if prob < 0.05:
            return text

        # Бюджет замен — ограничиваем % изменённых слов,
        # чтобы деканцеляризация не пожирала весь change budget.
        word_count = len(text.split())
        # Максимум 15% слов может быть заменено этим этапом
        self._max_changes = max(2, int(word_count * 0.15))
        self._changes_made = 0

        # 1. Сначала фразовые замены (более специфичные)
        text = self._replace_phrases(text, prob)

        # 2. Затем однословные замены
        text = self._replace_words(text, prob)

        return text

    def _replace_phrases(self, text: str, prob: float) -> str:
        """Заменить фразовые канцеляризмы."""
        phrases = self.lang_pack.get("bureaucratic_phrases", {})

        # Сортируем по длине (длинные фразы первыми)
        sorted_phrases = sorted(phrases.items(), key=lambda x: len(x[0]), reverse=True)

        for phrase, replacements in sorted_phrases:
            # Проверяем бюджет замен
            if self._changes_made >= self._max_changes:
                break

            if not coin_flip(prob, self.rng):
                continue

            # Ищем фразу с учётом регистра первой буквы
            # \b предотвращает совпадение внутри слов (напр. "є" внутри "Немає")
            pattern = re.compile(
                r'\b' + re.escape(phrase) + r'\b', re.IGNORECASE,
            )
            matches = list(pattern.finditer(text))

            for match in matches:
                original = match.group(0)
                replacement = self.rng.choice(replacements)

                # Context guard: проверяем, безопасна ли замена в контексте
                if not _is_replacement_safe(
                    phrase, text, match.start(), match.end(),
                    replacement=replacement,
                ):
                    continue

                # Сохраняем регистр первой буквы
                if original[0].isupper() and replacement[0].islower():
                    replacement = replacement[0].upper() + replacement[1:]
                elif original[0].islower() and replacement[0].isupper():
                    replacement = replacement[0].lower() + replacement[1:]

                text = text[:match.start()] + replacement + text[match.end():]
                self._changes_made += 1

                self.changes.append({
                    "type": "decancel_phrase",
                    "original": original,
                    "replacement": replacement,
                })

                # После замены нужно пересобрать matches
                break  # Обрабатываем одну замену за раз, чтобы не сбить индексы

        return text

    def _replace_words(self, text: str, prob: float) -> str:
        """Заменить однословные канцеляризмы."""
        words = self.lang_pack.get("bureaucratic", {})

        for word, replacements in words.items():
            # Проверяем бюджет замен
            if self._changes_made >= self._max_changes:
                break

            if not coin_flip(prob, self.rng):
                continue

            # Паттерн: целое слово, с учётом регистра
            pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
            matches = list(pattern.finditer(text))

            for match in reversed(matches):  # Обратный порядок, чтобы не сбить индексы
                if self._changes_made >= self._max_changes:
                    break

                if not coin_flip(prob, self.rng):
                    continue

                original = match.group(0)
                replacement = self.rng.choice(replacements)

                # Context guard: проверяем, безопасна ли замена в контексте
                if not _is_replacement_safe(
                    word, text, match.start(), match.end(),
                    replacement=replacement,
                ):
                    continue

                # Морфологическое согласование: подбираем форму синонима
                # под грамматическую форму оригинала
                if self.lang in ("ru", "uk", "en", "de"):
                    replacement = self._morph.find_synonym_form(
                        original.lower(), replacement,
                    )

                # Сохраняем регистр
                if original.isupper():
                    replacement = replacement.upper()
                elif original[0].isupper():
                    replacement = replacement[0].upper() + replacement[1:]

                text = text[:match.start()] + replacement + text[match.end():]
                self._changes_made += 1

                self.changes.append({
                    "type": "decancel_word",
                    "original": original,
                    "replacement": replacement,
                })

        return text
