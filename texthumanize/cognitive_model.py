"""Cognitive Load Modeling™ — simulate human cognitive patterns in text.

Part of the ASH™ (Adaptive Statistical Humanization) technology
developed by Oleksandr K. for TextHumanize.

Core idea
---------
Humans write with **cognitive constraints**: limited working memory
(~7 items), attention drift (quality varies through a document),
and fatigue (slight degradation toward the end).

AI writes *uniformly well* across an entire document.  This
uniformity is a strong detection signal: real authors show:

- **Polished openings** → relaxed middle → sometimes rushed ending
- **Progressive simplification** of repeated concepts
- **Controlled imperfections**: hedges, self-corrections, casual
  asides that break the "too-perfect" pattern
- **Working-memory traces**: new concepts introduced in bursts,
  then referenced with pronouns / short-forms

Cognitive Load Modeling™ introduces these human patterns at the
right positions based on a document-level attention curve.

Copyright (c) 2024-2026 Oleksandr K. / TextHumanize Project.
"""

from __future__ import annotations

import logging
import random
import re
from dataclasses import dataclass, field
from typing import Any

from texthumanize.sentence_split import split_sentences

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
#  COGNITIVE ARTEFACTS — things humans naturally do
# ═══════════════════════════════════════════════════════════════

_HEDGES: dict[str, list[str]] = {
    "en": [
        "I think", "probably", "maybe", "it seems", "sort of",
        "in a way", "roughly", "more or less", "as far as I can tell",
        "if I'm not mistaken", "arguably", "to some degree",
        "I suppose", "I guess", "to be honest", "in my view",
        "from what I gather", "if you ask me", "as I see it",
        "I believe", "it appears", "seemingly", "perhaps",
        "kind of", "I'd say", "in theory", "for the most part",
        "at first glance", "on the whole", "it looks like",
        "from my perspective", "as I understand it", "in principle",
        "broadly speaking", "one could argue", "tentatively",
        "in all likelihood", "quite possibly", "to my mind",
    ],
    "ru": [
        "думаю", "наверное", "пожалуй", "похоже", "вроде бы",
        "в каком-то смысле", "примерно", "плюс-минус",
        "насколько я понимаю", "если не ошибаюсь", "скорее всего",
        "в определённой степени", "мне кажется", "видимо",
        "предположительно", "по-моему", "по всей видимости",
        "как мне представляется", "судя по всему", "возможно",
        "как бы", "в целом", "на первый взгляд", "я бы сказал",
        "отчасти", "в основном", "грубо говоря", "по идее",
        "не исключено", "можно предположить", "ориентировочно",
        "по ощущениям", "в общих чертах", "так сказать",
        "условно говоря", "в некотором роде", "как говорится",
    ],
    "uk": [
        "думаю", "мабуть", "здається", "наче", "ніби",
        "у певному сенсі", "приблизно", "плюс-мінус",
        "наскільки я розумію", "якщо не помиляюсь", "скоріш за все",
        "до певної міри", "мені здається", "вочевидь",
        "припускаю", "на мою думку", "як на мене",
        "як мені уявляється", "судячи з усього", "можливо",
        "ніби-то", "загалом", "на перший погляд", "я б сказав",
        "почасти", "в основному", "грубо кажучи", "за ідеєю",
        "не виключено", "можна припустити", "орієнтовно",
        "за відчуттями", "в загальних рисах", "так би мовити",
        "умовно кажучи", "у певному розумінні", "як кажуть",
    ],
}

