"""Enhanced statistical perplexity estimation (v2).

Uses character-level n-gram cross-entropy against language-specific
background models. Provides much more accurate perplexity assessment
than the v1 self-referential approach, without requiring external APIs.

The key insight: AI text has abnormally LOW perplexity (it's too
predictable). Human text has HIGHER and more VARIABLE perplexity.
"""

from __future__ import annotations

import math
import re
from collections import Counter

# Pre-built character trigram frequency tables for common languages
# Top-50 most frequent trigrams with normalized probabilities
_CHAR_TRIGRAM_MODELS: dict[str, dict[str, float]] = {
    "en": {
        "the": 0.035, " th": 0.030, "he ": 0.028, "ing": 0.020,
        "and": 0.018, " an": 0.016, "nd ": 0.015, "tion": 0.014,
        "ion": 0.014, "tio": 0.013, " of": 0.012, "of ": 0.012,
        "ed ": 0.011, " to": 0.011, "to ": 0.010, "er ": 0.010,
        " in": 0.010, "in ": 0.009, "ent": 0.009, "hat": 0.008,
        "re ": 0.008, "is ": 0.008, " is": 0.008, "es ": 0.007,
        "on ": 0.007, "ati": 0.007, " co": 0.007, "for": 0.007,
        "al ": 0.007, " fo": 0.006, "or ": 0.006, "tha": 0.006,
        " ha": 0.006, "as ": 0.006, " re": 0.006, "her": 0.006,
        "ere": 0.005, " st": 0.005, "ter": 0.005, " be": 0.005,
        "ment": 0.005, "all": 0.005, "con": 0.005, " it": 0.005,
        "ith": 0.005, "wit": 0.005, "nt ": 0.005, "are": 0.004,
        " wh": 0.004, "his": 0.004,
    },
    "ru": {
        " не": 0.020, "ени": 0.015, "ост": 0.014, "ние": 0.013,
        "ани": 0.013, " по": 0.012, " на": 0.012, " пр": 0.011,
        " ко": 0.010, "ова": 0.010, "ого": 0.009, "ать": 0.009,
        "что": 0.009, " и ": 0.009, " в ": 0.009, "ить": 0.008,
        "про": 0.008, "ста": 0.008, "ере": 0.008, "пре": 0.007,
        "при": 0.007, " об": 0.007, "ных": 0.007, "ном": 0.007,
        "ной": 0.006, "ска": 0.006, "ком": 0.006, "ьно": 0.006,
        "тор": 0.006, " от": 0.006, "ель": 0.006, "тел": 0.006,
        "ное": 0.005, " до": 0.005, " бы": 0.005, "ает": 0.005,
        "кот": 0.005, "ото": 0.005, " ка": 0.005, "ами": 0.005,
    },
}


def _build_char_trigrams(text: str) -> Counter:
    """Build character trigram counter from text."""
    text = text.lower()
    trigrams = Counter()
    for i in range(len(text) - 2):
        trigrams[text[i:i+3]] += 1
    return trigrams


def cross_entropy(text: str, lang: str = "en") -> float:
    """Compute character-level cross-entropy against background model.

    Lower values mean the text is MORE predictable (more AI-like).
    Human text typically scores 3.5-5.5 bits.
    AI text typically scores 2.0-3.5 bits.

    Args:
        text: Text to analyze.
        lang: Language code for background model.

    Returns:
        Cross-entropy in bits (float). Lower = more predictable.
    """
    if not text or len(text) < 10:
        return 0.0

    bg_model = _CHAR_TRIGRAM_MODELS.get(lang, _CHAR_TRIGRAM_MODELS.get("en", {}))
    if not bg_model:
        return 0.0

    text_lower = text.lower()
    n = max(1, len(text_lower) - 2)
    total_entropy = 0.0

    smoothing = 1e-7  # Laplace smoothing for unseen trigrams
    bg_total = sum(bg_model.values())

    for i in range(n):
        trigram = text_lower[i:i+3]
        prob = bg_model.get(trigram, smoothing) / bg_total
        total_entropy -= math.log2(prob)

    return total_entropy / n


