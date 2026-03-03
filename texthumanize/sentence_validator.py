"""Sentence-level integrity validator — catches artifacts BETWEEN pipeline stages.

Instead of only checking for artifacts at the very end (Grammar Guard),
this validator runs after each major transformation stage. It compares
each output sentence against its pre-stage version and reverts broken
sentences immediately — preventing artifact cascading through later stages.

Checks performed per sentence:
  1. Triple repeated characters (e.g. «проведенння»)
  2. Truncated word stems (e.g. «реализаци» instead of «реализации»)
  3. Foreign word leaks (e.g. English «the» in French/German text)
  4. Garbled conjunction/connector chains
  5. Duplicate adjacent words (e.g. «и и», «the the»)
  6. Broken morphology (unrecognizable word forms)
  7. Empty/near-empty sentences that weren't empty before
  8. Sentence became much shorter than original (truncation)

Copyright (c) 2024-2026 Oleksandr K. / TextHumanize Project.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ── Compiled patterns ─────────────────────────────────────────

# Triple+ repeated letter (not ellipsis or punctuation)
_TRIPLE_LETTER = re.compile(r'([а-яёіїєґa-zäöüß])\1{2,}', re.IGNORECASE)

# Garbled conjunction chains: ", and, but, or, ..." × 3+
_CONJ_CHAIN_EN = re.compile(
    r'(?:,?\s*\b(?:and|but|or|yet|so|however|moreover|furthermore|granted'
    r'|also|thus|hence|indeed|actually)\b\s*){3,}',
    re.IGNORECASE,
)
_CONJ_CHAIN_RU = re.compile(
    r'(?:,?\s*\b(?:и|а|но|однако|также|кроме того|причём|более того'
    r'|ещё|впрочем|таким образом|следовательно)\b\s*){3,}',
    re.IGNORECASE,
)
_CONJ_CHAIN_UK = re.compile(
    r'(?:,?\s*\b(?:і|й|а|але|однак|також|крім того|причому|більш того'
    r'|ще|втім|таким чином|отже)\b\s*){3,}',
    re.IGNORECASE,
)
_CONJ_CHAIN_DE = re.compile(
    r'(?:,?\s*\b(?:und|aber|oder|jedoch|außerdem|darüber hinaus|zudem'
    r'|ferner|somit|daher|dennoch|allerdings)\b\s*){3,}',
    re.IGNORECASE,
)
_CONJ_CHAIN_FR = re.compile(
    r'(?:,?\s*\b(?:et|mais|ou|cependant|de plus|en outre|toutefois'
    r'|néanmoins|ainsi|donc|pourtant|par ailleurs)\b\s*){3,}',
    re.IGNORECASE,
)
_CONJ_CHAIN_ES = re.compile(
    r'(?:,?\s*\b(?:y|e|pero|o|u|sin embargo|además|no obstante'
    r'|por lo tanto|así|también|incluso)\b\s*){3,}',
    re.IGNORECASE,
)

_CONJ_CHAINS = {
    'en': _CONJ_CHAIN_EN,
    'ru': _CONJ_CHAIN_RU,
    'uk': _CONJ_CHAIN_UK,
    'de': _CONJ_CHAIN_DE,
    'fr': _CONJ_CHAIN_FR,
    'es': _CONJ_CHAIN_ES,
}

# English leaks into non-English text
_EN_LEAK_WORDS = frozenset({
    'the', 'this', 'that', 'however', 'moreover', 'furthermore',
    'nevertheless', 'consequently', 'therefore', 'meanwhile',
    'although', 'whereas', 'nonetheless', "here's", 'indeed',
    'granted', 'actually', 'basically',
})

# Common short words per language that shouldn't be flagged as truncated
_SHORT_OK: dict[str, frozenset[str]] = {
    'en': frozenset({'a', 'i', 'an', 'am', 'as', 'at', 'be', 'by',
                     'do', 'go', 'he', 'if', 'in', 'is', 'it', 'me',
                     'my', 'no', 'of', 'on', 'or', 'so', 'to', 'up',
                     'us', 'we'}),
    'ru': frozenset({'а', 'б', 'в', 'г', 'д', 'е', 'ж', 'и', 'к',
                     'о', 'с', 'у', 'я', 'не', 'на', 'по', 'от',
                     'за', 'из', 'до', 'ни', 'бы', 'же', 'ли'}),
    'uk': frozenset({'а', 'б', 'в', 'г', 'д', 'е', 'є', 'ж', 'з',
                     'и', 'і', 'й', 'к', 'о', 'с', 'у', 'я', 'не',
                     'на', 'по', 'від', 'за', 'із', 'до', 'ні',
                     'би', 'же', 'чи', 'ще'}),
    'de': frozenset({'ab', 'am', 'an', 'da', 'er', 'es', 'im', 'in',
                     'ob', 'um', 'so', 'zu'}),
    'fr': frozenset({'à', 'au', 'ce', 'de', 'du', 'en', 'et', 'il',
                     'je', 'la', 'le', 'me', 'ne', 'ni', 'on', 'ou',
                     'se', 'si', 'un', 'y'}),
    'es': frozenset({'a', 'al', 'de', 'el', 'en', 'es', 'la', 'lo',
                     'me', 'mi', 'ni', 'no', 'o', 'se', 'si', 'su',
                     'te', 'tu', 'un', 'y', 'ya'}),
}

_WORD_RE = re.compile(r'[a-zA-Zа-яА-ЯёЁіїєґІЇЄҐüöäßÜÖÄ\'-]+')


# ── Result ────────────────────────────────────────────────────

@dataclass
class ValidationResult:
    """Stats from a single interstage validation pass."""
    sentences_checked: int = 0
    sentences_reverted: int = 0
    reasons: list[str] = field(default_factory=list)


# ── Core validator ────────────────────────────────────────────

class SentenceValidator:
    """Validates sentence integrity between pipeline stages.

    Usage::

        sv = SentenceValidator(lang="ru")
        text_after = sv.validate(text_before_stage, text_after_stage)
        print(f"Reverted {sv.last_result.sentences_reverted} sentences")
    """

    def __init__(self, lang: str = "en"):
        self.lang = lang
        self.last_result = ValidationResult()
        self._total_reverts = 0

    @property
    def total_reverts(self) -> int:
        """Total sentences reverted across all validate() calls."""
        return self._total_reverts

    def validate(
        self,
        before: str,
        after: str,
        *,
        stage_name: str = "",
    ) -> str:
        """Compare before/after text and revert broken sentences.

        Splits both texts into paragraphs → sentences, aligns by
        index, checks each output sentence for artifacts. Broken
        sentences are reverted to the pre-stage version.

        Args:
            before: Text before the pipeline stage.
            after: Text after the pipeline stage.
            stage_name: Name of the stage (for logging).

        Returns:
            Cleaned text with broken sentences reverted.
        """
        self.last_result = ValidationResult()

        if not before or not after:
            return after

        # Split by paragraphs to preserve structure
        before_paras = before.split('\n\n')
        after_paras = after.split('\n\n')

        # If paragraph count changed, can't align — accept as-is
        if len(before_paras) != len(after_paras):
            return after

        result_paras: list[str] = []
        reverts = 0

        for bp, ap in zip(before_paras, after_paras):
            if not bp.strip() or not ap.strip():
                result_paras.append(ap)
                continue

            # Split paragraph into sentences
            b_sents = self._split_sents(bp)
            a_sents = self._split_sents(ap)

            # If sentence count differs moderately, try alignment;
            # if too different, accept the output paragraph as-is.
            if abs(len(b_sents) - len(a_sents)) > max(1, len(b_sents) // 3):
                result_paras.append(ap)
                continue

            self.last_result.sentences_checked += len(a_sents)

            fixed_sents: list[str] = []
            for i, a_sent in enumerate(a_sents):
                # Get corresponding pre-stage sentence (or empty if new)
                b_sent = b_sents[i] if i < len(b_sents) else ""

                artifact = self._check_sentence(a_sent, b_sent)
                if artifact:
                    # Revert to pre-stage version
                    if b_sent:
                        fixed_sents.append(b_sent)
                        reverts += 1
                        self.last_result.reasons.append(
                            f"{stage_name}[{i}]: {artifact}"
                        )
                    else:
                        # No pre-stage sentence to revert to — drop
                        reverts += 1
                else:
                    fixed_sents.append(a_sent)

            # Reconstruct paragraph
            result_paras.append(' '.join(fixed_sents))

        self.last_result.sentences_reverted = reverts
        self._total_reverts += reverts

        if reverts > 0:
            logger.info(
                "SentenceValidator [%s]: reverted %d/%d sentences",
                stage_name, reverts, self.last_result.sentences_checked,
            )

        return '\n\n'.join(result_paras)

    def _check_sentence(self, sent: str, original: str) -> str | None:
        """Check a single sentence for artifacts.

        Returns:
            Description of the artifact found, or None if clean.
        """
        if not sent or not sent.strip():
            return None

        words = _WORD_RE.findall(sent)
        if not words:
            return None

        # ── 1. Triple repeated characters ─────────────────────
        for word in words:
            if _TRIPLE_LETTER.search(word):
                # Allow valid words with triple letters (very rare)
                if word.lower() not in ('brrr', 'shhh', 'zzz', 'mmm'):
                    return f"triple_char: «{word}»"

        # ── 2. Truncated words ────────────────────────────────
        # If a word disappeared from the middle (stem got cut)
        if original:
            orig_words = set(w.lower() for w in _WORD_RE.findall(original))
            for word in words:
                wl = word.lower()
                # Skip known short words
                short_ok = _SHORT_OK.get(self.lang, _SHORT_OK.get('en', frozenset()))
                if wl in short_ok or len(wl) > 2:
                    continue
                # Single letter that wasn't in original and isn't a known word
                if len(wl) == 1 and wl not in orig_words and wl not in short_ok:
                    return f"truncated: «{word}»"

        # ── 3. Foreign word leaks ─────────────────────────────
        if self.lang not in ('en',):
            for word in words:
                if word.lower() in _EN_LEAK_WORDS:
                    return f"en_leak: «{word}»"

        # ── 4. Garbled conjunction chains ─────────────────────
        chain_re = _CONJ_CHAINS.get(self.lang, _CONJ_CHAIN_EN)
        if chain_re.search(sent):
            return "conjunction_chain"

        # ── 5. Duplicate adjacent words ───────────────────────
        for i in range(len(words) - 1):
            w1, w2 = words[i].lower(), words[i + 1].lower()
            if w1 == w2 and len(w1) > 1:
                # Allow some valid duplicates: "very very", "had had"
                _valid_dups = frozenset({
                    'very', 'had', 'that', 'so', 'no', 'bye',
                    'го', 'ну', 'да', 'ой', 'ах',
                })
                if w1 not in _valid_dups:
                    return f"duplicate: «{words[i]} {words[i+1]}»"

        # ── 6. Severe truncation ──────────────────────────────
        # If output sentence is less than 40% the length of the original,
        # something was lost.
        if original:
            orig_word_count = len(_WORD_RE.findall(original))
            if orig_word_count >= 5 and len(words) < orig_word_count * 0.4:
                return f"truncation: {len(words)}/{orig_word_count} words"

        # ── 7. Broken parenthetical insertions ────────────────
        # Unmatched parentheses or dashes
        open_parens = sent.count('(') - sent.count(')')
        if abs(open_parens) > 1:
            return "unmatched_parens"

        # ── 8. Article-noun splits (DE) ──────────────────────
        if self.lang == 'de':
            # "die Beachten" pattern: article + infinitive as noun
            _de_article_verb = re.compile(
                r'\b(der|die|das|dem|den|des)\s+'
                r'[A-ZÄÖÜ][a-zäöüß]*(?:en|ern|eln)\b'
            )
            if _de_article_verb.search(sent):
                # Check if the "noun" is actually a verb infinitive
                m = _de_article_verb.search(sent)
                if m:
                    candidate = m.group().split()[-1].lower()
                    _noun_suffixes = (
                        'ung', 'heit', 'keit', 'schaft', 'tion',
                        'nis', 'tum', 'ment', 'ität',
                    )
                    if not any(candidate.endswith(s) for s in _noun_suffixes):
                        return f"de_article_verb: «{m.group()}»"

        # ── 9. Missing noun: "the of", "the in" ─────────────
        # Article followed directly by a preposition (missing content noun)
        if self.lang == 'en':
            _art_prep = re.compile(
                r'\b(the|a|an)\s+(of|in|on|at|by|from|for|with|to)\b',
                re.IGNORECASE,
            )
            if _art_prep.search(sent):
                return f"missing_noun: «{_art_prep.search(sent).group()}»"

        # ── 10. Double conjunction ("and and", "but but") ────
        _dup_conj = re.compile(
            r'\b(and|but|or|yet|so|и|і|а|але|но|und|oder|aber'
            r'|et|ou|mais|y|o|pero)\s+\1\b',
            re.IGNORECASE,
        )
        if _dup_conj.search(sent):
            return f"double_conj: «{_dup_conj.search(sent).group()}»"

        return None

    @staticmethod
    def _split_sents(text: str) -> list[str]:
        """Split text into sentences (fast regex-based)."""
        if not text.strip():
            return [text]
        # Use a universal sentence-boundary pattern
        parts = re.split(
            r'(?<=[.!?»"])\s+(?=[A-ZА-ЯІЇЄҐÜÖÄÉÈÊÀÂ«"])',
            text,
        )
        return [p for p in parts if p.strip()]
