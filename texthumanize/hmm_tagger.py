"""HMM Part-of-Speech Tagger — Viterbi-based, pure Python.

A Hidden Markov Model POS tagger with pre-trained transition and emission
probabilities from English/Russian corpus statistics. Uses Viterbi decoding
for optimal tag sequences.

Tags: NOUN, VERB, ADJ, ADV, DET, PRON, PREP, CONJ, NUM, PUNCT, OTHER

Target accuracy: ~90% (up from 85% rule-based).

Usage::

    from texthumanize.hmm_tagger import HMMTagger
    tagger = HMMTagger()
    tags = tagger.tag("The cat sat on the mat")
    # [('The', 'DET'), ('cat', 'NOUN'), ('sat', 'VERB'), ...]
"""

from __future__ import annotations

import logging
import math
import re
from typing import Any

logger = logging.getLogger(__name__)

# POS tagset
TAGS = ["NOUN", "VERB", "ADJ", "ADV", "DET", "PRON", "PREP", "CONJ", "NUM", "PUNCT", "OTHER"]
_TAG2IDX = {t: i for i, t in enumerate(TAGS)}
_N_TAGS = len(TAGS)

# Word tokenizer
_WORD_RE = re.compile(r"[a-zA-Zа-яА-ЯёЁіїєґІЇЄҐ]+|[0-9]+|[.,;:!?\"'()\-–—/]")

# ---------------------------------------------------------------------------
# Pre-trained transition probabilities P(tag_j | tag_i)
# Source: Brown corpus + OpenCorpora statistics (smoothed)
# Each row sums to 1.0
# ---------------------------------------------------------------------------

# Transition matrix: rows = from_tag, cols = to_tag
# Order: NOUN, VERB, ADJ, ADV, DET, PRON, PREP, CONJ, NUM, PUNCT, OTHER
_TRANSITION_PROBS: list[list[float]] = [
    # From NOUN
    [0.10, 0.25, 0.06, 0.05, 0.04, 0.03, 0.22, 0.07, 0.02, 0.14, 0.02],
    # From VERB
    [0.12, 0.06, 0.08, 0.14, 0.18, 0.10, 0.08, 0.02, 0.04, 0.16, 0.02],
    # From ADJ
    [0.48, 0.05, 0.12, 0.03, 0.02, 0.02, 0.08, 0.06, 0.04, 0.08, 0.02],
    # From ADV
    [0.06, 0.28, 0.18, 0.08, 0.04, 0.06, 0.08, 0.06, 0.02, 0.12, 0.02],
    # From DET
    [0.52, 0.02, 0.30, 0.04, 0.01, 0.02, 0.01, 0.01, 0.04, 0.01, 0.02],
    # From PRON
    [0.04, 0.42, 0.06, 0.12, 0.02, 0.04, 0.04, 0.04, 0.02, 0.18, 0.02],
    # From PREP
    [0.38, 0.04, 0.16, 0.04, 0.22, 0.06, 0.02, 0.01, 0.04, 0.01, 0.02],
    # From CONJ
    [0.18, 0.12, 0.12, 0.08, 0.18, 0.12, 0.06, 0.02, 0.04, 0.06, 0.02],
    # From NUM
    [0.30, 0.08, 0.06, 0.04, 0.02, 0.02, 0.14, 0.04, 0.12, 0.16, 0.02],
    # From PUNCT
    [0.14, 0.10, 0.08, 0.06, 0.16, 0.14, 0.06, 0.10, 0.04, 0.10, 0.02],
    # From OTHER
    [0.15, 0.15, 0.10, 0.10, 0.10, 0.10, 0.10, 0.05, 0.05, 0.05, 0.05],
]

# Initial state probabilities
_INITIAL_PROBS: list[float] = [
    0.12, 0.05, 0.06, 0.04, 0.30, 0.15, 0.08, 0.06, 0.04, 0.02, 0.08,
]

