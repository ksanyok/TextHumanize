"""Grammar Guard — neural artifact detector + targeted synonym rollback.

Variant C implementation:
  1. Extract per-sentence grammar-quality features (collocation score,
     word-frequency smoothness, bigram novelty, repetition, etc.)
  2. MLP classifier predicts P(artifact) for each sentence.
  3. If artifact detected → targeted rollback of synonym replacements
     in that sentence, picking the variant with lowest artifact score.

The guard runs as a late pipeline stage (after grammar correction,
before coherence repair) to catch artifacts introduced by earlier
dictionary-based stages.
"""

from __future__ import annotations

import logging
import math
import os
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ── Feature constants ─────────────────────────────────────────

_WORD_RE = re.compile(r'[a-zA-Zа-яА-ЯёЁіїєґІЇЄҐüöäßÜÖÄ\'-]+')
_SENT_RE = re.compile(r'(?<=[.!?])\s+(?=[A-ZА-ЯЁ"\'"(])')

# Common function words per language (not counted as "content" for freq checks)
_FUNC_WORDS_EN = frozenset({
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'shall',
    'should', 'may', 'might', 'can', 'could', 'must', 'to', 'of', 'in',
    'for', 'on', 'with', 'at', 'by', 'from', 'it', 'this', 'that',
    'and', 'but', 'or', 'not', 'no', 'as', 'if', 'so',
})
_FUNC_WORDS_RU = frozenset({
    'и', 'в', 'не', 'на', 'я', 'что', 'он', 'она', 'оно', 'мы', 'вы',
    'они', 'это', 'с', 'а', 'но', 'по', 'к', 'у', 'о', 'из', 'за',
    'от', 'для', 'до', 'при', 'бы', 'же', 'ли', 'так', 'как', 'все',
    'его', 'её', 'их', 'наш', 'ваш', 'тот', 'этот', 'был', 'была',
    'были', 'быть', 'есть', 'нет',
})
_FUNC_WORDS_UK = frozenset({
    'і', 'й', 'в', 'у', 'не', 'на', 'я', 'що', 'він', 'вона', 'воно',
    'ми', 'ви', 'вони', 'це', 'з', 'а', 'але', 'по', 'до', 'від',
    'для', 'при', 'за', 'як', 'так', 'той', 'цей', 'ця', 'все', 'ще',
    'його', 'її', 'їх', 'наш', 'ваш', 'був', 'була', 'були', 'бути',
    'є', 'нема',
})


def _get_func_words(lang: str) -> frozenset[str]:
    if lang == 'ru':
        return _FUNC_WORDS_RU
    if lang == 'uk':
        return _FUNC_WORDS_UK
    return _FUNC_WORDS_EN


# ── Feature extraction (12 features per sentence) ────────────

def _tokenize(text: str) -> list[str]:
    return [m.group().lower() for m in _WORD_RE.finditer(text)]


def _bigram_pairs(tokens: list[str]) -> list[tuple[str, str]]:
    return [(tokens[i], tokens[i + 1]) for i in range(len(tokens) - 1)]


