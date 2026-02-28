"""Синтаксическое перефразирование без ML.

Трансформирует предложения:
- Изменение порядка клауз
- Active ↔ Passive (EN/RU/UK)
- Номинализация ↔ Вербализация
- Расщепление/объединение предложений
- Перестановка фраз
"""

from __future__ import annotations

import logging
import random
import re
from dataclasses import dataclass

from texthumanize.morphology import get_morphology
from texthumanize.sentence_split import split_sentences

logger = logging.getLogger(__name__)

@dataclass
class ParaphraseResult:
    """Результат перефразирования."""

    original: str
    paraphrased: str
    changes: list[str]  # описание применённых трансформаций
    confidence: float  # 0..1, уверенность в корректности


# ═══════════════════════════════════════════════════════════════
#  ПАТТЕРНЫ: Active ↔ Passive (English)
# ═══════════════════════════════════════════════════════════════

_EN_BE_FORMS = {"is", "are", "was", "were", "be", "been", "being"}

_EN_PASSIVE_PATTERN = re.compile(
    r'\b(is|are|was|were|has been|have been|had been|will be|can be|could be|'
    r'should be|would be|may be|might be)\s+(\w+ed)\b',
    re.IGNORECASE,
)

# Пассив → Актив (EN): "The book was written by John" → "John wrote the book"
_EN_PASSIVE_BY_PATTERN = re.compile(
    r'^(The\s+)?(.+?)\s+(was|were|is|are|has been|have been|had been)\s+'
    r'(\w+ed)\s+by\s+(.+?)([.!?]?)$',
    re.IGNORECASE,
)


# ═══════════════════════════════════════════════════════════════
#  ПАТТЕРНЫ: Перестановка клауз
# ═══════════════════════════════════════════════════════════════

# "Although X, Y" → "Y, although X"
_CLAUSE_SWAP_PATTERNS = {
    "en": [
        (re.compile(r'^(Although|Though|Even though|While|Whereas)\s+(.+?),\s+(.+)$', re.I),
         lambda m: f"{m.group(3)}, {m.group(1).lower()} {m.group(2)}"),
        (re.compile(r'^(Because|Since|As)\s+(.+?),\s+(.+)$', re.I),
         lambda m: f"{m.group(3)} {m.group(1).lower()} {m.group(2)}"),
        (re.compile(r'^(If)\s+(.+?),\s+(.+)$', re.I),
         lambda m: f"{m.group(3)} if {m.group(2)}"),
        (re.compile(r'^(When|Whenever)\s+(.+?),\s+(.+)$', re.I),
         lambda m: f"{m.group(3)} {m.group(1).lower()} {m.group(2)}"),
        # "X, but Y" → "Y, but X" — аккуратно, не всегда подходит
    ],
    "ru": [
        (re.compile(r'^(Хотя|Несмотря на то что|Несмотря на то, что)\s+(.+?),\s+(.+)$', re.I),
         lambda m: f"{m.group(3)}, {m.group(1).lower()} {m.group(2)}"),
        (re.compile(r'^(Потому что|Поскольку|Так как)\s+(.+?),\s+(.+)$', re.I),
         lambda m: f"{m.group(3)}, {m.group(1).lower()} {m.group(2)}"),
        (re.compile(r'^(Если)\s+(.+?),\s+(то\s+)?(.+)$', re.I),
         lambda m: f"{m.group(4)}, если {m.group(2)}"),
        (re.compile(r'^(Когда)\s+(.+?),\s+(.+)$', re.I),
         lambda m: f"{m.group(3)}, когда {m.group(2)}"),
    ],
    "uk": [
        (re.compile(r'^(Хоча|Незважаючи на те що)\s+(.+?),\s+(.+)$', re.I),
         lambda m: f"{m.group(3)}, {m.group(1).lower()} {m.group(2)}"),
        (re.compile(r'^(Тому що|Оскільки)\s+(.+?),\s+(.+)$', re.I),
         lambda m: f"{m.group(3)}, {m.group(1).lower()} {m.group(2)}"),
        (re.compile(r'^(Якщо)\s+(.+?),\s+(то\s+)?(.+)$', re.I),
         lambda m: f"{m.group(4)}, якщо {m.group(2)}"),
    ],
}


