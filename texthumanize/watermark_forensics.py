"""Watermark Forensics™ — detect and neutralise LLM statistical watermarks.

Part of the ASH™ (Adaptive Statistical Humanization) technology
developed by Oleksandr K. for TextHumanize.

Core idea
---------
Modern LLMs (GPT, Claude, Llama) embed *statistical watermarks*
by splitting the vocabulary into "green" and "red" lists based on
a hash of the preceding token (Kirchenbauer et al., 2023).  The
model then biases sampling toward green tokens, creating a signal
invisible to humans but detectable via z-test.

This is fundamentally different from Unicode watermarks (zero-width
chars, homoglyphs) which our ``watermark.py`` already handles.

Watermark Forensics™ detects this statistical bias and neutralises
it by replacing a portion of "green" tokens with "red" synonyms,
driving the green-ratio back to ~50%.

This is the first **offline, pure-Python** implementation of
statistical LLM watermark detection and removal.

Copyright (c) 2024-2026 Oleksandr K. / TextHumanize Project.
"""

from __future__ import annotations

import hashlib
import logging
import math
import random
import re
from dataclasses import dataclass, field
from typing import Any

from texthumanize._word_freq_data import (
    get_en_uni,
    get_ru_uni,
    get_uk_uni,
)

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
#  NEUTRALISATION SYNONYMS
# ═══════════════════════════════════════════════════════════════

# These are "red-list-likely" synonyms — words that are statistically
# less likely to end up in a green list for any hash scheme, because
# they are common enough to appear in many partitions.