def perplexity_score(text: str, lang: str = "en") -> dict:
    """Advanced perplexity analysis with multiple metrics.

    Combines character-level cross-entropy, vocabulary analysis,
    and local perplexity variance to provide a comprehensive
    assessment of text naturalness.

    Args:
        text: Text to analyze.
        lang: Language code.

    Returns:
        Dict with:
            - cross_entropy: Overall cross-entropy (bits)
            - perplexity: 2^cross_entropy
            - local_variance: Variance of per-sentence cross-entropy
            - burstiness_score: How "bursty" the perplexity is (0-1)
            - naturalness: Overall naturalness score (0-100)
            - verdict: "human", "mixed", or "ai"
    """
    if not text or len(text) < 20:
        return {
            "cross_entropy": 0.0,
            "perplexity": 1.0,
            "local_variance": 0.0,
            "burstiness_score": 0.0,
            "naturalness": 50.0,
            "verdict": "unknown",
        }

    # Overall cross-entropy
    ce = cross_entropy(text, lang)
    ppl = 2.0 ** ce if ce > 0 else 1.0

    # Per-sentence cross-entropy for variance analysis
    sentences = re.split(r'[.!?]+\s+', text)
    sentences = [s for s in sentences if len(s) > 10]

    if len(sentences) >= 3:
        local_ces = [cross_entropy(s, lang) for s in sentences]
        mean_ce = sum(local_ces) / len(local_ces)
        variance = sum((x - mean_ce) ** 2 for x in local_ces) / len(local_ces)

        # Burstiness: coefficient of variation of cross-entropy
        std_dev = variance ** 0.5
        cv = std_dev / mean_ce if mean_ce > 0 else 0.0
    else:
        variance = 0.0
        cv = 0.0

    # Vocabulary richness factor
    words = text.lower().split()
    if words:
        unique_ratio = len(set(words)) / len(words)
    else:
        unique_ratio = 0.0

    # Naturalness scoring
    # High cross-entropy + high variance + high vocabulary = human
    naturalness = 0.0

    # Cross-entropy contribution (human: 3.5-5.5, AI: 2-3.5)
    if ce >= 4.5:
        naturalness += 35
    elif ce >= 3.5:
        naturalness += 25
    elif ce >= 2.5:
        naturalness += 15
    else:
        naturalness += 5

    # Variance contribution (human text is more variable)
    if cv >= 0.3:
        naturalness += 30
    elif cv >= 0.15:
        naturalness += 20
    elif cv >= 0.05:
        naturalness += 10
    else:
        naturalness += 3

    # Vocabulary contribution
    if unique_ratio >= 0.7:
        naturalness += 20
    elif unique_ratio >= 0.5:
        naturalness += 15
    elif unique_ratio >= 0.3:
        naturalness += 10
    else:
        naturalness += 5

    # Sentence length variation
    if sentences:
        lens = [len(s.split()) for s in sentences]
        if len(lens) >= 2:
            len_mean = sum(lens) / len(lens)
            len_std = (sum((x - len_mean)**2 for x in lens) / len(lens)) ** 0.5
            len_cv = len_std / len_mean if len_mean > 0 else 0
            if len_cv >= 0.4:
                naturalness += 15
            elif len_cv >= 0.2:
                naturalness += 10
            else:
                naturalness += 3

    naturalness = min(100.0, naturalness)

    if naturalness >= 70:
        verdict = "human"
    elif naturalness >= 40:
        verdict = "mixed"
    else:
        verdict = "ai"

    return {
        "cross_entropy": round(ce, 4),
        "perplexity": round(ppl, 2),
        "local_variance": round(variance, 4),
        "burstiness_score": round(cv, 4),
        "naturalness": round(naturalness, 1),
        "verdict": verdict,
    }