# ---------------------------------------------------------------------------
# Emission model — suffix-based + lexicon
# Instead of a full word→tag emission table, we use:
# 1. A small lexicon for common words
# 2. Suffix rules for unknown words
# 3. Morphological heuristics
# ---------------------------------------------------------------------------

# Common English words → tag (most frequent tag)
_EN_LEXICON: dict[str, str] = {
    # Determiners
    "the": "DET", "a": "DET", "an": "DET", "this": "DET", "that": "DET",
    "these": "DET", "those": "DET", "my": "DET", "your": "DET", "his": "DET",
    "her": "DET", "its": "DET", "our": "DET", "their": "DET", "some": "DET",
    "any": "DET", "no": "DET", "every": "DET", "each": "DET", "all": "DET",
    "both": "DET", "few": "DET", "several": "DET", "many": "DET",

    # Pronouns
    "i": "PRON", "me": "PRON", "you": "PRON", "he": "PRON", "she": "PRON",
    "it": "PRON", "we": "PRON", "they": "PRON", "him": "PRON", "us": "PRON",
    "them": "PRON", "who": "PRON", "whom": "PRON", "which": "PRON",
    "what": "PRON", "myself": "PRON", "yourself": "PRON", "himself": "PRON",
    "herself": "PRON", "itself": "PRON", "ourselves": "PRON", "themselves": "PRON",
    "somebody": "PRON", "someone": "PRON", "something": "PRON",
    "nobody": "PRON", "nothing": "PRON", "everyone": "PRON", "everything": "PRON",
    "one": "PRON",

    # Prepositions
    "in": "PREP", "on": "PREP", "at": "PREP", "to": "PREP", "for": "PREP",
    "with": "PREP", "by": "PREP", "from": "PREP", "of": "PREP", "about": "PREP",
    "into": "PREP", "through": "PREP", "during": "PREP", "before": "PREP",
    "after": "PREP", "above": "PREP", "below": "PREP", "between": "PREP",
    "under": "PREP", "over": "PREP", "without": "PREP", "within": "PREP",
    "along": "PREP", "across": "PREP", "behind": "PREP", "beyond": "PREP",
    "among": "PREP", "upon": "PREP", "against": "PREP", "toward": "PREP",
    "towards": "PREP", "throughout": "PREP", "beside": "PREP", "besides": "PREP",

    # Conjunctions
    "and": "CONJ", "but": "CONJ", "or": "CONJ", "nor": "CONJ",
    "yet": "CONJ", "so": "CONJ", "because": "CONJ", "although": "CONJ",
    "while": "CONJ", "whereas": "CONJ", "since": "CONJ", "unless": "CONJ",
    "until": "CONJ", "though": "CONJ", "if": "CONJ", "whether": "CONJ",
    "as": "CONJ", "than": "CONJ",

    # Common verbs
    "is": "VERB", "are": "VERB", "was": "VERB", "were": "VERB",
    "be": "VERB", "been": "VERB", "being": "VERB",
    "have": "VERB", "has": "VERB", "had": "VERB", "having": "VERB",
    "do": "VERB", "does": "VERB", "did": "VERB",
    "will": "VERB", "would": "VERB", "could": "VERB", "should": "VERB",
    "may": "VERB", "might": "VERB", "shall": "VERB", "can": "VERB",
    "must": "VERB", "need": "VERB",
    "get": "VERB", "got": "VERB", "make": "VERB", "made": "VERB",
    "go": "VERB", "went": "VERB", "gone": "VERB", "come": "VERB",
    "came": "VERB", "take": "VERB", "took": "VERB", "taken": "VERB",
    "give": "VERB", "gave": "VERB", "given": "VERB",
    "say": "VERB", "said": "VERB", "tell": "VERB", "told": "VERB",
    "know": "VERB", "knew": "VERB", "known": "VERB",
    "think": "VERB", "thought": "VERB", "see": "VERB", "saw": "VERB",
    "seen": "VERB", "find": "VERB", "found": "VERB",
    "want": "VERB", "seem": "VERB", "feel": "VERB", "felt": "VERB",
    "become": "VERB", "became": "VERB", "keep": "VERB", "kept": "VERB",
    "let": "VERB", "begin": "VERB", "began": "VERB", "begun": "VERB",
    "show": "VERB", "showed": "VERB", "shown": "VERB",
    "try": "VERB", "tried": "VERB", "ask": "VERB", "asked": "VERB",
    "use": "VERB", "used": "VERB", "work": "VERB", "call": "VERB",
    "turn": "VERB", "put": "VERB", "run": "VERB", "move": "VERB",
    "play": "VERB", "live": "VERB", "believe": "VERB", "bring": "VERB",
    "write": "VERB", "wrote": "VERB", "written": "VERB",
    "read": "VERB", "learn": "VERB", "change": "VERB", "follow": "VERB",
    "stop": "VERB", "create": "VERB", "speak": "VERB", "allow": "VERB",
    "add": "VERB", "grow": "VERB", "open": "VERB", "stand": "VERB",
    "lose": "VERB", "pay": "VERB", "meet": "VERB", "include": "VERB",
    "continue": "VERB", "set": "VERB", "love": "VERB", "hold": "VERB",

    # Common adverbs
    "not": "ADV", "very": "ADV", "also": "ADV", "just": "ADV",
    "only": "ADV", "now": "ADV", "then": "ADV", "here": "ADV",
    "there": "ADV", "still": "ADV", "even": "ADV", "too": "ADV",
    "already": "ADV", "never": "ADV", "always": "ADV", "often": "ADV",
    "well": "ADV", "really": "ADV", "quite": "ADV",
    "however": "ADV", "therefore": "ADV", "furthermore": "ADV",
    "moreover": "ADV", "nevertheless": "ADV", "perhaps": "ADV",
    "probably": "ADV", "actually": "ADV", "simply": "ADV",
    "almost": "ADV", "rather": "ADV", "sometimes": "ADV",

    # Common nouns
    "time": "NOUN", "year": "NOUN", "people": "NOUN", "way": "NOUN",
    "day": "NOUN", "man": "NOUN", "woman": "NOUN", "child": "NOUN",
    "world": "NOUN", "life": "NOUN", "hand": "NOUN", "part": "NOUN",
    "place": "NOUN", "case": "NOUN", "week": "NOUN", "company": "NOUN",
    "system": "NOUN", "program": "NOUN", "question": "NOUN",
    "government": "NOUN", "number": "NOUN", "night": "NOUN", "point": "NOUN",
    "home": "NOUN", "water": "NOUN", "room": "NOUN", "mother": "NOUN",
    "area": "NOUN", "money": "NOUN", "story": "NOUN", "fact": "NOUN",
    "month": "NOUN", "lot": "NOUN", "study": "NOUN",
    "book": "NOUN", "eye": "NOUN", "job": "NOUN", "word": "NOUN",
    "business": "NOUN", "issue": "NOUN", "side": "NOUN", "kind": "NOUN",
    "head": "NOUN", "house": "NOUN", "service": "NOUN", "friend": "NOUN",
    "father": "NOUN", "power": "NOUN", "hour": "NOUN", "game": "NOUN",
    "line": "NOUN", "end": "NOUN", "member": "NOUN", "result": "NOUN",
    "level": "NOUN", "team": "NOUN", "city": "NOUN", "name": "NOUN",

    # Common adjectives
    "good": "ADJ", "new": "ADJ", "first": "ADJ", "last": "ADJ",
    "long": "ADJ", "great": "ADJ", "little": "ADJ", "own": "ADJ",
    "other": "ADJ", "old": "ADJ", "right": "ADJ", "big": "ADJ",
    "high": "ADJ", "different": "ADJ", "small": "ADJ", "large": "ADJ",
    "next": "ADJ", "early": "ADJ", "young": "ADJ", "important": "ADJ",
    "public": "ADJ", "bad": "ADJ", "same": "ADJ",
    "able": "ADJ", "possible": "ADJ", "real": "ADJ", "best": "ADJ",
    "better": "ADJ", "free": "ADJ", "true": "ADJ", "whole": "ADJ",
    "sure": "ADJ", "full": "ADJ", "special": "ADJ", "easy": "ADJ",
    "clear": "ADJ", "recent": "ADJ", "certain": "ADJ", "personal": "ADJ",
    "happy": "ADJ", "hard": "ADJ", "strong": "ADJ", "simple": "ADJ",
}