# ═══════════════════════════════════════════════════════════════
#  НОМИНАЛИЗАЦИЯ/ВЕРБАЛИЗАЦИЯ
# ═══════════════════════════════════════════════════════════════

_NOMINALIZATION_MAP = {
    "en": {
        # verb → noun
        "decide": "decision", "conclude": "conclusion",
        "develop": "development", "improve": "improvement",
        "analyze": "analysis", "investigate": "investigation",
        "implement": "implementation", "evaluate": "evaluation",
        "consider": "consideration", "recommend": "recommendation",
        "observe": "observation", "explain": "explanation",
        "describe": "description", "suggest": "suggestion",
        "discuss": "discussion", "produce": "production",
        "reduce": "reduction", "introduce": "introduction",
        "transform": "transformation", "create": "creation",
        "demonstrate": "demonstration", "participate": "participation",
    },
    "ru": {
        "решать": "решение", "развивать": "развитие",
        "анализировать": "анализ", "улучшать": "улучшение",
        "исследовать": "исследование", "внедрять": "внедрение",
        "оценивать": "оценка", "рекомендовать": "рекомендация",
        "обсуждать": "обсуждение", "производить": "производство",
        "сокращать": "сокращение", "создавать": "создание",
        "описывать": "описание", "объяснять": "объяснение",
        "предлагать": "предложение", "участвовать": "участие",
    },
}

# Обратная карта: noun → verb
_VERBALIZATION_MAP = {
    lang: {v: k for k, v in mapping.items()}
    for lang, mapping in _NOMINALIZATION_MAP.items()
}


# ═══════════════════════════════════════════════════════════════
#  ШАБЛОНЫ ДЛЯ РАСЩЕПЛЕНИЯ ПРЕДЛОЖЕНИЙ
# ═══════════════════════════════════════════════════════════════

# "X, and Y" → "X. Y" (с заглавной)
_SPLIT_CONJUNCTIONS = {
    "en": [", and ", ", but ", ", so ", ", yet ", "; however, ", "; moreover, ",
           "; therefore, ", "; furthermore, "],
    "ru": [", и ", ", но ", ", а ", ", поэтому ", "; однако ", "; кроме того, ",
           "; следовательно, "],
    "uk": [", і ", ", але ", ", а ", ", тому ", "; однак ", "; крім того, "],
}

# Шаблоны для объединения предложений
_MERGE_CONNECTORS = {
    "en": ["moreover", "furthermore", "in addition", "also", "besides"],
    "ru": ["кроме того", "помимо этого", "также", "к тому же", "и вдобавок"],
    "uk": ["крім того", "також", "до того ж", "на додаток"],
}


