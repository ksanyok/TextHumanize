"""Custom dictionary trainer.

Extracts patterns from a user's corpus to build custom replacement
dictionaries. Identifies overused phrases, repeated patterns, and
suggests natural alternatives based on statistical analysis.

No external APIs — purely statistical n-gram analysis.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass


@dataclass
class TrainingResult:
    """Result of dictionary training."""
    overused_phrases: dict[str, int]
    repeated_patterns: dict[str, int]
    suggested_replacements: dict[str, list[str]]
    vocabulary_stats: dict[str, float]
    corpus_size: int
    unique_tokens: int


def train_from_corpus(
    texts: list[str],
    lang: str = "en",
    *,
    min_frequency: int = 3,
    max_ngram: int = 4,
    top_k: int = 100,
) -> TrainingResult:
    """Train a custom dictionary from a corpus of texts.

    Analyzes the corpus to find overused phrases and repeated patterns
    that make text sound AI-generated or unnatural.

    Args:
        texts: List of text samples to analyze.
        lang: Language code.
        min_frequency: Minimum occurrences to be considered "overused".
        max_ngram: Maximum n-gram size to analyze.
        top_k: Maximum number of patterns to return.

    Returns:
        TrainingResult with discovered patterns and suggestions.
    """
    if not texts:
        return TrainingResult(
            overused_phrases={},
            repeated_patterns={},
            suggested_replacements={},
            vocabulary_stats={},
            corpus_size=0,
            unique_tokens=0,
        )

    # Combine all texts
    all_words: list[str] = []
    all_sentences: list[str] = []

    for text in texts:
        words = re.findall(r'\b\w+\b', text.lower())
        all_words.extend(words)
        sents = re.split(r'[.!?]+\s*', text)
        all_sentences.extend(s.strip() for s in sents if s.strip())

    corpus_size = len(all_words)
    unique_tokens = len(set(all_words))

    # N-gram analysis
    ngram_counts: dict[int, Counter] = {}
    for n in range(2, max_ngram + 1):
        ngrams = Counter()
        for text in texts:
            words = re.findall(r'\b\w+\b', text.lower())
            for i in range(len(words) - n + 1):
                ngram = " ".join(words[i:i+n])
                ngrams[ngram] += 1
        ngram_counts[n] = ngrams

    # Find overused phrases (frequency above threshold)
    overused: dict[str, int] = {}
    for n in range(2, max_ngram + 1):
        for phrase, count in ngram_counts[n].most_common(top_k):
            if count >= min_frequency:
                overused[phrase] = count

    # Find repeated sentence starters
    starters = Counter()
    for sent in all_sentences:
        words = sent.split()
        if len(words) >= 2:
            starter = " ".join(words[:2]).lower()
            starters[starter] += 1

    repeated_patterns: dict[str, int] = {
        k: v for k, v in starters.most_common(top_k)
        if v >= min_frequency
    }

    # AI-typical patterns detection
    ai_patterns = _detect_ai_patterns(all_sentences, lang)
    overused.update(ai_patterns)

    # Generate suggestions (simple synonym-based)
    suggestions = _generate_suggestions(overused, lang)

    # Vocabulary statistics
    word_freq = Counter(all_words)
    hapax = sum(1 for c in word_freq.values() if c == 1)
    vocab_stats = {
        "type_token_ratio": unique_tokens / corpus_size if corpus_size > 0 else 0.0,
        "hapax_ratio": hapax / unique_tokens if unique_tokens > 0 else 0.0,
        "avg_word_length": sum(len(w) for w in all_words) / corpus_size if corpus_size > 0 else 0.0,
        "vocabulary_richness": (
            min(1.0, (unique_tokens / corpus_size) * 2)
            if corpus_size > 0 else 0.0
        ),
    }

    return TrainingResult(
        overused_phrases=dict(sorted(overused.items(), key=lambda x: -x[1])[:top_k]),
        repeated_patterns=dict(sorted(repeated_patterns.items(), key=lambda x: -x[1])),
        suggested_replacements=suggestions,
        vocabulary_stats=vocab_stats,
        corpus_size=corpus_size,
        unique_tokens=unique_tokens,
    )


def _detect_ai_patterns(sentences: list[str], lang: str) -> dict[str, int]:
    """Detect common AI-generated text patterns."""
    ai_markers = {
        "en": [
            "it is important to note",
            "it is worth noting",
            "in conclusion",
            "furthermore",
            "moreover",
            "in today's world",
            "plays a crucial role",
            "it should be noted",
            "on the other hand",
            "in this regard",
            "as a result",
            "in summary",
            "to summarize",
            "overall",
            "in essence",
            "delve into",
            "tapestry",
            "landscape",
            "leverage",
            "utilize",
            "facilitate",
            "comprehensive",
            "robust",
            "streamline",
            "cutting-edge",
        ],
        "ru": [
            "необходимо отметить",
            "важно подчеркнуть",
            "в заключение",
            "кроме того",
            "более того",
            "в современном мире",
            "играет важную роль",
            "следует отметить",
            "с другой стороны",
            "в этой связи",
            "в результате",
            "подводя итоги",
            "в целом",
            "по сути",
            "таким образом",
            "осуществлять",
            "является",
            "данный",
            "представляет собой",
            "обусловлено",
        ],
        "uk": [
            "необхідно зазначити",
            "важливо підкреслити",
            "підсумовуючи",
            "крім того",
            "більш того",
            "відіграє важливу роль",
            "слід зазначити",
            "з іншого боку",
            "у зв'язку з цим",
            "в результаті",
            "в цілому",
            "по суті",
            "таким чином",
            "здійснювати",
            "є",
            "даний",
        ],
    }

    markers = ai_markers.get(lang, ai_markers.get("en", []))
    found: dict[str, int] = {}

    full_text = " ".join(sentences).lower()
    for marker in markers:
        count = full_text.count(marker.lower())
        if count > 0:
            found[marker] = count

    return found


def _generate_suggestions(
    overused: dict[str, int],
    lang: str,
) -> dict[str, list[str]]:
    """Generate replacement suggestions for overused phrases."""
    # Simple heuristic suggestions
    _suggestion_templates = {
        "en": {
            "it is important to note": ["notably", "significantly", "keep in mind"],
            "furthermore": ["also", "plus", "on top of that"],
            "moreover": ["besides", "what's more", "additionally"],
            "in conclusion": ["to wrap up", "finally", "all in all"],
            "it should be noted": ["note that", "worth pointing out", "keep in mind"],
            "on the other hand": ["then again", "but", "alternatively"],
            "as a result": ["so", "because of this", "consequently"],
            "in today's world": ["today", "now", "currently"],
            "plays a crucial role": ["matters a lot", "is key", "is essential"],
            "utilize": ["use", "apply", "employ"],
            "facilitate": ["help", "enable", "support"],
            "comprehensive": ["thorough", "complete", "full"],
            "leverage": ["use", "take advantage of", "capitalize on"],
            "robust": ["strong", "solid", "reliable"],
        },
        "ru": {
            "необходимо отметить": ["стоит сказать", "заметим", "скажем"],
            "важно подчеркнуть": ["стоит выделить", "обратим внимание", "заметим"],
            "в заключение": ["напоследок", "в итоге", "подытожим"],
            "кроме того": ["к тому же", "ещё", "плюс"],
            "более того": ["мало того", "к тому же", "и даже"],
            "играет важную роль": ["очень важен", "ключевой", "решающий"],
            "таким образом": ["итак", "значит", "получается"],
            "осуществлять": ["делать", "проводить", "выполнять"],
            "является": ["это", "представляет", "выступает"],
            "данный": ["этот", "такой", "текущий"],
        },
    }

    templates = _suggestion_templates.get(lang, _suggestion_templates.get("en", {}))
    suggestions: dict[str, list[str]] = {}

    for phrase in overused:
        phrase_lower = phrase.lower()
        if phrase_lower in templates:
            suggestions[phrase] = templates[phrase_lower]

    return suggestions


def export_custom_dict(
    result: TrainingResult,
    *,
    min_count: int = 2,
) -> dict[str, list[str]]:
    """Export training results as a custom_dict for humanize().

    Args:
        result: TrainingResult from train_from_corpus().
        min_count: Minimum frequency to include.

    Returns:
        Dict suitable for passing as custom_dict to humanize().
    """
    custom_dict: dict[str, list[str]] = {}

    for phrase, alternatives in result.suggested_replacements.items():
        if phrase in result.overused_phrases:
            count = result.overused_phrases[phrase]
            if count >= min_count and alternatives:
                custom_dict[phrase] = alternatives

    return custom_dict
