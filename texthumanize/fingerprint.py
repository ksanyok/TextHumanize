"""Author fingerprint — style profile comparison.

Build a statistical "style portrait" from reference texts and compare
new text against it to estimate whether it was written by the same author.

Zero-dependency, pure Python.
"""

from __future__ import annotations

import logging
import math
import statistics
from dataclasses import dataclass, field

from texthumanize.lang_detect import detect_language
from texthumanize.sentence_split import split_sentences

logger = logging.getLogger(__name__)

# ═════════════════════════════════════════════════════════════
#  AUTHOR FINGERPRINT
# ═════════════════════════════════════════════════════════════

@dataclass
class StyleProfile:
    """Statistical style profile of an author."""

    # Word-level
    avg_word_length: float = 0.0
    word_length_std: float = 0.0
    vocabulary_richness: float = 0.0      # TTR (types/tokens)
    hapax_ratio: float = 0.0              # Words appearing once / total types

    # Sentence-level
    avg_sentence_length: float = 0.0
    sentence_length_cv: float = 0.0       # Coefficient of variation
    avg_clause_depth: float = 0.0         # Comma + conjunction count

    # Punctuation profile
    comma_rate: float = 0.0               # Per 100 words
    semicolon_rate: float = 0.0
    dash_rate: float = 0.0
    exclamation_rate: float = 0.0
    question_rate: float = 0.0
    parenthesis_rate: float = 0.0

    # Function words ratio (most stable stylometric feature)
    function_word_ratio: float = 0.0

    # Start-of-sentence patterns (POS-proxies)
    pronoun_start_ratio: float = 0.0
    article_start_ratio: float = 0.0
    conjunction_start_ratio: float = 0.0

    # Paragraph-level
    avg_paragraph_length: float = 0.0     # In sentences

    # Meta
    sample_word_count: int = 0
    sample_sentence_count: int = 0
    lang: str = "en"


@dataclass
class FingerprintResult:
    """Result of comparing text against an author's profile."""

    similarity: float = 0.0             # 0.0–1.0 (1.0 = identical style)
    verdict: str = "unknown"            # "same_author", "different_author", "uncertain"
    confidence: float = 0.0
    deviations: dict[str, float] = field(default_factory=dict)  # Per-feature deviation

    def summary(self) -> str:
        lines = [
            f"Similarity: {self.similarity:.1%}",
            f"Verdict: {self.verdict}",
            f"Confidence: {self.confidence:.1%}",
        ]
        if self.deviations:
            lines.append("")
            lines.append("Feature deviations (0 = identical):")
            for feat, dev in sorted(self.deviations.items(), key=lambda x: -abs(x[1])):
                lines.append(f"  {feat:30s}  {dev:+.3f}")
        return "\n".join(lines)


# ─── English function words ──────────────────────────────────

_EN_FUNCTION_WORDS = frozenset({
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "shall",
    "should", "may", "might", "can", "could", "must",
    "i", "me", "my", "mine", "we", "us", "our", "ours",
    "you", "your", "yours", "he", "him", "his", "she", "her", "hers",
    "it", "its", "they", "them", "their", "theirs",
    "this", "that", "these", "those",
    "in", "on", "at", "to", "for", "with", "by", "from", "of", "about",
    "into", "through", "during", "before", "after", "above", "below",
    "between", "under", "over", "up", "down", "out", "off",
    "and", "but", "or", "nor", "so", "yet", "if", "then", "else",
    "when", "while", "as", "since", "because", "although", "though",
    "not", "no", "very", "too", "also", "just", "only",
})

_RU_FUNCTION_WORDS = frozenset({
    "и", "в", "на", "с", "он", "она", "они", "мы", "вы", "я",
    "не", "но", "а", "что", "это", "как", "за", "к", "по", "из",
    "от", "до", "у", "о", "об", "при", "для", "же", "ли", "бы",
    "до", "ещё", "еще", "так", "уже", "все", "его", "ее", "её",
    "то", "только", "ну", "то", "тоже", "также", "где", "когда",
    "если", "чтобы", "потому", "хотя", "были", "был", "была",
    "будет", "есть", "нет", "да",
})