_SELF_CORRECTIONS: dict[str, list[str]] = {
    "en": [
        "— well, actually", "— or rather", "— no, wait",
        "— let me rephrase that:", "— I mean",
        "(well, not exactly, but close)", "(or something like that)",
        "— actually, scratch that", "— hold on, let me think",
        "— correction:", "— okay, not quite",
        "— what I really meant was", "— that's not right, let me fix that",
        "— or more precisely", "— well, to put it differently",
        "— hmm, actually", "— on second thought",
        "— no, that came out wrong", "— let me put it another way",
        "— okay, maybe that's a stretch", "— sorry, I misspoke",
    ],
    "ru": [
        " — ну, точнее", " — вернее", " — нет, подождите",
        " — перефразирую:", " — я имею в виду",
        " (ну, не совсем так, но близко)", " (или что-то в этом роде)",
        " — стоп, не так", " — дайте подумать",
        " — поправка:", " — хотя нет, не совсем",
        " — то есть на самом деле", " — это неточно, исправлюсь",
        " — точнее говоря", " — ну, другими словами",
        " — хм, вообще-то", " — если подумать заново",
        " — нет, я не так выразился", " — давайте иначе",
        " — ладно, может я преувеличил", " — простите, оговорился",
    ],
    "uk": [
        " — ну, точніше", " — вірніше", " — ні, зачекайте",
        " — перефразую:", " — я маю на увазі",
        " (ну, не зовсім так, але близько)", " (чи щось подібне)",
        " — стоп, не так", " — дайте подумати",
        " — виправлення:", " — хоча ні, не зовсім",
        " — тобто насправді", " — це неточно, виправлюсь",
        " — точніше кажучи", " — ну, іншими словами",
        " — хм, взагалі-то", " — якщо подумати ще раз",
        " — ні, я не так висловився", " — давайте інакше",
        " — гаразд, може я перебільшив", " — вибачте, обмовився",
    ],
}

_CASUAL_ASIDES: dict[str, list[str]] = {
    "en": [
        "(yes, really)", "(bear with me here)", "(stay with me)",
        "(I know, I know)", "(fun fact:)", "(which is a lot, by the way)",
        "(no kidding)", "(spoiler alert)",
        "(just saying)", "(don't quote me on this)",
        "(wild, right?)", "(seriously though)",
        "(if you can believe it)", "(honest)", "(true story)",
        "(not gonna lie)", "(trust me on this one)",
        "(been there, done that)", "(surprise, surprise)",
        "(believe it or not)", "(and I'm being generous here)",
        "(for what it's worth)", "(welcome to my world)",
        "(pun intended)", "(okay, bad joke)",
    ],
    "ru": [
        "(да-да)", "(потерпите)", "(не уходите)",
        "(знаю-знаю)", "(интересный факт:)", "(это много, между прочим)",
        "(не шучу)", "(спойлер:)",
        "(просто говорю)", "(не цитируйте меня)",
        "(серьёзно)", "(да ладно, правда)",
        "(можете не верить)", "(честно)", "(реальная история)",
        "(не буду врать)", "(поверьте мне)",
        "(бывало и такое)", "(сюрприз-сюрприз)",
        "(как ни странно)", "(и это ещё мягко сказано)",
        "(к слову)", "(вот такие дела)",
        "(каламбур)", "(ладно, неудачная шутка)",
    ],
    "uk": [
        "(так-так)", "(потерпіть)", "(не йдіть)",
        "(знаю-знаю)", "(цікавий факт:)", "(це багато, до речі)",
        "(не жартую)", "(спойлер:)",
        "(просто кажу)", "(не цитуйте мене)",
        "(серйозно)", "(та невже, правда)",
        "(можете не вірити)", "(чесно)", "(реальна історія)",
        "(не буду брехати)", "(повірте мені)",
        "(бувало й таке)", "(сюрприз-сюрприз)",
        "(як не дивно)", "(і це ще м'яко сказано)",
        "(до слова)", "(ось такі справи)",
        "(каламбур)", "(гаразд, невдалий жарт)",
    ],
}

