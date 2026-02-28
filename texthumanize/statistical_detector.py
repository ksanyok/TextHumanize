"""Statistical AI text detector with logistic regression.

Uses 35 hand-crafted features and pre-trained weights.
No external dependencies — pure Python with stdlib only.
"""

from __future__ import annotations

import logging
import math
import re
from collections import Counter

from texthumanize.ai_markers import load_ai_markers

logger = logging.getLogger(__name__)

# ----------------------------------------------------------
# AI-characteristic marker words (EN)
# ----------------------------------------------------------
_AI_MARKERS_EN: set[str] = {
    "furthermore",
    "moreover",
    "crucial",
    "paramount",
    "comprehensive",
    "utilize",
    "utilizes",
    "utilized",
    "utilizing",
    "implement",
    "implements",
    "implemented",
    "facilitate",
    "facilitates",
    "facilitated",
    "leverage",
    "leverages",
    "leveraged",
    "leveraging",
    "optimal",
    "enhance",
    "enhances",
    "enhanced",
    "enhancing",
    "streamline",
    "streamlined",
    "streamlines",
    "robust",
    "significant",
    "significantly",
    "demonstrate",
    "demonstrates",
    "demonstrated",
    "subsequently",
    "consequently",
    "nevertheless",
    "nonetheless",
    "aforementioned",
    "delve",
    "delves",
    "delving",
    "pivotal",
    "multifaceted",
    "intricate",
    "intricacies",
    "noteworthy",
    "commendable",
    "meticulous",
    "meticulously",
    "underpinning",
    "underpinnings",
    "encompass",
    "encompasses",
    "encompassing",
    "tapestry",
    "landscape",
    "realm",
    "paradigm",
    "synergy",
    "holistic",
    "nuanced",
    "nuances",
    "arguably",
    "underscores",
    "underscoring",
    "fostering",
    "elevate",
    "elevating",
    "embark",
    "embarking",
    "spearhead",
    "bolster",
    "bolstering",
    "captivate",
    "captivating",
    "groundbreaking",
    "indispensable",
    "unparalleled",
    "bustling",
    "resonate",
    "resonates",
    "resonating",
    "testament",
    "underscore",
}

# ----------------------------------------------------------
# AI-characteristic marker phrases (RU)
# ----------------------------------------------------------
_AI_MARKERS_RU: list[str] = [
    "кроме того",
    "более того",
    "следует отметить",
    "необходимо подчеркнуть",
    "в контексте",
    "в рамках",
    "представляет собой",
    "является",
    "обусловлен",
    "свидетельствует",
    "демонстрирует",
    "в свою очередь",
    "таким образом",
    "в данном случае",
    "на основании",
    "в соответствии с",
    "в значительной степени",
    "с целью",
    "по мере",
    "в первую очередь",
    "в целом",
    "на сегодняшний день",
    "по сути",
    "с учетом",
    "в результате",
    "в частности",
    "по существу",
    "в то же время",
    "в связи с этим",
    "в настоящее время",
    "немаловажным является",
    "ключевым аспектом",
    "стоит подчеркнуть",
    "нельзя не отметить",
    "заслуживает внимания",
    "играет важную роль",
    "имеет место",
    "оказывает влияние",
]

# ----------------------------------------------------------
# Transition / discourse words (EN)
# ----------------------------------------------------------
_TRANSITIONS_EN: set[str] = {
    "however",
    "therefore",
    "thus",
    "hence",
    "accordingly",
    "meanwhile",
    "furthermore",
    "moreover",
    "additionally",
    "consequently",
    "nevertheless",
    "nonetheless",
    "alternatively",
    "conversely",
    "similarly",
    "likewise",
    "specifically",
    "notably",
    "importantly",
    "indeed",
    "certainly",
    "undoubtedly",
    "essentially",
    "basically",
    "overall",
    "ultimately",
}

