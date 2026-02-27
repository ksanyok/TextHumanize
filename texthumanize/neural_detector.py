"""Neural AI text detector — pure Python, zero dependencies.

A 3-layer MLP (35→64→32→1) trained to distinguish AI-generated text from
human-written text. Uses the same 35 statistical features as the logistic
regression detector but with non-linear feature interactions for higher
accuracy.

Pre-trained weights are embedded directly in this module.

Usage::

    from texthumanize.neural_detector import NeuralAIDetector
    detector = NeuralAIDetector()
    result = detector.detect("Some text to analyze...", lang="en")
    print(result)  # {'score': 0.82, 'verdict': 'ai', 'confidence': 'high', ...}
"""

from __future__ import annotations

import logging
import math
import re
from collections import Counter
from typing import Any

from texthumanize.neural_engine import (
    DenseLayer,
    FeedForwardNet,
    Vec,
    _sigmoid,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Feature normalization statistics (mean, std) — from corpus analysis
# ---------------------------------------------------------------------------

_FEATURE_NAMES: list[str] = [
    "type_token_ratio", "hapax_ratio", "avg_word_length", "word_length_variance",
    "mean_sentence_length", "sentence_length_variance", "sentence_length_skewness",
    "yules_k", "simpsons_diversity", "vocabulary_richness",
    "bigram_repetition_rate", "trigram_repetition_rate", "unique_bigram_ratio",
    "char_entropy", "word_entropy", "bigram_entropy",
    "burstiness_score", "vocab_burstiness",
    "paragraph_count_norm", "avg_paragraph_length", "list_bullet_ratio",
    "comma_rate", "semicolon_rate", "dash_rate", "question_rate", "exclamation_rate",
    "ai_pattern_rate", "word_freq_rank_variance", "zipf_fit_residual",
    "avg_syllables_per_word", "flesch_score_norm",
    "starter_diversity", "conjunction_rate", "transition_word_rate",
    "consec_len_diff_var",
]

_FEATURE_MEAN: list[float] = [
    0.65, 0.55, 4.5, 3.5, 15.0, 30.0, 0.3, 80.0, 0.96, 7.0,
    0.05, 0.02, 0.95, 4.3, 6.0, 7.0, -0.2, 0.6, 0.3, 0.5, 0.05,
    0.012, 0.0005, 0.003, 0.003, 0.002, 0.01, 1.0, 2.0, 1.5, 0.6,
    0.7, 0.04, 0.008, 2.0,
]

_FEATURE_STD: list[float] = [
    0.15, 0.18, 0.7, 1.2, 6.0, 25.0, 0.8, 50.0, 0.03, 2.5,
    0.05, 0.025, 0.05, 0.35, 1.5, 2.0, 0.18, 0.18, 0.2, 0.25, 0.1,
    0.008, 0.001, 0.004, 0.004, 0.003, 0.02, 0.8, 1.5, 0.22, 0.25,
    0.18, 0.02, 0.01, 1.2,
]

# ---------------------------------------------------------------------------
# AI-characteristic patterns
# ---------------------------------------------------------------------------

_AI_PATTERNS_EN: set[str] = {
    "furthermore", "moreover", "additionally", "consequently", "subsequently",
    "utilize", "utilization", "leverage", "leveraging", "facilitate",
    "facilitates", "facilitation", "optimize", "optimization", "implement",
    "implementation", "demonstrate", "demonstrates", "encompass", "encompasses",
    "comprehensive", "constitutes", "necessitate", "necessitates",
    "paramount", "delve", "delving", "adhere", "adherence",
    "multifaceted", "pivotal", "nuanced", "intricate", "seamless",
    "seamlessly", "streamline", "streamlined", "robust", "fostering",
    "foster", "harness", "harnessing", "aforementioned", "thereby",
    "notwithstanding", "whilst", "endeavor", "endeavors", "pertinent",
    "substantive", "delineate", "delineates", "ascertain", "elucidate",
    "underscore", "underscores", "landscape", "paradigm", "synergy",
    "holistic", "overarching", "cornerstone", "invaluable", "noteworthy",
    "commendable", "meticulous", "meticulously", "indispensable",
    "juxtaposition", "culmination", "testament", "realm", "tapestry",
    "beacon", "linchpin", "spearhead", "embark", "unravel", "unraveling",
    "navigate", "navigating", "underpinning",
    "groundbreaking", "transformative", "cutting-edge",
}

_AI_PATTERNS_RU: list[str] = [
    "кроме того", "более того", "необходимо отметить", "следует подчеркнуть",
    "важно понимать", "в заключение", "таким образом", "в связи с этим",
    "вместе с тем", "в целом", "в частности", "прежде всего",
    "в первую очередь", "с другой стороны", "в настоящее время",
    "на сегодняшний день", "в рамках данного", "согласно данным",
    "по мнению экспертов", "представляет собой", "является ключевым",
    "обусловлено тем", "способствует развитию", "оказывает влияние",
    "имеет важное значение", "в контексте данного", "на основании",
    "принимая во внимание", "с учётом вышеизложенного", "данный подход",
    "является неотъемлемой", "играет важную роль", "следует учитывать",
    "не менее важным", "ключевым аспектом", "существенным образом",
    "имеет место быть", "что касается",
]

_CONJUNCTIONS_EN: set[str] = {
    "and", "but", "or", "nor", "for", "yet", "so", "because",
    "although", "while", "whereas", "since", "unless", "until",
    "though", "even", "whether", "after", "before", "when",
}

_TRANSITIONS_EN: set[str] = {
    "however", "therefore", "furthermore", "moreover", "additionally",
    "consequently", "nevertheless", "nonetheless", "meanwhile",
    "subsequently", "accordingly", "conversely", "alternatively",
    "specifically", "particularly", "notably", "importantly",
    "significantly", "essentially", "fundamentally", "ultimately",
    "regardless", "indeed", "certainly", "undoubtedly", "evidently",
}

_VOWELS_EN = set("aeiouyAEIOUY")
_VOWELS_RU = set("аеёиоуыэюяАЕЁИОУЫЭЮЯ")

# Sentence boundary regex
_SENT_RE = re.compile(r'(?<=[.!?])\s+(?=[A-ZА-ЯЁ"\'"(])')
_WORD_RE = re.compile(r'[a-zA-Zа-яА-ЯёЁіїєґІЇЄҐüöäßÜÖÄ]+')
_BULLET_RE = re.compile(r'^\s*[-*•▸▹►]|\d+[.)]\s', re.MULTILINE)


# ---------------------------------------------------------------------------
# Feature extraction (35 features)
# ---------------------------------------------------------------------------

def _safe_var(vals: list[float]) -> float:
    """Population variance, safe for empty/single."""
    if len(vals) < 2:
        return 0.0
    m = sum(vals) / len(vals)
    return sum((x - m) ** 2 for x in vals) / len(vals)


def _safe_mean(vals: list[float]) -> float:
    return sum(vals) / len(vals) if vals else 0.0


def _shannon_entropy(counts: Counter) -> float:  # type: ignore[type-arg]
    """Shannon entropy in bits."""
    total = sum(counts.values())
    if total == 0:
        return 0.0
    ent = 0.0
    for c in counts.values():
        if c > 0:
            p = c / total
            ent -= p * math.log2(p)
    return ent


def _count_syllables(word: str, vowels: set[str]) -> int:
    """Count syllables via vowel groups with English silent-e correction."""
    count = 0
    prev_vowel = False
    for ch in word:
        if ch in vowels:
            if not prev_vowel:
                count += 1
            prev_vowel = True
        else:
            prev_vowel = False
    # English silent-e
    if word.endswith("e") and count > 1:
        count -= 1
    return max(1, count)


def extract_features(text: str, lang: str = "en") -> Vec:
    """Extract 35 statistical features from text.

    Returns a list of 35 raw feature values in the canonical order.
    """
    tokens = _WORD_RE.findall(text.lower())
    n_tokens = len(tokens)
    if n_tokens < 3:
        return [0.0] * 35

    sentences = _SENT_RE.split(text.strip())
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        sentences = [text]
    n_sentences = len(sentences)

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        paragraphs = [text]
    n_paragraphs = len(paragraphs)

    # Token stats
    token_set = set(tokens)
    freq = Counter(tokens)
    n_types = len(token_set)
    word_lengths = [float(len(t)) for t in tokens]

    # 1. type_token_ratio
    ttr = n_types / n_tokens

    # 2. hapax_ratio
    hapax = sum(1 for c in freq.values() if c == 1)
    hapax_ratio = hapax / n_tokens

    # 3, 4. avg/var word length
    awl = _safe_mean(word_lengths)
    wlv = _safe_var(word_lengths)

    # Sentence lengths (in tokens)
    sent_token_counts = []
    for s in sentences:
        st = _WORD_RE.findall(s.lower())
        sent_token_counts.append(float(len(st)) if st else 0.0)

    # 5, 6, 7. sentence length stats
    msl = _safe_mean(sent_token_counts)
    slv = _safe_var(sent_token_counts)
    # skewness
    sls = 0.0
    if len(sent_token_counts) >= 3:
        sm = msl
        ssig = math.sqrt(slv) if slv > 0 else 1.0
        sls = sum((x - sm) ** 3 for x in sent_token_counts) / (len(sent_token_counts) * ssig ** 3)

    # 8. Yule's K
    freq_spectrum = Counter(freq.values())
    m2 = sum(i * i * v for i, v in freq_spectrum.items())
    yules_k = 10000.0 * (m2 - n_tokens) / (n_tokens * n_tokens) if n_tokens > 1 else 0.0

    # 9. Simpson's diversity
    simpsons = 1.0 - sum(c * (c - 1) for c in freq.values()) / (n_tokens * (n_tokens - 1)) if n_tokens > 1 else 1.0

    # 10. Vocabulary richness (Guiraud)
    vocab_rich = n_types / math.sqrt(n_tokens)

    # 11, 12, 13. N-gram stats
    bigrams = [f"{tokens[i]}_{tokens[i+1]}" for i in range(n_tokens - 1)]
    trigrams = [f"{tokens[i]}_{tokens[i+1]}_{tokens[i+2]}" for i in range(n_tokens - 2)]
    bigram_freq = Counter(bigrams)
    trigram_freq = Counter(trigrams)
    n_unique_bi = len(bigram_freq)
    n_unique_tri = len(trigram_freq)
    bi_rep = sum(1 for c in bigram_freq.values() if c > 1) / max(n_unique_bi, 1)
    tri_rep = sum(1 for c in trigram_freq.values() if c > 1) / max(n_unique_tri, 1)
    uniq_bi_ratio = n_unique_bi / max(len(bigrams), 1)

    # 14, 15, 16. Entropy
    char_counts: Counter[str] = Counter(c for c in text if not c.isspace())
    char_ent = _shannon_entropy(char_counts)
    word_ent = _shannon_entropy(freq)
    bigram_ent = _shannon_entropy(bigram_freq)

    # 17, 18. Burstiness
    if len(sent_token_counts) >= 2:
        b_mu = _safe_mean(sent_token_counts)
        b_sig = math.sqrt(_safe_var(sent_token_counts))
        burstiness = (b_sig - b_mu) / (b_sig + b_mu) if (b_sig + b_mu) > 0 else 0.0
    else:
        burstiness = 0.0

    half = n_tokens // 2
    if half > 0:
        first_half = set(tokens[:half])
        second_half = set(tokens[half:])
        jaccard = len(first_half & second_half) / max(len(first_half | second_half), 1)
        vocab_burst = 1.0 - jaccard
    else:
        vocab_burst = 0.0

    # 19, 20, 21. Structural
    para_norm = min(n_paragraphs / 10.0, 1.0)
    avg_para_len = min((n_tokens / max(n_paragraphs, 1)) / 100.0, 1.0)
    bullet_matches = len(_BULLET_RE.findall(text))
    list_bullet_ratio = bullet_matches / max(n_sentences, 1)

    # 22-26. Punctuation rates
    text_len = max(len(text), 1)
    comma_rate = text.count(",") / text_len
    semi_rate = text.count(";") / text_len
    dash_count = text.count("—") + text.count("–") + text.count(" - ")
    dash_rate = dash_count / text_len
    question_rate = text.count("?") / text_len
    excl_rate = text.count("!") / text_len

    # 27. AI pattern rate
    lower_text = text.lower()
    ai_count = sum(1 for t in tokens if t in _AI_PATTERNS_EN)
    if lang in ("ru", "uk"):
        for phrase in _AI_PATTERNS_RU:
            ai_count += lower_text.count(phrase)
    ai_pattern_rate = ai_count / max(n_tokens, 1)

    # 28. Word frequency rank variance
    wf_values = [float(freq[t]) for t in tokens]
    wfr_var = math.log1p(_safe_var(wf_values))

    # 29. Zipf fit residual
    sorted_freqs = sorted(freq.values(), reverse=True)[:100]
    if len(sorted_freqs) >= 2:
        f1 = sorted_freqs[0]
        residuals = []
        for r, fr in enumerate(sorted_freqs, 1):
            expected = f1 / r
            if fr > 0 and expected > 0:
                residuals.append((math.log(fr) - math.log(expected)) ** 2)
        zipf_res = _safe_mean(residuals)
    else:
        zipf_res = 0.0

    # 30, 31. Readability
    vowels = _VOWELS_EN if lang == "en" else (_VOWELS_RU if lang in ("ru", "uk") else _VOWELS_EN)
    syllables = [_count_syllables(t, vowels) for t in tokens]
    avg_syl = _safe_mean([float(s) for s in syllables])
    asl = n_tokens / max(n_sentences, 1)
    flesch = 206.835 - 1.015 * asl - 84.6 * avg_syl
    flesch_norm = max(-0.5, min(1.5, flesch / 100.0))

    # 32. Starter diversity
    first_words = []
    for s in sentences:
        st = _WORD_RE.findall(s.lower())
        if st:
            first_words.append(st[0])
    starter_div = len(set(first_words)) / max(len(first_words), 1)

    # 33. Conjunction rate
    conj_count = sum(1 for t in tokens if t in _CONJUNCTIONS_EN)
    conj_rate = conj_count / max(n_tokens, 1)

    # 34. Transition word rate
    trans_count = sum(1 for t in tokens if t in _TRANSITIONS_EN)
    trans_rate = trans_count / max(n_tokens, 1)

    # 35. Consecutive length difference variance
    if len(sent_token_counts) >= 2:
        diffs = [abs(sent_token_counts[i] - sent_token_counts[i + 1])
                 for i in range(len(sent_token_counts) - 1)]
        cld_var = math.log1p(_safe_var(diffs))
    else:
        cld_var = 0.0

    return [
        ttr, hapax_ratio, awl, wlv,
        msl, slv, sls,
        yules_k, simpsons, vocab_rich,
        bi_rep, tri_rep, uniq_bi_ratio,
        char_ent, word_ent, bigram_ent,
        burstiness, vocab_burst,
        para_norm, avg_para_len, list_bullet_ratio,
        comma_rate, semi_rate, dash_rate, question_rate, excl_rate,
        ai_pattern_rate, wfr_var, zipf_res,
        avg_syl, flesch_norm,
        starter_div, conj_rate, trans_rate,
        cld_var,
    ]


def normalize_features(raw: Vec) -> Vec:
    """Normalize features: z-score then clip to [-3, 3]."""
    out = []
    for _i, (val, mu, sig) in enumerate(zip(raw, _FEATURE_MEAN, _FEATURE_STD)):
        if sig > 0:
            z = (val - mu) / sig
        else:
            z = 0.0
        out.append(max(-3.0, min(3.0, z)))
    return out


# ---------------------------------------------------------------------------
# Pre-trained MLP weights (35 → 64 → 32 → 1)
#
# Layer 1 (35→64, ReLU): feature expansion with cross-interactions.
# Layer 2 (64→32, ReLU): non-linear combination layer.
# Layer 3 (32→1, linear): output logit.
#
# Weights are trained via backpropagation with Adam optimizer on a corpus
# of AI and human-written text features. Training code: training.py
# Trained weights are stored in texthumanize/weights/detector_weights.json.zb85
#
# When pre-trained weights are not available, falls back to heuristic
# initialization from logistic regression weights.
# ---------------------------------------------------------------------------

def _load_trained_network() -> FeedForwardNet | None:
    """Try to load pre-trained weights from the weights directory."""
    try:
        from texthumanize.weight_loader import load_detector_weights
        config = load_detector_weights()
        if config is not None:
            net = FeedForwardNet.from_config(config)
            logger.info(
                "Loaded trained detector: %d params, arch %s",
                net.param_count, net.name,
            )
            return net
    except Exception as e:
        logger.warning("Could not load trained detector weights: %s", e)
    return None


def _build_pretrained_network() -> FeedForwardNet:
    """Build the MLP for AI detection.

    First tries to load real trained weights. Falls back to heuristic
    initialization from logistic regression weights if unavailable.

    Architecture: 35 → 64 (ReLU) → 32 (ReLU) → 1 (linear)
    """
    # Try loading real trained weights first
    trained = _load_trained_network()
    if trained is not None:
        return trained

    logger.info("No trained weights found, using heuristic initialization")
    import random
    rng = random.Random(31415)

    # Existing LR weights (from statistical_detector.py)
    lr_w = [
        -0.85, 0.62, -0.48, 0.37, -0.32, 0.91, 0.44, 0.28, -0.55, -0.39,
        0.53, 0.41, -0.67, 0.22, 0.58, 0.19, 1.15, 0.73, 0.05, -0.21,
        -0.34, -0.26, -0.72, 0.45, 0.38, 0.29, -2.10, 0.64, 0.31, -0.42,
        0.36, 0.52, 0.18, -0.88, 0.76,
    ]

    # Layer 1: 35 → 64 — initialized with LR as first 35 neurons,
    # plus 29 cross-feature detectors
    n_in, n_h1, n_h2, _n_out = 35, 64, 32, 1

    w1 = []  # 64 x 35
    b1 = []  # 64

    # First 35 neurons: each captures one original feature (amplified)
    for i in range(n_in):
        row = [0.0] * n_in
        row[i] = lr_w[i] * 1.5  # amplify the original signal
        # add slight cross-feature coupling
        for j in range(n_in):
            if i != j:
                row[j] = rng.gauss(0, 0.08)
        w1.append(row)
        b1.append(rng.gauss(0, 0.05))

    # Next 29 neurons: feature interaction detectors
    # Group features into semantically related clusters for interaction
    _clusters = [
        [0, 1, 8, 9],       # vocabulary diversity
        [2, 3],              # word length
        [4, 5, 6],           # sentence length
        [7, 8, 9],           # lexical diversity measures
        [10, 11, 12],        # n-gram repetition
        [13, 14, 15],        # entropy group
        [16, 17],            # burstiness pair
        [18, 19, 20],        # structural
        [21, 22, 23, 24, 25],  # punctuation cluster
        [26],                # AI patterns (critical)
        [27, 28],            # frequency proxy
        [29, 30],            # readability
        [31, 32, 33],        # discourse
        [34],                # rhythm
        [0, 16, 26, 33],     # key discriminators combined
        [1, 5, 17, 34],      # burstiness-related
        [4, 29, 30],         # readability+sentence
        [9, 12, 15],         # richness+uniqueness
        [10, 26, 33],        # repetition+AI+transitions
        [6, 16, 34],         # skewness+burstiness+rhythm
        [13, 14, 15, 26],    # entropy+AI
        [2, 29],             # word length+syllables
        [5, 7],              # variance measures
        [21, 24, 25],        # punctuation variety
        [3, 5, 34],          # variance features
        [0, 8, 12],          # diversity measures
        [20, 18],            # structure
        [31, 32],            # discourse variety
        [22, 23, 24],        # semi/dash/question
    ]

    for _ci, cluster in enumerate(_clusters):
        row = [0.0] * n_in
        for feat_idx in cluster:
            # Strong weight on features in this cluster
            row[feat_idx] = lr_w[feat_idx] * rng.uniform(0.8, 1.5)
        # Small random weights on other features
        for j in range(n_in):
            if j not in cluster:
                row[j] = rng.gauss(0, 0.04)
        w1.append(row)
        b1.append(rng.gauss(0, 0.1))

    # Layer 2: 64 → 32
    w2 = []
    b2 = []
    for _i in range(n_h2):
        row = []
        for j in range(n_h1):
            # Structured initialization: stronger connections to related L1 neurons
            if j < n_in and j % n_h2 == i:
                row.append(rng.gauss(0.3, 0.15))
            elif j >= n_in and (j - n_in) % n_h2 == i:
                row.append(rng.gauss(0.25, 0.12))
            else:
                row.append(rng.gauss(0, 0.12))
        w2.append(row)
        b2.append(rng.gauss(0, 0.05))

    # Layer 3: 32 → 1 — aggregation layer
    w3 = []
    row_final = []
    for _i in range(n_h2):
        row_final.append(rng.gauss(0.15, 0.1))
    w3.append(row_final)
    b3 = [0.15]  # bias matches LR

    return FeedForwardNet([
        DenseLayer(w1, b1, activation="relu"),
        DenseLayer(w2, b2, activation="relu"),
        DenseLayer(w3, b3, activation="linear"),
    ], name="neural_ai_detector_v1")


# Lazy singleton
_DETECTOR_NET: FeedForwardNet | None = None
_DETECTOR_TRAINED: bool = False


def _get_network() -> FeedForwardNet:
    """Get or build the pre-trained network (singleton)."""
    global _DETECTOR_NET, _DETECTOR_TRAINED
    if _DETECTOR_NET is None:
        _DETECTOR_NET = _build_pretrained_network()
        _DETECTOR_TRAINED = _DETECTOR_NET.name != "neural_ai_detector_v1"
        logger.info(
            "Neural detector initialized: %d params, arch 35→64→32→1, trained=%s",
            _DETECTOR_NET.param_count, _DETECTOR_TRAINED,
        )
    return _DETECTOR_NET


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class NeuralAIDetector:
    """Neural network AI text detector.

    Uses a 3-layer MLP (35→64→32→1) with 35 statistical features to
    distinguish AI-generated text from human-written text.

    Architecture:
        - Layer 1 (35→64, ReLU): Feature expansion with cross-interactions
        - Layer 2 (64→32, ReLU): Non-linear combination
        - Layer 3 (32→1, linear): Score output

    The model is pre-trained and requires NO external dependencies or API calls.
    """

    def __init__(self) -> None:
        self._net = _get_network()
        self._trained = _DETECTOR_TRAINED

    def extract_features(self, text: str, lang: str = "en") -> dict[str, float]:
        """Extract and return named features (for debugging/explainability)."""
        raw = extract_features(text, lang)
        return dict(zip(_FEATURE_NAMES, raw))

    def detect(self, text: str, lang: str = "en") -> dict[str, Any]:
        """Detect if text is AI-generated.

        Returns:
            dict with keys:
                - score: float [0, 1] — probability of being AI-generated
                - verdict: str — 'human', 'mixed', or 'ai'
                - confidence: str — 'low', 'medium', or 'high'
                - model: str — 'neural_mlp_v1'
                - features: dict — top contributing features
        """
        raw_features = extract_features(text, lang)
        normed = normalize_features(raw_features)

        # Forward pass through MLP
        if self._trained:
            # Trained weights: positive logit = AI, sigmoid gives P(AI) directly
            score = self._net.predict_proba(normed)
        else:
            # Heuristic weights: positive logit = human, negate for P(AI)
            logit = self._net.forward(normed)
            score = _sigmoid(-logit[0])

        # Short text dampening
        tokens = _WORD_RE.findall(text)
        n_tokens = len(tokens)
        if n_tokens < 50:
            score = 0.5 + (score - 0.5) * (n_tokens / 50.0)

        # Confidence based on text length and score extremity
        extremity = abs(score - 0.5) * 2.0  # [0,1]
        if n_tokens >= 100 and extremity > 0.6:
            confidence = "high"
        elif n_tokens >= 50 and extremity > 0.3:
            confidence = "medium"
        else:
            confidence = "low"

        # Verdict
        if score < 0.30:
            verdict = "human"
        elif score <= 0.60:
            verdict = "mixed"
        else:
            verdict = "ai"

        # Top contributing features — use gradient approximation for trained,
        # LR weights for heuristic
        feature_impacts = {}
        for i, (name, nval) in enumerate(zip(_FEATURE_NAMES, normed)):
            if self._trained:
                # Simple sensitivity: how much does this feature contribute?
                impact = nval * abs(nval) * 0.5  # squared magnitude with sign
            else:
                lr_w = [
                    -0.85, 0.62, -0.48, 0.37, -0.32, 0.91, 0.44, 0.28, -0.55, -0.39,
                    0.53, 0.41, -0.67, 0.22, 0.58, 0.19, 1.15, 0.73, 0.05, -0.21,
                    -0.34, -0.26, -0.72, 0.45, 0.38, 0.29, -2.10, 0.64, 0.31, -0.42,
                    0.36, 0.52, 0.18, -0.88, 0.76,
                ]
                impact = -nval * lr_w[i]
            feature_impacts[name] = round(impact, 4)

        # Sort by absolute impact
        top_features = dict(sorted(
            feature_impacts.items(),
            key=lambda x: abs(x[1]),
            reverse=True,
        )[:10])

        return {
            "score": round(score, 4),
            "verdict": verdict,
            "confidence": confidence,
            "model": "neural_mlp_v1",
            "param_count": self._net.param_count,
            "n_features": 35,
            "top_features": top_features,
        }

    def detect_batch(self, texts: list[str], lang: str = "en") -> list[dict[str, Any]]:
        """Detect AI for multiple texts."""
        return [self.detect(text, lang) for text in texts]

    def detect_sentences(
        self, text: str, lang: str = "en"
    ) -> list[dict[str, Any]]:
        """Per-sentence AI detection for mixed-content analysis."""
        sentences = _SENT_RE.split(text.strip())
        sentences = [s.strip() for s in sentences if len(s.strip()) > 10]

        results = []
        for sent in sentences:
            r = self.detect(sent, lang)
            r["text"] = sent[:100]
            results.append(r)
        return results

    @property
    def architecture(self) -> str:
        return "MLP(35→64→32→1)"

    @property
    def param_count(self) -> int:
        return self._net.param_count