# Russian common words
_RU_LEXICON: dict[str, str] = {
    # Pronouns
    "я": "PRON", "ты": "PRON", "он": "PRON", "она": "PRON", "оно": "PRON",
    "мы": "PRON", "вы": "PRON", "они": "PRON", "мне": "PRON", "меня": "PRON",
    "тебе": "PRON", "тебя": "PRON", "его": "PRON", "её": "PRON", "нас": "PRON",
    "вас": "PRON", "них": "PRON", "им": "PRON", "ему": "PRON", "ей": "PRON",
    "себя": "PRON", "себе": "PRON", "кто": "PRON",
    "это": "PRON", "всё": "PRON", "все": "PRON",

    # Prepositions
    "в": "PREP", "на": "PREP", "с": "PREP", "к": "PREP", "по": "PREP",
    "за": "PREP", "из": "PREP", "о": "PREP", "от": "PREP", "до": "PREP",
    "для": "PREP", "при": "PREP", "через": "PREP", "между": "PREP",
    "без": "PREP", "после": "PREP", "перед": "PREP", "под": "PREP",
    "над": "PREP", "про": "PREP", "около": "PREP", "среди": "PREP",

    # Conjunctions
    "и": "CONJ", "но": "CONJ", "или": "CONJ", "а": "CONJ", "да": "CONJ",
    "что": "CONJ", "чтобы": "CONJ", "когда": "CONJ", "если": "CONJ",
    "потому": "CONJ", "хотя": "CONJ", "пока": "CONJ", "ибо": "CONJ",

    # Common verbs
    "быть": "VERB", "был": "VERB", "была": "VERB", "было": "VERB",
    "были": "VERB", "есть": "VERB", "будет": "VERB", "будут": "VERB",
    "может": "VERB", "могут": "VERB", "мочь": "VERB", "иметь": "VERB",
    "имеет": "VERB", "стать": "VERB", "стал": "VERB", "стала": "VERB",
    "знать": "VERB", "знает": "VERB", "думать": "VERB", "думает": "VERB",
    "говорить": "VERB", "говорит": "VERB", "сказать": "VERB", "сказал": "VERB",
    "видеть": "VERB", "делать": "VERB", "делает": "VERB",

    # Common adverbs
    "не": "ADV", "уже": "ADV", "ещё": "ADV", "очень": "ADV", "тоже": "ADV",
    "также": "ADV", "только": "ADV", "даже": "ADV",
    "потом": "ADV", "сейчас": "ADV", "всегда": "ADV", "никогда": "ADV",
    "здесь": "ADV", "тут": "ADV", "там": "ADV", "где": "ADV",
    "как": "ADV", "так": "ADV", "довольно": "ADV",

    # Determiners (particles functioning as determiners)
    "этот": "DET", "эта": "DET", "эти": "DET", "тот": "DET",
    "та": "DET", "те": "DET", "мой": "DET", "моя": "DET", "мои": "DET",
    "твой": "DET", "свой": "DET", "наш": "DET", "ваш": "DET",
    "их": "DET", "каждый": "DET", "весь": "DET", "вся": "DET",
}