_PRONOUNS_EN = frozenset({
    "i", "we", "you", "he", "she", "it", "they", "who", "this", "that",
    "my", "our", "your", "his", "her", "its", "their",
})

_ARTICLES_EN = frozenset({"the", "a", "an"})

_CONJUNCTIONS_EN = frozenset({
    "and", "but", "or", "yet", "so", "for", "nor",
    "however", "moreover", "furthermore", "nevertheless",
    "although", "because", "since", "while", "when", "if",
})


# ═════════════════════════════════════════════════════════════
#  CORE CLASS
# ═════════════════════════════════════════════════════════════

class AuthorFingerprint:
    """Build and compare author style fingerprints.

    Usage:
        fp = AuthorFingerprint()
        profile = fp.build_profile(["Text1 by author...", "Text2 by author..."])
        result = fp.compare(profile, "New text to check...")
    """

    def build_profile(
        self,
        texts: list[str],
        lang: str = "auto",
    ) -> StyleProfile:
        """Build a style profile from reference texts.

        Args:
            texts: List of reference texts by the same author.
            lang: Language code ('auto' for detection).

        Returns:
            StyleProfile with averaged statistics.
        """
        if not texts:
            return StyleProfile()

        if lang == "auto":
            lang = detect_language(texts[0])

        profiles: list[StyleProfile] = []
        for text in texts:
            p = self._extract_features(text, lang)
            profiles.append(p)

        # Average all numeric features
        merged = StyleProfile(lang=lang)
        float_fields = [
            f.name for f in StyleProfile.__dataclass_fields__.values()
            if f.type == "float" and f.name != "lang"
        ]

        for field_name in float_fields:
            vals = [getattr(p, field_name) for p in profiles]
            setattr(merged, field_name, statistics.mean(vals))

        merged.sample_word_count = sum(p.sample_word_count for p in profiles)
        merged.sample_sentence_count = sum(p.sample_sentence_count for p in profiles)

        return merged

    def compare(
        self,
        profile: StyleProfile,
        text: str,
        lang: str | None = None,
    ) -> FingerprintResult:
        """Compare new text against an author's profile.

        Args:
            profile: Reference style profile.
            text: New text to compare.
            lang: Language code (uses profile.lang if None).

        Returns:
            FingerprintResult with similarity score and deviations.
        """
        if not text or not profile.sample_word_count:
            return FingerprintResult()

        effective_lang = lang or profile.lang
        new_profile = self._extract_features(text, effective_lang)

        # Compute per-feature normalized deviations
        float_fields = [
            f.name for f in StyleProfile.__dataclass_fields__.values()
            if f.type == "float" and f.name != "lang"
        ]

        deviations: dict[str, float] = {}
        similarities: list[float] = []

        # Feature weights (more stable features get higher weight)
        weights = {
            "function_word_ratio": 3.0,    # Most stable
            "avg_word_length": 2.5,
            "sentence_length_cv": 2.0,
            "comma_rate": 2.0,
            "vocabulary_richness": 1.5,
            "pronoun_start_ratio": 1.5,
            "avg_sentence_length": 1.5,
            "hapax_ratio": 1.0,
            "semicolon_rate": 1.0,
            "dash_rate": 1.0,
            "exclamation_rate": 1.0,
            "question_rate": 1.0,
            "parenthesis_rate": 1.0,
            "avg_clause_depth": 1.0,
            "article_start_ratio": 1.0,
            "conjunction_start_ratio": 1.0,
            "word_length_std": 1.0,
            "avg_paragraph_length": 0.8,
        }

        for field_name in float_fields:
            ref_val = getattr(profile, field_name)
            new_val = getattr(new_profile, field_name)

            # Normalized deviation: how many "reference units" apart
            scale = max(abs(ref_val), 0.01)
            deviation = (new_val - ref_val) / scale
            deviations[field_name] = round(deviation, 4)

            # Similarity for this feature (Gaussian kernel)
            sim = math.exp(-0.5 * deviation ** 2)
            w = weights.get(field_name, 1.0)
            similarities.append(sim * w)

        total_weight = sum(weights.get(f, 1.0) for f in float_fields)
        similarity = sum(similarities) / total_weight if total_weight > 0 else 0.5

        # Confidence based on reference sample size
        ref_words = profile.sample_word_count
        size_factor = min(ref_words / 500, 1.0)  # Full confidence at 500+ words
        text_factor = min(len(text.split()) / 100, 1.0)
        confidence = size_factor * text_factor * 0.9

        # Verdict
        if similarity >= 0.70:
            verdict = "same_author"
        elif similarity <= 0.40:
            verdict = "different_author"
        else:
            verdict = "uncertain"

        return FingerprintResult(
            similarity=round(similarity, 4),
            verdict=verdict,
            confidence=round(confidence, 4),
            deviations=deviations,
        )

    # ─── Private ──────────────────────────────────────────────

    def _extract_features(self, text: str, lang: str) -> StyleProfile:
        """Extract style features from a single text."""
        p = StyleProfile(lang=lang)

        words = text.split()
        if not words:
            return p

        sentences = split_sentences(text, lang)
        if not sentences:
            return p

        p.sample_word_count = len(words)
        p.sample_sentence_count = len(sentences)

        # Word-level
        word_lengths = [len(w.strip(".,;:!?\"'()-–—")) for w in words]
        word_lengths = [wl for wl in word_lengths if wl > 0]
        if word_lengths:
            p.avg_word_length = statistics.mean(word_lengths)
            p.word_length_std = statistics.stdev(word_lengths) if len(word_lengths) > 1 else 0.0

        # Vocabulary richness
        lower_words = [w.lower().strip(".,;:!?\"'()-–—") for w in words]
        lower_words = [w for w in lower_words if w]
        types = set(lower_words)
        if lower_words:
            p.vocabulary_richness = len(types) / len(lower_words)

        # Hapax legomena
        from collections import Counter
        freq = Counter(lower_words)
        hapax = sum(1 for c in freq.values() if c == 1)
        p.hapax_ratio = hapax / len(types) if types else 0.0

        # Sentence-level
        sent_lens = [len(s.split()) for s in sentences]
        if sent_lens:
            p.avg_sentence_length = statistics.mean(sent_lens)
            if len(sent_lens) > 1:
                p.sentence_length_cv = (
                    statistics.stdev(sent_lens) / p.avg_sentence_length
                    if p.avg_sentence_length > 0 else 0.0
                )

        # Clause depth proxy
        clause_counts = [s.count(",") + s.count(" and ") + s.count(" but ") for s in sentences]
        p.avg_clause_depth = statistics.mean(clause_counts) if clause_counts else 0.0

        # Punctuation rates (per 100 words)
        n100 = len(words) / 100 if words else 1
        p.comma_rate = text.count(",") / n100
        p.semicolon_rate = text.count(";") / n100
        p.dash_rate = (text.count("—") + text.count("–") + text.count(" - ")) / n100
        p.exclamation_rate = text.count("!") / n100
        p.question_rate = text.count("?") / n100
        p.parenthesis_rate = (text.count("(") + text.count("[")) / n100

        # Function words
        func_words = _RU_FUNCTION_WORDS if lang in ("ru", "uk") else _EN_FUNCTION_WORDS
        func_count = sum(1 for w in lower_words if w in func_words)
        p.function_word_ratio = func_count / len(lower_words) if lower_words else 0.0

        # Start-of-sentence patterns
        if sentences:
            first_words = [s.split()[0].lower().strip("\"'«") for s in sentences if s.split()]
            n_sent = len(first_words) or 1
            p.pronoun_start_ratio = sum(1 for w in first_words if w in _PRONOUNS_EN) / n_sent
            p.article_start_ratio = sum(1 for w in first_words if w in _ARTICLES_EN) / n_sent
            p.conjunction_start_ratio = (
                sum(1 for w in first_words if w in _CONJUNCTIONS_EN) / n_sent
            )

        # Paragraph-level
        paragraphs = [p_text for p_text in text.split("\n") if p_text.strip()]
        if paragraphs:
            para_sent_counts = []
            for para_text in paragraphs:
                para_sents = split_sentences(para_text, lang)
                para_sent_counts.append(len(para_sents))
            p.avg_paragraph_length = statistics.mean(para_sent_counts) if para_sent_counts else 0.0

        return p
