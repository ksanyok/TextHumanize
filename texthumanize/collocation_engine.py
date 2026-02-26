"""Collocation engine for context-aware synonym selection.

Uses PMI (Pointwise Mutual Information) to score word
collocations, ensuring replacements sound natural.
"heavy rain" → ok, "heavy sun" → bad.

Usage:
    from texthumanize.collocation_engine import CollocEngine

    eng = CollocEngine(lang="en")
    score = eng.pmi("heavy", "rain")
    best = eng.best_synonym("important", ["crucial", "key",
                                           "significant"],
                            context=["very", "decision"])
"""

from __future__ import annotations

import re
from typing import Any

# ── English collocations ──────────────────────────────────
# (word_a, word_b) → log-frequency

_EN_COLL: dict[tuple[str, str], float] = {
    # Nature / Weather
    ("heavy", "rain"): 5.2, ("heavy", "snow"): 4.8,
    ("strong", "wind"): 5.1, ("bright", "sun"): 4.6,
    ("thick", "fog"): 4.5, ("clear", "sky"): 4.4,
    ("pouring", "rain"): 4.3, ("gentle", "breeze"): 4.5,
    ("bitter", "cold"): 4.4, ("scorching", "heat"): 4.3,
    # Action intensity
    ("deeply", "concerned"): 4.8, ("highly", "unlikely"): 5.1,
    ("bitterly", "disappointed"): 4.7,
    ("seriously", "injured"): 4.9,
    ("heavily", "influenced"): 4.6,
    ("widely", "known"): 4.7, ("widely", "used"): 4.8,
    ("closely", "related"): 4.8, ("closely", "monitored"): 4.5,
    ("strongly", "recommended"): 4.7,
    ("greatly", "appreciated"): 4.6,
    ("actively", "involved"): 4.5,
    ("firmly", "believe"): 4.4, ("firmly", "believed"): 4.4,
    # Common adj+noun
    ("significant", "impact"): 4.9,
    ("significant", "role"): 4.6,
    ("significant", "change"): 4.5,
    ("crucial", "role"): 4.8,
    ("crucial", "decision"): 4.5,
    ("vital", "role"): 4.6, ("vital", "importance"): 4.4,
    ("key", "factor"): 4.8, ("key", "role"): 4.7,
    ("key", "issue"): 4.5,
    ("major", "role"): 4.6, ("major", "impact"): 4.5,
    ("major", "concern"): 4.4,
    ("profound", "impact"): 4.7,
    ("profound", "effect"): 4.5,
    ("sharp", "increase"): 4.8,
    ("sharp", "decline"): 4.7,
    ("steep", "rise"): 4.5,
    ("dramatic", "increase"): 4.6,
    ("dramatic", "change"): 4.5,
    ("swift", "action"): 4.4,
    ("bitter", "dispute"): 4.3,
    ("fierce", "competition"): 4.6,
    ("stiff", "competition"): 4.4,
    ("heated", "debate"): 4.7,
    ("broad", "range"): 4.8, ("wide", "range"): 5.0,
    ("vast", "majority"): 5.1,
    ("overwhelming", "majority"): 4.9,
    ("slim", "chance"): 4.5,
    ("golden", "opportunity"): 4.4,
    ("prime", "minister"): 5.2,
    ("public", "opinion"): 4.9,
    ("common", "sense"): 4.8,
    ("common", "ground"): 4.5,
    ("grave", "concern"): 4.5,
    ("grave", "mistake"): 4.4,
    ("fatal", "error"): 4.5, ("fatal", "flaw"): 4.4,
    ("vicious", "cycle"): 4.6,
    ("vicious", "circle"): 4.5,
    # Verbs
    ("make", "decision"): 4.8, ("make", "progress"): 4.7,
    ("make", "mistake"): 4.6, ("make", "effort"): 4.5,
    ("take", "action"): 4.9, ("take", "place"): 5.0,
    ("take", "advantage"): 4.7, ("take", "responsibility"): 4.6,
    ("pay", "attention"): 5.0, ("pay", "tribute"): 4.4,
    ("reach", "agreement"): 4.6,
    ("reach", "conclusion"): 4.5,
    ("draw", "conclusion"): 4.6,
    ("draw", "attention"): 4.7,
    ("raise", "awareness"): 4.7,
    ("raise", "concern"): 4.5,
    ("raise", "question"): 4.5,
    ("pose", "threat"): 4.6, ("pose", "challenge"): 4.5,
    ("face", "challenge"): 4.6,
    ("meet", "demand"): 4.5, ("meet", "requirement"): 4.4,
    ("break", "record"): 4.5, ("break", "silence"): 4.4,
    ("set", "goal"): 4.4, ("set", "standard"): 4.5,
    ("achieve", "goal"): 4.5, ("achieve", "success"): 4.4,
    ("gain", "momentum"): 4.5,
    ("gain", "experience"): 4.4,
    ("bear", "mind"): 4.5, ("keep", "mind"): 4.6,
    ("run", "risk"): 4.4, ("face", "risk"): 4.3,
    ("commit", "crime"): 4.5, ("commit", "offense"): 4.3,
    # Adverb combos
    ("perfectly", "clear"): 4.5,
    ("utterly", "ridiculous"): 4.4,
    ("absolutely", "essential"): 4.5,
    ("thoroughly", "enjoyed"): 4.3,
    ("entirely", "different"): 4.4,
    ("completely", "different"): 4.5,
    ("extremely", "important"): 4.6,
    ("remarkably", "similar"): 4.3,
    ("significantly", "higher"): 4.5,
    ("considerably", "more"): 4.3,
    ("substantially", "more"): 4.3,
    ("relatively", "new"): 4.2,
    ("relatively", "small"): 4.2,
    ("increasingly", "important"): 4.4,
    ("undeniably", "important"): 4.0,
    # Preposition patterns
    ("interested", "in"): 4.8, ("depend", "on"): 4.9,
    ("rely", "on"): 4.8, ("result", "in"): 4.7,
    ("consist", "of"): 4.8, ("apply", "to"): 4.5,
    ("refer", "to"): 4.7, ("belong", "to"): 4.5,
    ("contribute", "to"): 4.6,
    ("lead", "to"): 4.7, ("due", "to"): 4.9,
    ("according", "to"): 5.0, ("thanks", "to"): 4.5,
    ("prior", "to"): 4.4, ("subject", "to"): 4.5,
}