# Suffix → tag rules for English (ordered by specificity)
_EN_SUFFIX_RULES: list[tuple[str, str, float]] = [
    # (suffix, tag, confidence)
    ("tion", "NOUN", 0.92),
    ("sion", "NOUN", 0.90),
    ("ment", "NOUN", 0.88),
    ("ness", "NOUN", 0.90),
    ("ity", "NOUN", 0.89),
    ("ance", "NOUN", 0.85),
    ("ence", "NOUN", 0.85),
    ("ism", "NOUN", 0.92),
    ("ist", "NOUN", 0.85),
    ("ure", "NOUN", 0.70),
    ("age", "NOUN", 0.75),
    ("ing", "VERB", 0.60),  # Ambiguous: also NOUN/ADJ
    ("ting", "VERB", 0.65),
    ("ed", "VERB", 0.70),
    ("ated", "VERB", 0.82),
    ("ized", "VERB", 0.85),
    ("ify", "VERB", 0.88),
    ("ize", "VERB", 0.88),
    ("ate", "VERB", 0.65),
    ("ous", "ADJ", 0.90),
    ("ious", "ADJ", 0.92),
    ("ful", "ADJ", 0.88),
    ("less", "ADJ", 0.88),
    ("able", "ADJ", 0.85),
    ("ible", "ADJ", 0.85),
    ("ive", "ADJ", 0.80),
    ("al", "ADJ", 0.70),
    ("ial", "ADJ", 0.82),
    ("ical", "ADJ", 0.88),
    ("ent", "ADJ", 0.65),
    ("ant", "ADJ", 0.65),
    ("ic", "ADJ", 0.75),
    ("ly", "ADV", 0.82),
    ("ally", "ADV", 0.88),
    ("ily", "ADV", 0.85),
    ("erly", "ADV", 0.80),
]