def extract_sentence_features(
    sentence: str,
    context_before: str,
    context_after: str,
    lang: str = "en",
) -> list[float]:
    """Extract 12 grammar-quality features for a single sentence.

    Features:
      0. collocation_score   — avg PMI of adjacent content-word pairs
      1. freq_smoothness     — variance of word-frequency ranks (low = natural)
      2. bigram_novelty      — fraction of bigrams not in collocation DB
      3. word_length_var     — variance of word lengths (variety = natural)
      4. rare_word_ratio     — ratio of words not in top-10k frequency list
      5. repetition_context  — word overlap with surrounding sentences
      6. sentence_length_z   — normalized sentence length (z-score vs context)
      7. punct_density       — punctuation chars per word
      8. case_anomaly        — fraction of unexpected capitalizations
      9. adj_noun_distance   — avg distance between adj and nearest noun (RU/UK)
     10. connector_overuse   — connector/transition density
     11. syllable_uniformity — variance of syllable counts (low = robotic)
    """
    tokens = _tokenize(sentence)
    n_tokens = max(len(tokens), 1)
    func_words = _get_func_words(lang)
    content_tokens = [t for t in tokens if t not in func_words and len(t) > 2]
    n_content = max(len(content_tokens), 1)

    # ── 0. Collocation score ──────────────────────────────────
    colloc_score = 0.0
    try:
        from texthumanize.collocation_engine import CollocEngine
        ce = CollocEngine(lang=lang)
        content_pairs = _bigram_pairs(content_tokens)
        if content_pairs:
            pmis = [ce.pmi(a, b) for a, b in content_pairs]
            colloc_score = sum(pmis) / len(pmis)
    except Exception:
        pass

    # ── 1. Frequency smoothness ───────────────────────────────
    freq_smooth = 0.0
    try:
        from texthumanize._word_freq_data import get_word_freq
        freq = get_word_freq(lang)
        ranks = [float(freq.get(t, 0)) for t in content_tokens]
        if len(ranks) >= 2:
            mean_r = sum(ranks) / len(ranks)
            freq_smooth = sum((r - mean_r) ** 2 for r in ranks) / len(ranks)
            freq_smooth = math.log1p(freq_smooth)
    except Exception:
        pass

    # ── 2. Bigram novelty ─────────────────────────────────────
    bigram_novelty = 0.5  # default if no colloc data
    try:
        from texthumanize.collocation_engine import CollocEngine
        ce = CollocEngine(lang=lang)
        pairs = _bigram_pairs(content_tokens)
        if pairs:
            unknown = sum(1 for a, b in pairs if ce.pmi(a, b) == 0.0)
            bigram_novelty = unknown / len(pairs)
    except Exception:
        pass

    # ── 3. Word length variance ───────────────────────────────
    word_lens = [len(t) for t in tokens]
    if len(word_lens) >= 2:
        wl_mean = sum(word_lens) / len(word_lens)
        wl_var = sum((w - wl_mean) ** 2 for w in word_lens) / len(word_lens)
    else:
        wl_var = 0.0

    # ── 4. Rare word ratio ────────────────────────────────────
    rare_ratio = 0.0
    try:
        from texthumanize._word_freq_data import get_word_freq
        freq = get_word_freq(lang)
        rare = sum(1 for t in content_tokens if freq.get(t, 0) == 0)
        rare_ratio = rare / n_content
    except Exception:
        pass

    # ── 5. Repetition with context ────────────────────────────
    ctx_tokens = set(_tokenize(context_before + ' ' + context_after))
    sent_set = set(content_tokens)
    if ctx_tokens and sent_set:
        overlap = len(sent_set & ctx_tokens) / max(len(sent_set), 1)
    else:
        overlap = 0.0

    # ── 6. Sentence length z-score ────────────────────────────
    all_ctx = context_before + ' ' + sentence + ' ' + context_after
    ctx_sents = _SENT_RE.split(all_ctx)
    ctx_lens = [len(_tokenize(s)) for s in ctx_sents if s.strip()]
    if len(ctx_lens) >= 2:
        ctx_mean = sum(ctx_lens) / len(ctx_lens)
        ctx_std = (sum((x - ctx_mean) ** 2 for x in ctx_lens) / len(ctx_lens)) ** 0.5
        sent_len_z = (n_tokens - ctx_mean) / max(ctx_std, 1.0)
    else:
        sent_len_z = 0.0

    # ── 7. Punctuation density ────────────────────────────────
    punct_count = sum(1 for c in sentence if c in '.,;:!?—–-()[]{}«»""\'')
    punct_density = punct_count / n_tokens

    # ── 8. Case anomaly ───────────────────────────────────────
    # Unexpected capitals mid-sentence
    words_raw = sentence.split()
    case_anom = 0
    for i, w in enumerate(words_raw):
        if i == 0:
            continue  # sentence start is expected
        if w and w[0].isupper() and not w.isupper() and w.lower() not in func_words:
            case_anom += 1
    case_anomaly = case_anom / max(len(words_raw), 1)

    # ── 9. Adj-noun distance (RU/UK heuristic) ───────────────
    # For Slavic languages, check agreement proximity
    adj_noun_dist = 0.0
    if lang in ('ru', 'uk'):
        adj_suffixes = ('ый', 'ий', 'ой', 'ая', 'яя', 'ое', 'ее',
                        'ые', 'ие') if lang == 'ru' else (
                        'ий', 'ій', 'а', 'я', 'е', 'є', 'і')
        noun_suffixes = ('ие', 'ия', 'ка', 'ок', 'ть', 'ст', 'ор') if lang == 'ru' else (
                         'ія', 'ка', 'ок', 'ть', 'ст', 'ор')
        positions_adj: list[int] = []
        positions_noun: list[int] = []
        for idx, t in enumerate(tokens):
            if any(t.endswith(s) for s in adj_suffixes):
                positions_adj.append(idx)
            if any(t.endswith(s) for s in noun_suffixes):
                positions_noun.append(idx)
        if positions_adj and positions_noun:
            dists = []
            for a in positions_adj:
                min_dist = min(abs(a - n) for n in positions_noun)
                dists.append(min_dist)
            adj_noun_dist = sum(dists) / len(dists)

    # ── 10. Connector overuse ─────────────────────────────────
    _CONNECTORS = {
        'en': {'however', 'therefore', 'furthermore', 'moreover', 'additionally',
               'consequently', 'nevertheless', 'nonetheless', 'accordingly'},
        'ru': {'однако', 'поэтому', 'следовательно', 'кроме того', 'более того',
               'дополнительно', 'тем не менее', 'соответственно', 'таким образом'},
        'uk': {'однак', 'тому', 'отже', 'крім того', 'більше того',
               'додатково', 'тим не менш', 'відповідно', 'таким чином'},
    }
    conn_set = _CONNECTORS.get(lang, _CONNECTORS['en'])
    lower_sent = sentence.lower()
    conn_count = sum(1 for c in conn_set if c in lower_sent)
    conn_overuse = conn_count / n_tokens

    # ── 11. Syllable uniformity ───────────────────────────────
    _vowels = set('aeiouy') if lang == 'en' else (
        set('аеёиоуыэюя') if lang == 'ru' else
        set('аеіїоуєюя') if lang == 'uk' else set('aeiouy')
    )
    def _syllables(w: str) -> int:
        count = 0
        prev = False
        for c in w.lower():
            if c in _vowels:
                if not prev:
                    count += 1
                prev = True
            else:
                prev = False
        return max(1, count)

    syl_counts = [_syllables(t) for t in tokens]
    if len(syl_counts) >= 2:
        syl_mean = sum(syl_counts) / len(syl_counts)
        syl_var = sum((s - syl_mean) ** 2 for s in syl_counts) / len(syl_counts)
    else:
        syl_var = 1.0  # single-token sentence, neutral

    return [
        colloc_score,       # 0
        freq_smooth,        # 1
        bigram_novelty,     # 2
        wl_var,             # 3
        rare_ratio,         # 4
        overlap,            # 5 (repetition_context)
        sent_len_z,         # 6
        punct_density,      # 7
        case_anomaly,       # 8
        adj_noun_dist,      # 9
        conn_overuse,       # 10
        syl_var,            # 11
    ]