_CONJUNCTIONS_EN: set[str] = {
    "and",
    "but",
    "or",
    "nor",
    "for",
    "yet",
    "so",
    "because",
    "although",
    "though",
    "while",
    "whereas",
    "since",
    "unless",
    "until",
    "if",
    "when",
    "after",
    "before",
}

# ----------------------------------------------------------
# Pre-trained logistic regression weights (35 features)
# ----------------------------------------------------------
_LR_WEIGHTS: dict[str, float] = {
    # Lexical features
    "type_token_ratio": -0.85,
    "hapax_ratio": 0.62,
    "avg_word_length": -0.48,
    "word_length_variance": 0.37,
    # Sentence-level features
    "mean_sentence_length": -0.32,
    "sentence_length_variance": 0.91,
    "sentence_length_skewness": 0.44,
    # Vocabulary measures
    "yules_k": 0.28,
    "simpsons_diversity": -0.55,
    "vocabulary_richness": -0.39,
    # N-gram features
    "bigram_repetition_rate": 0.53,
    "trigram_repetition_rate": 0.41,
    "unique_bigram_ratio": -0.67,
    # Entropy features
    "char_entropy": 0.22,
    "word_entropy": 0.58,
    "bigram_entropy": 0.19,
    # Burstiness features
    "burstiness_score": 1.15,
    "vocab_burstiness": 0.73,
    # Structural features
    "paragraph_count_norm": 0.05,
    "avg_paragraph_length": -0.21,
    "list_bullet_ratio": -0.34,
    # Punctuation features
    "comma_rate": -0.26,
    "semicolon_rate": -0.72,
    "dash_rate": 0.45,
    "question_rate": 0.38,
    "exclamation_rate": 0.29,
    # AI pattern features
    "ai_pattern_rate": -2.10,
    # Perplexity-proxy features
    "word_freq_rank_variance": 0.64,
    "zipf_fit_residual": 0.31,
    # Readability features
    "avg_syllables_per_word": -0.42,
    "flesch_score_norm": 0.36,
    # Discourse features
    "starter_diversity": 0.52,
    "conjunction_rate": 0.18,
    "transition_word_rate": -0.88,
    # Rhythm features
    "consec_len_diff_var": 0.76,
}

_LR_BIAS: float = 0.15

# ----------------------------------------------------------
# Feature normalization (mean, std) from corpus stats
# ----------------------------------------------------------
_FEAT_NORM: dict[str, tuple[float, float]] = {
    # (mean, std) — derived from mixed corpus
    "type_token_ratio": (0.65, 0.15),
    "hapax_ratio": (0.55, 0.18),
    "avg_word_length": (4.5, 0.7),
    "word_length_variance": (3.5, 1.2),
    "mean_sentence_length": (15.0, 6.0),
    "sentence_length_variance": (30.0, 25.0),
    "sentence_length_skewness": (0.3, 0.8),
    "yules_k": (80.0, 50.0),
    "simpsons_diversity": (0.96, 0.03),
    "vocabulary_richness": (7.0, 2.5),
    "bigram_repetition_rate": (0.05, 0.05),
    "trigram_repetition_rate": (0.02, 0.025),
    "unique_bigram_ratio": (0.95, 0.05),
    "char_entropy": (4.3, 0.35),
    "word_entropy": (6.0, 1.5),
    "bigram_entropy": (7.0, 2.0),
    "burstiness_score": (-0.2, 0.18),
    "vocab_burstiness": (0.6, 0.18),
    "paragraph_count_norm": (0.3, 0.2),
    "avg_paragraph_length": (0.5, 0.25),
    "list_bullet_ratio": (0.05, 0.1),
    "comma_rate": (0.012, 0.008),
    "semicolon_rate": (0.0005, 0.001),
    "dash_rate": (0.003, 0.004),
    "question_rate": (0.003, 0.004),
    "exclamation_rate": (0.002, 0.003),
    "ai_pattern_rate": (0.01, 0.02),
    "word_freq_rank_variance": (1.0, 0.8),
    "zipf_fit_residual": (2.0, 1.5),
    "avg_syllables_per_word": (1.5, 0.22),
    "flesch_score_norm": (0.6, 0.25),
    "starter_diversity": (0.7, 0.18),
    "conjunction_rate": (0.04, 0.02),
    "transition_word_rate": (0.008, 0.01),
    "consec_len_diff_var": (2.0, 1.2),
}

