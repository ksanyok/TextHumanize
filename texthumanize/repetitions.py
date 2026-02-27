"""Уменьшение повторов и тавтологии."""

from __future__ import annotations

import logging
import random
import re
from collections import Counter

from texthumanize.context import ContextualSynonyms
from texthumanize.lang import get_lang_pack
from texthumanize.morphology import get_morphology
from texthumanize.segmenter import has_placeholder
from texthumanize.sentence_split import split_sentences
from texthumanize.utils import coin_flip, get_profile, intensity_probability

logger = logging.getLogger(__name__)

class RepetitionReducer:
    """Уменьшает повторы слов и фраз в тексте.

    Ищет повторяющиеся нестоповые слова в скользящем окне
    и заменяет их синонимами из языкового пакета.
    Использует морфологический движок для лемматизации и
    согласования форм синонимов.
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
        self._stop_words = self.lang_pack.get("stop_words", set())
        self._synonyms = self.lang_pack.get("synonyms", {})
        self._morph = get_morphology(lang)
        self._ctx = ContextualSynonyms(lang=lang, seed=seed)

    def process(self, text: str) -> str:
        """Уменьшить повторы в тексте.

        Args:
            text: Текст для обработки.

        Returns:
            Текст с уменьшенными повторами.
        """
        self.changes = []
        prob = intensity_probability(
            self.intensity,
            self.profile["repetition_intensity"],
        )

        if prob < 0.05:
            return text

        # Определяем тематику текста для контекстного подбора синонимов
        self._ctx.detect_topic(text)

        # 1. Повторы одинаковых слов в окне
        text = self._reduce_word_repetitions(text, prob)

        # 2. Повторы биграмм
        text = self._reduce_bigram_repetitions(text, prob)

        return text

    def _reduce_word_repetitions(self, text: str, prob: float) -> str:
        """Заменить повторяющиеся слова синонимами."""
        sentences = split_sentences(text, lang=self.lang)
        if len(sentences) < 2:
            return text

        # Окно: 2-3 предложения
        window_size = 3
        modified = False

        for i in range(len(sentences)):
            # Собираем окно предложений
            window_start = max(0, i - window_size + 1)
            window_sents = sentences[window_start:i + 1]
            window_text = ' '.join(window_sents)

            # Извлекаем значимые слова текущего предложения
            curr_words = self._extract_content_words(sentences[i])
            if not curr_words:
                continue

            # Считаем слова во всём окне
            all_words = self._extract_content_words(window_text)
            word_counts = Counter(all_words)

            # Ищем повторы (слово встречается > 1 раза во окне)
            for word, count in word_counts.items():
                if count < 2:
                    continue

                if has_placeholder(word):
                    continue

                # Проверяем, есть ли синоним
                word_lower = word.lower()
                synonyms = self._synonyms.get(word_lower, [])

                # Fallback: попробовать лемму
                if not synonyms:
                    lemma = self._morph.lemmatize(word_lower)
                    synonyms = self._synonyms.get(lemma, [])

                if not synonyms:
                    continue

                if not coin_flip(prob, self.rng):
                    continue

                # Контекстный подбор синонима (вместо random.choice)
                context_text = ' '.join(window_sents)
                synonym = self._ctx.choose_synonym(
                    word, synonyms, context_text,
                )

                # Согласовать форму синонима с оригиналом
                synonym = self._morph.find_synonym_form(word, synonym)

                # Паттерн: целое слово
                pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
                matches = list(pattern.finditer(sentences[i]))

                # Заменяем последнее вхождение в предложении
                if matches:
                    match = matches[-1]
                    original_word = match.group(0)

                    # Сохраняем регистр
                    if original_word.isupper():
                        synonym = synonym.upper()
                    elif original_word[0].isupper():
                        synonym = synonym[0].upper() + synonym[1:]

                    sentences[i] = (
                        sentences[i][:match.start()]
                        + synonym
                        + sentences[i][match.end():]
                    )
                    modified = True

                    self.changes.append({
                        "type": "repetition_word",
                        "original": original_word,
                        "replacement": synonym,
                    })
                    break  # Одна замена за предложение

        if modified:
            return ' '.join(sentences)
        return text

    def _reduce_bigram_repetitions(self, text: str, prob: float) -> str:
        """Уменьшить повторение биграмм."""
        words = text.split()
        if len(words) < 10:
            return text

        # Находим повторяющиеся биграммы
        bigrams: Counter = Counter()
        for i in range(len(words) - 1):
            w1 = words[i].lower().strip('.,;:!?\"\'()[]{}')
            w2 = words[i + 1].lower().strip('.,;:!?\"\'()[]{}')
            if w1 and w2 and w1 not in self._stop_words and w2 not in self._stop_words:
                bigram = (w1, w2)
                bigrams[bigram] += 1

        # Ищем повторяющиеся биграммы
        repeated = {bg: cnt for bg, cnt in bigrams.items() if cnt >= 2}
        if not repeated:
            return text

        # Заменяем одно из слов в повторяющейся биграмме
        for (w1, w2), _count in repeated.items():
            if not coin_flip(prob * 0.4, self.rng):
                continue

            if has_placeholder(w1) or has_placeholder(w2):
                continue

            # Пробуем заменить второе вхождение биграммы
            for word in (w1, w2):
                synonyms = self._synonyms.get(word, [])
                if synonyms:
                    synonym = self.rng.choice(synonyms)
                    # Ищем второе вхождение слова
                    pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
                    matches = list(pattern.finditer(text))
                    if len(matches) >= 2:
                        match = matches[1]  # Второе вхождение
                        original_word = match.group(0)
                        if original_word[0].isupper():
                            synonym = synonym[0].upper() + synonym[1:]
                        text = (
                            text[:match.start()]
                            + synonym
                            + text[match.end():]
                        )
                        self.changes.append({
                            "type": "repetition_bigram",
                            "original": original_word,
                            "replacement": synonym,
                        })
                        break

        return text

    def _extract_content_words(self, text: str) -> list[str]:
        """Извлечь значимые слова (без стоп-слов)."""
        words = re.findall(r'[а-яА-ЯёЁіІїЇєЄґҐa-zA-Z]+', text)
        return [
            w.lower()
            for w in words
            if w.lower() not in self._stop_words and len(w) > 2
            and '\x00' not in w
        ]