_RU_COLL: dict[tuple[str, str], float] = {
    ("принять", "решение"): 5.0,
    ("принять", "меры"): 4.8,
    ("оказать", "влияние"): 4.9,
    ("оказать", "помощь"): 4.6,
    ("играть", "роль"): 5.0,
    ("нести", "ответственность"): 4.7,
    ("иметь", "значение"): 4.9,
    ("иметь", "место"): 4.5,
    ("представлять", "интерес"): 4.6,
    ("представлять", "угрозу"): 4.5,
    ("вести", "борьбу"): 4.4,
    ("вести", "переговоры"): 4.5,
    ("давать", "возможность"): 4.6,
    ("достигать", "цели"): 4.5,
    ("ставить", "задачу"): 4.4,
    ("решать", "проблему"): 4.6,
    # adj+noun
    ("важный", "роль"): 4.8, ("важный", "значение"): 4.5,
    ("большой", "значение"): 4.7,
    ("большой", "внимание"): 4.5,
    ("серьёзный", "проблема"): 4.5,
    ("острый", "вопрос"): 4.3,
    ("глубокий", "анализ"): 4.4,
    ("широкий", "круг"): 4.5,
    ("ключевой", "фактор"): 4.5,
    ("существенный", "влияние"): 4.4,
    # adverbs
    ("крайне", "важно"): 4.5,
    ("весьма", "вероятно"): 4.3,
    ("чрезвычайно", "важно"): 4.4,
    ("значительно", "выше"): 4.3,
    ("существенно", "отличаться"): 4.3,
    ("настоятельно", "рекомендовать"): 4.3,
    ("тесно", "связан"): 4.4,
    ("активно", "участвовать"): 4.3,
    ("глубоко", "убеждён"): 4.2,
    ("безусловно", "важно"): 4.1,
}