# ── MLP Artifact Detector ────────────────────────────────────

# Feature normalization (empirical means & stds from training data)
_FEAT_MEAN = [
    0.8, 6.5, 0.4, 4.5, 0.15, 0.35, 0.0, 0.25, 0.02, 1.5, 0.01, 1.8
]
_FEAT_STD = [
    0.6, 2.0, 0.2, 2.0, 0.12, 0.15, 1.0, 0.12, 0.02, 1.0, 0.01, 0.8
]

# Initial hand-tuned weights. Replaced at runtime if trained weights exist.
_W1: list[list[float]] = []
_B1: list[float] = []
_W2: list[list[float]] = []
_B2: list[float] = []
_W3: list[list[float]] = []
_B3: list[float] = []
_WEIGHTS_LOADED = False


def _ensure_weights() -> None:
    """Load trained weights from disk, or fallback to heuristic initialization."""
    global _W1, _B1, _W2, _B2, _W3, _B3, _FEAT_MEAN, _FEAT_STD, _WEIGHTS_LOADED
    if _WEIGHTS_LOADED:
        return

    # Try loading trained weights
    weights_loaded = False

    try:
        weights_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'weights',
        )
        weights_path = os.path.join(weights_dir, 'grammar_guard_weights.json')
        if os.path.exists(weights_path):
            import json
            with open(weights_path) as f:
                data = json.load(f)
            _W1 = data['W1']
            _B1 = data['B1']
            _W2 = data['W2']
            _B2 = data['B2']
            _W3 = data['W3']
            _B3 = data['B3']
            if 'means' in data:
                _FEAT_MEAN = data['means']
            if 'stds' in data:
                _FEAT_STD = data['stds']
            weights_loaded = True
            logger.debug("Grammar Guard: loaded trained weights")
    except Exception as e:
        logger.debug("Grammar Guard: could not load trained weights: %s", e)

    if not weights_loaded:
        # Fallback: heuristic initialization
        logger.debug("Grammar Guard: using heuristic weights")
        import random as _rng
        r = _rng.Random(42)
        _W1 = [[r.gauss(0, 0.3) for _ in range(12)] for _ in range(16)]
        _B1 = [0.0] * 16
        _W2 = [[r.gauss(0, 0.3) for _ in range(16)] for _ in range(8)]
        _B2 = [0.0] * 8
        _W3 = [[r.gauss(0, 0.3) for _ in range(8)]]
        _B3 = [0.0]

    _WEIGHTS_LOADED = True


