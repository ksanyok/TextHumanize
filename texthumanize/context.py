"""Контекстные синонимы — Word Sense Disambiguation без ML.

Выбирает правильный синоним на основе контекста (коллокации,
тематики, грамматических ограничений) без нейросетей.
"""

from __future__ import annotations

import logging
import random
from typing import Any

from texthumanize.morphology import get_morphology

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
#  КОЛЛОКАЦИОННЫЕ ПРАВИЛА (что с чем сочетается)
# ═══════════════════════════════════════════════════════════════

# Запрещённые сочетания: (синоним, контекстное_слово) → нельзя
_NEGATIVE_COLLOCATIONS = {
    "ru": {
        # "взять решение" — нельзя, "принять решение" — можно
        ("взять", "решение"), ("взять", "решения"),
        ("брать", "решение"), ("брать", "решения"),
        ("сильный", "мороз"),  # "крепкий мороз", не "сильный"
        ("большой", "дождь"),  # "сильный дождь"
        ("состоять", "ошибку"),  # "совершить ошибку"
        ("проводить", "время"),  # Ок, но "убивать время" — нет
        ("делать", "промах"),  # "допустить промах"
        ("поставить", "вопрос"),  # "задать вопрос"
        ("быстрый", "развитие"),  # "стремительное развитие"
        ("давать", "ответственность"),  # "нести ответственность"
        ("покупать", "доверие"),  # "завоевать доверие"
        ("взять", "выводы"),  # "сделать выводы"
    },
    "uk": {
        ("взяти", "рішення"),
        ("брати", "рішення"),
        ("давати", "відповідальність"),
        ("купувати", "довіру"),  # "здобути довіру"
        ("ставити", "питання"),  # "задати питання"
    },
    "en": {
        ("do", "mistake"),  # "make a mistake"
        ("take", "conclusion"),  # "reach/draw a conclusion"
        ("strong", "rain"),  # "heavy rain"
        ("big", "temperature"),  # "high temperature"
        ("quick", "food"),  # "fast food"
        ("hard", "decision"),  # "difficult decision" is ok, but "hard decision" also ok
        ("make", "damage"),  # "cause/do damage"
        ("do", "progress"),  # "make progress"
        ("take", "advantage"),  # ok as "take advantage", but NOT "do advantage"
        ("do", "advantage"),
        ("give", "attention"),  # "pay attention"
        ("say", "speech"),  # "give a speech"
    },
    "de": {
        ("machen", "Entscheidung"),  # "eine Entscheidung treffen"
        ("nehmen", "Schluss"),  # "einen Schluss ziehen"
        ("geben", "Aufmerksamkeit"),  # "Aufmerksamkeit schenken"
        ("tun", "Fehler"),  # "einen Fehler machen"
        ("starker", "Regen"),  # "starker Regen" is OK, but "heftiger" better for heavy
    },
}

# Положительные сочетания: (слово, контекст) → предпочтительный синоним
_POSITIVE_COLLOCATIONS = {
    "ru": {
        ("влияние", "оказ"): "оказывать",
        ("решение", "прин"): "принимать",
        ("роль", "игра"): "играть",
        ("внимание", "обращ"): "обращать",
        ("внимание", "уделя"): "уделять",
        ("ошибка", "соверш"): "совершать",
        ("ошибка", "допус"): "допускать",
        ("вывод", "дела"): "делать",
        ("итог", "подвод"): "подводить",
    },
    "en": {
        ("decision", "make"): "make",
        ("mistake", "make"): "make",
        ("attention", "pay"): "pay",
        ("conclusion", "draw"): "draw",
        ("conclusion", "reach"): "reach",
        ("role", "play"): "play",
        ("effort", "make"): "make",
    },
}

# Тематические кластеры: слова-маркеры темы → предпочтительные синонимы
_TOPIC_PREFERENCES = {
    "en": {
        "technology": {
            "markers": ["software", "code", "program", "system", "data", "algorithm",
                       "computer", "digital", "internet", "server", "database", "api"],
            "preferences": {
                "big": "large",
                "fast": "rapid",
                "use": "employ",
                "make": "create",
                "fix": "resolve",
                "show": "display",
            },
        },
        "business": {
            "markers": ["company", "revenue", "market", "sales", "customer",
                       "strategy", "business", "profit", "invest", "stock"],
            "preferences": {
                "big": "significant",
                "important": "critical",
                "start": "launch",
                "grow": "expand",
                "help": "facilitate",
            },
        },
        "casual": {
            "markers": ["friend", "fun", "cool", "awesome", "like", "love",
                       "happy", "life", "day", "feel", "think", "want"],
            "preferences": {
                "big": "huge",
                "good": "great",
                "bad": "terrible",
                "important": "big deal",
                "fast": "quick",
            },
        },
    },
    "ru": {
        "technology": {
            "markers": ["программа", "код", "система", "данные", "алгоритм",
                       "сервер", "база", "приложение", "интерфейс"],
            "preferences": {
                "большой": "крупный",
                "быстрый": "высокоскоростной",
                "делать": "создавать",
                "работать": "функционировать",
            },
        },
        "business": {
            "markers": ["компания", "рынок", "продажа", "клиент", "стратегия",
                       "бизнес", "прибыль", "инвестиция"],
            "preferences": {
                "большой": "значительный",
                "важный": "критический",
                "начать": "запустить",
                "расти": "расширяться",
            },
        },
    },
}


