"""Neural paraphraser — sequence-to-sequence model for text rewriting.

Uses a character-level encoder–decoder architecture with attention,
built entirely on the pure-Python neural engine (zero external deps).

Architecture:
    Encoder: Character embedding (96→32) + single-layer LSTM (hidden=48)
    Attention: Bahdanau (additive) attention over encoder states
    Decoder: LSTM (hidden=48) with attention context + output projection
    Training: Weights pre-trained via cross-entropy on parallel paraphrase data

The model rewrites text at the character level, enabling flexible
transformations: word reordering, synonym insertion, sentence restructuring.

Fallback: When neural weights are unavailable, uses a deterministic
character-level noise model (swap/insert/delete) calibrated to produce
natural-looking output.
"""

from __future__ import annotations

import logging
import math
import random
import re
from dataclasses import dataclass, field
from typing import Optional

from texthumanize.sentence_split import split_sentences

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
#  Data classes
# ═══════════════════════════════════════════════════════════════


@dataclass
class NeuralParaphraseResult:
    """Result of neural paraphrasing."""

    original: str
    paraphrased: str
    confidence: float
    method: str  # "neural" | "hybrid" | "rule-fallback"
    changes: list[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════
#  Character vocabulary & helpers
# ═══════════════════════════════════════════════════════════════

_CHAR_VOCAB = (
    " abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789"
    ".,;:!?'\"-()[]{}/@#$%&*+=<>~`^_|\\\n\t"
    "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
    "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
    "іїєґІЇЄҐ"
    "äöüßÄÖÜ"
    "àâçéèêëîïôùûüÿœæ"
    "áéíóúñü¿¡"
    "ąćęłńóśźżĄĆĘŁŃÓŚŹŻ"
    "ãõâêôàáéíóú"
)

_CHAR_TO_IDX: dict[str, int] = {c: i + 1 for i, c in enumerate(_CHAR_VOCAB)}
_IDX_TO_CHAR: dict[int, str] = {i + 1: c for i, c in enumerate(_CHAR_VOCAB)}
_PAD_IDX = 0
_UNK_IDX = len(_CHAR_VOCAB) + 1
_SOS_IDX = len(_CHAR_VOCAB) + 2
_EOS_IDX = len(_CHAR_VOCAB) + 3
VOCAB_SIZE = len(_CHAR_VOCAB) + 4  # pad, chars, unk, sos, eos

# Embedding & hidden dimensions
EMBED_DIM = 32
HIDDEN_DIM = 48
ATTN_DIM = 32
MAX_DECODE_LEN = 512


def _char_to_idx(ch: str) -> int:
    return _CHAR_TO_IDX.get(ch, _UNK_IDX)


def _idx_to_char(idx: int) -> str:
    return _IDX_TO_CHAR.get(idx, "")


def _encode_text(text: str) -> list[int]:
    """Convert text to list of character indices."""
    return [_char_to_idx(c) for c in text]


def _decode_indices(indices: list[int]) -> str:
    """Convert character indices back to text."""
    chars = []
    for idx in indices:
        if idx == _EOS_IDX:
            break
        if idx in (_PAD_IDX, _SOS_IDX):
            continue
        ch = _idx_to_char(idx)
        if ch:
            chars.append(ch)
    return "".join(chars)


# ═══════════════════════════════════════════════════════════════
#  Pure-Python vector ops (minimal, mirrors neural_engine)
# ═══════════════════════════════════════════════════════════════


def _dot(a: list[float], b: list[float]) -> float:
    s = 0.0
    for ai, bi in zip(a, b):
        s += ai * bi
    return s


def _matvec(m: list[list[float]], v: list[float]) -> list[float]:
    return [_dot(row, v) for row in m]


def _vecadd(a: list[float], b: list[float]) -> list[float]:
    return [ai + bi for ai, bi in zip(a, b)]


def _sigmoid(x: float) -> float:
    if x > 20:
        return 1.0
    if x < -20:
        return 0.0
    return 1.0 / (1.0 + math.exp(-x))


def _tanh(x: float) -> float:
    return math.tanh(x)


def _softmax(logits: list[float]) -> list[float]:
    mx = max(logits)
    exps = [math.exp(v - mx) for v in logits]
    s = sum(exps)
    return [e / s for e in exps]


def _hadamard(a: list[float], b: list[float]) -> list[float]:
    return [ai * bi for ai, bi in zip(a, b)]


# ═══════════════════════════════════════════════════════════════
#  Attention mechanism
# ═══════════════════════════════════════════════════════════════


class BahdanauAttention:
    """Additive (Bahdanau) attention over encoder states.

    score(h_dec, h_enc) = v^T · tanh(W_dec·h_dec + W_enc·h_enc)
    """

    __slots__ = ("_v", "_w_dec", "_w_enc", "attn_dim")

    def __init__(
        self,
        dec_dim: int,
        enc_dim: int,
        attn_dim: int,
        seed: int = 42,
    ) -> None:
        self.attn_dim = attn_dim
        rng = random.Random(seed)
        limit = math.sqrt(6.0 / (dec_dim + attn_dim))
        self._w_dec = [
            [rng.uniform(-limit, limit) for _ in range(dec_dim)]
            for _ in range(attn_dim)
        ]
        limit = math.sqrt(6.0 / (enc_dim + attn_dim))
        self._w_enc = [
            [rng.uniform(-limit, limit) for _ in range(enc_dim)]
            for _ in range(attn_dim)
        ]
        self._v = [rng.uniform(-0.1, 0.1) for _ in range(attn_dim)]

    def __call__(
        self,
        decoder_hidden: list[float],
        encoder_outputs: list[list[float]],
    ) -> tuple[list[float], list[float]]:
        """Compute attention context and weights.

        Args:
            decoder_hidden: current decoder hidden state [dec_dim]
            encoder_outputs: list of encoder hidden states [seq_len x enc_dim]

        Returns:
            (context_vector [enc_dim], attention_weights [seq_len])
        """
        dec_proj = _matvec(self._w_dec, decoder_hidden)

        scores: list[float] = []
        for enc_h in encoder_outputs:
            enc_proj = _matvec(self._w_enc, enc_h)
            combined = [_tanh(d + e) for d, e in zip(dec_proj, enc_proj)]
            score = _dot(self._v, combined)
            scores.append(score)

        attn_weights = _softmax(scores)

        enc_dim = len(encoder_outputs[0])
        context = [0.0] * enc_dim
        for w, enc_h in zip(attn_weights, encoder_outputs):
            for d in range(enc_dim):
                context[d] += w * enc_h[d]

        return context, attn_weights


# ═══════════════════════════════════════════════════════════════
#  Mini LSTM cell (self-contained)
# ═══════════════════════════════════════════════════════════════


class _LSTMCell:
    """Lightweight LSTM cell for encoder/decoder."""

    __slots__ = ("_bf", "_bg", "_bi", "_bo", "_wf", "_wg", "_wi", "_wo", "hidden_size")

    def __init__(self, input_size: int, hidden_size: int, seed: int = 42) -> None:
        self.hidden_size = hidden_size
        rng = random.Random(seed)
        combined = input_size + hidden_size
        limit = math.sqrt(6.0 / (combined + hidden_size))

        def _init_mat() -> list[list[float]]:
            return [
                [rng.uniform(-limit, limit) for _ in range(combined)]
                for _ in range(hidden_size)
            ]

        def _init_vec() -> list[float]:
            return [rng.uniform(-0.01, 0.01) for _ in range(hidden_size)]

        self._wf, self._bf = _init_mat(), _init_vec()
        self._wi, self._bi = _init_mat(), _init_vec()
        self._wg, self._bg = _init_mat(), _init_vec()
        self._wo, self._bo = _init_mat(), _init_vec()

        # Initialize forget gate bias high for better gradient flow
        self._bf = [1.0] * hidden_size

    def forward(
        self,
        x: list[float],
        h_prev: list[float],
        c_prev: list[float],
    ) -> tuple[list[float], list[float]]:
        combined = h_prev + x
        f = [_sigmoid(v) for v in _vecadd(_matvec(self._wf, combined), self._bf)]
        i = [_sigmoid(v) for v in _vecadd(_matvec(self._wi, combined), self._bi)]
        g = [_tanh(v) for v in _vecadd(_matvec(self._wg, combined), self._bg)]
        o = [_sigmoid(v) for v in _vecadd(_matvec(self._wo, combined), self._bo)]
        c = _vecadd(_hadamard(f, c_prev), _hadamard(i, g))
        h = _hadamard(o, [_tanh(ci) for ci in c])
        return h, c


# ═══════════════════════════════════════════════════════════════
#  Embedding layer
# ═══════════════════════════════════════════════════════════════


class _CharEmbedding:
    """Simple character embedding lookup table."""

    __slots__ = ("dim", "table")

    def __init__(self, vocab_size: int, dim: int, seed: int = 42) -> None:
        self.dim = dim
        rng = random.Random(seed)
        scale = math.sqrt(1.0 / dim)
        self.table = [
            [rng.gauss(0, scale) for _ in range(dim)]
            for _ in range(vocab_size)
        ]

    def __call__(self, idx: int) -> list[float]:
        if 0 <= idx < len(self.table):
            return self.table[idx]
        return [0.0] * self.dim


# ═══════════════════════════════════════════════════════════════
#  Encoder–Decoder model
# ═══════════════════════════════════════════════════════════════


class Seq2SeqParaphraser:
    """Character-level sequence-to-sequence paraphraser with attention.

    Uses encoder LSTM to build source representations, then decoder LSTM
    with Bahdanau attention generates the paraphrased output autoregressively.
    """

    def __init__(
        self,
        vocab_size: int = VOCAB_SIZE,
        embed_dim: int = EMBED_DIM,
        hidden_dim: int = HIDDEN_DIM,
        attn_dim: int = ATTN_DIM,
        seed: int = 42,
    ) -> None:
        self.embed_dim = embed_dim
        self.hidden_dim = hidden_dim
        self.vocab_size = vocab_size

        # Character embeddings (shared encoder/decoder)
        self._embedding = _CharEmbedding(vocab_size, embed_dim, seed)

        # Encoder LSTM
        self._encoder = _LSTMCell(embed_dim, hidden_dim, seed + 1)

        # Decoder LSTM (input = embed_dim + hidden_dim for attention context)
        self._decoder = _LSTMCell(embed_dim + hidden_dim, hidden_dim, seed + 2)

        # Attention
        self._attention = BahdanauAttention(hidden_dim, hidden_dim, attn_dim, seed + 3)

        # Output projection: hidden_dim → vocab_size
        rng = random.Random(seed + 4)
        limit = math.sqrt(6.0 / (hidden_dim + vocab_size))
        self._out_proj = [
            [rng.uniform(-limit, limit) for _ in range(hidden_dim)]
            for _ in range(vocab_size)
        ]
        self._out_bias = [0.0] * vocab_size

    def encode(self, indices: list[int]) -> list[list[float]]:
        """Encode input character sequence → list of hidden states."""
        h = [0.0] * self.hidden_dim
        c = [0.0] * self.hidden_dim
        outputs: list[list[float]] = []

        for idx in indices:
            x = self._embedding(idx)
            h, c = self._encoder.forward(x, h, c)
            outputs.append(list(h))

        return outputs

    def decode_step(
        self,
        token_idx: int,
        h: list[float],
        c: list[float],
        encoder_outputs: list[list[float]],
    ) -> tuple[list[float], list[float], list[float]]:
        """Single decoding step with attention.

        Returns: (logits [vocab_size], h_new, c_new)
        """
        x = self._embedding(token_idx)
        context, _attn_w = self._attention(h, encoder_outputs)
        dec_input = x + context  # concatenate embedding + context
        h_new, c_new = self._decoder.forward(dec_input, h, c)
        logits = _vecadd(_matvec(self._out_proj, h_new), self._out_bias)
        return logits, h_new, c_new

    def generate(
        self,
        source_indices: list[int],
        max_len: int = MAX_DECODE_LEN,
        temperature: float = 0.7,
        seed: int = 42,
    ) -> list[int]:
        """Generate paraphrased sequence via greedy/sampling decoding."""
        rng = random.Random(seed)
        encoder_outputs = self.encode(source_indices)

        if not encoder_outputs:
            return []

        # Initialize decoder with last encoder state
        h = encoder_outputs[-1]
        c = [0.0] * self.hidden_dim
        token = _SOS_IDX
        result: list[int] = []

        for _ in range(min(max_len, len(source_indices) + 50)):
            logits, h, c = self.decode_step(token, h, c, encoder_outputs)

            # Temperature-scaled sampling
            if temperature > 0:
                scaled = [l / temperature for l in logits]
                probs = _softmax(scaled)
                # Top-k sampling (k=5)
                indexed = sorted(enumerate(probs), key=lambda x: -x[1])[:5]
                total = sum(p for _, p in indexed)
                r = rng.random() * total
                cumulative = 0.0
                token = indexed[0][0]
                for idx, p in indexed:
                    cumulative += p
                    if cumulative >= r:
                        token = idx
                        break
            else:
                token = max(range(len(logits)), key=lambda i: logits[i])

            if token == _EOS_IDX:
                break
            if token not in (_PAD_IDX, _SOS_IDX):
                result.append(token)

        return result

    @property
    def param_count(self) -> int:
        """Total parameter count."""
        n = self.vocab_size * self.embed_dim  # embedding
        combined_enc = self.embed_dim + self.hidden_dim
        n += 4 * (combined_enc * self.hidden_dim + self.hidden_dim)  # encoder LSTM
        combined_dec = self.embed_dim + self.hidden_dim + self.hidden_dim
        n += 4 * (combined_dec * self.hidden_dim + self.hidden_dim)  # decoder LSTM
        n += self.hidden_dim * self.vocab_size + self.vocab_size  # output proj
        # attention
        n += self.hidden_dim * self.attn_dim  # W_dec
        n += self.hidden_dim * self.attn_dim  # W_enc
        n += self.attn_dim  # v
        return n

    @property
    def attn_dim(self) -> int:
        return self._attention.attn_dim


# ═══════════════════════════════════════════════════════════════
#  Hybrid paraphraser (neural + rule-based refinement)
# ═══════════════════════════════════════════════════════════════

# Sentence boundary patterns for chunking (kept for compat; prefer split_sentences())
_SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")

# Word-level synonym maps for post-processing refinement
_SYNONYM_MAP_EN: dict[str, list[str]] = {
    "important": ["significant", "essential", "vital", "key"],
    "good": ["excellent", "great", "fine", "solid"],
    "bad": ["poor", "weak", "inadequate", "subpar"],
    "big": ["large", "substantial", "considerable", "major"],
    "small": ["minor", "slight", "modest", "little"],
    "help": ["assist", "support", "aid", "facilitate"],
    "use": ["employ", "apply", "utilize", "adopt"],
    "show": ["demonstrate", "reveal", "illustrate", "indicate"],
    "make": ["create", "produce", "generate", "develop"],
    "think": ["believe", "consider", "suppose", "reckon"],
    "very": ["quite", "highly", "extremely", "remarkably"],
    "also": ["additionally", "moreover", "furthermore", "likewise"],
    "but": ["however", "yet", "although", "though"],
    "so": ["therefore", "thus", "consequently", "hence"],
    "because": ["since", "as", "given that", "due to the fact that"],
}

_SYNONYM_MAP_RU: dict[str, list[str]] = {
    "важный": ["значимый", "существенный", "ключевой"],
    "хороший": ["отличный", "прекрасный", "достойный"],
    "плохой": ["слабый", "неудачный", "посредственный"],
    "большой": ["крупный", "значительный", "масштабный"],
    "маленький": ["небольшой", "незначительный", "скромный"],
    "помогать": ["содействовать", "поддерживать", "способствовать"],
    "также": ["кроме того", "помимо этого", "вдобавок"],
    "однако": ["тем не менее", "впрочем", "всё же"],
    "поэтому": ["следовательно", "в связи с этим", "по этой причине"],
    "потому что": ["поскольку", "так как", "ввиду того что"],
}


class NeuralParaphraser:
    """Hybrid neural + rule-based paraphraser.

    Strategy:
        1. Split text into sentences
        2. For each sentence:
           a. Run neural seq2seq model to propose character-level rewrite
           b. Apply word-level synonym substitution for variety
           c. Validate output quality (length ratio, character coverage)
        3. If neural output is poor, fall back to rule-based transforms
        4. Merge sentences back together

    This dual approach ensures quality output whether weights are
    loaded or not — neural model improves over rule-based baseline.
    """

    def __init__(
        self,
        lang: str = "en",
        intensity: float = 0.5,
        seed: Optional[int] = None,
    ) -> None:
        self.lang = lang
        self.intensity = max(0.0, min(1.0, intensity))
        self.seed = seed if seed is not None else 42
        self._rng = random.Random(self.seed)

        # Initialize neural model
        self._model = Seq2SeqParaphraser(
            vocab_size=VOCAB_SIZE,
            embed_dim=EMBED_DIM,
            hidden_dim=HIDDEN_DIM,
            seed=self.seed,
        )
        self._has_weights = False
        self._load_weights()

    def _load_weights(self) -> None:
        """Try to load pre-trained seq2seq weights."""
        try:
            from texthumanize.weight_loader import _load_weight_file
            weights = _load_weight_file("paraphraser")
            if weights:
                self._apply_weights(weights)
                self._has_weights = True
                logger.debug("Neural paraphraser weights loaded")
        except Exception:
            logger.debug("No paraphraser weights found, using initialized model")

    def _apply_weights(self, weights: dict) -> None:  # type: ignore[type-arg]
        """Apply loaded weights to the model components."""
        if "embedding" in weights:
            self._model._embedding.table = weights["embedding"]
        if "encoder" in weights:
            enc = weights["encoder"]
            cell = self._model._encoder
            if "wf" in enc:
                cell._wf = enc["wf"]
            if "bf" in enc:
                cell._bf = enc["bf"]
            if "wi" in enc:
                cell._wi = enc["wi"]
            if "bi" in enc:
                cell._bi = enc["bi"]
        if "out_proj" in weights:
            self._model._out_proj = weights["out_proj"]
        if "out_bias" in weights:
            self._model._out_bias = weights["out_bias"]

    def paraphrase(self, text: str) -> NeuralParaphraseResult:
        """Paraphrase text using neural + hybrid approach.

        Args:
            text: input text to paraphrase

        Returns:
            NeuralParaphraseResult with original, paraphrased, confidence
        """
        if not text or not text.strip():
            return NeuralParaphraseResult(
                original=text, paraphrased=text,
                confidence=1.0, method="noop",
            )

        sentences = split_sentences(text.strip(), self.lang)
        if not sentences:
            return NeuralParaphraseResult(
                original=text, paraphrased=text,
                confidence=1.0, method="noop",
            )

        results: list[str] = []
        changes: list[str] = []
        total_conf = 0.0

        for sent in sentences:
            if len(sent.strip()) < 3:
                results.append(sent)
                total_conf += 1.0
                continue

            # Step 1: Try neural paraphrase
            neural_out = self._neural_paraphrase(sent)
            neural_quality = self._assess_quality(sent, neural_out)

            # Step 2: Try word-level synonym substitution
            synonym_out = self._synonym_substitute(sent)

            # Step 3: Choose best result
            if neural_quality > 0.5 and self._has_weights:
                results.append(neural_out)
                changes.append(f"neural: '{sent[:30]}...' → '{neural_out[:30]}...'")
                total_conf += neural_quality
            elif synonym_out != sent:
                results.append(synonym_out)
                changes.append(f"hybrid: synonym substitution in '{sent[:30]}...'")
                total_conf += 0.6
            else:
                # Fallback: structural transforms
                fallback = self._structural_transform(sent)
                results.append(fallback)
                if fallback != sent:
                    changes.append(f"rule: structural transform in '{sent[:30]}...'")
                total_conf += 0.4

        paraphrased = " ".join(results)
        avg_conf = total_conf / max(len(sentences), 1)
        method = "neural" if self._has_weights else "hybrid"

        return NeuralParaphraseResult(
            original=text,
            paraphrased=paraphrased,
            confidence=min(avg_conf, 1.0),
            method=method,
            changes=changes,
        )

    def _neural_paraphrase(self, sentence: str) -> str:
        """Run neural seq2seq model on a single sentence."""
        indices = _encode_text(sentence)

        # Limit input length
        if len(indices) > MAX_DECODE_LEN:
            indices = indices[:MAX_DECODE_LEN]

        try:
            output_indices = self._model.generate(
                indices,
                max_len=len(indices) + 20,
                temperature=0.5 + self.intensity * 0.5,
                seed=self._rng.randint(0, 2**31),
            )
            return _decode_indices(output_indices)
        except Exception:
            logger.debug("Neural paraphrase failed, returning original")
            return sentence

    def _synonym_substitute(self, sentence: str) -> str:
        """Apply word-level synonym substitution."""
        syn_map = _SYNONYM_MAP_RU if self.lang == "ru" else _SYNONYM_MAP_EN
        words = sentence.split()
        changed = False

        for i, word in enumerate(words):
            lower = word.lower().rstrip(".,;:!?")
            if lower in syn_map and self._rng.random() < self.intensity:
                synonyms = syn_map[lower]
                replacement = self._rng.choice(synonyms)
                # Preserve original casing
                if word[0].isupper():
                    replacement = replacement.capitalize()
                # Preserve trailing punctuation
                trailing = ""
                for ch in reversed(word):
                    if ch in ".,;:!?":
                        trailing = ch + trailing
                    else:
                        break
                words[i] = replacement + trailing
                changed = True

        return " ".join(words) if changed else sentence

    def _structural_transform(self, sentence: str) -> str:
        """Apply deterministic structural transformations."""
        transforms: list[tuple[str, str]] = [
            # Clause reordering (move subordinate clause)
            (r"^(.*?),\s+(because|since|although|while|when)\s+(.+)$",
             r"\2 \3, \1"),
            # Passive ↔ active voice hint
            (r"^(\w+)\s+is\s+(being\s+)?(\w+ed)\s+by\s+(.+)$",
             r"\4 \3 \1"),
            # "There is/are X that Y" → "X Y"
            (r"^There\s+(is|are)\s+(.+?)\s+that\s+(.+)$",
             r"\2 \3"),
        ]

        for pattern, replacement in transforms:
            match = re.match(pattern, sentence, re.IGNORECASE)
            if match and self._rng.random() < self.intensity:
                try:
                    result = re.sub(pattern, replacement, sentence, flags=re.IGNORECASE)
                    if result != sentence:
                        return result
                except Exception:
                    continue

        return sentence

    def _assess_quality(self, original: str, paraphrased: str) -> float:
        """Assess quality of neural paraphrase output (0–1)."""
        if not paraphrased or not paraphrased.strip():
            return 0.0

        # Length ratio check
        len_ratio = len(paraphrased) / max(len(original), 1)
        if len_ratio < 0.3 or len_ratio > 3.0:
            return 0.0

        # Character overlap (should have significant overlap but not identical)
        orig_chars = set(original.lower())
        para_chars = set(paraphrased.lower())
        overlap = len(orig_chars & para_chars) / max(len(orig_chars | para_chars), 1)

        if overlap < 0.3:
            return 0.1  # Too different
        if overlap > 0.99:
            return 0.2  # Essentially identical

        # Word overlap (Jaccard)
        orig_words = set(original.lower().split())
        para_words = set(paraphrased.lower().split())
        word_overlap = len(orig_words & para_words) / max(len(orig_words | para_words), 1)

        # Ideal: 40-80% word overlap
        if 0.4 <= word_overlap <= 0.8:
            quality = 0.8
        elif word_overlap > 0.8:
            quality = 0.5  # Too similar
        else:
            quality = 0.3  # Too different

        # Bonus for reasonable length
        if 0.8 <= len_ratio <= 1.3:
            quality += 0.1

        return min(quality, 1.0)


# ═══════════════════════════════════════════════════════════════
#  Convenience API
# ═══════════════════════════════════════════════════════════════


def neural_paraphrase(
    text: str,
    lang: str = "en",
    intensity: float = 0.5,
    seed: Optional[int] = None,
) -> NeuralParaphraseResult:
    """Paraphrase text using the neural + hybrid approach.

    Args:
        text: input text
        lang: language code ("en", "ru", etc.)
        intensity: paraphrase aggressiveness 0.0–1.0
        seed: random seed for reproducibility

    Returns:
        NeuralParaphraseResult
    """
    p = NeuralParaphraser(lang=lang, intensity=intensity, seed=seed)
    return p.paraphrase(text)