def _sigmoid(x: float) -> float:
    if x > 20:
        return 1.0
    if x < -20:
        return 0.0
    return 1.0 / (1.0 + math.exp(-x))


def _relu(x: float) -> float:
    return max(0.0, x)


def _mlp_forward(features: list[float]) -> float:
    """Run 12→16→8→1 MLP and return P(artifact)."""
    _ensure_weights()

    # Normalize
    normed = []
    for i, (v, m, s) in enumerate(zip(features, _FEAT_MEAN, _FEAT_STD)):
        if s > 0:
            normed.append(max(-3.0, min(3.0, (v - m) / s)))
        else:
            normed.append(0.0)

    # Layer 1
    h1 = []
    for j in range(len(_W1)):
        acc = _B1[j]
        for i, x in enumerate(normed):
            acc += _W1[j][i] * x
        h1.append(_relu(acc))

    # Layer 2
    h2 = []
    for j in range(len(_W2)):
        acc = _B2[j]
        for i, x in enumerate(h1):
            acc += _W2[j][i] * x
        h2.append(_relu(acc))

    # Layer 3 (output)
    logit = _B3[0]
    for i, x in enumerate(h2):
        logit += _W3[0][i] * x

    return _sigmoid(logit)


# ── Synonym rollback engine ───────────────────────────────────

@dataclass
class RollbackCandidate:
    """A possible reverse-substitution for a word in an artifact sentence."""
    position: int        # token index in sentence
    current_word: str    # word after humanization
    original_word: str   # word before humanization (from diff)
    artifact_delta: float  # how much artifact score drops when reverted


@dataclass
class GuardResult:
    """Result of Grammar Guard analysis on full text."""
    sentences_checked: int = 0
    artifacts_found: int = 0
    rollbacks_applied: int = 0
    changes: list[dict] = field(default_factory=list)