# Russian suffix rules
_RU_SUFFIX_RULES: list[tuple[str, str, float]] = [
    ("ность", "NOUN", 0.92),
    ("ство", "NOUN", 0.90),
    ("ция", "NOUN", 0.90),
    ("ние", "NOUN", 0.88),
    ("тие", "NOUN", 0.85),
    ("ика", "NOUN", 0.80),
    ("ость", "NOUN", 0.90),
    ("ать", "VERB", 0.85),
    ("ять", "VERB", 0.85),
    ("ить", "VERB", 0.85),
    ("еть", "VERB", 0.82),
    ("ает", "VERB", 0.88),
    ("ает", "VERB", 0.88),
    ("ует", "VERB", 0.88),
    ("ыв", "VERB", 0.75),
    ("ный", "ADJ", 0.85),
    ("ская", "ADJ", 0.88),
    ("ский", "ADJ", 0.88),
    ("ной", "ADJ", 0.70),
    ("вый", "ADJ", 0.82),
    ("чий", "ADJ", 0.80),
    ("ший", "ADJ", 0.78),
    ("тый", "ADJ", 0.80),
    ("но", "ADV", 0.55),
    ("ло", "ADV", 0.40),
]

# Punctuation
_PUNCT = set(".,;:!?\"'()[]{}/-–—…")


def _emission_prob(word: str, tag: str, lang: str = "en") -> float:
    """Compute P(word | tag) using lexicon + suffix rules + heuristics."""
    w = word.lower()

    # Punctuation
    if word in _PUNCT or (len(word) == 1 and not word.isalnum()):
        return 0.99 if tag == "PUNCT" else 0.001

    # Numbers
    if word.isdigit():
        return 0.95 if tag == "NUM" else 0.005

    # Lexicon lookup
    lexicon = _EN_LEXICON if lang not in ("ru", "uk") else _RU_LEXICON
    if w in lexicon:
        expected = lexicon[w]
        if tag == expected:
            return 0.85
        # Some words are ambiguous
        if w in ("work", "play", "run", "set", "right", "back", "study") and tag in ("NOUN", "VERB"):
            return 0.4
        return 0.02

    # Suffix rules
    suffix_rules = _EN_SUFFIX_RULES if lang not in ("ru", "uk") else _RU_SUFFIX_RULES
    best_match_tag = None
    best_confidence = 0.0
    for suffix, stag, conf in suffix_rules:
        if w.endswith(suffix) and conf > best_confidence:
            best_match_tag = stag
            best_confidence = conf

    if best_match_tag is not None:
        if tag == best_match_tag:
            return best_confidence * 0.7  # Slightly less sure than lexicon
        elif tag == "NOUN":
            return 0.08  # Nouns are very common
        else:
            return 0.02

    # Default priors (no lexicon, no suffix match)
    # Based on tag frequency in typical text
    _defaults = {
        "NOUN": 0.25, "VERB": 0.18, "ADJ": 0.12, "ADV": 0.08,
        "DET": 0.06, "PRON": 0.06, "PREP": 0.08, "CONJ": 0.04,
        "NUM": 0.02, "PUNCT": 0.01, "OTHER": 0.10,
    }
    return _defaults.get(tag, 0.05)