_FATIGUE_SIMPLIFIERS: dict[str, dict[str, str]] = {
    "en": {
        "consequently": "so",
        "nevertheless": "still",
        "notwithstanding": "despite",
        "approximately": "about",
        "fundamentally": "basically",
        "implementation": "setup",
        "methodology": "method",
        "infrastructure": "setup",
        "optimization": "tuning",
        "characteristics": "traits",
        "subsequently": "then",
        "furthermore": "also",
        "additionally": "plus",
        "predominantly": "mostly",
        "approximately": "roughly",
        "demonstrate": "show",
        "facilitate": "help",
        "accommodate": "fit",
        "comprehensive": "full",
        "significant": "big",
        "utilize": "use",
        "endeavor": "try",
        "sufficient": "enough",
        "commence": "start",
        "terminate": "end",
        "acquisition": "getting",
        "modification": "change",
        "configuration": "setup",
        "functionality": "feature",
        "parameters": "settings",
    },
    "ru": {
        "следовательно": "значит",
        "тем не менее": "всё же",
        "приблизительно": "примерно",
        "фундаментально": "по сути",
        "реализация": "настройка",
        "методология": "метод",
        "инфраструктура": "база",
        "оптимизация": "настройка",
        "характеристики": "свойства",
        "впоследствии": "потом",
        "дополнительно": "ещё",
        "преимущественно": "в основном",
        "демонстрировать": "показать",
        "обеспечивать": "давать",
        "содействовать": "помогать",
        "комплексный": "полный",
        "значительный": "большой",
        "использовать": "брать",
        "достаточный": "хватит",
        "конфигурация": "настройка",
        "функциональность": "возможность",
        "параметры": "настройки",
        "предшествующий": "прошлый",
        "осуществлять": "делать",
        "формулировать": "говорить",
    },
    "uk": {
        "отже": "тож",
        "тим не менш": "все ж",
        "приблизно": "десь",
        "фундаментально": "по суті",
        "реалізація": "налаштування",
        "методологія": "метод",
        "інфраструктура": "база",
        "оптимізація": "налаштування",
        "характеристики": "властивості",
        "згодом": "потім",
        "додатково": "ще",
        "переважно": "здебільшого",
        "демонструвати": "показати",
        "забезпечувати": "давати",
        "сприяти": "допомагати",
        "комплексний": "повний",
        "значний": "великий",
        "використовувати": "брати",
        "достатній": "вистачить",
        "конфігурація": "налаштування",
        "функціональність": "можливість",
        "параметри": "налаштування",
        "попередній": "минулий",
        "здійснювати": "робити",
        "формулювати": "казати",
    },
}

# ═══════════════════════════════════════════════════════════════
#  RESULT DATACLASS
# ═══════════════════════════════════════════════════════════════

@dataclass
class CognitiveResult:
    """Result of Cognitive Load Modeling™ pass."""
    text: str
    original_text: str
    hedges_added: int = 0
    corrections_added: int = 0
    asides_added: int = 0
    fatigue_simplifications: int = 0
    changes: list[dict[str, Any]] = field(default_factory=list)

    @property
    def total_artefacts(self) -> int:
        return (self.hedges_added + self.corrections_added +
                self.asides_added + self.fatigue_simplifications)


# ═══════════════════════════════════════════════════════════════
#  CORE ENGINE
# ═══════════════════════════════════════════════════════════════

