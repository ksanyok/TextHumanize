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

import logging
import re
from typing import Any

from texthumanize._colloc_data import get_collocations

logger = logging.getLogger(__name__)

# ── Lazy-loaded collocation data ──────────────────────────
# 2500+ collocations across 9 languages.
# Data compressed in _colloc_data.py (auto-generated).

_COLLOCS_CACHE: dict[str, dict[tuple[str, str], float]] = {}
_SUPPORTED_LANGS = frozenset({
    "en", "ru", "de", "fr", "es", "it", "pt", "pl", "uk",
})

def _get_collocs(lang: str) -> dict[tuple[str, str], float]:
    """Get collocation dict for a language (lazy-loaded)."""
    if lang not in _COLLOCS_CACHE:
        _COLLOCS_CACHE[lang] = get_collocations(lang)
    return _COLLOCS_CACHE[lang]

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
        self.lang = lang if lang in _SUPPORTED_LANGS else "en"
        self._coll = _get_collocs(self.lang)

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
        window: int = 5,
    ) -> str:
        """Pick the best-fitting synonym given context.

        Parameters:
            original:   The word being replaced.
            candidates: List of synonym options.
            context:    Surrounding words (before + after).
            window:     Max context words to consider (expanded from 3→5).

        Returns:
            Best candidate, or a randomly-weighted one if no collocation data.
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
            # No context — prefer shorter/simpler candidates (more natural)
            sorted_by_len = sorted(candidates, key=len)
            return sorted_by_len[0]

        scores: list[tuple[str, float]] = []
        for cand in candidates:
            s = self.context_score(cand, ctx)
            # Bonus for shorter candidates (simpler words sound more human)
            len_bonus = max(0, (12 - len(cand)) * 0.02)
            scores.append((cand, s + len_bonus))

        scores.sort(key=lambda x: -x[1])

        # Only pick candidate if it scores > 0
        best_cand, best_score = scores[0]
        if best_score > 0:
            return best_cand

        # No collocation data — prefer shorter/simpler candidates
        sorted_by_len = sorted(candidates, key=len)
        return sorted_by_len[0]

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