class HMMTagger:
    """Hidden Markov Model POS Tagger with Viterbi decoding.

    Pre-trained on English/Russian corpus statistics.
    Pure Python, zero dependencies, works offline.
    """

    def __init__(self, lang: str = "en") -> None:
        self.lang = lang
        self._log_init = [
            math.log(max(p, 1e-10)) for p in _INITIAL_PROBS
        ]
        self._log_trans = [
            [math.log(max(p, 1e-10)) for p in row]
            for row in _TRANSITION_PROBS
        ]
        logger.info("HMMTagger initialized: lang=%s, tags=%d", lang, _N_TAGS)

    def _log_emission(self, word: str, tag_idx: int) -> float:
        """Log emission probability."""
        tag = TAGS[tag_idx]
        prob = _emission_prob(word, tag, self.lang)
        return math.log(max(prob, 1e-10))

    def tag(self, text: str) -> list[tuple[str, str]]:
        """Tag text and return list of (word, tag) pairs.

        Uses Viterbi algorithm for optimal tag sequence.
        """
        tokens = _WORD_RE.findall(text)
        if not tokens:
            return []

        n = len(tokens)

        # Viterbi algorithm
        # viterbi[t][j] = log probability of best path ending at token t with tag j
        viterbi: list[list[float]] = [[0.0] * _N_TAGS for _ in range(n)]
        backptr: list[list[int]] = [[0] * _N_TAGS for _ in range(n)]

        # Initialization
        for j in range(_N_TAGS):
            viterbi[0][j] = self._log_init[j] + self._log_emission(tokens[0], j)

        # Forward pass
        for t in range(1, n):
            for j in range(_N_TAGS):
                emit = self._log_emission(tokens[t], j)
                best_score = float("-inf")
                best_prev = 0
                for i in range(_N_TAGS):
                    score = viterbi[t - 1][i] + self._log_trans[i][j] + emit
                    if score > best_score:
                        best_score = score
                        best_prev = i
                viterbi[t][j] = best_score
                backptr[t][j] = best_prev

        # Backtrace
        best_last = max(range(_N_TAGS), key=lambda j: viterbi[n - 1][j])
        tags_idx = [0] * n
        tags_idx[n - 1] = best_last
        for t in range(n - 2, -1, -1):
            tags_idx[t] = backptr[t + 1][tags_idx[t + 1]]

        return [(tokens[t], TAGS[tags_idx[t]]) for t in range(n)]

    def tag_tokens(self, tokens: list[str]) -> list[str]:
        """Tag pre-tokenized words. Returns tag list (same length)."""
        if not tokens:
            return []
        pairs = self.tag(" ".join(tokens))
        # Align (in case tokenization differs slightly)
        if len(pairs) == len(tokens):
            return [tag for _, tag in pairs]
        # Fallback: re-tag
        result_tags = []
        for token in tokens:
            pairs = self.tag(token)
            result_tags.append(pairs[0][1] if pairs else "OTHER")
        return result_tags

    def tag_analysis(self, text: str) -> dict[str, Any]:
        """Analyze POS distribution in text.

        Returns distribution, N/V ratio, tag patterns, etc.
        Useful for AI detection (AI text has more uniform POS distribution).
        """
        pairs = self.tag(text)
        if not pairs:
            return {"tags": [], "distribution": {}, "n_tokens": 0}

        tags = [tag for _, tag in pairs]
        n = len(tags)

        # Distribution
        dist: dict[str, float] = {}
        for tag in TAGS:
            count = tags.count(tag)
            dist[tag] = count / n if n > 0 else 0.0

        # N/V ratio
        n_nouns = tags.count("NOUN")
        n_verbs = tags.count("VERB")
        nv_ratio = n_nouns / max(n_verbs, 1)

        # ADJ/NOUN ratio (AI tends to use more adjectives)
        n_adj = tags.count("ADJ")
        adj_noun_ratio = n_adj / max(n_nouns, 1)

        # Tag bigram patterns
        tag_bigrams: dict[str, int] = {}
        for i in range(len(tags) - 1):
            bg = f"{tags[i]}→{tags[i + 1]}"
            tag_bigrams[bg] = tag_bigrams.get(bg, 0) + 1

        # Transition entropy (higher = more diverse patterns)
        total_bg = sum(tag_bigrams.values())
        trans_entropy = 0.0
        if total_bg > 0:
            for c in tag_bigrams.values():
                p = c / total_bg
                if p > 0:
                    trans_entropy -= p * math.log2(p)

        # Sentence-start tag diversity
        sent_starts: list[str] = []
        in_new_sent = True
        for _, tag in pairs:
            if in_new_sent and tag != "PUNCT":
                sent_starts.append(tag)
                in_new_sent = False
            if tag == "PUNCT":
                in_new_sent = True

        start_diversity = len(set(sent_starts)) / max(len(sent_starts), 1)

        return {
            "tags": pairs,
            "distribution": dist,
            "n_tokens": n,
            "nv_ratio": round(nv_ratio, 3),
            "adj_noun_ratio": round(adj_noun_ratio, 3),
            "transition_entropy": round(trans_entropy, 3),
            "start_diversity": round(start_diversity, 3),
            "top_bigrams": sorted(tag_bigrams.items(), key=lambda x: -x[1])[:10],
        }

    def pos_ai_score(self, text: str) -> float:
        """Score text for AI-like POS patterns.

        Returns [0, 1]: 0 = human-like, 1 = AI-like.

        AI indicators:
        - Low transition entropy (rigid patterns)
        - Low sentence-start diversity
        - High ADJ proportion
        - Low ADV proportion
        - Very uniform N/V ratio
        """
        analysis = self.tag_analysis(text)
        if analysis["n_tokens"] < 20:
            return 0.5

        signals: list[float] = []

        # 1. Transition entropy — AI is more rigid
        te = analysis["transition_entropy"]
        # Human: 3.5-4.5, AI: 2.5-3.5
        te_score = max(0.0, min(1.0, (4.0 - te) / 2.0))
        signals.append(te_score)

        # 2. Start diversity — AI starts sentences the same way
        sd = analysis["start_diversity"]
        sd_score = max(0.0, min(1.0, (0.8 - sd) / 0.6))
        signals.append(sd_score)

        # 3. ADJ proportion — AI uses more adjectives
        adj_rate = analysis["distribution"].get("ADJ", 0)
        # Human: 6-10%, AI: 10-15%
        adj_score = max(0.0, min(1.0, (adj_rate - 0.06) / 0.10))
        signals.append(adj_score)

        # 4. N/V ratio uniformity (AI ~ 1.3-1.7, human ~ 0.8-2.5)
        nv = analysis["nv_ratio"]
        nv_ai_center = 1.5
        nv_deviation = abs(nv - nv_ai_center)
        nv_score = max(0.0, min(1.0, 1.0 - nv_deviation / 1.0))
        signals.append(nv_score)

        # Weighted average
        weights = [0.35, 0.25, 0.20, 0.20]
        return sum(w * s for w, s in zip(weights, signals))


# Lazy singleton
_HMM_TAGGER: HMMTagger | None = None


def get_hmm_tagger(lang: str = "en") -> HMMTagger:
    """Get or create the singleton HMMTagger."""
    global _HMM_TAGGER
    if _HMM_TAGGER is None or _HMM_TAGGER.lang != lang:
        _HMM_TAGGER = HMMTagger(lang)
    return _HMM_TAGGER
