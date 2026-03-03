"""Adversarial Ensemble Self-Play™ — detector-guided iterative humanization.

Part of the ASH™ (Adaptive Statistical Humanization) technology
developed by Oleksandr K. for TextHumanize.

Core idea
---------
Three independent detectors (heuristic, statistical, neural-MLP)
score the text.  At each iteration the **problem map** is built:
every sentence that *any* detector flags is marked, along with the
specific features that triggered.

Only flagged sentences are modified — the rest stay intact.
Each iteration escalates in strictness; after a maximum number of
rounds (default 4) the process stops, even if some sentences remain
flagged.

Key advantages:
- **Minimal changes** — only truly problematic parts are touched.
- **No over-processing** — human parts are never degraded.
- **Ensemble diversity** — three architecturally different detectors
  catch different AI signals.

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
#  RESULT DATACLASS
# ═══════════════════════════════════════════════════════════════

@dataclass
class PlayResult:
    """Result of Adversarial Ensemble Self-Play™ run."""
    text: str
    original_text: str
    rounds: int = 0
    sentences_modified: int = 0
    final_score: float = 1.0
    initial_score: float = 1.0
    history: list[dict[str, Any]] = field(default_factory=list)

    @property
    def score_drop(self) -> float:
        """How much the AI score decreased (higher = better)."""
        return max(0.0, self.initial_score - self.final_score)


# ═══════════════════════════════════════════════════════════════
#  SENTENCE-LEVEL FIXES (targeted)
# ═══════════════════════════════════════════════════════════════

_DISCOURSE_MARKERS: dict[str, list[str]] = {
    "en": [
        "Actually,", "Well,", "You know,", "Honestly,",
        "Look,", "Anyway,", "Thing is,", "Frankly,",
        "So basically,", "I mean,", "Right,", "See,",
        "Okay so,", "Here's the deal:", "True,",
        "That said,", "In fairness,", "Mind you,",
        "Point is,", "Fun fact:", "Funnily enough,",
        "Funny thing is,", "For what it's worth,",
        "Come to think of it,", "To be clear,",
    ],
    "ru": [
        "Кстати,", "Вообще,", "Знаете,", "Ну так вот,",
        "Послушайте,", "В общем,", "Дело в том, что",
        "Честно говоря,", "Так вот,", "Я к тому, что",
        "Ну,", "Слушайте,", "Ладно,", "Вот смотрите:",
        "Правда,", "При этом,", "Между прочим,",
        "Суть в том, что", "К слову,", "Так сказать,",
        "Если честно,", "По правде говоря,",
        "Как ни крути,", "Мало того,", "Ну а если серьёзно,",
    ],
    "uk": [
        "До речі,", "Взагалі,", "Знаєте,", "Ну от,",
        "Послухайте,", "У цілому,", "Справа в тому, що",
        "Чесно кажучи,", "Ось так,", "Я до того, що",
        "Ну,", "Слухайте,", "Гаразд,", "Ось дивіться:",
        "Правда,", "При цьому,", "Між іншим,",
        "Суть у тому, що", "До слова,", "Так би мовити,",
        "Якщо чесно,", "По правді кажучи,",
        "Як не крути,", "Мало того,", "Ну а якщо серйозно,",
    ],
}

_AI_OPENERS: dict[str, list[str]] = {
    "en": [
        "Additionally,", "Furthermore,", "Moreover,",
        "In conclusion,", "It is important to note that",
        "It is worth noting that", "It should be noted that",
        "Significantly,", "Consequently,",
        "In essence,", "Ultimately,", "In summary,",
        "In light of this,", "It is evident that",
        "It is crucial to", "As previously mentioned,",
        "As a result,", "In this regard,", "Notably,",
        "Indeed,", "Hereby,", "Thus,", "Henceforth,",
        "To elaborate,", "In the context of",
    ],
    "ru": [
        "Кроме того,", "Более того,", "В заключение,",
        "Важно отметить, что", "Стоит отметить, что",
        "Следует отметить, что", "Немаловажно,",
        "Вследствие этого,", "Таким образом,",
        "По сути,", "В конечном счёте,", "Подводя итог,",
        "В свете этого,", "Очевидно, что",
        "Критически важно", "Как уже упоминалось,",
        "В результате,", "В этом отношении,", "Примечательно,",
        "Действительно,", "Исходя из этого,", "Вместе с тем,",
        "Необходимо подчеркнуть,", "Следовательно,",
        "В рамках данного контекста,",
    ],
    "uk": [
        "Крім того,", "Більш того,", "На завершення,",
        "Важливо зазначити, що", "Варто зазначити, що",
        "Слід зазначити, що", "Немаловажно,",
        "Внаслідок цього,", "Таким чином,",
        "По суті,", "Зрештою,", "Підсумовуючи,",
        "У світлі цього,", "Очевидно, що",
        "Критично важливо", "Як вже згадувалось,",
        "У результаті,", "У цьому відношенні,", "Примітно,",
        "Дійсно,", "Виходячи з цього,", "Разом з тим,",
        "Необхідно підкреслити,", "Відповідно,",
        "У межах даного контексту,",
    ],
}

_HUMANISERS: dict[str, list[str]] = {
    "en": [
        "In practice,", "From my experience,", "The way I see it,",
        "Interestingly,", "Here's the thing:", "Let me put it this way:",
        "To be fair,", "Long story short,", "Bottom line:",
        "Real talk:", "In my book,", "Truth is,",
        "What really matters is", "The short version:",
        "In plain terms,", "Call me crazy, but",
        "Let's be real,", "The takeaway here:",
        "Speaking from experience,", "If you ask me,",
        "At the end of the day,", "No sugarcoating:",
        "Cutting to the chase,", "Between you and me,",
        "Off the top of my head,",
    ],
    "ru": [
        "На практике,", "По моему опыту,", "Как я это вижу,",
        "Интересно, что", "Вот в чём дело:", "Скажу так:",
        "Справедливости ради,", "Короче говоря,", "Суть такая:",
        "Если честно,", "По-моему,", "Правда в том, что",
        "Что действительно важно —", "Вкратце:",
        "Простыми словами,", "Может я и ошибаюсь, но",
        "Давайте начистоту,", "Главный вывод:",
        "По собственному опыту,", "Если спросите меня,",
        "В конце концов,", "Без прикрас:",
        "Если по существу,", "Между нами говоря,",
        "Навскидку,",
    ],
    "uk": [
        "На практиці,", "З мого досвіду,", "Як я це бачу,",
        "Цікаво, що", "Ось у чому справа:", "Скажу так:",
        "Задля справедливості,", "Коротко кажучи,", "Суть така:",
        "Якщо чесно,", "На мою думку,", "Правда в тому, що",
        "Що дійсно важливо —", "Стисло:",
        "Простими словами,", "Може я й помиляюсь, але",
        "Давайте відверто,", "Головний висновок:",
        "З власного досвіду,", "Якщо запитаєте мене,",
        "Зрештою,", "Без прикрас:",
        "Якщо по суті,", "Між нами кажучи,",
        "Навскидку,",
    ],
}

_CONTRACTION_MAP_EN: dict[str, str] = {
    "it is": "it's", "that is": "that's", "there is": "there's",
    "they are": "they're", "we are": "we're", "you are": "you're",
    "do not": "don't", "does not": "doesn't", "did not": "didn't",
    "is not": "isn't", "are not": "aren't", "was not": "wasn't",
    "cannot": "can't", "will not": "won't", "would not": "wouldn't",
    "could not": "couldn't", "should not": "shouldn't",
    "have not": "haven't", "has not": "hasn't", "had not": "hadn't",
    "I am": "I'm", "I have": "I've", "I will": "I'll",
    "I would": "I'd", "they have": "they've",
    "we have": "we've", "you have": "you've",
    "let us": "let's",
}


# ═══════════════════════════════════════════════════════════════
#  CORE ENGINE
# ═══════════════════════════════════════════════════════════════

class AdversarialPlay:
    """Detector-guided iterative humanization.

    ASH™ Adversarial Ensemble Self-Play™ — proprietary technology.

    Uses three detectors to build a per-sentence problem map and
    applies targeted fixes only where needed, iterating until the
    text passes detection or max rounds are reached.

    Usage::

        ap = AdversarialPlay(lang="en")
        result = ap.play(text, intensity=0.5, max_rounds=4)
        print(f"Score: {result.initial_score:.2f} → {result.final_score:.2f}")
        print(result.text)
    """

    def __init__(
        self,
        lang: str = "en",
        seed: int | None = None,
    ) -> None:
        self.lang = lang
        self.seed = seed
        self._rng = random.Random(seed)
        self._markers = _DISCOURSE_MARKERS.get(lang, _DISCOURSE_MARKERS["en"])
        self._ai_openers = _AI_OPENERS.get(lang, _AI_OPENERS["en"])
        self._humanisers = _HUMANISERS.get(lang, _HUMANISERS["en"])
        self._contractions = _CONTRACTION_MAP_EN if lang == "en" else {}

    # ── Public API ──

    def play(
        self,
        text: str,
        intensity: float = 0.5,
        max_rounds: int = 4,
        target_score: float = 0.35,
    ) -> PlayResult:
        """Run adversarial self-play iterations.

        Parameters
        ----------
        text : str
            Input text.
        intensity : float
            Base intensity (0.0–1.0). Escalates each round.
        max_rounds : int
            Max iteration rounds (default 4).
        target_score : float
            Stop if combined AI score ≤ this.

        Returns
        -------
        PlayResult
        """
        if not text or not text.strip():
            return PlayResult(text=text, original_text=text)

        current = text
        history: list[dict[str, Any]] = []
        initial_score = self._detect_score(current)
        total_modified = 0

        for rnd in range(1, max_rounds + 1):
            escalated = min(1.0, intensity + 0.1 * (rnd - 1))

            # Build problem map (adaptive: uses initial score)
            problem_map = self._build_problem_map(current, escalated, initial_score)

            flagged = [pm for pm in problem_map if pm["flagged"]]
            if not flagged:
                logger.info("Round %d: no flagged sentences, stopping.", rnd)
                break

            # Apply fixes
            modified, n_fixed = self._apply_fixes(current, problem_map, escalated)

            # Score after
            new_score = self._detect_score(modified)
            prev_score = self._detect_score(current)

            round_info = {
                "round": rnd,
                "flagged_sentences": len(flagged),
                "fixed_sentences": n_fixed,
                "score_before": prev_score,
                "score_after": new_score,
                "intensity": escalated,
            }
            history.append(round_info)
            logger.info(
                "Round %d: %d flagged, %d fixed, score %.3f → %.3f",
                rnd, len(flagged), n_fixed,
                round_info["score_before"], new_score,
            )

            # Hill-climbing guard: only accept changes that improve score
            if new_score <= prev_score:
                current = modified
                total_modified += n_fixed
            else:
                logger.info(
                    "Round %d: score worsened (%.3f → %.3f), rolling back.",
                    rnd, prev_score, new_score,
                )

            if new_score <= target_score:
                logger.info("Target score reached (%.3f ≤ %.3f)", new_score, target_score)
                break

        final_score = self._detect_score(current)

        return PlayResult(
            text=current,
            original_text=text,
            rounds=len(history),
            sentences_modified=total_modified,
            initial_score=initial_score,
            final_score=final_score,
            history=history,
        )

    # ── Problem Map ──

    def _build_problem_map(
        self, text: str, intensity: float,
        initial_score: float = 0.6,
    ) -> list[dict[str, Any]]:
        """Build per-sentence problem map using detectors."""
        sentences = split_sentences(text, self.lang)
        problem_map: list[dict[str, Any]] = []

        # Adaptive threshold: relative to initial text score AND intensity.
        # Lower base (0.45 vs old 0.6) + lower floor (0.20 vs old 0.30)
        # ensures sentences are flagged even after prior ASH steps.
        relative_threshold = initial_score * 0.65
        absolute_threshold = 0.45 - intensity * 0.25
        threshold = max(0.20, min(relative_threshold, absolute_threshold))

        for i, sent in enumerate(sentences):
            if len(sent.split()) < 3:
                problem_map.append({
                    "idx": i,
                    "text": sent,
                    "flagged": False,
                    "score": 0.0,
                    "reasons": [],
                })
                continue

            score = self._detect_sentence_score(sent)
            flagged = score > threshold

            reasons: list[str] = []
            if flagged:
                reasons = self._diagnose_sentence(sent)

            problem_map.append({
                "idx": i,
                "text": sent,
                "flagged": flagged,
                "score": score,
                "reasons": reasons,
            })

        # ── Force-flag fallback ──────────────────────────────────
        # If the overall text scores high (AI-like) but NO individual
        # sentences were flagged (common: our detector works best on
        # longer contexts, not single sentences), force-flag the
        # highest-scoring sentences so the adversarial loop fires.
        flagged_count = sum(1 for pm in problem_map if pm["flagged"])
        if flagged_count == 0 and initial_score > 0.40:
            eligible = [
                pm for pm in problem_map
                if len(pm["text"].split()) >= 3
            ]
            eligible.sort(key=lambda pm: pm["score"], reverse=True)
            # Flag top ~40% of eligible sentences (at least 1)
            n_force = max(1, int(len(eligible) * 0.4))
            for pm in eligible[:n_force]:
                pm["flagged"] = True
                if not pm["reasons"]:
                    pm["reasons"] = self._diagnose_sentence(pm["text"])
                    if not pm["reasons"]:
                        pm["reasons"] = ["high_score"]

        return problem_map

    def _detect_score(self, text: str) -> float:
        """Get combined AI detection score."""
        try:
            from texthumanize.detectors import AIDetector
            det = AIDetector(lang=self.lang)
            result = det.detect(text, lang=self.lang)
            return float(result.ai_probability)
        except Exception:
            return 0.5

    def _detect_sentence_score(self, sentence: str) -> float:
        """Score a single sentence."""
        try:
            from texthumanize.detectors import AIDetector
            det = AIDetector(lang=self.lang)
            result = det.detect(sentence, lang=self.lang)
            return float(result.ai_probability)
        except Exception:
            return 0.5

    def _diagnose_sentence(self, sentence: str) -> list[str]:
        """Identify specific problems in a sentence."""
        reasons = []

        words = sentence.split()
        n_words = len(words)

        # Check for AI openers
        for opener in self._ai_openers:
            if sentence.startswith(opener):
                reasons.append("ai_opener")
                break

        # Check for too-uniform sentence structure
        if n_words > 15 and all(len(w) < 12 for w in words):
            reasons.append("uniform_length")

        # Check for lack of contractions (EN)
        if self.lang == "en":
            for formal, _contraction in self._contractions.items():
                if formal.lower() in sentence.lower():
                    reasons.append("no_contractions")
                    break

        # Check for overly formal language
        formal_markers_en = {"utilize", "endeavor", "facilitate", "commence"}
        formal_markers_ru = {"осуществлять", "представляется", "целесообразно"}
        formal_markers_uk = {"здійснювати", "уявляється", "доцільно"}

        markers = {
            "en": formal_markers_en,
            "ru": formal_markers_ru,
            "uk": formal_markers_uk,
        }.get(self.lang, formal_markers_en)

        lower_words = {w.lower().strip(".,;:!?") for w in words}
        if lower_words & markers:
            reasons.append("overly_formal")

        # Check for very long sentence (AI tends to write longer)
        if n_words > 35:
            reasons.append("too_long")

        if not reasons:
            reasons.append("high_score")

        return reasons

    # ── Targeted Fixes ──

    def _apply_fixes(
        self,
        text: str,
        problem_map: list[dict[str, Any]],
        intensity: float,
    ) -> tuple[str, int]:
        """Apply targeted fixes to flagged sentences."""
        sentences = [pm["text"] for pm in problem_map]
        new_sents = list(sentences)
        fixed = 0

        for pm in problem_map:
            if not pm["flagged"]:
                continue

            idx = pm["idx"]
            sent = pm["text"]
            reasons = pm["reasons"]
            modified = sent

            # Apply reason-specific fixes
            for reason in reasons:
                modified = self._fix_reason(modified, reason, intensity)

            if modified != sent:
                new_sents[idx] = modified
                fixed += 1

        # Rejoin
        result = text
        for old, new in zip(sentences, new_sents):
            if old != new:
                result = result.replace(old, new, 1)

        return result, fixed

    def _fix_reason(
        self, sentence: str, reason: str, intensity: float,
    ) -> str:
        """Apply a fix for a specific reason."""
        if reason == "ai_opener":
            return self._fix_ai_opener(sentence)
        elif reason == "no_contractions":
            return self._fix_contractions(sentence)
        elif reason == "overly_formal":
            return self._fix_formal(sentence)
        elif reason == "too_long":
            return self._fix_long_sentence(sentence, intensity)
        elif reason == "uniform_length":
            return self._add_discourse_marker(sentence)
        elif reason == "high_score":
            return self._general_fix(sentence, intensity)
        return sentence

    def _fix_ai_opener(self, sentence: str) -> str:
        """Replace AI-typical openers."""
        for opener in self._ai_openers:
            if sentence.startswith(opener):
                replacement = self._rng.choice(self._humanisers)
                rest = sentence[len(opener):].lstrip()
                if rest:
                    return replacement + " " + rest
        return sentence

    def _fix_contractions(self, sentence: str) -> str:
        """Add contractions (EN only)."""
        if self.lang != "en":
            return sentence

        result = sentence
        for formal, contr in self._contractions.items():
            if self._rng.random() < 0.6:
                pattern = re.compile(re.escape(formal), re.IGNORECASE)
                result = pattern.sub(contr, result, count=1)
        return result

    def _fix_formal(self, sentence: str) -> str:
        """Replace overly formal words."""
        replacements = {
            "en": {
                "utilize": "use", "endeavor": "try",
                "facilitate": "help", "commence": "start",
                "implement": "set up", "subsequently": "then",
                "regarding": "about",
            },
            "ru": {
                "осуществлять": "делать", "представляется": "кажется",
                "целесообразно": "стоит", "вышеупомянутый": "этот",
                "нижеследующий": "этот",
            },
            "uk": {
                "здійснювати": "робити", "уявляється": "здається",
                "доцільно": "варто", "вищезгаданий": "цей",
                "нижченаведений": "цей",
            },
        }.get(self.lang, {})

        result = sentence
        for formal, simple in replacements.items():
            pattern = re.compile(re.escape(formal), re.IGNORECASE)
            if pattern.search(result):
                result = pattern.sub(simple, result, count=1)
                break
        return result

    def _fix_long_sentence(self, sentence: str, intensity: float) -> str:
        """Split a very long sentence."""
        words = sentence.split()
        if len(words) < 20:
            return sentence

        # Find a good split point (after comma, conjunction)
        split_words = {"and", "but", "however", "which", "while",
                       "и", "но", "однако", "который", "в то время как",
                       "і", "але", "однак", "який", "у той час як"}

        mid = len(words) // 2
        best_pos = mid

        for offset in range(min(8, len(words) // 4)):
            for d in (offset, -offset):
                pos = mid + d
                if 0 < pos < len(words):
                    w = words[pos].lower().strip(".,;:")
                    if w in split_words or words[pos - 1].endswith(","):
                        best_pos = pos
                        break
            else:
                continue
            break

        first_half = " ".join(words[:best_pos]).rstrip(",;:")
        second_half = " ".join(words[best_pos:])

        if first_half and first_half[-1] not in ".!?":
            first_half += "."

        if second_half:
            second_half = second_half[0].upper() + second_half[1:]

        return first_half + " " + second_half

    def _add_discourse_marker(self, sentence: str) -> str:
        """Add a human discourse marker."""
        if self._rng.random() < 0.5:
            marker = self._rng.choice(self._markers)
            # lowercase first letter of sentence
            lower = sentence[0].lower() + sentence[1:] if sentence else sentence
            return marker + " " + lower
        return sentence

    def _general_fix(self, sentence: str, intensity: float) -> str:
        """Apply a general humanization fix."""
        strategies = ["marker", "minor_edit", "restructure"]
        if self.lang == "en":
            strategies.append("contraction")

        strategy = self._rng.choice(strategies)

        if strategy == "marker" and self._rng.random() < intensity:
            return self._add_discourse_marker(sentence)
        elif strategy == "contraction":
            return self._fix_contractions(sentence)
        elif strategy == "restructure":
            return self._restructure_sentence(sentence, intensity)
        elif strategy == "minor_edit":
            return self._minor_edit(sentence)
        return sentence

    def _restructure_sentence(self, sentence: str, intensity: float) -> str:
        """Apply sentence-level structural transforms."""
        try:
            from texthumanize.sentence_restructurer import (
                apply_deep_sentence_transforms,
            )
            result = apply_deep_sentence_transforms(
                sentence, self.lang, rng=self._rng, intensity=intensity,
            )
            return result if result != sentence else self._add_discourse_marker(sentence)
        except Exception:
            return self._add_discourse_marker(sentence)

    def _minor_edit(self, sentence: str) -> str:
        """Small edit to break uniformity."""
        words = sentence.split()
        if len(words) < 5:
            return sentence

        # Add a parenthetical aside
        asides = {
            "en": ["(really)", "(actually)", "(in short)"],
            "ru": ["(правда)", "(вообще)", "(короче)"],
            "uk": ["(правда)", "(взагалі)", "(коротше)"],
        }.get(self.lang, ["(really)"])

        insert_pos = self._rng.randint(2, min(len(words) - 1, 6))
        words.insert(insert_pos, self._rng.choice(asides))
        return " ".join(words)


# ═══════════════════════════════════════════════════════════════
#  MODULE-LEVEL CONVENIENCE
# ═══════════════════════════════════════════════════════════════

def adversarial_humanize(
    text: str,
    lang: str = "en",
    intensity: float = 0.5,
    max_rounds: int = 4,
    target_score: float = 0.35,
    seed: int | None = None,
) -> PlayResult:
    """Detector-guided iterative humanization.

    ASH™ Adversarial Ensemble Self-Play™.

    Runs multiple rounds where detectors identify problems and
    targeted fixes are applied only to flagged sentences.
    """
    return AdversarialPlay(lang=lang, seed=seed).play(
        text,
        intensity=intensity,
        max_rounds=max_rounds,
        target_score=target_score,
    )


def build_problem_map(
    text: str,
    lang: str = "en",
    intensity: float = 0.5,
) -> list[dict[str, Any]]:
    """Build per-sentence AI-detection problem map.

    Returns a list of dicts — one per sentence — with:
    idx, text, flagged (bool), score, reasons.
    """
    return AdversarialPlay(lang=lang)._build_problem_map(text, intensity)