_DE_COLL: dict[tuple[str, str], float] = {
    ("eine", "rolle"): 4.8, ("große", "rolle"): 4.7,
    ("wichtige", "rolle"): 4.6,
    ("entscheidende", "rolle"): 4.5,
    ("eine", "entscheidung"): 4.6,
    ("maßnahmen", "ergreifen"): 4.6,
    ("zur", "verfügung"): 4.8,
    ("in", "betracht"): 4.5,
    ("in", "frage"): 4.5,
    ("auswirkungen", "haben"): 4.4,
    ("einfluss", "nehmen"): 4.4,
    ("beitrag", "leisten"): 4.4,
    ("verantwortung", "tragen"): 4.5,
    ("bedeutung", "haben"): 4.5,
    ("aufmerksamkeit", "schenken"): 4.3,
    ("äußerst", "wichtig"): 4.3,
    ("besonders", "wichtig"): 4.4,
    ("eng", "verbunden"): 4.3,
    ("stark", "betroffen"): 4.2,
    ("weit", "verbreitet"): 4.3,
    ("deutlich", "höher"): 4.2,
    ("erheblich", "steigern"): 4.1,
}

_FR_COLL: dict[tuple[str, str], float] = {
    ("jouer", "rôle"): 4.8, ("rôle", "important"): 4.6,
    ("prendre", "décision"): 4.7,
    ("avoir", "lieu"): 4.8,
    ("mettre", "place"): 4.7,
    ("rendre", "compte"): 4.6,
    ("tenir", "compte"): 4.7,
    ("faire", "preuve"): 4.5,
    ("porter", "attention"): 4.5,
    ("grande", "importance"): 4.5,
    ("extrêmement", "important"): 4.3,
    ("fortement", "recommandé"): 4.3,
    ("étroitement", "lié"): 4.3,
    ("largement", "utilisé"): 4.3,
    ("profondément", "convaincu"): 4.1,
}

_ES_COLL: dict[tuple[str, str], float] = {
    ("tomar", "decisión"): 4.7,
    ("desempeñar", "papel"): 4.5,
    ("tener", "lugar"): 4.8,
    ("poner", "marcha"): 4.5,
    ("prestar", "atención"): 4.6,
    ("gran", "importancia"): 4.5,
    ("sumamente", "importante"): 4.3,
    ("estrechamente", "vinculado"): 4.2,
    ("ampliamente", "utilizado"): 4.3,
    ("profundamente", "convencido"): 4.1,
    ("papel", "importante"): 4.6,
    ("factor", "clave"): 4.5,
}

_COLLOCS: dict[str, dict[tuple[str, str], float]] = {
    "en": _EN_COLL, "ru": _RU_COLL, "de": _DE_COLL,
    "fr": _FR_COLL, "es": _ES_COLL,
}

_TOK_RE = re.compile(r"[\w'']+", re.UNICODE)


def _tokenize(text: str) -> list[str]:
    return [w.lower() for w in _TOK_RE.findall(text)]