class ContextualSynonyms:
    """Контекстный подбор синонимов.

    Учитывает:
    - Коллокации (какие слова сочетаются)
    - Тематику текста (IT, бизнес, разговорный)
    - Грамматическое согласование (через morphology engine)
    - Negative constraints (что точно не подходит)
    """

    def __init__(self, lang: str = "ru", seed: int | None = None):
        self.lang = lang
        self.rng = random.Random(seed)
        self.morph = get_morphology(lang)
        self._neg_colloc = _NEGATIVE_COLLOCATIONS.get(lang, set())
        self._pos_colloc = _POSITIVE_COLLOCATIONS.get(lang, {})
        self._topics: dict[str, dict[str, Any]] = _TOPIC_PREFERENCES.get(lang, {})
        self._detected_topic: str | None = None

    def detect_topic(self, text: str) -> str | None:
        """Определить тематику текста по маркерным словам.

        Returns:
            Название темы или None.
        """
        text_lower = text.lower()
        best_topic = None
        best_score = 0

        for topic_name, topic_data in self._topics.items():
            markers = topic_data.get("markers", [])
            score = sum(1 for m in markers if m in text_lower)
            if score > best_score and score >= 2:
                best_score = score
                best_topic = topic_name

        self._detected_topic = best_topic
        return best_topic

    def choose_synonym(
        self,
        word: str,
        synonyms: list[str],
        context: str,
        window: int = 50,
    ) -> str:
        """Выбрать лучший синоним с учётом контекста.

        Args:
            word: Исходное слово.
            synonyms: Список синонимов-кандидатов.
            context: Текст вокруг слова.
            window: Размер контекстного окна (символов).

        Returns:
            Лучший синоним для данного контекста.
        """
        if not synonyms:
            return word
        if len(synonyms) == 1:
            return synonyms[0]

        # Извлекаем контекстные слова
        context_words = set(
            w.lower().strip('.,;:!?"\'()[]{}')
            for w in context.split()
            if len(w.strip('.,;:!?"\'()[]{}')) > 2
        )

        scored: list[tuple[str, float]] = []

        for syn in synonyms:
            score = 0.0
            syn_lower = syn.lower()

            # 1. Negative collocation check (-100 = запрещено)
            is_blocked = False
            for ctx_word in context_words:
                if (syn_lower, ctx_word) in self._neg_colloc:
                    is_blocked = True
                    break
                if (ctx_word, syn_lower) in self._neg_colloc:
                    is_blocked = True
                    break

            if is_blocked:
                scored.append((syn, -100.0))
                continue

            # 2. Positive collocation bonus (+5)
            for (key_word, key_ctx), preferred in self._pos_colloc.items():
                if syn_lower == preferred:
                    for ctx_word in context_words:
                        if key_word in ctx_word or key_ctx in ctx_word:
                            score += 5.0
                            break

            # 3. Topic preference bonus (+3)
            if self._detected_topic and self._detected_topic in self._topics:
                prefs = self._topics[self._detected_topic].get("preferences", {})
                word_lemma = self.morph.lemmatize(word)
                if word_lemma in prefs and prefs[word_lemma] == syn_lower:
                    score += 3.0

            # 4. Length similarity bonus (ближе по длине к оригиналу = лучше)
            len_diff = abs(len(syn) - len(word))
            score -= len_diff * 0.1

            # 5. Morphological compatibility
            pos_original = self.morph.detect_pos(word)
            pos_synonym = self.morph.detect_pos(syn)
            if pos_original == pos_synonym:
                score += 1.0

            # 6. Небольшая рандомизация для естественности
            score += self.rng.uniform(-0.3, 0.3)

            scored.append((syn, score))

        # Фильтруем заблокированные
        valid = [(s, sc) for s, sc in scored if sc > -50]

        if not valid:
            # Все заблокированы — возвращаем оригинал
            return word

        # Выбираем лучший (с некоторой случайностью в топ-3)
        valid.sort(key=lambda x: x[1], reverse=True)

        # Из топ-3 выбираем случайно (но с весами)
        top = valid[:min(3, len(valid))]
        if len(top) == 1:
            return top[0][0]

        # Weighted random selection
        min_score = min(s for _, s in top)
        weights = [max(s - min_score + 0.1, 0.1) for _, s in top]
        total = sum(weights)
        r = self.rng.uniform(0, total)
        cumulative: float = 0
        for (syn, _), w in zip(top, weights):
            cumulative += w
            if r <= cumulative:
                return syn

        return top[0][0]

    def match_form(self, original: str, synonym: str) -> str:
        """Согласовать форму синонима с оригиналом.

        Args:
            original: Исходное слово в определённой форме.
            synonym: Синоним (лемма или другая форма).

        Returns:
            Синоним в согласованной форме.
        """
        result = self.morph.find_synonym_form(original, synonym)

        # Сохраняем регистр
        if original and original.isupper():
            result = result.upper()
        elif original and original[0].isupper() and result and result[0].islower():
            result = result[0].upper() + result[1:]

        return result