class Paraphraser:
    """Синтаксический перефразировщик.

    Трансформирует предложения, сохраняя смысл:
    - Перестановка клауз
    - Active ↔ Passive (EN)
    - Расщепление/объединение предложений
    - Замена конструкций
    """

    def __init__(self, lang: str = "en", seed: int | None = None, intensity: float = 0.5):
        """
        Args:
            lang: Язык текста.
            seed: Зерно для RNG.
            intensity: 0..1, доля предложений для изменения.
        """
        self.lang = lang
        self.rng = random.Random(seed)
        self.intensity = intensity
        self.morph = get_morphology(lang)
        self._clause_patterns = _CLAUSE_SWAP_PATTERNS.get(lang, [])
        self._split_conj = _SPLIT_CONJUNCTIONS.get(lang, [])
        self._merge_conn = _MERGE_CONNECTORS.get(lang, [])
        self._nom_map = _NOMINALIZATION_MAP.get(lang, {})
        self._verb_map = _VERBALIZATION_MAP.get(lang, {})

    def paraphrase(self, text: str) -> ParaphraseResult:
        """Перефразировать текст.

        Args:
            text: Исходный текст.

        Returns:
            ParaphraseResult с перефразированным текстом.
        """
        sentences = self._split_sentences(text)
        changes: list[str] = []
        result_sentences: list[str] = []
        total_confidence = 0.0
        n_changed = 0

        for i, sent in enumerate(sentences):
            if self.rng.random() > self.intensity:
                result_sentences.append(sent)
                continue

            transformed, change_type, conf = self._try_transform(sent, i, sentences)
            if transformed != sent:
                result_sentences.append(transformed)
                changes.append(change_type)
                total_confidence += conf
                n_changed += 1
            else:
                result_sentences.append(sent)

        result_text = " ".join(result_sentences)

        avg_conf = total_confidence / n_changed if n_changed > 0 else 1.0

        return ParaphraseResult(
            original=text,
            paraphrased=result_text,
            changes=changes,
            confidence=avg_conf,
        )

    def paraphrase_sentence(self, sentence: str) -> tuple[str, str]:
        """Перефразировать одно предложение.

        Returns:
            (перефразированное предложение, тип изменения).
        """
        result, change_type, _ = self._try_transform(sentence, 0, [sentence])
        return result, change_type

    def _try_transform(
        self, sent: str, idx: int, all_sents: list[str]
    ) -> tuple[str, str, float]:
        """Попробовать трансформировать предложение.

        Returns:
            (result, change_description, confidence).
        """
        # Порядок попыток (от безопасного к рискованному):
        transformations = [
            self._try_clause_swap,
            self._try_passive_to_active,
            self._try_sentence_split,
            self._try_fronting,
            self._try_nominalization_swap,
        ]

        self.rng.shuffle(transformations)

        for transform_fn in transformations:
            result, desc, conf = transform_fn(sent)
            if result != sent:
                return result, desc, conf

        return sent, "no_change", 1.0

    def _try_clause_swap(self, sent: str) -> tuple[str, str, float]:
        """Перестановка клауз: "Although X, Y" → "Y, although X"."""
        for pattern, replacement in self._clause_patterns:
            m = pattern.match(sent.rstrip('.!?'))
            if m:
                # Определяем пунктуацию
                punct = sent[-1] if sent and sent[-1] in '.!?' else '.'
                try:
                    new_sent = replacement(m) + punct
                    # Заглавная буква в начале
                    new_sent = new_sent[0].upper() + new_sent[1:]
                    return new_sent, "clause_reorder", 0.9
                except (IndexError, AttributeError):
                    continue

        return sent, "", 0.0

    def _try_passive_to_active(self, sent: str) -> tuple[str, str, float]:
        """Passive → Active (только EN)."""
        if self.lang != "en":
            return sent, "", 0.0

        m = _EN_PASSIVE_BY_PATTERN.match(sent.strip())
        if m:
            _article = m.group(1) or ""
            obj = m.group(2).strip()
            _aux = m.group(3)
            verb_past = m.group(4)
            subj = m.group(5).strip()
            punct = m.group(6) or "."

            # Простая попытка: "The book was written by John" → "John wrote the book"
            active = f"{subj} {verb_past} the {obj.lower()}{punct}"
            active = active[0].upper() + active[1:]
            return active, "passive_to_active", 0.7

        return sent, "", 0.0

    def _try_sentence_split(self, sent: str) -> tuple[str, str, float]:
        """Разбить длинное предложение на два."""
        if len(sent.split()) < 12:
            return sent, "", 0.0

        for conj in self._split_conj:
            if conj in sent.lower():
                idx = sent.lower().index(conj)
                part1 = sent[:idx].strip()
                part2 = sent[idx + len(conj):].strip()

                if len(part1.split()) >= 4 and len(part2.split()) >= 4:
                    # Убедимся что part1 заканчивается пунктуацией
                    if not part1.endswith(('.', '!', '?')):
                        part1 += '.'
                    part2 = part2[0].upper() + part2[1:] if part2 else part2
                    return f"{part1} {part2}", "sentence_split", 0.75

        return sent, "", 0.0

    def _try_fronting(self, sent: str) -> tuple[str, str, float]:
        """Вынести обстоятельство в начало.

        "She completed the task quickly" → "Quickly, she completed the task"
        """
        words = sent.rstrip('.!?').split()
        punct = sent[-1] if sent and sent[-1] in '.!?' else '.'

        if len(words) < 5:
            return sent, "", 0.0

        # EN: вынос наречия с конца
        if self.lang == "en":
            last_word = words[-1].lower()
            if last_word.endswith("ly") and len(last_word) > 4:
                # Move adverb to front
                front = last_word[0].upper() + last_word[1:]
                rest = " ".join(words[:-1])
                rest = rest[0].lower() + rest[1:]
                return f"{front}, {rest}{punct}", "adverb_fronting", 0.8

        # RU/UK: вынос обстоятельства
        if self.lang in ("ru", "uk"):
            # Ищем наречие в конце (слова на -о, -е для RU)
            last = words[-1].lower()
            if self.lang == "ru" and (last.endswith("но") or last.endswith("ки") or
                                     last.endswith("ло")):
                front = last[0].upper() + last[1:]
                rest = " ".join(words[:-1])
                rest = rest[0].lower() + rest[1:]
                return f"{front} {rest}{punct}", "adverb_fronting", 0.7

        return sent, "", 0.0

    def _try_nominalization_swap(self, sent: str) -> tuple[str, str, float]:
        """Заменить глагол на существительное или наоборот.

        Пример: "We decided to..." → "Our decision was to..."
        (Упрощённая версия — точечные замены)
        """
        words = sent.split()
        if len(words) < 4:
            return sent, "", 0.0

        # Ищем слова из карты номинализации
        for i, word in enumerate(words):
            w_lower = word.lower().rstrip('.,;:!?')
            # verb → noun
            if w_lower in self._nom_map:
                noun = self._nom_map[w_lower]
                # Простая замена слова
                new_word = noun
                if word[0].isupper():
                    new_word = new_word[0].upper() + new_word[1:]
                words[i] = new_word + word[len(w_lower):]  # сохраняем пунктуацию
                return " ".join(words), "nominalization", 0.6
            # noun → verb
            if w_lower in self._verb_map:
                verb = self._verb_map[w_lower]
                new_word = verb
                if word[0].isupper():
                    new_word = new_word[0].upper() + new_word[1:]
                words[i] = new_word + word[len(w_lower):]
                return " ".join(words), "verbalization", 0.6

        return sent, "", 0.0

    def _split_sentences(self, text: str) -> list[str]:
        """Базовое разбиение на предложения (email/URL safe)."""
        sentences = split_sentences(text.strip(), self.lang)
        return [s.strip() for s in sentences if s.strip()]


# ═══════════════════════════════════════════════════════════════
#  УДОБНЫЕ ФУНКЦИИ
# ═══════════════════════════════════════════════════════════════

def paraphrase_text(
    text: str,
    lang: str = "en",
    intensity: float = 0.5,
    seed: int | None = None,
) -> str:
    """Перефразировать текст.

    Args:
        text: Исходный текст.
        lang: Язык.
        intensity: Доля предложений для изменения (0..1).
        seed: Зерно RNG для воспроизводимости.

    Returns:
        Перефразированный текст.
    """
    p = Paraphraser(lang=lang, seed=seed, intensity=intensity)
    result = p.paraphrase(text)
    return result.paraphrased
