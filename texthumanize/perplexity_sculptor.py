"""Perplexity Sculpting™ — reshape the perplexity curve of text.

Part of the ASH™ (Adaptive Statistical Humanization) technology
developed by Oleksandr K. for TextHumanize.

Core idea
---------
AI-generated text has a *smooth, low* perplexity curve: every word
is highly predictable from its context.  Human text has a *jagged*
curve: predictable stretches alternate with surprises (rare words,
creative phrases, topic shifts).

Perplexity Sculpting™ detects regions where the curve is "too smooth"
and introduces controlled *surprises* — semantically valid but less
predictable synonyms — in exactly the right positions, reshaping the
curve to match a human profile without changing the meaning.

Copyright (c) 2024-2026 Oleksandr K. / TextHumanize Project.
"""

from __future__ import annotations

import logging
import random
import re
from dataclasses import dataclass, field
from typing import Any

from texthumanize._human_profiles import (
    get_ai_profile,
    get_human_profile,
)
from texthumanize.sentence_split import split_sentences
from texthumanize.word_lm import WordLanguageModel

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
#  DATA — surprise synonyms (less-predictable but correct)
# ═══════════════════════════════════════════════════════════════

# These replacements are specifically chosen to be *less* predictable
# (higher surprise) while remaining semantically appropriate.
# Ordered from most-common (low surprise) to least-common (high surprise).
_SURPRISE_SYNONYMS: dict[str, dict[str, list[str]]] = {
    "en": {
        "important": ["crucial", "pivotal", "vital", "paramount"],
        "significant": ["substantial", "noteworthy", "appreciable", "sizable"],
        "various": ["assorted", "sundry", "manifold", "disparate"],
        "however": ["yet", "still", "though", "nonetheless", "that said"],
        "therefore": ["hence", "thus", "so", "accordingly", "as a result"],
        "additionally": ["also", "besides", "on top of that", "what's more"],
        "furthermore": ["moreover", "what's more", "beyond that", "besides"],
        "consequently": ["as a result", "so", "thus", "hence"],
        "utilize": ["use", "employ", "harness", "leverage", "tap into"],
        "implement": ["put in place", "roll out", "set up", "carry out"],
        "facilitate": ["help", "ease", "enable", "foster", "pave the way for"],
        "demonstrate": ["show", "reveal", "illustrate", "make clear"],
        "establish": ["set up", "create", "build", "found", "forge"],
        "provide": ["offer", "supply", "deliver", "furnish", "give"],
        "ensure": ["make sure", "guarantee", "see to it", "confirm"],
        "approach": ["method", "strategy", "tactic", "angle", "way"],
        "enhance": ["improve", "boost", "strengthen", "enrich", "amplify"],
        "achieve": ["reach", "attain", "accomplish", "pull off", "manage"],
        "contribute": ["add", "bring", "feed into", "help with"],
        "effective": ["efficient", "potent", "powerful", "impactful"],
        "comprehensive": ["thorough", "exhaustive", "full", "wide-ranging"],
        "process": ["procedure", "sequence", "workflow", "routine"],
        "very": ["quite", "really", "truly", "remarkably", "decidedly"],
        "good": ["solid", "strong", "decent", "fine", "reliable"],
        "make": ["create", "build", "craft", "produce", "put together"],
        "thing": ["element", "factor", "aspect", "piece", "item"],
        "analyze": ["examine", "dissect", "break down", "probe", "scrutinize"],
        "benefit": ["perk", "upside", "advantage", "boon", "win"],
        "challenge": ["hurdle", "obstacle", "snag", "roadblock"],
        "component": ["part", "piece", "building block", "module"],
        "consider": ["weigh", "ponder", "mull over", "think about"],
        "development": ["growth", "evolution", "progress", "advance"],
        "environment": ["setting", "landscape", "arena", "sphere"],
        "feature": ["trait", "attribute", "characteristic", "quality"],
        "generate": ["produce", "create", "yield", "churn out"],
        "identify": ["spot", "pinpoint", "flag", "single out"],
        "include": ["cover", "encompass", "span", "feature"],
        "indicate": ["suggest", "hint", "point to", "signal"],
        "maintain": ["keep", "uphold", "preserve", "sustain"],
        "opportunity": ["chance", "opening", "window", "shot"],
        "particular": ["specific", "certain", "given", "distinct"],
        "perspective": ["viewpoint", "angle", "lens", "take"],
        "potential": ["possible", "promising", "likely", "latent"],
        "structure": ["framework", "scaffold", "skeleton", "layout"],
        "suggest": ["propose", "hint", "imply", "recommend"],
        "system": ["setup", "framework", "mechanism", "apparatus"],
    },
    "ru": {
        "важно": ["существенно", "принципиально", "критично", "немаловажно"],
        "значительный": ["ощутимый", "заметный", "весомый", "внушительный"],
        "различный": ["разнообразный", "всевозможный", "разноплановый"],
        "однако": ["впрочем", "тем не менее", "хотя", "при этом", "правда"],
        "поэтому": ["потому", "оттого", "вследствие этого", "из-за этого"],
        "кроме того": ["помимо этого", "вдобавок", "ещё", "плюс к тому"],
        "следовательно": ["стало быть", "значит", "выходит", "отсюда"],
        "обеспечивать": ["гарантировать", "давать", "создавать условия"],
        "осуществлять": ["проводить", "делать", "выполнять", "вести"],
        "реализовать": ["воплотить", "претворить", "сделать", "провернуть"],
        "демонстрировать": ["показывать", "являть", "обнаруживать"],
        "способствовать": ["помогать", "содействовать", "вести к"],
        "является": ["представляет собой", "выступает", "есть", "служит"],
        "необходимо": ["нужно", "требуется", "следует", "стоит", "надо"],
        "данный": ["этот", "настоящий", "указанный", "текущий"],
        "существенный": ["заметный", "ощутимый", "серьёзный", "весомый"],
        "эффективный": ["действенный", "результативный", "продуктивный"],
        "определённый": ["конкретный", "некоторый", "известный", "чёткий"],
        "процесс": ["ход", "течение", "механизм", "порядок"],
        "подход": ["метод", "способ", "путь", "приём", "стратегия"],
        "очень": ["весьма", "крайне", "чрезвычайно", "довольно", "на редкость"],
        "хороший": ["добротный", "крепкий", "приличный", "ладный"],
        "анализировать": ["разбирать", "изучать", "исследовать", "рассекать"],
        "вариант": ["опция", "путь", "ход", "возможность"],
        "возможность": ["шанс", "перспектива", "окно", "выход"],
        "задача": ["цель", "дело", "замысел", "миссия"],
        "качество": ["свойство", "черта", "признак", "достоинство"],
        "компонент": ["часть", "элемент", "звено", "блок"],
        "направление": ["курс", "русло", "вектор", "линия"],
        "особенность": ["черта", "свойство", "штрих", "нюанс"],
        "результат": ["итог", "плод", "исход", "выход"],
        "система": ["устройство", "механизм", "схема", "аппарат"],
        "создавать": ["строить", "мастерить", "лепить", "формировать"],
        "структура": ["каркас", "остов", "скелет", "схема"],
        "условие": ["предпосылка", "фактор", "обстоятельство"],
        "фактор": ["причина", "обстоятельство", "момент", "движущая сила"],
        "часть": ["доля", "кусок", "фрагмент", "отрезок"],
    },
    "uk": {
        "важливо": ["суттєво", "принципово", "критично", "неабияк"],
        "значний": ["відчутний", "помітний", "вагомий", "чималий"],
        "різний": ["різноманітний", "всілякий", "різноплановий"],
        "однак": ["втім", "проте", "хоча", "при цьому", "щоправда"],
        "тому": ["через це", "відтак", "з цієї причини", "ось чому"],
        "крім того": ["окрім цього", "додатково", "ще", "на додачу"],
        "отже": ["відтак", "стало бути", "виходить", "звідси"],
        "забезпечувати": ["гарантувати", "давати", "створювати умови"],
        "здійснювати": ["проводити", "робити", "виконувати", "вести"],
        "реалізувати": ["втілити", "зробити", "запровадити"],
        "демонструвати": ["показувати", "являти", "виявляти"],
        "сприяти": ["допомагати", "посприяти", "вести до"],
        "є": ["виступає", "являє собою", "становить", "слугує"],
        "необхідно": ["потрібно", "треба", "слід", "варто", "належить"],
        "даний": ["цей", "вказаний", "поточний", "наявний"],
        "суттєвий": ["помітний", "відчутний", "серйозний", "вагомий"],
        "ефективний": ["дієвий", "результативний", "продуктивний"],
        "процес": ["хід", "перебіг", "механізм", "порядок"],
        "підхід": ["метод", "спосіб", "шлях", "прийом", "стратегія"],
        "дуже": ["вельми", "надзвичайно", "доволі", "напрочуд"],
        "аналізувати": ["розбирати", "вивчати", "досліджувати"],
        "варіант": ["опція", "шлях", "хід", "можливість"],
        "можливість": ["шанс", "перспектива", "вікно", "вихід"],
        "завдання": ["мета", "справа", "замисел", "місія"],
        "якість": ["властивість", "риса", "ознака", "чеснота"],
        "компонент": ["частина", "елемент", "ланка", "блок"],
        "напрямок": ["курс", "русло", "вектор", "лінія"],
        "особливість": ["риса", "властивість", "штрих", "нюанс"],
        "результат": ["підсумок", "плід", "вихід", "наслідок"],
        "система": ["устрій", "механізм", "схема", "апарат"],
        "створювати": ["будувати", "майструвати", "ліпити", "формувати"],
        "структура": ["каркас", "кістяк", "скелет", "схема"],
        "умова": ["передумова", "чинник", "обставина"],
        "чинник": ["причина", "обставина", "момент", "рушійна сила"],
        "частина": ["доля", "шматок", "фрагмент", "відтинок"],
    },
}


