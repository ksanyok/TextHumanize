"""Оптимизация читаемости — этап пайплайна.

Анализирует и улучшает читаемость на уровне предложений:
- Разбивает слишком сложные/длинные предложения
- Объединяет слишком короткие предложения
- Упрощает чрезмерно вложенные конструкции

Использует sentence_readability.py для анализа сложности.
"""

from __future__ import annotations

import logging
import random
import re

from texthumanize.segmenter import has_placeholder, skip_placeholder_sentence
from texthumanize.sentence_readability import sentence_readability

logger = logging.getLogger(__name__)

# Конъюнкции/места для разбивки по языкам
_SPLIT_CONJUNCTIONS: dict[str, list[str]] = {
    "en": [
        ", which ", ", and ", ", but ", ", however ", ", although ",
        ", while ", ", whereas ", "; ", ", so ", ", yet ",
        ", therefore ", ", moreover ", ", furthermore ",
    ],
    "ru": [
        ", который ", ", которая ", ", которое ", ", которые ",
        ", а ", ", но ", ", однако ", ", хотя ", ", причём ",
        "; ", ", поэтому ", ", кроме того ", ", при этом ",
        ", и ", ", что ", ", где ", ", когда ",
    ],
    "uk": [
        ", який ", ", яка ", ", яке ", ", які ",
        ", а ", ", але ", ", однак ", ", хоча ",
        "; ", ", тому ", ", крім того ", ", при цьому ",
        ", і ", ", що ", ", де ", ", коли ",
    ],
    "de": [
        ", der ", ", die ", ", das ", ", und ", ", aber ",
        ", jedoch ", ", obwohl ", "; ", ", deshalb ",
        ", außerdem ", ", wobei ", ", wenn ", ", weil ",
    ],
    "fr": [
        ", qui ", ", que ", ", et ", ", mais ", ", cependant ",
        ", bien que ", "; ", ", donc ", ", de plus ",
        ", tandis que ", ", lorsque ", ", parce que ",
    ],
    "es": [
        ", que ", ", y ", ", pero ", ", sin embargo ",
        ", aunque ", "; ", ", por lo tanto ", ", además ",
        ", mientras ", ", cuando ", ", porque ",
    ],
    "it": [
        ", che ", ", e ", ", ma ", ", tuttavia ",
        ", sebbene ", "; ", ", quindi ", ", inoltre ",
        ", mentre ", ", quando ", ", perché ",
    ],
    "pl": [
        ", który ", ", która ", ", które ", ", i ", ", ale ",
        ", jednak ", ", chociaż ", "; ", ", dlatego ",
        ", ponadto ", ", podczas gdy ", ", gdy ", ", ponieważ ",
    ],
    "pt": [
        ", que ", ", e ", ", mas ", ", no entanto ",
        ", embora ", "; ", ", portanto ", ", além disso ",
        ", enquanto ", ", quando ", ", porque ",
    ],
    "ar": [
        "، و", "، لكن", "، إلا أن", "، على الرغم من",
        "؛ ", "، لذلك", "، بالإضافة إلى", "، حيث",
    ],
    "zh": [
        "，而", "，但是", "，然而", "，虽然",
        "；", "，因此", "，此外", "，其中",
    ],
    "ja": [
        "、しかし", "、また", "、さらに", "、ただし",
        "；", "、そのため", "、なお", "、一方",
    ],
    "ko": [
        ", 그러나", ", 또한", ", 게다가", ", 다만",
        "; ", ", 따라서", ", 한편", ", 그리고",
    ],
    "tr": [
        ", ancak", ", ayrıca", ", bununla birlikte",
        "; ", ", bu nedenle", ", üstelik", ", oysa",
    ],
}

# Слова-связки для объединения коротких предложений
_JOIN_WORDS: dict[str, list[str]] = {
    "en": [" and ", " while ", ", also ", " — "],
    "ru": [" и ", " а также ", ", причём ", " — "],
    "uk": [" і ", " а також ", ", причому ", " — "],
    "de": [" und ", " wobei ", ", außerdem ", " — "],
    "fr": [" et ", " et aussi ", ", d'ailleurs ", " — "],
    "es": [" y ", " y también ", ", además ", " — "],
    "it": [" e ", " e anche ", ", inoltre ", " — "],
    "pl": [" i ", " a także ", ", ponadto ", " — "],
    "pt": [" e ", " e também ", ", além disso ", " — "],
}