# ----------------------------------------------------------
# Syllable counting helpers
# ----------------------------------------------------------
_VOWELS_EN = set("aeiouy")
_VOWELS_RU = set("аеёиоуыэюя")
_VOWELS_DE = set("aeiouyäöü")
_VOWELS_FR = set("aeiouyàâéèêëïîôùûüÿæœ")
_VOWELS_ES = set("aeiouáéíóúü")

_VOWEL_MAP: dict[str, set[str]] = {
    "en": _VOWELS_EN,
    "ru": _VOWELS_RU,
    "de": _VOWELS_DE,
    "fr": _VOWELS_FR,
    "es": _VOWELS_ES,
}


def _syllable_count(
    word: str, lang: str = "en"
) -> int:
    """Count syllables in a word.

    Uses vowel-group heuristic with language-specific
    vowel sets and English silent-e rule.
    """
    w = word.lower().strip()
    if not w:
        return 0
    vowels = _VOWEL_MAP.get(lang, _VOWELS_EN)
    count = 0
    prev_vowel = False
    for ch in w:
        is_v = ch in vowels
        if is_v and not prev_vowel:
            count += 1
        prev_vowel = is_v
    # English silent-e adjustment
    if lang == "en" and w.endswith("e") and count > 1:
        count -= 1
    # English -le ending (e.g. "table")
    if (
        lang == "en"
        and len(w) > 2
        and w.endswith("le")
        and w[-3] not in vowels
        and count < 1
    ):
        count = 1
    return max(count, 1)


# ----------------------------------------------------------
# Statistical helper functions
# ----------------------------------------------------------

def _compute_entropy(tokens: list[str]) -> float:
    """Shannon entropy of a token list."""
    if not tokens:
        return 0.0
    n = len(tokens)
    freq = Counter(tokens)
    ent = 0.0
    for c in freq.values():
        p = c / n
        if p > 0:
            ent -= p * math.log2(p)
    return ent


def _compute_burstiness(
    lengths: list[float],
) -> float:
    """Burstiness B = (std - mean) / (std + mean).

    Returns value in [-1, 1]. Higher = more bursty.
    Human text tends to be more bursty.
    """
    if len(lengths) < 2:
        return 0.0
    mu = sum(lengths) / len(lengths)
    var = sum((x - mu) ** 2 for x in lengths)
    std = math.sqrt(var / len(lengths))
    denom = std + mu
    if denom == 0:
        return 0.0
    return (std - mu) / denom


def _yules_k(tokens: list[str]) -> float:
    """Yule's K vocabulary measure.

    Higher K means less lexical diversity.
    """
    if not tokens:
        return 0.0
    n = len(tokens)
    freq = Counter(tokens)
    freq_spectrum = Counter(freq.values())
    m2 = sum(
        i * i * vi for i, vi in freq_spectrum.items()
    )
    if n <= 1:
        return 0.0
    denom = n * n
    k = 10000 * (m2 - n) / denom if denom else 0
    return max(k, 0.0)


def _simpsons_diversity(tokens: list[str]) -> float:
    """Simpson's diversity index.

    Range [0, 1]. Higher = more diverse.
    """
    if len(tokens) < 2:
        return 0.0
    n = len(tokens)
    freq = Counter(tokens)
    total = sum(c * (c - 1) for c in freq.values())
    denom = n * (n - 1)
    if denom == 0:
        return 0.0
    return 1.0 - total / denom