# ═══════════════════════════════════════════════════════════════
#  RESULT DATACLASS
# ═══════════════════════════════════════════════════════════════

@dataclass
class SculptResult:
    """Result of Perplexity Sculpting™ pass."""
    text: str
    original_text: str
    changes: list[dict[str, Any]] = field(default_factory=list)
    ppl_before: float = 0.0
    ppl_after: float = 0.0
    ppl_cv_before: float = 0.0
    ppl_cv_after: float = 0.0
    autocorr_before: float = 0.0
    autocorr_after: float = 0.0
    surprises_injected: int = 0

    @property
    def improvement(self) -> float:
        """How much closer to human profile (0–1, higher=better)."""
        if self.ppl_cv_before == 0:
            return 0.0
        return min(1.0, max(0.0,
            (self.ppl_cv_after - self.ppl_cv_before) /
            max(0.01, 0.70 - self.ppl_cv_before)))


# ═══════════════════════════════════════════════════════════════
#  CORE ENGINE
# ═══════════════════════════════════════════════════════════════

class PerplexitySculptor:
    """Reshape the perplexity curve of text to match human patterns.

    ASH™ Perplexity Sculpting™ — proprietary technology.

    Usage::

        sculptor = PerplexitySculptor(lang="en")
        result = sculptor.sculpt(text, intensity=0.6)
        print(result.text)
        print(result.ppl_cv_before, "→", result.ppl_cv_after)
    """

    def __init__(
        self,
        lang: str = "en",
        seed: int | None = None,
    ) -> None:
        self.lang = lang
        self.seed = seed
        self._rng = random.Random(seed)
        self._lm = WordLanguageModel(lang)
        self._human = get_human_profile(lang)
        self._ai = get_ai_profile(lang)
        self._synonyms = _SURPRISE_SYNONYMS.get(lang, _SURPRISE_SYNONYMS["en"])

    # ── Public API ──

    def sculpt(
        self,
        text: str,
        intensity: float = 0.6,
    ) -> SculptResult:
        """Main entry: reshape the perplexity curve.

        Parameters
        ----------
        text : str
            Input text.
        intensity : float
            0.0–1.0.  Higher = more aggressive reshaping.

        Returns
        -------
        SculptResult
        """
        if not text or not text.strip():
            return SculptResult(text=text, original_text=text)

        sentences = split_sentences(text, self.lang)
        if len(sentences) < 2:
            return SculptResult(text=text, original_text=text)

        # Step 1: Build perplexity map
        ppl_map = self._build_perplexity_map(sentences)
        ppl_before = self._mean_ppl(ppl_map)
        cv_before = self._ppl_cv(ppl_map)
        ac_before = self._autocorrelation(ppl_map)

        # Step 2: Find "too smooth" regions
        smooth_regions = self._find_smooth_regions(ppl_map, intensity)

        # Step 3: Inject surprises
        new_sentences = list(sentences)
        changes: list[dict[str, Any]] = []
        injected = 0

        for region in smooth_regions:
            idx = region["sentence_idx"]
            if idx >= len(new_sentences):
                continue

            original = new_sentences[idx]
            modified, region_changes = self._inject_surprise(
                original, region, intensity
            )
            if modified != original:
                new_sentences[idx] = modified
                changes.extend(region_changes)
                injected += len(region_changes)

        # Step 4: Verify improvement
        result_text = self._rejoin(text, sentences, new_sentences)

        new_sents = split_sentences(result_text, self.lang)
        ppl_map_after = self._build_perplexity_map(new_sents)
        cv_after = self._ppl_cv(ppl_map_after)
        ac_after = self._autocorrelation(ppl_map_after)

        return SculptResult(
            text=result_text,
            original_text=text,
            changes=changes,
            ppl_before=ppl_before,
            ppl_after=self._mean_ppl(ppl_map_after),
            ppl_cv_before=cv_before,
            ppl_cv_after=cv_after,
            autocorr_before=ac_before,
            autocorr_after=ac_after,
            surprises_injected=injected,
        )

    def analyze_curve(self, text: str) -> dict[str, Any]:
        """Analyze the perplexity curve without modifying text.

        Returns detailed metrics about the perplexity distribution.
        """
        sentences = split_sentences(text, self.lang)
        if len(sentences) < 2:
            return {"sentences": 0, "verdict": "too_short"}

        ppl_map = self._build_perplexity_map(sentences)
        mean_ppl = self._mean_ppl(ppl_map)
        cv = self._ppl_cv(ppl_map)
        ac = self._autocorrelation(ppl_map)
        peak_ratio = self._peak_ratio(ppl_map, mean_ppl)

        # Compare against profiles
        human_cv = self._human.get("PPL_word_cv", {}).get("mean", 0.70)
        ai_cv = self._ai.get("PPL_word_cv", {}).get("mean", 0.30)
        human_ac = self._human.get("PPL_autocorr_lag1", {}).get("mean", 0.15)
        ai_ac = self._ai.get("PPL_autocorr_lag1", {}).get("mean", 0.40)

        # Closeness score: 0 = AI-like, 1 = human-like
        cv_score = min(1.0, max(0.0, (cv - ai_cv) / max(0.01, human_cv - ai_cv)))
        ac_score = min(1.0, max(0.0, (ai_ac - ac) / max(0.01, ai_ac - human_ac)))
        humanness = (cv_score * 0.6 + ac_score * 0.4)

        return {
            "sentences": len(sentences),
            "mean_perplexity": round(mean_ppl, 2),
            "perplexity_cv": round(cv, 4),
            "autocorrelation_lag1": round(ac, 4),
            "peak_ratio": round(peak_ratio, 4),
            "humanness_score": round(humanness, 4),
            "verdict": (
                "human_like" if humanness > 0.6
                else "mixed" if humanness > 0.3
                else "ai_like"
            ),
            "per_sentence": [
                {
                    "index": i,
                    "text": s[:80],
                    "perplexity": round(p, 2),
                    "is_smooth": p < mean_ppl * 0.6,
                }
                for i, (s, p) in enumerate(zip(sentences, ppl_map))
            ],
        }

    # ── Internals ──

    def _build_perplexity_map(
        self, sentences: list[str]
    ) -> list[float]:
        """Compute per-sentence perplexity."""
        result = []
        for s in sentences:
            s_clean = s.strip()
            if not s_clean or len(s_clean.split()) < 2:
                result.append(50.0)  # default neutral
                continue
            try:
                ppl = self._lm.sentence_perplexity(s_clean)
                result.append(max(1.0, ppl))
            except Exception:
                result.append(50.0)
        return result

    def _mean_ppl(self, ppl_map: list[float]) -> float:
        if not ppl_map:
            return 0.0
        return sum(ppl_map) / len(ppl_map)

    def _ppl_cv(self, ppl_map: list[float]) -> float:
        """Coefficient of variation of the perplexity curve."""
        if len(ppl_map) < 2:
            return 0.0
        mean = self._mean_ppl(ppl_map)
        if mean <= 0:
            return 0.0
        var = sum((x - mean) ** 2 for x in ppl_map) / len(ppl_map)
        return (var ** 0.5) / mean

    def _autocorrelation(self, ppl_map: list[float]) -> float:
        """Lag-1 autocorrelation of the perplexity curve."""
        n = len(ppl_map)
        if n < 3:
            return 0.0
        mean = sum(ppl_map) / n
        var = sum((x - mean) ** 2 for x in ppl_map)
        if var == 0:
            return 0.0
        cov = sum(
            (ppl_map[i] - mean) * (ppl_map[i + 1] - mean)
            for i in range(n - 1)
        )
        return cov / var

    def _peak_ratio(self, ppl_map: list[float], mean: float) -> float:
        """Ratio of sentences with perplexity > 1.5× mean (surprises)."""
        if not ppl_map:
            return 0.0
        threshold = mean * 1.5
        peaks = sum(1 for x in ppl_map if x > threshold)
        return peaks / len(ppl_map)

    def _find_smooth_regions(
        self,
        ppl_map: list[float],
        intensity: float,
    ) -> list[dict[str, Any]]:
        """Find sentences where perplexity is too low/smooth."""
        if len(ppl_map) < 2:
            return []

        mean = self._mean_ppl(ppl_map)
        target_cv = self._human.get("PPL_word_cv", {}).get("mean", 0.70)
        current_cv = self._ppl_cv(ppl_map)

        # If already human-like, skip
        if current_cv >= target_cv * 0.9:
            return []

        # Find the smoothest (most predictable) sentences
        regions = []
        for i, ppl in enumerate(ppl_map):
            # Smoothness = how much below mean (too predictable)
            smoothness = max(0.0, 1.0 - ppl / max(1.0, mean))

            # Also check local smoothness (similar to neighbors)
            local_smooth = 0.0
            if i > 0 and i < len(ppl_map) - 1:
                diff_prev = abs(ppl - ppl_map[i - 1])
                diff_next = abs(ppl - ppl_map[i + 1])
                avg_diff = (diff_prev + diff_next) / 2
                local_smooth = max(0.0, 1.0 - avg_diff / max(1.0, mean * 0.5))

            combined = smoothness * 0.6 + local_smooth * 0.4

            # Intensity controls threshold — lowered for more aggressive sculpting
            threshold = 0.45 - intensity * 0.35  # high intensity → lower threshold
            if combined > threshold:
                regions.append({
                    "sentence_idx": i,
                    "smoothness": combined,
                    "current_ppl": ppl,
                    "target_ppl": mean * (1.0 + self._rng.uniform(0.3, 0.8)),
                })

        # Sort by smoothness (worst first) and limit — higher cap
        regions.sort(key=lambda r: r["smoothness"], reverse=True)
        max_changes = max(1, int(len(ppl_map) * intensity * 0.8))
        return regions[:max_changes]

    def _inject_surprise(
        self,
        sentence: str,
        region: dict[str, Any],
        intensity: float,
    ) -> tuple[str, list[dict[str, Any]]]:
        """Inject surprise words into a sentence."""
        changes: list[dict[str, Any]] = []
        words = sentence.split()
        if len(words) < 3:
            return sentence, changes

        # Find replaceable words
        candidates: list[tuple[int, str, list[str]]] = []
        for i, word in enumerate(words):
            clean = re.sub(r'[^\w]', '', word.lower())
            if clean in self._synonyms:
                candidates.append((i, word, self._synonyms[clean]))
            else:
                # Fallback: massive synonym DB
                try:
                    from texthumanize._synonym_db import SynonymDB
                    _fb = SynonymDB().get(clean, self.lang)
                    if _fb:
                        candidates.append((i, word, _fb))
                except Exception:
                    pass

        if not candidates:
            # Fallback: try to add a surprise discourse marker
            return self._inject_discourse_surprise(sentence, region, intensity)

        # Pick 1-3 candidates based on intensity
        num_replacements = (
            1 if intensity < 0.4
            else 2 if intensity < 0.7
            else min(3, len(candidates))
        )
        chosen = self._rng.sample(
            candidates, min(num_replacements, len(candidates))
        )

        for idx, original_word, synonyms in chosen:
            # Pick a less-common synonym (later in list = less common)
            # Higher intensity → pick from deeper in the list (more surprise)
            start = max(0, int(len(synonyms) * intensity * 0.3))
            pool = synonyms[start:]
            if not pool:
                pool = synonyms
            replacement = self._rng.choice(pool)

            # Preserve capitalization
            if original_word[0].isupper():
                replacement = replacement[0].upper() + replacement[1:]

            # Preserve trailing punctuation
            trailing = ""
            for ch in reversed(original_word):
                if ch.isalpha():
                    break
                trailing = ch + trailing
            if trailing:
                replacement = replacement.rstrip(".,;:!?") + trailing

            words[idx] = replacement
            changes.append({
                "type": "perplexity_surprise",
                "position": idx,
                "original": original_word,
                "replacement": replacement,
                "sentence_idx": region["sentence_idx"],
            })

        return " ".join(words), changes

    def _inject_discourse_surprise(
        self,
        sentence: str,
        region: dict[str, Any],
        intensity: float,
    ) -> tuple[str, list[dict[str, Any]]]:
        """Add a discourse marker to inject perplexity spike."""
        markers: dict[str, list[str]] = {
            "en": [
                "honestly,", "in fact,", "oddly enough,", "sure,",
                "well,", "look,", "mind you,", "granted,",
                "to be fair,", "naturally,",
            ],
            "ru": [
                "честно говоря,", "по сути,", "ну,", "вообще-то,",
                "скажем так,", "ладно,", "впрочем,", "знаете,",
                "по правде,", "разумеется,",
            ],
            "uk": [
                "чесно кажучи,", "по суті,", "ну,", "загалом,",
                "скажімо,", "гаразд,", "втім,", "знаєте,",
                "зрештою,", "звісно,",
            ],
        }

        lang_markers = markers.get(self.lang, markers["en"])
        if not lang_markers or intensity < 0.4:
            return sentence, []

        # Only inject if sentence starts with a word (not a marker already)
        first_word = sentence.split()[0].lower().rstrip(",")
        existing_markers = {m.split(",")[0].split()[0].lower() for m in lang_markers}
        if first_word in existing_markers:
            return sentence, []

        marker = self._rng.choice(lang_markers)
        new_sentence = marker + " " + sentence[0].lower() + sentence[1:]

        return new_sentence, [{
            "type": "discourse_surprise",
            "marker": marker,
            "sentence_idx": region["sentence_idx"],
        }]

    def _rejoin(
        self,
        original: str,
        old_sentences: list[str],
        new_sentences: list[str],
    ) -> str:
        """Rejoin modified sentences preserving original whitespace."""
        result = original
        for old, new in zip(old_sentences, new_sentences):
            if old != new:
                result = result.replace(old, new, 1)
        return result


# ═══════════════════════════════════════════════════════════════
#  MODULE-LEVEL CONVENIENCE
# ═══════════════════════════════════════════════════════════════

def sculpt_perplexity(
    text: str,
    lang: str = "en",
    intensity: float = 0.6,
    seed: int | None = None,
) -> SculptResult:
    """Reshape the perplexity curve of text to match human patterns.

    ASH™ Perplexity Sculpting™ — see :class:`PerplexitySculptor`.
    """
    return PerplexitySculptor(lang=lang, seed=seed).sculpt(text, intensity)


def analyze_perplexity_curve(
    text: str,
    lang: str = "en",
) -> dict[str, Any]:
    """Analyze the perplexity distribution of text.

    Returns metrics + verdict (ai_like / mixed / human_like).
    """
    return PerplexitySculptor(lang=lang).analyze_curve(text)