class ReadabilityOptimizer:
    """Оптимизатор читаемости текста для пайплайна.

    Разбивает сложные предложения и объединяет слишком короткие
    для улучшения потока чтения.

    Работает для ВСЕХ 14 языков.
    """

    def __init__(
        self,
        lang: str = "en",
        profile: str = "default",
        intensity: int = 50,
        seed: int | None = None,
    ):
        self.lang = lang
        self.profile = profile
        self.intensity = intensity
        self.seed = seed
        self.changes: list[dict] = []
        self._rng = random.Random(seed)

    def process(self, text: str) -> str:
        """Оптимизировать читаемость текста.

        Returns:
            Текст с улучшенной читаемостью.
        """
        if not text or not text.strip():
            return text

        # Анализируем читаемость
        report = sentence_readability(text)

        # Если текст уже хорошо читается — не трогаем
        if report.very_hard_count == 0 and report.avg_difficulty < 50:
            return text

        splits_done = 0
        joins_done = 0
        result = text

        # 1. Разбиваем очень сложные предложения
        for sent_score in report.sentences:
            if sent_score.grade != "very_hard":
                continue
            if sent_score.word_count < 25:
                continue  # Слишком короткое для разбивки — сложность от слов
            if skip_placeholder_sentence(sent_score.text):
                continue

            new_text = self._try_split(sent_score.text)
            if new_text and new_text != sent_score.text:
                result = result.replace(sent_score.text, new_text, 1)
                splits_done += 1

        # 2. Объединяем слишком короткие предложения (≤5 слов подряд)
        if self.intensity >= 40:
            result, joins = self._join_short_sentences(result)
            joins_done = joins

        if splits_done > 0 or joins_done > 0:
            parts = []
            if splits_done:
                parts.append(f"разбито {splits_done} сложных")
            if joins_done:
                parts.append(f"объединено {joins_done} коротких")
            self.changes.append({
                "type": "readability_optimization",
                "description": f"Читаемость: {', '.join(parts)} предложений",
            })

        return result

    def _try_split(self, sentence: str) -> str | None:
        """Попытаться разбить сложное предложение."""
        conjunctions = _SPLIT_CONJUNCTIONS.get(
            self.lang,
            _SPLIT_CONJUNCTIONS.get("en", []),
        )

        # Пробуем разбить по конъюнкциям (предпочитаем точку с запятой)
        best_split = None
        best_balance = 0.0  # Чем ближе к 0.5, тем лучше

        for conj in conjunctions:
            idx = sentence.find(conj)
            if idx < 0:
                continue

            part1 = sentence[:idx].strip()
            part2 = sentence[idx + len(conj):].strip()

            # Обе части должны быть достаточно длинными
            w1 = len(part1.split())
            w2 = len(part2.split())
            if w1 < 5 or w2 < 5:
                continue

            # Проверяем placeholder-безопасность
            if has_placeholder(part1) or has_placeholder(part2):
                continue

            balance = min(w1, w2) / max(w1, w2)
            if balance > best_balance:
                best_balance = balance
                # Капитализируем вторую часть
                if part2 and part2[0].islower():
                    part2 = part2[0].upper() + part2[1:]
                # Добавляем точку к первой части если нету
                if part1 and part1[-1] not in ".!?…":
                    part1 += "."
                best_split = f"{part1} {part2}"

        return best_split

    def _join_short_sentences(self, text: str) -> tuple[str, int]:
        """Объединить слишком короткие предложения."""
        join_words = _JOIN_WORDS.get(
            self.lang,
            _JOIN_WORDS.get("en", [" and "]),
        )

        sentences = re.split(r'(?<=[.!?])\s+', text)
        if len(sentences) < 2:
            return text, 0

        result: list[str] = []
        joins = 0
        i = 0

        while i < len(sentences):
            sent = sentences[i].strip()
            if not sent:
                i += 1
                continue

            words = sent.split()
            # Если предложение очень короткое и следующее тоже
            if (
                len(words) <= 5
                and i + 1 < len(sentences)
                and len(sentences[i + 1].split()) <= 8
                and not skip_placeholder_sentence(sent)
                and not skip_placeholder_sentence(sentences[i + 1])
                and self._rng.random() < self.intensity / 100
            ):
                next_sent = sentences[i + 1].strip()
                # Убираем точку в конце первого
                if sent.endswith("."):
                    sent = sent[:-1]
                connector = self._rng.choice(join_words)
                # Делаем начало второго строчным
                if next_sent and next_sent[0].isupper():
                    next_sent = next_sent[0].lower() + next_sent[1:]
                combined = sent + connector + next_sent
                result.append(combined)
                joins += 1
                i += 2
            else:
                result.append(sent)
                i += 1

        if joins == 0:
            return text, 0

        return " ".join(result), joins