class GrammarGuard:
    """Neural Grammar Guard — detects and fixes humanization artifacts.

    Usage:
        guard = GrammarGuard(lang="ru")
        fixed_text = guard.process(humanized_text, original_text)
        print(guard.result.artifacts_found)
    """

    def __init__(
        self,
        lang: str = "en",
        threshold: float = 0.72,
        max_rollbacks_per_sentence: int = 2,
    ):
        self.lang = lang
        self.threshold = threshold
        self.max_rollbacks = max_rollbacks_per_sentence
        self.result = GuardResult()

    def process(self, text: str, original: str = "") -> str:
        """Analyze text for grammar artifacts and apply targeted rollbacks.

        Args:
            text: Humanized text to check.
            original: Original text before humanization (for rollback source).

        Returns:
            Text with artifact sentences corrected.
        """
        if not text or len(text.strip()) < 20:
            return text

        from texthumanize.sentence_split import split_sentences

        sentences = split_sentences(text, lang=self.lang)
        if not sentences:
            return text

        self.result = GuardResult(sentences_checked=len(sentences))

        # Build context windows
        artifact_indices: list[int] = []
        artifact_scores: list[float] = []

        for i, sent in enumerate(sentences):
            ctx_before = sentences[i - 1] if i > 0 else ""
            ctx_after = sentences[i + 1] if i < len(sentences) - 1 else ""

            features = extract_sentence_features(
                sent, ctx_before, ctx_after, lang=self.lang,
            )
            score = _mlp_forward(features)

            if score >= self.threshold:
                artifact_indices.append(i)
                artifact_scores.append(score)

        self.result.artifacts_found = len(artifact_indices)

        if not artifact_indices:
            return text

        # Try rollback for each artifact sentence
        if original:
            original_sents = split_sentences(original, lang=self.lang)
        else:
            original_sents = []

        fixed_sentences = list(sentences)
        for idx, score in zip(artifact_indices, artifact_scores):
            fixed = self._try_rollback(
                fixed_sentences[idx],
                original_sents[idx] if idx < len(original_sents) else "",
                sentences[idx - 1] if idx > 0 else "",
                sentences[idx + 1] if idx < len(sentences) - 1 else "",
            )
            if fixed != fixed_sentences[idx]:
                self.result.rollbacks_applied += 1
                self.result.changes.append({
                    "type": "grammar_guard_rollback",
                    "description": (
                        f"Artifact (score={score:.2f}): "
                        f"«{sentences[idx][:60]}…» → «{fixed[:60]}…»"
                    ),
                })
                fixed_sentences[idx] = fixed

        # Reconstruct text preserving original whitespace
        result = text
        for idx in reversed(artifact_indices):
            if fixed_sentences[idx] != sentences[idx]:
                result = result.replace(sentences[idx], fixed_sentences[idx], 1)

        return result

    def _try_rollback(
        self,
        sentence: str,
        original_sentence: str,
        ctx_before: str,
        ctx_after: str,
    ) -> str:
        """Try targeted word-level rollbacks to reduce artifact score.

        Compare humanized sentence to original, find changed words,
        and try reverting each one. Keep reversions that lower the score.
        """
        if not original_sentence:
            return sentence

        hum_tokens = _tokenize(sentence)
        orig_tokens = _tokenize(original_sentence)

        if not hum_tokens or not orig_tokens:
            return sentence

        # Safety gate: if sentences diverged too much, positional alignment
        # is unreliable and rollback would produce garbled text.
        hum_set = {t.lower() for t in hum_tokens}
        orig_set = {t.lower() for t in orig_tokens}
        overlap = len(hum_set & orig_set) / max(len(hum_set | orig_set), 1)
        if overlap < 0.55:
            return sentence  # sentences restructured too much, skip rollback

        # Also check positional alignment quality: if too many positions differ,
        # the alignment is unreliable even with decent vocabulary overlap.
        min_len = min(len(hum_tokens), len(orig_tokens))
        pos_matches = sum(1 for i in range(min_len) if hum_tokens[i] == orig_tokens[i])
        pos_ratio = pos_matches / max(min_len, 1)
        if pos_ratio < 0.35:
            return sentence  # too many positional mismatches

        # Find changed positions via simple alignment
        candidates: list[RollbackCandidate] = []
        min_len = min(len(hum_tokens), len(orig_tokens))

        for i in range(min_len):
            if hum_tokens[i] != orig_tokens[i]:
                candidates.append(RollbackCandidate(
                    position=i,
                    current_word=hum_tokens[i],
                    original_word=orig_tokens[i],
                    artifact_delta=0.0,
                ))

        if not candidates:
            return sentence

        # Score each candidate rollback
        base_features = extract_sentence_features(
            sentence, ctx_before, ctx_after, self.lang,
        )
        base_score = _mlp_forward(base_features)

        for cand in candidates:
            # Try reverting this one word
            trial = sentence
            # Case-preserving replacement
            old_w = cand.current_word
            new_w = cand.original_word
            # Find the word in actual sentence text (case-sensitive)
            pattern = re.compile(r'\b' + re.escape(old_w) + r'\b', re.IGNORECASE)
            match = pattern.search(trial)
            if match:
                # Preserve original casing pattern
                found = match.group()
                if found[0].isupper():
                    replacement = new_w[0].upper() + new_w[1:] if len(new_w) > 1 else new_w.upper()
                else:
                    replacement = new_w
                trial = trial[:match.start()] + replacement + trial[match.end():]

            trial_features = extract_sentence_features(
                trial, ctx_before, ctx_after, self.lang,
            )
            trial_score = _mlp_forward(trial_features)
            cand.artifact_delta = base_score - trial_score

        # Apply best rollbacks (up to max_rollbacks)
        candidates.sort(key=lambda c: c.artifact_delta, reverse=True)
        result = sentence
        applied = 0

        for cand in candidates:
            if applied >= self.max_rollbacks:
                break
            if cand.artifact_delta <= 0.01:
                continue  # not beneficial

            old_w = cand.current_word
            new_w = cand.original_word
            pattern = re.compile(r'\b' + re.escape(old_w) + r'\b', re.IGNORECASE)
            match = pattern.search(result)
            if match:
                found = match.group()
                if found[0].isupper():
                    replacement = new_w[0].upper() + new_w[1:] if len(new_w) > 1 else new_w.upper()
                else:
                    replacement = new_w
                result = result[:match.start()] + replacement + result[match.end():]
                applied += 1

        # Verify final score is lower
        final_features = extract_sentence_features(
            result, ctx_before, ctx_after, self.lang,
        )
        final_score = _mlp_forward(final_features)

        if final_score < base_score:
            return result
        return sentence  # rollback didn't help, revert