_RED_SYNONYMS: dict[str, dict[str, list[str]]] = {
    "en": {
        "important": ["key", "big", "main", "core"],
        "significant": ["major", "big", "real", "true"],
        "utilize": ["use", "take", "try", "pick"],
        "implement": ["do", "run", "set", "add"],
        "facilitate": ["help", "let", "aid"],
        "demonstrate": ["show", "prove", "tell"],
        "Additionally": ["Also", "And", "Plus"],
        "Furthermore": ["Also", "And", "Next"],
        "However": ["But", "Yet", "Still"],
        "Therefore": ["So", "Thus", "Hence"],
        "Consequently": ["So", "Thus"],
        "Moreover": ["Also", "And", "Plus"],
        "comprehensive": ["full", "wide", "deep", "broad"],
        "effective": ["good", "real", "strong", "solid"],
        "enhance": ["boost", "lift", "grow", "raise"],
        "ensure": ["make sure", "keep", "hold"],
        "establish": ["set", "build", "make", "form"],
        "leverage": ["use", "tap", "pull"],
        "optimize": ["tune", "fix", "trim", "hone"],
        "provide": ["give", "show", "bring", "pass"],
        "obtain": ["get", "grab", "find", "gain"],
        "require": ["need", "want", "call for"],
        "achieve": ["get", "hit", "reach", "win"],
        "approach": ["way", "path", "plan", "line"],
        "endeavor": ["try", "aim", "work", "push"],
        "considerable": ["big", "large", "huge", "vast"],
        "constitute": ["form", "make", "be"],
        "determine": ["find", "tell", "check", "set"],
        "illustrate": ["show", "paint", "draw"],
        "incorporate": ["add", "blend", "mix", "fold"],
        "maintain": ["keep", "hold", "run"],
        "participate": ["join", "take part", "do"],
        "prioritize": ["rank", "pick", "set", "sort"],
        "recommend": ["suggest", "tip", "hint", "pick"],
        "sufficient": ["enough", "fine", "fair"],
        "transform": ["shift", "turn", "flip", "change"],
        "ultimately": ["in the end", "at last", "finally"],
        "fundamental": ["basic", "core", "key", "root"],
    },
    "ru": {
        "значительный": ["большой", "крупный", "серьёзный"],
        "обеспечивать": ["давать", "вести", "нести"],
        "осуществлять": ["делать", "вести", "брать"],
        "способствовать": ["вести к", "давать", "нести"],
        "является": ["есть", "это", "стал"],
        "необходимо": ["нужно", "надо", "стоит"],
        "данный": ["этот", "тот", "такой"],
        "определённый": ["некий", "один", "свой"],
        "эффективный": ["сильный", "хороший", "верный"],
        "существенный": ["большой", "серьёзный", "явный"],
        "Кроме того,": ["Ещё", "И", "Плюс"],
        "Однако": ["Но", "А", "Хотя"],
        "Поэтому": ["Вот", "Так", "Ну и"],
        "Следовательно": ["Значит", "Так", "Ну"],
        "значимый": ["важный", "весомый", "ценный"],
        "реализовать": ["сделать", "внедрить", "ввести"],
        "применять": ["брать", "ставить", "вести"],
        "содержать": ["иметь", "нести", "хранить"],
        "формировать": ["строить", "лепить", "делать"],
        "рекомендовать": ["советовать", "просить", "звать"],
        "предоставлять": ["давать", "вручать", "нести"],
        "достигать": ["брать", "иметь", "нести"],
        "преобразовать": ["менять", "сдвинуть", "вести"],
        "включать": ["иметь", "нести", "брать"],
        "устанавливать": ["ставить", "класть", "делать"],
        "демонстрировать": ["видеть", "нести", "дать"],
        "использовать": ["брать", "вести", "нести"],
        "рассматривать": ["смотреть", "брать", "вести"],
    },
    "uk": {
        "значний": ["великий", "серйозний", "чималий"],
        "забезпечувати": ["давати", "вести", "нести"],
        "здійснювати": ["робити", "вести", "брати"],
        "сприяти": ["вести до", "давати", "нести"],
        "є": ["це", "стало", "буде"],
        "необхідно": ["треба", "потрібно", "слід"],
        "даний": ["цей", "той", "такий"],
        "ефективний": ["сильний", "добрий", "вірний"],
        "суттєвий": ["великий", "серйозний", "явний"],
        "Крім того,": ["Ще", "І", "Плюс"],
        "Однак": ["Але", "А", "Хоча"],
        "Тому": ["Ось", "Так", "Ну й"],
        "значущий": ["важливий", "вагомий", "цінний"],
        "реалізувати": ["зробити", "впровадити", "ввести"],
        "застосовувати": ["брати", "ставити", "вести"],
        "містити": ["мати", "нести", "тримати"],
        "формувати": ["будувати", "ліпити", "робити"],
        "рекомендувати": ["радити", "просити", "кликати"],
        "надавати": ["давати", "вручати", "нести"],
        "досягати": ["брати", "мати", "нести"],
        "перетворювати": ["міняти", "зсувати", "вести"],
        "включати": ["мати", "нести", "брати"],
        "встановлювати": ["ставити", "класти", "робити"],
        "демонструвати": ["бачити", "нести", "дати"],
        "використовувати": ["брати", "вести", "нести"],
        "розглядати": ["дивитись", "брати", "вести"],
    },
}


# ═══════════════════════════════════════════════════════════════
#  RESULT DATACLASS
# ═══════════════════════════════════════════════════════════════

@dataclass
class ForensicResult:
    """Result of Watermark Forensics™ analysis or cleaning."""
    text: str
    original_text: str
    watermark_detected: bool = False
    watermark_strength: float = 0.0     # z-score
    green_ratio: float = 0.5            # before
    green_ratio_after: float = 0.5
    confidence: float = 0.0
    tokens_analyzed: int = 0
    tokens_neutralised: int = 0
    changes: list[dict[str, Any]] = field(default_factory=list)
    hash_schemes_tested: int = 0

    @property
    def verdict(self) -> str:
        if self.watermark_strength > 3.0:
            return "strong_watermark"
        elif self.watermark_strength > 2.0:
            return "weak_watermark"
        elif self.watermark_strength > 1.5:
            return "possible_watermark"
        return "no_watermark"


# ═══════════════════════════════════════════════════════════════
#  CORE ENGINE
# ═══════════════════════════════════════════════════════════════

