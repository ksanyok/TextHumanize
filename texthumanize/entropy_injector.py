"""Entropy & burstiness injector — Phase 1 humanization.

Targets core statistical signals that AI detectors look for:
1. Sentence-length distribution → reshape to log-normal (human-like)
2. Burstiness → inject variance in sentence lengths (CV > 0.5)
3. Cadence → alternate long/short sentences instead of uniform
4. Word-level surprise → insert discourse markers, fragments,
   parentheticals to raise token-level entropy

Works for all languages, no external dependencies.
"""

from __future__ import annotations

import math
import random
import re
from typing import Optional

from texthumanize.sentence_split import split_sentences


class EntropyInjector:
    """Inject human-like entropy and burstiness into text.

    This module addresses the two strongest AI detection signals:
    - Low burstiness (uniform sentence lengths)
    - Low perplexity (predictable word sequences)

    Parameters
    ----------
    lang : str
        Language code (affects discourse markers, merging logic).
    intensity : float
        0-100, controls aggressiveness of transformations.
    seed : int or None
        Random seed for reproducibility.
    profile : str
        Text profile ('chat', 'web', 'seo', 'docs', 'formal').
    """

    __slots__ = ("_lang", "_intensity", "_rng", "_profile", "_changes")

    def __init__(
        self,
        lang: str = "en",
        intensity: float = 50.0,
        seed: Optional[int] = None,
        profile: str = "web",
    ) -> None:
        self._lang = lang
        self._intensity = max(0.0, min(100.0, intensity))
        self._rng = random.Random(seed)
        self._profile = profile
        self._changes: list[dict] = []

    @property
    def changes(self) -> list[dict]:
        """Return list of changes made."""
        return self._changes

    def process(self, text: str) -> str:
        """Apply entropy and burstiness injection.

        Returns transformed text with more human-like statistical properties.
        Preserves paragraph boundaries (newlines).
        """
        self._changes = []
        if not text or len(text.strip()) < 50:
            return text

        # Process each paragraph independently to preserve structure
        paragraphs = text.split("\n")
        result_paragraphs = []

        for para in paragraphs:
            if not para.strip():
                result_paragraphs.append(para)
                continue

            sentences = self._split_sentences(para)
            if len(sentences) < 3:
                result_paragraphs.append(para)
                continue

            # Step 1: Measure current burstiness
            lengths = [len(s.split()) for s in sentences]
            mean_len = sum(lengths) / len(lengths) if lengths else 0
            if mean_len <= 0:
                result_paragraphs.append(para)
                continue
            std_len = (sum((x - mean_len) ** 2 for x in lengths) / len(lengths)) ** 0.5
            cv = std_len / mean_len

            # Step 2: Target CV based on profile
            target_cv = self._get_target_cv()
            prob = self._intensity / 100.0

            # Step 3: If CV is too low (too uniform = AI-like), inject burstiness
            if cv < target_cv * 0.85:
                sentences = self._inject_burstiness(sentences, target_cv, prob)
                self._changes.append({
                    "type": "burstiness_injection",
                    "description": f"Burstiness: CV {cv:.2f} → target {target_cv:.2f}",
                })

            # Step 4: Cadence variation (break monotonic long→long runs)
            sentences = self._inject_cadence(sentences, prob)

            # Step 5: Discourse surprise injection (raise token entropy)
            if self._intensity >= 30:
                sentences = self._inject_discourse_surprise(sentences, prob)

            result_paragraphs.append(self._join_sentences(sentences))

        return "\n".join(result_paragraphs)

    # ── Burstiness injection ──────────────────────────────────

    def _inject_burstiness(
        self,
        sentences: list[str],
        target_cv: float,
        prob: float,
    ) -> list[str]:
        """Reshape sentence lengths toward target CV.

        Strategy:
        - Split sentences that are too close to the mean (reduce uniformity)
        - Merge some short adjacent sentences
        - Occasionally create very short fragment sentences
        """
        result = []
        i = 0
        while i < len(sentences):
            sent = sentences[i]
            words = sent.split()
            n = len(words)
            avg = self._avg_length(sentences)

            # Split long uniform sentences (close to mean)
            if n > 8 and abs(n - avg) < avg * 0.2 and self._rng.random() < prob * 0.4:
                split_result = self._split_sentence(sent)
                if split_result:
                    result.extend(split_result)
                    self._changes.append({
                        "type": "sentence_split",
                        "description": f"Split {n}-word sentence for burstiness",
                    })
                    i += 1
                    continue

            # Merge short adjacent sentences
            if (n <= 6 and i + 1 < len(sentences)
                    and len(sentences[i + 1].split()) <= 8
                    and self._rng.random() < prob * 0.3):
                merged = self._merge_sentences(sent, sentences[i + 1])
                if merged:
                    result.append(merged)
                    self._changes.append({
                        "type": "sentence_merge",
                        "description": f"Merged {n}+{len(sentences[i+1].split())}-word sentences",
                    })
                    i += 2
                    continue

            result.append(sent)
            i += 1

        return result

    def _split_sentence(self, sent: str) -> Optional[list[str]]:
        """Split a sentence at natural breakpoints."""
        words = sent.split()
        n = len(words)
        if n < 10:
            return None

        # Look for conjunction/transition split points
        # NEVER split on relative pronouns (which, where, который, etc.)
        # — they create invalid sentence fragments
        split_words_en = {
            "and", "but", "while", "whereas", "although",
            "because", "since", "however",
        }
        split_words_ru = {
            "и", "но", "а", "однако", "хотя", "потому",
            "поскольку", "причём",
        }
        split_words_de = {
            "und", "aber", "während", "obwohl", "weil",
            "da", "jedoch",
        }
        split_words_fr = {
            "et", "mais", "tandis", "bien", "parce",
            "puisque", "cependant",
        }
        split_words_es = {
            "y", "pero", "mientras", "aunque", "porque",
            "sin", "embargo",
        }

        split_words_uk = {
            "і", "але", "а", "однак", "хоча", "тому",
            "оскільки", "причому",
        }

        split_candidates = split_words_en
        if self._lang == "ru":
            split_candidates = split_words_ru
        elif self._lang == "uk":
            split_candidates = split_words_uk
        elif self._lang == "de":
            split_candidates = split_words_de
        elif self._lang == "fr":
            split_candidates = split_words_fr
        elif self._lang == "es":
            split_candidates = split_words_es

        # Find split points in middle third
        start = n // 3
        end = (2 * n) // 3
        best_split = None

        for j in range(start, end):
            w = words[j].lower().rstrip(".,;:")
            if w in split_candidates:
                best_split = j
                break

        # Also look for comma-separated clauses
        if best_split is None:
            for j in range(start, end):
                if words[j].endswith(","):
                    best_split = j + 1
                    break

        if best_split is None:
            return None

        first = " ".join(words[:best_split]).rstrip(",;:")
        second = " ".join(words[best_split:])

        # Ensure first part has sentence-ending punctuation
        if first and not first[-1] in ".!?":
            first += "."
        # Capitalize second part
        if second:
            second = second[0].upper() + second[1:]

        # Validate both parts are substantial
        if len(first.split()) < 3 or len(second.split()) < 3:
            return None

        return [first, second]

    def _merge_sentences(self, s1: str, s2: str) -> Optional[str]:
        """Merge two short sentences naturally."""
        s1 = s1.rstrip()
        s2 = s2.strip()
        if not s1 or not s2:
            return None

        # Remove trailing sentence-end punctuation from first sentence
        if s1 and s1[-1] in ".!?":
            s1 = s1[:-1]

        # Choose connector based on language
        connectors = self._get_merge_connectors()
        connector = self._rng.choice(connectors)

        # Lowercase start of second sentence (but not proper nouns/acronyms)
        if s2 and s2[0].isupper() and not s2.split()[0].isupper() and not (len(s2) > 1 and s2[1:2].isupper()):
            s2 = s2[0].lower() + s2[1:]

        return f"{s1}{connector}{s2}"

    def _get_merge_connectors(self) -> list[str]:
        """Get natural sentence connectors for merging."""
        if self._lang == "ru":
            return [", и ", ", а ", " — ", ", причём "]
        if self._lang == "uk":
            return [", і ", ", а ", " — ", ", причому "]
        if self._lang == "de":
            return [", und ", ", aber ", " — ", ", wobei "]
        if self._lang == "fr":
            return [", et ", ", mais ", " — ", ", car "]
        if self._lang == "es":
            return [", y ", ", pero ", " — ", ", ya que "]
        if self._lang == "it":
            return [", e ", ", ma ", " — ", ", poiché "]
        if self._lang == "pl":
            return [", i ", ", ale ", " — ", ", gdyż "]
        if self._lang == "pt":
            return [", e ", ", mas ", " — ", ", pois "]
        # English default
        return [", and ", ", but ", " — ", ", since "]

    # ── Cadence variation ─────────────────────────────────────

    def _inject_cadence(
        self,
        sentences: list[str],
        prob: float,
    ) -> list[str]:
        """Break monotonic long-sentence runs with short fragments.

        Human writing has cadence: long→short→medium→long→very_short.
        AI tends to produce uniform medium-length sentences.
        """
        result = []
        consecutive_medium = 0

        for sent in sentences:
            words = sent.split()
            n = len(words)
            avg = self._avg_length(sentences)

            # Track consecutive "medium" sentences (close to average)
            if abs(n - avg) < avg * 0.25:
                consecutive_medium += 1
            else:
                consecutive_medium = 0

            result.append(sent)

            # After 3+ consecutive medium sentences, inject a short fragment
            if consecutive_medium >= 3 and self._rng.random() < prob * 0.35:
                fragment = self._generate_fragment()
                if fragment:
                    result.append(fragment)
                    self._changes.append({
                        "type": "cadence_fragment",
                        "description": f"Inserted fragment after {consecutive_medium} uniform sentences",
                    })
                    consecutive_medium = 0

        return result

    def _generate_fragment(self) -> Optional[str]:
        """Generate a short discourse fragment for cadence breaking."""
        fragments = self._get_fragments()
        if not fragments:
            return None
        return self._rng.choice(fragments)

    def _get_fragments(self) -> list[str]:
        """Get language-specific short discourse fragments."""
        if self._lang == "ru":
            return [
                "И это важно.", "Это факт.", "Вот в чём суть.",
                "Звучит логично.", "Стоит задуматься.",
                "Не всё так просто.", "Это ещё не всё.",
                "И вот почему.", "Вопрос непростой.",
            ]
        if self._lang == "uk":
            return [
                "І це важливо.", "Це факт.", "Ось у чому суть.",
                "Звучить логічно.", "Варто замислитися.",
                "Не все так просто.", "Це ще не все.",
                "І ось чому.", "Питання непросте.",
            ]
        if self._lang == "de":
            return [
                "Das ist wichtig.", "So ist es.", "Genau das.",
                "Klingt logisch.", "Nicht ganz einfach.",
                "Das ist noch nicht alles.", "Und genau darum.",
            ]
        if self._lang == "fr":
            return [
                "C'est important.", "C'est un fait.", "Voilà l'enjeu.",
                "C'est logique.", "Pas si simple.", "Ce n'est pas tout.",
            ]
        if self._lang == "es":
            return [
                "Esto es importante.", "Un hecho.", "Ese es el punto.",
                "Tiene sentido.", "No es tan simple.", "Y hay más.",
            ]
        if self._lang == "it":
            return [
                "Questo è importante.", "Un dato di fatto.",
                "Ha senso.", "Non è così semplice.", "E c'è di più.",
            ]
        if self._lang == "pl":
            return [
                "To ważne.", "To fakt.", "O to chodzi.",
                "Ma to sens.", "To nie takie proste.",
            ]
        if self._lang == "pt":
            return [
                "Isso é importante.", "Um fato.", "Esse é o ponto.",
                "Faz sentido.", "Não é tão simples.",
            ]
        # English default
        if self._profile in ("chat", "web"):
            return [
                "That matters.", "Here's the thing.", "Worth noting.",
                "Think about it.", "Not quite.", "It's that simple.",
                "And that's key.", "Fair enough.", "Makes sense, right?",
                "There's more to it.", "Big difference.",
            ]
        return [
            "This matters.", "That is the key point.",
            "It is worth considering.", "The implications are clear.",
            "This distinction matters.",
        ]

    # ── Discourse surprise injection ──────────────────────────

    def _inject_discourse_surprise(
        self,
        sentences: list[str],
        prob: float,
    ) -> list[str]:
        """Inject discourse markers to raise token-level entropy.

        AI text is highly predictable. Human text has "surprises":
        - Parenthetical asides: "The method (surprisingly) worked."
        - Hedging: "maybe", "probably", "sort of"
        - Self-correction: "or rather", "well, actually"
        - Rhetorical questions inserted mid-text
        """
        result = []
        for sent in sentences:
            # Only modify some sentences
            if self._rng.random() > prob * 0.25:
                result.append(sent)
                continue

            transformed = sent
            choice = self._rng.random()

            if choice < 0.35:
                # Insert parenthetical aside
                transformed = self._insert_parenthetical(sent)
            elif choice < 0.6:
                # Add hedging word
                transformed = self._add_hedging(sent)
            elif choice < 0.85:
                # Add introductory phrase variation
                transformed = self._add_intro_variation(sent)
            else:
                # Keep original (controlled randomness)
                pass

            if transformed and transformed != sent:
                self._changes.append({
                    "type": "discourse_surprise",
                    "description": "Discourse marker injection",
                })
            result.append(transformed if transformed else sent)

        return result

    def _insert_parenthetical(self, sent: str) -> str:
        """Insert a parenthetical aside into a sentence."""
        words = sent.split()
        if len(words) < 6:
            return sent

        asides = self._get_parenthetical_asides()
        if not asides:
            return sent

        aside = self._rng.choice(asides)
        # Insert after 30-50% of the sentence, but only at a safe position
        # (not adjacent to punctuation, which creates "(, which ..." garbage)
        lo = max(1, len(words) // 3)
        hi = max(lo, len(words) // 2)
        candidates = []
        for idx in range(lo, hi + 1):
            prev_w = words[idx - 1] if idx > 0 else ""
            next_w = words[idx] if idx < len(words) else ""
            # Skip if previous word ends with punctuation or next starts with it
            if prev_w and prev_w[-1] in ",.;:!?":
                continue
            if next_w and next_w[0] in ",.;:!?('\"":
                continue
            candidates.append(idx)
        if not candidates:
            return sent
        pos = self._rng.choice(candidates)
        words.insert(pos, aside)
        return " ".join(words)

    def _get_parenthetical_asides(self) -> list[str]:
        """Get language-specific parenthetical asides."""
        if self._lang == "ru":
            return [
                "— что важно —", "— и это ключевой момент —",
                "— что интересно —", "— по сути —",
                "— стоит отметить —", "— как ни странно —",
            ]
        if self._lang == "uk":
            return [
                "— що важливо —", "— і це ключовий момент —",
                "— що цікаво —", "— по суті —",
                "— варто зазначити —", "— як не дивно —",
            ]
        if self._lang == "de":
            return [
                "— was wichtig ist —", "— interessanterweise —",
                "— im Grunde —", "— bemerkenswert —",
            ]
        if self._lang == "fr":
            return [
                "— fait important —", "— chose intéressante —",
                "— en somme —", "— ce qui est notable —",
            ]
        if self._lang == "es":
            return [
                "— dato importante —", "— curiosamente —",
                "— en esencia —", "— cabe señalar —",
            ]
        # English default
        if self._profile in ("chat", "web"):
            return [
                "(interestingly)", "(and this is key)",
                "(surprisingly)", "(worth noting)",
                "(to be fair)", "(oddly enough)",
            ]
        return [
            "(notably)", "(importantly)",
            "(in practice)", "(it should be noted)",
        ]

    def _add_hedging(self, sent: str) -> str:
        """Add hedging word/phrase to reduce certainty (AI is too certain)."""
        hedges = self._get_hedging_words()
        if not hedges:
            return sent

        hedge = self._rng.choice(hedges)
        words = sent.split()
        if not words:
            return sent

        # Skip if sentence already starts with a transition/marker/hedge
        first_lower = words[0].lower().rstrip(".,;:")
        _skip_starts = {
            "however", "furthermore", "moreover", "additionally",
            "therefore", "thus", "consequently", "meanwhile",
            "nevertheless", "first", "second", "finally", "also",
            "indeed", "arguably", "honestly", "frankly", "realistically",
            "actually", "basically", "clearly", "still", "well",
            "in", "for", "on", "from", "yet", "but", "so",
            # RU
            "однако", "кроме", "более", "помимо", "пожалуй",
            "вероятно", "скорее", "надо", "по",
            # UK
            "однак", "крім", "більш", "окрім", "мабуть",
            "ймовірно", "швидше", "треба",
        }
        if first_lower in _skip_starts:
            return sent

        # Don't lowercase proper nouns / acronyms at sentence start
        first_word = words[0]
        if first_word[0].isupper() and not first_word.isupper() and not first_word[1:2].isupper():
            words[0] = first_word[0].lower() + first_word[1:]
        return f"{hedge} " + " ".join(words)

    def _get_hedging_words(self) -> list[str]:
        """Get language-specific hedging words/phrases."""
        if self._lang == "ru":
            return [
                "Пожалуй,", "Скорее всего,", "Вероятно,",
                "По всей видимости,", "Надо сказать,",
                "Как мне кажется,",
            ]
        if self._lang == "uk":
            return [
                "Мабуть,", "Найімовірніше,", "Ймовірно,",
                "Вочевидь,", "Треба сказати,",
                "Як на мене,",
            ]
        if self._lang == "de":
            return [
                "Vermutlich", "Wahrscheinlich", "Möglicherweise",
                "Es scheint,", "Gewissermaßen",
            ]
        if self._lang == "fr":
            return [
                "Probablement,", "Sans doute,", "Il semble que",
                "Vraisemblablement,", "En quelque sorte,",
            ]
        if self._lang == "es":
            return [
                "Probablemente,", "Tal vez,", "Al parecer,",
                "En cierto modo,", "Parece que",
            ]
        # English default
        if self._profile in ("chat", "web"):
            return [
                "Honestly,", "Arguably,", "In a way,",
                "To some extent,", "Realistically,",
                "From what I can tell,",
            ]
        return [
            "Arguably,", "In many cases,", "To some degree,",
            "In practice,", "Typically,",
        ]

    def _add_intro_variation(self, sent: str) -> str:
        """Add varied introductory phrase to break sentence-start monotony."""
        # Skip if sentence already starts with a transition/marker/hedge
        first_word = sent.split()[0].lower().rstrip(".,;:") if sent.split() else ""
        skip_starts = {
            "however", "furthermore", "moreover", "additionally",
            "therefore", "thus", "consequently", "meanwhile",
            "nevertheless", "first", "second", "finally", "also",
            "indeed", "arguably", "honestly", "frankly", "realistically",
            "actually", "basically", "clearly", "still", "well",
            "in", "for", "on", "from", "yet", "but", "so",
            "однако", "кроме", "более", "помимо", "пожалуй",
            "вероятно", "скорее", "надо", "по", "між",
            "cependant", "de", "néanmoins", "sin", "además",
            "jedoch", "darüber", "außerdem",
        }
        if first_word in skip_starts:
            return sent

        intros = self._get_intro_variations()
        if not intros:
            return sent

        intro = self._rng.choice(intros)
        words = sent.split()
        # Don't lowercase proper nouns / acronyms at sentence start
        if words and words[0][0].isupper() and not words[0].isupper() and not words[0][1:2].isupper():
            words[0] = words[0][0].lower() + words[0][1:]
        return f"{intro} " + " ".join(words)

    def _get_intro_variations(self) -> list[str]:
        """Get language-specific introductory phrase variations."""
        if self._lang == "ru":
            return [
                "При этом", "К слову,", "Между тем,",
                "Что касается этого,", "В целом,",
                "С другой стороны,",
            ]
        if self._lang == "uk":
            return [
                "При цьому", "До речі,", "Тим часом,",
                "Що стосується цього,", "Загалом,",
                "З іншого боку,",
            ]
        if self._lang == "de":
            return [
                "Dabei", "Übrigens,", "Im Grunde,",
                "Was das betrifft,", "Insgesamt,",
            ]
        if self._lang == "fr":
            return [
                "Par ailleurs,", "Au passage,", "Dans l'ensemble,",
                "À cet égard,", "En fait,",
            ]
        if self._lang == "es":
            return [
                "Por cierto,", "En general,", "Al respecto,",
                "De hecho,", "En resumen,",
            ]
        # English default
        if self._profile in ("chat", "web"):
            return [
                "Actually,", "In fact,", "On that note,",
                "Speaking of which,", "By the way,",
                "If you think about it,", "As it turns out,",
            ]
        return [
            "In practice,", "On this point,", "Notably,",
            "In this regard,", "It is also worth noting that",
        ]

    # ── Utility methods ───────────────────────────────────────

    def _get_target_cv(self) -> float:
        """Get target CV for sentence-length distribution.

        Human writing typically has CV 0.5-0.8.
        AI writing typically has CV 0.2-0.4.
        """
        targets = {
            "chat": 0.70,
            "web": 0.60,
            "blog": 0.55,
            "seo": 0.50,
            "docs": 0.45,
            "formal": 0.42,
        }
        return targets.get(self._profile, 0.55)

    @staticmethod
    def _avg_length(sentences: list[str]) -> float:
        """Average sentence length in words."""
        lengths = [len(s.split()) for s in sentences if s.strip()]
        return sum(lengths) / len(lengths) if lengths else 0.0

    @staticmethod
    def _split_sentences(text: str) -> list[str]:
        """Split text into sentences (email/URL safe)."""
        return split_sentences(text)

    @staticmethod
    def _join_sentences(sentences: list[str]) -> str:
        """Join sentences back into text."""
        return " ".join(sentences)