def _zipf_fit(tokens: list[str]) -> float:
    """Zipf's law goodness-of-fit residual.

    Lower residual = closer to Zipf. Returns mean
    squared log-residual; human text deviates more.
    """
    if len(tokens) < 5:
        return 0.0
    freq = Counter(tokens)
    ranked = sorted(freq.values(), reverse=True)
    n = min(len(ranked), 100)
    if n < 2:
        return 0.0
    top = ranked[0]
    if top == 0:
        return 0.0
    residual = 0.0
    for rank_idx in range(n):
        rank = rank_idx + 1
        expected = top / rank  # ideal Zipf
        actual = ranked[rank_idx]
        if actual > 0 and expected > 0:
            diff = math.log(actual) - math.log(expected)
            residual += diff * diff
    return residual / n


# ----------------------------------------------------------
# Sentence splitting (lightweight)
# ----------------------------------------------------------
_SENT_RE = re.compile(
    r'(?<=[.!?])\s+(?=[A-ZА-ЯЁ"\'\(])'
)
_BULLET_RE = re.compile(
    r"^[\s]*[-*•▸▹►]|\d+[.)]\s", re.MULTILINE
)


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences (heuristic)."""
    raw = _SENT_RE.split(text.strip())
    return [s.strip() for s in raw if s.strip()]


def _tokenize(text: str) -> list[str]:
    """Simple word tokenizer."""
    return re.findall(r"[a-zA-Zа-яА-ЯёЁ]+", text.lower())


def _get_bigrams(
    tokens: list[str],
) -> list[tuple[str, str]]:
    """Get bigrams from token list."""
    return [
        (tokens[i], tokens[i + 1])
        for i in range(len(tokens) - 1)
    ]


def _get_trigrams(
    tokens: list[str],
) -> list[tuple[str, str, str]]:
    """Get trigrams from token list."""
    return [
        (tokens[i], tokens[i + 1], tokens[i + 2])
        for i in range(len(tokens) - 2)
    ]


# ----------------------------------------------------------
# Core feature extraction
# ----------------------------------------------------------

def _safe_var(values: list[float]) -> float:
    """Variance with safety check."""
    if len(values) < 2:
        return 0.0
    mu = sum(values) / len(values)
    return sum((x - mu) ** 2 for x in values) / len(
        values
    )


def _safe_skew(values: list[float]) -> float:
    """Skewness with safety check."""
    if len(values) < 3:
        return 0.0
    mu = sum(values) / len(values)
    var = _safe_var(values)
    if var == 0:
        return 0.0
    std = math.sqrt(var)
    n = len(values)
    skew = sum((x - mu) ** 3 for x in values) / n
    return skew / (std ** 3) if std > 0 else 0.0


def _count_ai_markers(
    text: str, lang: str
) -> float:
    """Count AI-characteristic markers in text.

    Returns rate (count / total_words).
    Uses multilingual markers from ai_markers module.
    """
    lower = text.lower()
    tokens = _tokenize(text)
    n = len(tokens)
    if n == 0:
        return 0.0
    count = 0

    # Load language-specific markers from ai_markers module
    lang_markers = load_ai_markers(lang)

    if lang_markers:
        # Count single-word markers from all categories
        all_words: set[str] = set()
        all_phrases: list[str] = []
        for category, words in lang_markers.items():
            for w in words:
                if " " in w:
                    all_phrases.append(w.lower())
                else:
                    all_words.add(w.lower())

        # Count phrase matches
        for phrase in all_phrases:
            count += lower.count(phrase)

        # Count word matches
        for t in tokens:
            if t in all_words:
                count += 1
    else:
        # Fallback: use hardcoded EN/RU markers
        if lang == "ru":
            for phrase in _AI_MARKERS_RU:
                count += lower.count(phrase)
            for t in tokens:
                if t in _AI_MARKERS_EN:
                    count += 1
        else:
            for t in tokens:
                if t in _AI_MARKERS_EN:
                    count += 1

    # For non-EN languages, also check EN markers as AI often
    # leaks English-style words even in other languages
    if lang not in ("en",) and lang_markers:
        en_markers = load_ai_markers("en")
        if en_markers:
            en_words: set[str] = set()
            for words in en_markers.values():
                for w in words:
                    if " " not in w:
                        en_words.add(w.lower())
            for t in tokens:
                if t in en_words:
                    count += 1

    return count / n


def extract_features(
    text: str, lang: str = "en"
) -> dict[str, float]:
    """Extract 35 numerical features from text.

    Works for any language but is most accurate for
    English and Russian.
    """
    tokens = _tokenize(text)
    sentences = _split_sentences(text)
    paragraphs = [
        p.strip()
        for p in text.split("\n\n")
        if p.strip()
    ]
    n_tok = len(tokens)
    n_sent = max(len(sentences), 1)
    n_para = max(len(paragraphs), 1)
    chars = list(text)

    # --- Lexical ---
    types = set(tokens)
    n_types = len(types)
    ttr = n_types / n_tok if n_tok else 0.0
    freq = Counter(tokens)
    hapax = sum(1 for v in freq.values() if v == 1)
    hapax_r = hapax / n_tok if n_tok else 0.0
    wlens = [len(t) for t in tokens]
    avg_wlen = (
        sum(wlens) / len(wlens) if wlens else 0.0
    )
    wlen_var = _safe_var(
        [float(x) for x in wlens]
    )

    # --- Sentence ---
    sent_lens = [
        len(_tokenize(s)) for s in sentences
    ]
    mean_slen = (
        sum(sent_lens) / len(sent_lens)
        if sent_lens
        else 0.0
    )
    slen_var = _safe_var(
        [float(x) for x in sent_lens]
    )
    slen_skew = _safe_skew(
        [float(x) for x in sent_lens]
    )

    # --- Vocabulary measures ---
    yk = _yules_k(tokens)
    sd = _simpsons_diversity(tokens)
    vr = n_types / math.sqrt(n_tok) if n_tok else 0.0

    # --- N-grams ---
    bigrams = _get_bigrams(tokens)
    trigrams = _get_trigrams(tokens)
    bg_cnt = Counter(bigrams)
    tg_cnt = Counter(trigrams)
    bg_rep = (
        sum(1 for v in bg_cnt.values() if v > 1)
        / max(len(bg_cnt), 1)
    )
    tg_rep = (
        sum(1 for v in tg_cnt.values() if v > 1)
        / max(len(tg_cnt), 1)
    )
    ubg_ratio = (
        len(bg_cnt) / max(len(bigrams), 1)
    )

    # --- Entropy ---
    ch_ent = _compute_entropy(
        [c for c in chars if c.strip()]
    )
    w_ent = _compute_entropy(tokens)
    bg_strs = [
        f"{a}_{b}" for a, b in bigrams
    ]
    bg_ent = _compute_entropy(bg_strs)

    # --- Burstiness ---
    burst = _compute_burstiness(
        [float(x) for x in sent_lens]
    )
    # Vocab burstiness: measure how vocabulary
    # usage varies across sentence halves
    half = n_tok // 2
    if half > 0:
        t1 = set(tokens[:half])
        t2 = set(tokens[half:])
        union = t1 | t2
        if union:
            jaccard = len(t1 & t2) / len(union)
            vburst = 1.0 - jaccard
        else:
            vburst = 0.0
    else:
        vburst = 0.0

    # --- Structural ---
    para_norm = min(n_para / 10.0, 1.0)
    avg_plen = n_tok / n_para if n_para else 0.0
    avg_plen_norm = min(avg_plen / 100.0, 1.0)
    bullets = len(_BULLET_RE.findall(text))
    bullet_ratio = bullets / n_sent

    # --- Punctuation ---
    n_chars = max(len(text), 1)
    comma_r = text.count(",") / n_chars
    semi_r = text.count(";") / n_chars
    dash_r = (
        text.count("—")
        + text.count("–")
        + text.count(" - ")
    ) / n_chars
    quest_r = text.count("?") / n_chars
    excl_r = text.count("!") / n_chars

    # --- AI patterns ---
    ai_rate = _count_ai_markers(text, lang)

    # --- Perplexity proxy ---
    wfrv = _safe_var(
        [float(freq[t]) for t in tokens]
    ) if tokens else 0.0
    # Normalize to reasonable range
    wfrv_norm = math.log1p(wfrv)
    zipf_r = _zipf_fit(tokens)

    # --- Readability ---
    syl_counts = [
        _syllable_count(t, lang) for t in tokens
    ]
    avg_syl = (
        sum(syl_counts) / len(syl_counts)
        if syl_counts
        else 0.0
    )
    # Flesch-like: 206.835 - 1.015*(words/sents)
    #              - 84.6*(syls/words)
    wps = n_tok / n_sent if n_sent else 0.0
    spw = avg_syl
    flesch = 206.835 - 1.015 * wps - 84.6 * spw
    flesch_norm = max(min(flesch / 100.0, 1.5), -0.5)

    # --- Discourse ---
    starters = [
        _tokenize(s)[0]
        for s in sentences
        if _tokenize(s)
    ]
    starter_div = (
        len(set(starters)) / max(len(starters), 1)
    )
    conj_cnt = sum(
        1 for t in tokens if t in _CONJUNCTIONS_EN
    )
    conj_rate = conj_cnt / n_tok if n_tok else 0.0
    trans_cnt = sum(
        1 for t in tokens if t in _TRANSITIONS_EN
    )
    trans_rate = (
        trans_cnt / n_tok if n_tok else 0.0
    )

    # --- Rhythm ---
    consec_diffs = [
        abs(sent_lens[i] - sent_lens[i + 1])
        for i in range(len(sent_lens) - 1)
    ]
    cld_var = _safe_var(
        [float(x) for x in consec_diffs]
    )
    cld_var_norm = math.log1p(cld_var)

    return {
        "type_token_ratio": ttr,
        "hapax_ratio": hapax_r,
        "avg_word_length": avg_wlen,
        "word_length_variance": wlen_var,
        "mean_sentence_length": mean_slen,
        "sentence_length_variance": slen_var,
        "sentence_length_skewness": slen_skew,
        "yules_k": yk,
        "simpsons_diversity": sd,
        "vocabulary_richness": vr,
        "bigram_repetition_rate": bg_rep,
        "trigram_repetition_rate": tg_rep,
        "unique_bigram_ratio": ubg_ratio,
        "char_entropy": ch_ent,
        "word_entropy": w_ent,
        "bigram_entropy": bg_ent,
        "burstiness_score": burst,
        "vocab_burstiness": vburst,
        "paragraph_count_norm": para_norm,
        "avg_paragraph_length": avg_plen_norm,
        "list_bullet_ratio": bullet_ratio,
        "comma_rate": comma_r,
        "semicolon_rate": semi_r,
        "dash_rate": dash_r,
        "question_rate": quest_r,
        "exclamation_rate": excl_r,
        "ai_pattern_rate": ai_rate,
        "word_freq_rank_variance": wfrv_norm,
        "zipf_fit_residual": zipf_r,
        "avg_syllables_per_word": avg_syl,
        "flesch_score_norm": flesch_norm,
        "starter_diversity": starter_div,
        "conjunction_rate": conj_rate,
        "transition_word_rate": trans_rate,
        "consec_len_diff_var": cld_var_norm,
    }


# ----------------------------------------------------------
# Logistic regression inference
# ----------------------------------------------------------

def _sigmoid(x: float) -> float:
    """Numerically stable sigmoid."""
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    ex = math.exp(x)
    return ex / (1.0 + ex)


def _predict_proba(
    features: dict[str, float],
    n_tokens: int = 0,
) -> float:
    """Compute P(AI) from normalized features.

    Weights are positive for human-indicative features
    and negative for AI-indicative features.  We negate
    the logit so that sigmoid maps to P(AI).
    Features are clipped to [-3, 3] after normalisation
    to prevent outlier dominance.
    """
    z = _LR_BIAS
    for name, w in _LR_WEIGHTS.items():
        raw = features.get(name, 0.0)
        mu, std = _FEAT_NORM.get(
            name, (0.0, 1.0)
        )
        if std > 0:
            normed = (raw - mu) / std
        else:
            normed = raw - mu
        # Clip to prevent single-feature dominance
        normed = max(-3.0, min(3.0, normed))
        z += w * normed
    # Negate: positive z = human-leaning → low P(AI)
    prob = _sigmoid(-z)
    # Dampen confidence for short texts (< 50 words)
    if n_tokens > 0 and n_tokens < 50:
        factor = n_tokens / 50.0
        prob = 0.5 + (prob - 0.5) * factor
    return prob


def _verdict(prob: float) -> str:
    """Map probability to verdict string."""
    if prob < 0.3:
        return "human"
    if prob <= 0.6:
        return "mixed"
    return "ai"


# ----------------------------------------------------------
# StatisticalDetector class
# ----------------------------------------------------------

class StatisticalDetector:
    """Statistical AI text detector with LR.

    Usage::

        det = StatisticalDetector(lang="en")
        result = det.detect("Some text...")
        print(result["probability"])   # 0.0-1.0
        print(result["verdict"])       # human/mixed/ai
        print(result["features"])      # dict
    """

    def __init__(self, lang: str = "en") -> None:
        self.lang = lang

    def extract_features(
        self, text: str
    ) -> dict[str, float]:
        """Extract all 35 features from text."""
        return extract_features(text, self.lang)

    def probability(self, text: str) -> float:
        """Quick AI probability score [0, 1]."""
        feats = self.extract_features(text)
        ntok = len(_tokenize(text))
        return _predict_proba(feats, ntok)

    def detect(self, text: str) -> dict:
        """Full detection with features + prob.

        Returns dict with keys:
          - probability: float [0, 1]
          - verdict: 'human' | 'mixed' | 'ai'
          - features: dict[str, float]
          - feature_count: int
        """
        feats = self.extract_features(text)
        ntok = len(_tokenize(text))
        prob = _predict_proba(feats, ntok)
        return {
            "probability": round(prob, 4),
            "verdict": _verdict(prob),
            "features": feats,
            "feature_count": len(feats),
        }

    def detect_sentences(
        self,
        text: str,
        window: int = 3,
    ) -> list[dict]:
        """Per-sentence detection via sliding window.

        Slides a window of *window* sentences across
        the text and returns a result for each step.
        """
        sentences = _split_sentences(text)
        if not sentences:
            return []
        results: list[dict] = []
        # Pad short texts
        if len(sentences) < window:
            chunk = " ".join(sentences)
            feats = extract_features(
                chunk, self.lang
            )
            ntok = len(_tokenize(chunk))
            prob = _predict_proba(feats, ntok)
            results.append(
                {
                    "sentence_index": 0,
                    "sentences": sentences,
                    "probability": round(prob, 4),
                    "verdict": _verdict(prob),
                }
            )
            return results
        for i in range(len(sentences) - window + 1):
            chunk_sents = sentences[i: i + window]
            chunk = " ".join(chunk_sents)
            feats = extract_features(
                chunk, self.lang
            )
            ntok = len(_tokenize(chunk))
            prob = _predict_proba(feats, ntok)
            results.append(
                {
                    "sentence_index": i,
                    "sentences": chunk_sents,
                    "probability": round(prob, 4),
                    "verdict": _verdict(prob),
                }
            )
        return results


# ----------------------------------------------------------
# Convenience function
# ----------------------------------------------------------

def detect_ai_statistical(
    text: str, lang: str = "en"
) -> dict:
    """Quick statistical AI detection.

    Returns dict with probability, verdict, features.
    """
    det = StatisticalDetector(lang=lang)
    return det.detect(text)
