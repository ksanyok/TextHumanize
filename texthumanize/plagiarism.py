"""Plagiarism detection and originality analysis.

Checks text originality using n-gram fingerprinting and
self-similarity analysis. No external APIs — works entirely
offline using statistical methods.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass


@dataclass
class PlagiarismReport:
    """Result of plagiarism analysis."""
    originality_score: float  # 0-100, higher = more original
    self_similarity: float  # Internal repetition ratio
    fingerprint_hash: str  # Unique text fingerprint
    repeated_segments: list[dict]  # Repeated text blocks
    ngram_diversity: float  # N-gram diversity ratio
    sentence_originality: list[dict]  # Per-sentence scores
    verdict: str  # "original", "moderate_overlap", "high_overlap"


def check_originality(
    text: str,
    *,
    reference_texts: list[str] | None = None,
    ngram_size: int = 4,
    min_match_length: int = 5,
) -> PlagiarismReport:
    """Check text originality against reference texts.

    Performs n-gram fingerprinting to detect copied or nearly-copied
    passages. If no reference texts are given, analyzes internal
    self-repetition only.

    Args:
        text: Text to check.
        reference_texts: Optional reference texts to compare against.
        ngram_size: Size of word n-grams for fingerprinting.
        min_match_length: Minimum matching words to flag.

    Returns:
        PlagiarismReport with originality analysis.
    """
    if not text or not text.strip():
        return PlagiarismReport(
            originality_score=100.0,
            self_similarity=0.0,
            fingerprint_hash="",
            repeated_segments=[],
            ngram_diversity=1.0,
            sentence_originality=[],
            verdict="original",
        )

    words = re.findall(r'\b\w+\b', text.lower())

    # Generate fingerprint
    text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]

    # N-gram analysis
    text_ngrams = _extract_ngrams(words, ngram_size)
    unique_ngrams = len(set(text_ngrams))
    total_ngrams = max(1, len(text_ngrams))
    ngram_diversity = unique_ngrams / total_ngrams

    # Self-similarity: find repeated segments within the text
    self_sim, repeated = _find_self_repetitions(text, min_match_length)

    # Compare against reference texts if provided
    ref_overlap = 0.0
    ref_matches = []
    if reference_texts:
        ref_overlap, ref_matches = _compare_against_refs(
            text, reference_texts, ngram_size, min_match_length
        )

    # Per-sentence originality
    sentences = re.split(r'[.!?]+\s*', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

    sentence_scores = []
    for sent in sentences:
        sent_words = re.findall(r'\b\w+\b', sent.lower())
        sent_ngrams = _extract_ngrams(sent_words, min(ngram_size, len(sent_words)))
        unique = len(set(sent_ngrams))
        total = max(1, len(sent_ngrams))

        # Check against references
        sent_overlap = 0.0
        if reference_texts:
            for ref in reference_texts:
                ref_words = re.findall(r'\b\w+\b', ref.lower())
                ref_ngrams_set = set(_extract_ngrams(ref_words, min(ngram_size, len(ref_words))))
                if ref_ngrams_set:
                    overlap = len(set(sent_ngrams) & ref_ngrams_set) / max(1, len(set(sent_ngrams)))
                    sent_overlap = max(sent_overlap, overlap)

        sentence_scores.append({
            "sentence": sent[:100],
            "originality": (
                round((1.0 - sent_overlap) * 100, 1)
                if reference_texts
                else round(unique / total * 100, 1)
            ),
            "is_original": sent_overlap < 0.3 if reference_texts else unique / total > 0.5,
        })

    # Overall originality score
    base_score = ngram_diversity * 50 + (1.0 - self_sim) * 30
    if reference_texts:
        base_score = (1.0 - ref_overlap) * 70 + ngram_diversity * 20 + (1.0 - self_sim) * 10

    originality = min(100.0, max(0.0, base_score))

    if originality >= 80:
        verdict = "original"
    elif originality >= 50:
        verdict = "moderate_overlap"
    else:
        verdict = "high_overlap"

    all_repeated = repeated + ref_matches

    return PlagiarismReport(
        originality_score=round(originality, 1),
        self_similarity=round(self_sim, 4),
        fingerprint_hash=text_hash,
        repeated_segments=all_repeated[:20],  # Top 20
        ngram_diversity=round(ngram_diversity, 4),
        sentence_originality=sentence_scores,
        verdict=verdict,
    )


def compare_originality(
    text: str,
    original: str,
    *,
    ngram_size: int = 3,
) -> dict:
    """Compare humanized text against original for sufficient divergence.

    Ensures the humanized version is different enough from the original
    to avoid being flagged as a trivially modified copy.

    Args:
        text: Humanized text.
        original: Original (AI-generated) text.
        ngram_size: N-gram size for comparison.

    Returns:
        Dict with: divergence (0-1), shared_ngrams_ratio,
        unique_to_humanized, is_sufficiently_different.
    """
    text_words = re.findall(r'\b\w+\b', text.lower())
    orig_words = re.findall(r'\b\w+\b', original.lower())

    text_ngrams = set(_extract_ngrams(text_words, ngram_size))
    orig_ngrams = set(_extract_ngrams(orig_words, ngram_size))

    shared = text_ngrams & orig_ngrams
    all_ngrams = text_ngrams | orig_ngrams

    shared_ratio = len(shared) / max(1, len(all_ngrams))
    unique_to_new = len(text_ngrams - orig_ngrams) / max(1, len(text_ngrams))
    divergence = 1.0 - shared_ratio

    return {
        "divergence": round(divergence, 4),
        "shared_ngrams_ratio": round(shared_ratio, 4),
        "unique_to_humanized": round(unique_to_new, 4),
        "is_sufficiently_different": divergence > 0.25,
    }


def _extract_ngrams(words: list[str], n: int) -> list[tuple]:
    """Extract word n-grams."""
    if n <= 0 or not words:
        return []
    return [tuple(words[i:i+n]) for i in range(max(1, len(words) - n + 1))]


def _find_self_repetitions(
    text: str,
    min_length: int = 5,
) -> tuple[float, list[dict]]:
    """Find repeated segments within the text."""
    words = text.lower().split()
    if len(words) < min_length * 2:
        return 0.0, []

    # Sliding window to find repeated word sequences
    seen: dict[tuple, list[int]] = {}
    for n in range(min_length, min(min_length + 3, len(words) // 2)):
        for i in range(len(words) - n + 1):
            key = tuple(words[i:i+n])
            if key not in seen:
                seen[key] = []
            seen[key].append(i)

    repeated = []
    repeated_word_count = 0
    seen_positions = set()

    for key, positions in seen.items():
        if len(positions) > 1:
            phrase = " ".join(key)
            # Only count if not already covered
            new_positions = [p for p in positions[1:] if p not in seen_positions]
            if new_positions:
                repeated.append({
                    "phrase": phrase,
                    "count": len(positions),
                    "positions": positions,
                })
                for p in new_positions:
                    for j in range(len(key)):
                        seen_positions.add(p + j)
                repeated_word_count += len(key) * len(new_positions)

    self_sim = min(1.0, repeated_word_count / max(1, len(words)))

    # Sort by count
    repeated.sort(key=lambda x: -x["count"])

    return self_sim, repeated[:10]


def _compare_against_refs(
    text: str,
    refs: list[str],
    ngram_size: int,
    min_match: int,
) -> tuple[float, list[dict]]:
    """Compare text against reference texts."""
    text_words = re.findall(r'\b\w+\b', text.lower())
    text_ngrams = set(_extract_ngrams(text_words, ngram_size))

    if not text_ngrams:
        return 0.0, []

    max_overlap = 0.0
    matches = []

    for i, ref in enumerate(refs):
        ref_words = re.findall(r'\b\w+\b', ref.lower())
        ref_ngrams = set(_extract_ngrams(ref_words, ngram_size))

        shared = text_ngrams & ref_ngrams
        overlap = len(shared) / len(text_ngrams) if text_ngrams else 0.0
        max_overlap = max(max_overlap, overlap)

        if overlap > 0.1:
            # Find matching phrases
            for ngram in list(shared)[:5]:
                matches.append({
                    "phrase": " ".join(ngram),
                    "reference_index": i,
                    "overlap_ratio": round(overlap, 4),
                })

    return max_overlap, matches