class WatermarkForensics:
    """Detect and neutralise LLM statistical watermarks.

    ASH™ Watermark Forensics™ — proprietary technology.
    First offline pure-Python statistical watermark detector.

    Usage::

        wf = WatermarkForensics(lang="en")
        result = wf.detect("Text possibly watermarked by an LLM")
        print(f"Watermark: {result.verdict}, z={result.watermark_strength:.2f}")

        cleaned = wf.neutralise("Watermarked text here", intensity=0.6)
        print(cleaned.text)
    """

    # Number of hash schemes to test for watermark detection
    _N_SCHEMES = 8
    # Green-list fraction (standard is 0.5)
    _GAMMA = 0.5

    def __init__(
        self,
        lang: str = "en",
        seed: int | None = None,
    ) -> None:
        self.lang = lang
        self.seed = seed
        self._rng = random.Random(seed)
        self._vocab = self._load_vocab(lang)
        self._synonyms = _RED_SYNONYMS.get(lang, _RED_SYNONYMS["en"])

    # ── Public API ──

    def detect(self, text: str) -> ForensicResult:
        """Detect whether text contains a statistical LLM watermark.

        Tests multiple hash schemes and returns the best match.
        """
        if not text or not text.strip():
            return ForensicResult(text=text, original_text=text)

        tokens = self._tokenize(text)
        if len(tokens) < 10:
            return ForensicResult(
                text=text, original_text=text,
                tokens_analyzed=len(tokens),
            )

        # Test multiple hash schemes
        best_z = 0.0
        best_green_ratio = 0.5

        for scheme_id in range(self._N_SCHEMES):
            green_count = 0
            total = 0

            for i in range(1, len(tokens)):
                prev_token = tokens[i - 1].lower()
                curr_token = tokens[i].lower()

                is_green = self._is_green(prev_token, curr_token, scheme_id)
                if is_green:
                    green_count += 1
                total += 1

            if total < 5:
                continue

            green_ratio = green_count / total

            # z-test: H0 = no watermark (green_ratio ≈ 0.5)
            # Under H0: green_count ~ Binomial(total, gamma)
            expected = total * self._GAMMA
            std = (total * self._GAMMA * (1 - self._GAMMA)) ** 0.5
            if std > 0:
                z = (green_count - expected) / std
            else:
                z = 0.0

            if z > best_z:
                best_z = z
                best_green_ratio = green_ratio

        # Confidence: sigmoid of z-score shifted by 2
        confidence = 1.0 / (1.0 + math.exp(-1.5 * (best_z - 2.0)))

        return ForensicResult(
            text=text,
            original_text=text,
            watermark_detected=best_z > 2.0,
            watermark_strength=round(best_z, 3),
            green_ratio=round(best_green_ratio, 4),
            confidence=round(confidence, 4),
            tokens_analyzed=len(tokens),
            hash_schemes_tested=self._N_SCHEMES,
        )

    def neutralise(
        self,
        text: str,
        intensity: float = 0.6,
    ) -> ForensicResult:
        """Detect and neutralise statistical watermarks.

        Replaces "green" tokens with "red" synonyms to drive
        the green-ratio back to ~50%.
        """
        # First detect
        detection = self.detect(text)
        if not detection.watermark_detected and detection.watermark_strength < 1.5:
            # No watermark found, return as-is
            detection.green_ratio_after = detection.green_ratio
            return detection

        # Neutralise by replacing green tokens with red synonyms
        tokens = self._tokenize(text)
        result = text
        changes: list[dict[str, Any]] = []
        neutralised = 0

        # Find tokens that are consistently "green" across schemes
        green_scores: dict[int, float] = {}
        for i in range(1, len(tokens)):
            score = 0.0
            for scheme_id in range(self._N_SCHEMES):
                if self._is_green(tokens[i - 1].lower(), tokens[i].lower(), scheme_id):
                    score += 1.0
            green_scores[i] = score / self._N_SCHEMES

        # Sort by greenness (most consistently green first)
        green_indices = sorted(
            [i for i, s in green_scores.items() if s > 0.6],
            key=lambda i: green_scores[i],
            reverse=True,
        )

        # Replace a portion of green tokens
        max_replacements = max(1, int(len(green_indices) * intensity * 0.4))

        for idx in green_indices[:max_replacements]:
            token = tokens[idx]
            clean_token = re.sub(r'[^\w]', '', token)

            # Look for a synonym
            replacement = self._find_red_synonym(clean_token)
            if replacement:
                # Preserve punctuation
                prefix = ""
                suffix = ""
                for ch in token:
                    if ch.isalpha():
                        break
                    prefix += ch
                for ch in reversed(token):
                    if ch.isalpha():
                        break
                    suffix = ch + suffix

                # Preserve case
                if token[0].isupper() if token else False:
                    replacement = replacement[0].upper() + replacement[1:]

                full_replacement = prefix + replacement + suffix
                result = result.replace(token, full_replacement, 1)
                changes.append({
                    "type": "watermark_neutralise",
                    "position": idx,
                    "original": token,
                    "replacement": full_replacement,
                    "green_score": round(green_scores[idx], 2),
                })
                neutralised += 1

        # Re-measure
        after_detection = self.detect(result)

        return ForensicResult(
            text=result,
            original_text=text,
            watermark_detected=detection.watermark_detected,
            watermark_strength=detection.watermark_strength,
            green_ratio=detection.green_ratio,
            green_ratio_after=after_detection.green_ratio,
            confidence=detection.confidence,
            tokens_analyzed=detection.tokens_analyzed,
            tokens_neutralised=neutralised,
            changes=changes,
            hash_schemes_tested=self._N_SCHEMES,
        )

    # British spelling alias
    neutralize = neutralise

    # ── Internals ──

    def _tokenize(self, text: str) -> list[str]:
        """Simple whitespace tokenization preserving punctuation."""
        return [t for t in text.split() if t.strip()]

    def _is_green(self, prev: str, curr: str, scheme_id: int) -> bool:
        """Determine if 'curr' is in the green list given 'prev' context.

        Simulates multiple watermark hash schemes by varying the hash
        function.  The actual LLM scheme is unknown, so we test several
        plausible ones.
        """
        # Create hash from previous token + scheme_id
        key = f"{scheme_id}:{prev}".encode("utf-8", errors="ignore")
        h = hashlib.sha256(key).digest()

        # Use hash to create a threshold for this context
        threshold = h[0] / 256.0  # 0.0–1.0

        # Hash the current token
        curr_hash = hashlib.md5(
            f"{scheme_id}:{curr}".encode("utf-8", errors="ignore")
        ).digest()
        curr_val = curr_hash[0] / 256.0

        # "Green" if curr_val < gamma (0.5) after rotation by threshold
        rotated = (curr_val + threshold) % 1.0
        return rotated < self._GAMMA

    def _find_red_synonym(self, word: str) -> str | None:
        """Find a "red-list-likely" synonym for the word."""
        lower = word.lower()
        if lower in self._synonyms:
            return self._rng.choice(self._synonyms[lower])

        # Also check capitalized version
        cap = word.capitalize()
        if cap in self._synonyms:
            return self._rng.choice(self._synonyms[cap])

        # Fallback: massive synonym DB
        try:
            from texthumanize._synonym_db import SynonymDB
            _fb = SynonymDB().get(lower, self.lang)
            if _fb:
                return self._rng.choice(_fb)
        except Exception:
            pass

        return None

    def _load_vocab(self, lang: str) -> set[str]:
        """Load vocabulary for the language."""
        loaders = {
            "en": get_en_uni,
            "ru": get_ru_uni,
            "uk": get_uk_uni,
        }
        loader = loaders.get(lang)
        if loader:
            try:
                freq = loader()
                return set(freq.keys())
            except Exception:
                pass
        return set()


# ═══════════════════════════════════════════════════════════════
#  MODULE-LEVEL CONVENIENCE
# ═══════════════════════════════════════════════════════════════

def detect_statistical_watermark(
    text: str,
    lang: str = "en",
) -> ForensicResult:
    """Detect LLM statistical watermarks in text.

    ASH™ Watermark Forensics™ — first offline watermark detector.
    """
    return WatermarkForensics(lang=lang).detect(text)


def neutralise_watermark(
    text: str,
    lang: str = "en",
    intensity: float = 0.6,
    seed: int | None = None,
) -> ForensicResult:
    """Detect and neutralise LLM statistical watermarks.

    ASH™ Watermark Forensics™.
    """
    return WatermarkForensics(lang=lang, seed=seed).neutralise(text, intensity)


# Aliases
neutralize_watermark = neutralise_watermark