class CollocEngine:
    """Collocation-aware scoring engine.

    Uses pre-built PMI scores and on-the-fly context matching
    to rank synonym candidates by how naturally they fit
    the surrounding words.
    """

    def __init__(self, lang: str = "en") -> None:
        self.lang = lang if lang in _COLLOCS else "en"
        self._coll = _COLLOCS.get(self.lang, {})

    def pmi(self, w1: str, w2: str) -> float:
        """Collocation strength between two words.

        Returns PMI-like score (higher = stronger).
        0.0 if no data.
        """
        key = (w1.lower(), w2.lower())
        return self._coll.get(key, 0.0)

    def collocates(
        self, word: str, *, top_n: int = 10,
    ) -> list[tuple[str, float]]:
        """All known collocates of a word, sorted by strength."""
        w = word.lower()
        hits: list[tuple[str, float]] = []
        for (a, b), score in self._coll.items():
            if a == w:
                hits.append((b, score))
            elif b == w:
                hits.append((a, score))
        hits.sort(key=lambda x: -x[1])
        return hits[:top_n]

    def context_score(
        self,
        candidate: str,
        context: list[str],
    ) -> float:
        """Score a candidate word against context words.

        Sums PMI with each context word. Higher = better fit.
        """
        c = candidate.lower()
        total = 0.0
        for ctx_word in context:
            w = ctx_word.lower()
            total += self.pmi(c, w)
            total += self.pmi(w, c)
        return total

    def best_synonym(
        self,
        original: str,
        candidates: list[str],
        context: list[str] | None = None,
        *,
        window: int = 3,
    ) -> str:
        """Pick the best-fitting synonym given context.

        Parameters:
            original:   The word being replaced.
            candidates: List of synonym options.
            context:    Surrounding words (before + after).
            window:     Max context words to consider.

        Returns:
            Best candidate, or original if none scores above 0.
        """
        if not candidates:
            return original
        if context is None:
            context = []

        ctx = [
            w.lower()
            for w in context[:window * 2]
            if len(w) > 2
        ]

        if not ctx:
            return candidates[0]

        scores: list[tuple[str, float]] = []
        for cand in candidates:
            s = self.context_score(cand, ctx)
            scores.append((cand, s))

        scores.sort(key=lambda x: -x[1])

        # Only pick candidate if it scores > 0
        best_cand, best_score = scores[0]
        if best_score > 0:
            return best_cand

        # No collocation data → return first candidate
        return candidates[0]

    def rank_synonyms(
        self,
        candidates: list[str],
        context: list[str],
    ) -> list[tuple[str, float]]:
        """Rank candidates by context score.

        Returns list of (candidate, score) sorted descending.
        """
        ctx = [w.lower() for w in context if len(w) > 2]
        result: list[tuple[str, float]] = []
        for cand in candidates:
            s = self.context_score(cand, ctx)
            result.append((cand, s))
        result.sort(key=lambda x: -x[1])
        return result

    def sentence_collocation_score(
        self, sentence: str,
    ) -> dict[str, Any]:
        """Analyze collocation density of a sentence.

        Higher scores = more natural-sounding combinations.
        """
        tokens = _tokenize(sentence)
        if len(tokens) < 2:
            return {
                "score": 0.0, "pairs": 0,
                "density": 0.0, "collocs": [],
            }

        total = 0.0
        pairs_found: list[dict[str, Any]] = []
        checked = 0

        for i in range(len(tokens) - 1):
            for j in range(i + 1, min(i + 4, len(tokens))):
                checked += 1
                p = self.pmi(tokens[i], tokens[j])
                if p > 0:
                    pairs_found.append({
                        "w1": tokens[i],
                        "w2": tokens[j],
                        "pmi": round(p, 2),
                    })
                    total += p

        density = total / max(checked, 1)
        return {
            "score": round(total, 2),
            "pairs": len(pairs_found),
            "density": round(density, 4),
            "collocs": pairs_found,
        }


# ── Convenience ───────────────────────────────────────────

def collocation_score(
    w1: str, w2: str, lang: str = "en",
) -> float:
    """Quick PMI lookup between two words."""
    return CollocEngine(lang=lang).pmi(w1, w2)


def best_synonym_in_context(
    original: str,
    candidates: list[str],
    context: list[str],
    lang: str = "en",
) -> str:
    """Pick best synonym given surrounding words."""
    return CollocEngine(lang=lang).best_synonym(
        original, candidates, context,
    )