class CognitiveModeler:
    """Introduce human cognitive patterns into text.

    ASH™ Cognitive Load Modeling™ — proprietary technology.

    Simulates the attention curve of a human writer:
    - Polished opening (first ~20%)
    - Relaxed middle (20–70%)
    - Possible fatigue near the end (last ~30%)

    Usage::

        cm = CognitiveModeler(lang="en")
        result = cm.model(text, intensity=0.5)
        print(result.text)
        print(f"Added {result.total_artefacts} cognitive artefacts")
    """

    def __init__(
        self,
        lang: str = "en",
        seed: int | None = None,
    ) -> None:
        self.lang = lang
        self.seed = seed
        self._rng = random.Random(seed)
        self._hedges = _HEDGES.get(lang, _HEDGES["en"])
        self._corrections = _SELF_CORRECTIONS.get(lang, _SELF_CORRECTIONS["en"])
        self._asides = _CASUAL_ASIDES.get(lang, _CASUAL_ASIDES["en"])
        self._simplifiers = _FATIGUE_SIMPLIFIERS.get(lang, _FATIGUE_SIMPLIFIERS["en"])

    # ── Public API ──

    def model(
        self,
        text: str,
        intensity: float = 0.5,
    ) -> CognitiveResult:
        """Apply cognitive load modeling to text.

        Parameters
        ----------
        text : str
            Input text.
        intensity : float
            0.0–1.0.  Controls how many artefacts to introduce.
            0.3 = subtle, 0.5 = moderate, 0.8 = aggressive.

        Returns
        -------
        CognitiveResult
        """
        if not text or not text.strip():
            return CognitiveResult(text=text, original_text=text)

        sentences = split_sentences(text, self.lang)
        n = len(sentences)
        if n < 3:
            return CognitiveResult(text=text, original_text=text)

        new_sents = list(sentences)
        changes: list[dict[str, Any]] = []
        hedges = 0
        corrections = 0
        asides = 0
        fatigue = 0

        for i, sent in enumerate(sentences):
            position = i / max(1, n - 1)  # 0.0 = start, 1.0 = end
            zone = self._attention_zone(position)

            # ── Zone 1: Opening (0–20%) — polished, no artefacts ──
            if zone == "opening":
                continue

            # ── Zone 2: Middle (20–70%) — relaxed, hedges + asides ──
            elif zone == "middle":
                # Hedge injection (probability based on intensity)
                if self._should_act(intensity * 0.3):
                    modified, change = self._add_hedge(sent, i)
                    if change:
                        new_sents[i] = modified
                        changes.append(change)
                        hedges += 1
                        continue

                # Casual aside (less frequent)
                if self._should_act(intensity * 0.15):
                    modified, change = self._add_aside(sent, i)
                    if change:
                        new_sents[i] = modified
                        changes.append(change)
                        asides += 1
                        continue

            # ── Zone 3: Late middle (50–80%) — self-corrections ──
            elif zone == "late_middle":
                if self._should_act(intensity * 0.2):
                    modified, change = self._add_correction(sent, i)
                    if change:
                        new_sents[i] = modified
                        changes.append(change)
                        corrections += 1
                        continue

                # Also hedges
                if self._should_act(intensity * 0.25):
                    modified, change = self._add_hedge(sent, i)
                    if change:
                        new_sents[i] = modified
                        changes.append(change)
                        hedges += 1
                        continue

            # ── Zone 4: Ending (80–100%) — fatigue simplification ──
            elif zone == "ending":
                if self._should_act(intensity * 0.4):
                    modified, n_simplified = self._apply_fatigue(sent)
                    if n_simplified > 0:
                        new_sents[i] = modified
                        fatigue += n_simplified
                        changes.append({
                            "type": "cognitive_fatigue",
                            "sentence_idx": i,
                            "simplifications": n_simplified,
                        })
                        continue

                # Hedges also appear in endings
                if self._should_act(intensity * 0.2):
                    modified, change = self._add_hedge(sent, i)
                    if change:
                        new_sents[i] = modified
                        changes.append(change)
                        hedges += 1

        # Rejoin
        result_text = self._rejoin(text, sentences, new_sents)

        return CognitiveResult(
            text=result_text,
            original_text=text,
            hedges_added=hedges,
            corrections_added=corrections,
            asides_added=asides,
            fatigue_simplifications=fatigue,
            changes=changes,
        )

    def analyze_uniformity(self, text: str) -> dict[str, Any]:
        """Detect cognitive uniformity (AI signal).

        Human text shows quality variation across the document.
        AI text is uniformly polished.
        """
        sentences = split_sentences(text, self.lang)
        if len(sentences) < 5:
            return {"sentences": len(sentences), "verdict": "too_short"}

        n = len(sentences)

        # Split into thirds
        third = max(1, n // 3)
        opening = sentences[:third]
        middle = sentences[third:2 * third]
        ending = sentences[2 * third:]

        # Compute per-section metrics
        sections = {
            "opening": opening,
            "middle": middle,
            "ending": ending,
        }

        section_scores: dict[str, dict[str, float]] = {}
        for name, sents in sections.items():
            if not sents:
                continue
            lens = [len(s.split()) for s in sents]
            avg_len = sum(lens) / len(lens)
            len_var = (sum((x - avg_len) ** 2 for x in lens) / len(lens)) ** 0.5
            avg_word_len = sum(len(w) for s in sents for w in s.split()) / max(1, sum(len(s.split()) for s in sents))

            section_scores[name] = {
                "avg_sent_len": avg_len,
                "sent_len_std": len_var,
                "avg_word_len": avg_word_len,
                "sentence_count": len(sents),
            }

        # Measure uniformity: how similar are the three sections?
        if len(section_scores) < 3:
            return {"sentences": n, "verdict": "too_short"}

        # Uniformity = low variance between sections
        avg_lens = [s["avg_sent_len"] for s in section_scores.values()]
        avg_word_lens = [s["avg_word_len"] for s in section_scores.values()]

        sent_len_uniformity = 1.0 - min(1.0, self._cv(avg_lens))
        word_len_uniformity = 1.0 - min(1.0, self._cv(avg_word_lens) * 3)

        uniformity = (sent_len_uniformity + word_len_uniformity) / 2

        return {
            "sentences": n,
            "sections": section_scores,
            "uniformity_score": round(uniformity, 4),
            "verdict": (
                "ai_uniform" if uniformity > 0.85
                else "mixed" if uniformity > 0.65
                else "human_varied"
            ),
        }

    # ── Attention Curve ──

    def _attention_zone(self, position: float) -> str:
        """Map document position (0–1) to an attention zone."""
        if position < 0.20:
            return "opening"
        elif position < 0.50:
            return "middle"
        elif position < 0.80:
            return "late_middle"
        else:
            return "ending"

    def _should_act(self, probability: float) -> bool:
        """Probabilistic decision."""
        return self._rng.random() < probability

    # ── Artefact Injection ──

    def _add_hedge(
        self, sentence: str, idx: int,
    ) -> tuple[str, dict[str, Any] | None]:
        """Add a hedge to the sentence."""
        words = sentence.split()
        if len(words) < 5:
            return sentence, None

        hedge = self._rng.choice(self._hedges)

        # Decide where to put the hedge
        strategy = self._rng.choice(["prefix", "infix"])

        if strategy == "prefix":
            # "Probably, the system works..."
            new = hedge + ", " + sentence[0].lower() + sentence[1:]
        else:
            # Insert after the subject (roughly: after first 2-3 words)
            insert_pos = min(3, len(words) // 3)
            words.insert(insert_pos, hedge + ",")
            new = " ".join(words)

        return new, {
            "type": "cognitive_hedge",
            "sentence_idx": idx,
            "hedge": hedge,
            "strategy": strategy,
        }

    def _add_correction(
        self, sentence: str, idx: int,
    ) -> tuple[str, dict[str, Any] | None]:
        """Add a self-correction to the sentence."""
        if len(sentence.split()) < 6:
            return sentence, None

        correction = self._rng.choice(self._corrections)

        # Add correction after the sentence
        if sentence[-1] in ".!":
            new = sentence[:-1] + correction + sentence[-1]
        else:
            new = sentence + correction

        return new, {
            "type": "cognitive_correction",
            "sentence_idx": idx,
            "correction": correction,
        }

    def _add_aside(
        self, sentence: str, idx: int,
    ) -> tuple[str, dict[str, Any] | None]:
        """Add a casual aside."""
        words = sentence.split()
        if len(words) < 6:
            return sentence, None

        aside = self._rng.choice(self._asides)

        # Insert aside in the middle
        insert_pos = len(words) // 2
        words.insert(insert_pos, aside)
        new = " ".join(words)

        return new, {
            "type": "cognitive_aside",
            "sentence_idx": idx,
            "aside": aside,
        }

    def _apply_fatigue(self, sentence: str) -> tuple[str, int]:
        """Simplify vocabulary (fatigue effect)."""
        result = sentence
        count = 0

        for formal, simple in self._simplifiers.items():
            if formal in result.lower():
                # Find and replace preserving case
                pattern = re.compile(re.escape(formal), re.IGNORECASE)
                result = pattern.sub(simple, result, count=1)
                count += 1

        return result, count

    # ── Helpers ──

    @staticmethod
    def _cv(data: list[float]) -> float:
        if len(data) < 2:
            return 0.0
        mean = sum(data) / len(data)
        if mean == 0:
            return 0.0
        var = sum((x - mean) ** 2 for x in data) / len(data)
        return (var ** 0.5) / mean

    def _rejoin(
        self, original: str, old_sents: list[str], new_sents: list[str],
    ) -> str:
        result = original
        for old, new in zip(old_sents, new_sents):
            if old != new:
                result = result.replace(old, new, 1)
        return result


# ═══════════════════════════════════════════════════════════════
#  MODULE-LEVEL CONVENIENCE
# ═══════════════════════════════════════════════════════════════

def model_cognition(
    text: str,
    lang: str = "en",
    intensity: float = 0.5,
    seed: int | None = None,
) -> CognitiveResult:
    """Introduce human cognitive patterns into text.

    ASH™ Cognitive Load Modeling™.
    """
    return CognitiveModeler(lang=lang, seed=seed).model(text, intensity)


def analyze_cognitive_uniformity(
    text: str,
    lang: str = "en",
) -> dict[str, Any]:
    """Detect cognitive uniformity (AI writes uniformly, humans don't)."""
    return CognitiveModeler(lang=lang).analyze_uniformity(text)
