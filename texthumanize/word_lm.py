"""Word-level language model for perplexity computation.

Unigram/bigram model with pre-built frequency tables for
14 languages. Replaces character-trigram perplexity with
real word-level measurement.

Major languages (EN, RU, DE, FR, ES) use expanded frequency
data (EN: 10K+ unigrams, 237 bigrams) from compressed
data module for better perplexity estimation.

Usage:
    from texthumanize.word_lm import WordLanguageModel

    lm = WordLanguageModel(lang="en")
    pp = lm.perplexity("The quick brown fox jumps")
    score = lm.naturalness_score("Some text here")
"""

from __future__ import annotations

import math
import re
from typing import Any

from texthumanize._word_freq_data import (
    get_de_uni,
    get_en_bi,
    get_en_uni,
    get_es_uni,
    get_fr_uni,
    get_ru_bi,
    get_ru_uni,
)

# ── Frequency tables ──────────────────────────────────────
# Major languages (EN, RU, DE, FR, ES) use compressed data
# from _word_freq_data module (10K+ EN unigrams).
# Smaller languages use inline dicts below.

# ── Compact models for other languages ────────────────────
_UK_UNI: dict[str, float] = {
    "і": 0.028, "в": 0.025, "не": 0.018,
    "на": 0.015, "що": 0.012, "я": 0.010,
    "з": 0.010, "він": 0.008, "а": 0.008,
    "як": 0.007, "це": 0.007, "по": 0.005,
    "але": 0.005, "вона": 0.004, "до": 0.005,
    "за": 0.004, "від": 0.004, "його": 0.004,
    "всі": 0.003, "так": 0.003, "вони": 0.003,
    "ж": 0.003, "у": 0.003, "б": 0.003,
    "із": 0.002, "ми": 0.003, "для": 0.003,
    "ви": 0.002, "при": 0.002, "її": 0.002,
    "ні": 0.002, "вже": 0.002, "мені": 0.002,
    "ось": 0.001, "був": 0.003, "було": 0.002,
    "бути": 0.002, "є": 0.002, "цей": 0.002,
    "той": 0.002, "свій": 0.002, "весь": 0.002,
    "який": 0.002, "тільки": 0.002,
    "можна": 0.001, "треба": 0.001,
    "себе": 0.001, "коли": 0.001,
    "якщо": 0.001, "буде": 0.001,
    "були": 0.001, "нас": 0.001,
    "них": 0.001, "ніж": 0.001,
    "де": 0.001, "тут": 0.001,
    "дуже": 0.001, "навіть": 0.001,
    "після": 0.001, "між": 0.001,
    "також": 0.001, "ще": 0.001,
    "час": 0.001, "рік": 0.001,
    "людина": 0.001, "може": 0.001,
}

# DE, FR, ES — loaded from compressed _word_freq_data module

_IT_UNI: dict[str, float] = {
    "di": 0.035, "e": 0.028, "il": 0.020,
    "la": 0.018, "che": 0.015, "in": 0.013,
    "un": 0.010, "per": 0.009, "è": 0.008,
    "del": 0.007, "non": 0.007, "una": 0.006,
    "a": 0.006, "le": 0.005, "con": 0.005,
    "si": 0.005, "da": 0.004, "i": 0.004,
    "lo": 0.004, "al": 0.003, "ha": 0.003,
    "dei": 0.003, "nel": 0.003, "alla": 0.003,
    "più": 0.002, "come": 0.002, "su": 0.002,
    "anche": 0.002, "ma": 0.002, "sono": 0.002,
    "degli": 0.002, "questo": 0.002,
    "delle": 0.002, "se": 0.002,
    "tra": 0.001, "sua": 0.001,
    "suo": 0.001, "quando": 0.001,
    "stato": 0.001, "essere": 0.001,
    "tutto": 0.001, "ancora": 0.001,
    "poi": 0.001, "già": 0.001,
    "molto": 0.001, "dove": 0.001,
}

_PL_UNI: dict[str, float] = {
    "i": 0.028, "w": 0.025, "nie": 0.018,
    "na": 0.015, "z": 0.012, "że": 0.010,
    "do": 0.009, "to": 0.008, "się": 0.008,
    "jest": 0.006, "jak": 0.005, "ale": 0.005,
    "o": 0.005, "co": 0.004, "tak": 0.004,
    "po": 0.004, "za": 0.004, "od": 0.003,
    "ten": 0.003, "już": 0.003, "był": 0.003,
    "by": 0.003, "tylko": 0.002, "jego": 0.002,
    "jej": 0.002, "ich": 0.002, "tego": 0.002,
    "może": 0.002, "tym": 0.002, "czy": 0.002,
    "przed": 0.001, "też": 0.001,
    "kiedy": 0.001, "sobie": 0.001,
    "jeszcze": 0.001, "który": 0.001,
    "dla": 0.001, "przy": 0.001,
    "bardzo": 0.001, "dobrze": 0.001,
    "więc": 0.001, "jednak": 0.001,
    "potem": 0.001, "teraz": 0.001,
}

_PT_UNI: dict[str, float] = {
    "de": 0.040, "a": 0.024, "o": 0.020,
    "que": 0.018, "e": 0.016, "do": 0.012,
    "da": 0.011, "em": 0.009, "um": 0.008,
    "para": 0.007, "é": 0.006, "com": 0.006,
    "não": 0.005, "uma": 0.005, "os": 0.005,
    "no": 0.004, "se": 0.004, "na": 0.004,
    "por": 0.004, "mais": 0.003, "as": 0.003,
    "dos": 0.003, "como": 0.003, "mas": 0.003,
    "foi": 0.002, "ao": 0.002, "ele": 0.002,
    "das": 0.002, "tem": 0.002, "à": 0.002,
    "seu": 0.002, "sua": 0.002, "ou": 0.002,
    "ser": 0.001, "quando": 0.001,
    "muito": 0.001, "há": 0.001,
    "nos": 0.001, "já": 0.001,
    "está": 0.001, "eu": 0.001,
    "também": 0.001, "só": 0.001,
    "pelo": 0.001, "pela": 0.001,
}

_AR_UNI: dict[str, float] = {
    "في": 0.025, "من": 0.022, "على": 0.015,
    "إلى": 0.012, "أن": 0.012, "هذا": 0.008,
    "التي": 0.008, "الذي": 0.006, "ما": 0.006,
    "عن": 0.006, "لا": 0.006, "هذه": 0.005,
    "بين": 0.004, "كان": 0.005, "قد": 0.004,
    "ذلك": 0.004, "عند": 0.003, "لم": 0.003,
    "بعد": 0.003, "كل": 0.003, "هو": 0.004,
    "هي": 0.003, "أو": 0.003, "حتى": 0.002,
    "لأن": 0.002, "تم": 0.002, "ثم": 0.002,
    "أي": 0.002, "قبل": 0.002, "أكثر": 0.002,
    "يمكن": 0.002, "مع": 0.003, "فقط": 0.001,
    "كما": 0.002, "أيضا": 0.001, "دون": 0.001,
    "خلال": 0.001, "حيث": 0.001, "مثل": 0.001,
    "جدا": 0.001, "لكن": 0.002, "ليس": 0.001,
}

_ZH_UNI: dict[str, float] = {
    "的": 0.040, "是": 0.015, "了": 0.012,
    "在": 0.012, "不": 0.010, "和": 0.008,
    "有": 0.008, "我": 0.008, "他": 0.006,
    "这": 0.006, "中": 0.005, "人": 0.005,
    "们": 0.004, "大": 0.004, "来": 0.004,
    "上": 0.004, "个": 0.004, "到": 0.004,
    "说": 0.003, "就": 0.003, "会": 0.003,
    "也": 0.003, "地": 0.003, "出": 0.003,
    "对": 0.003, "要": 0.003, "能": 0.003,
    "以": 0.003, "为": 0.003, "时": 0.002,
    "年": 0.002, "可": 0.002, "都": 0.002,
    "把": 0.002, "那": 0.002, "你": 0.002,
    "她": 0.002, "着": 0.002, "过": 0.002,
    "被": 0.001, "从": 0.002, "而": 0.002,
}

_JA_UNI: dict[str, float] = {
    "の": 0.030, "に": 0.020, "は": 0.018,
    "を": 0.015, "た": 0.012, "が": 0.012,
    "で": 0.010, "て": 0.010, "と": 0.009,
    "し": 0.007, "れ": 0.006, "さ": 0.005,
    "ある": 0.005, "いる": 0.005, "も": 0.005,
    "する": 0.004, "から": 0.004, "な": 0.004,
    "こと": 0.004, "ない": 0.004, "この": 0.003,
    "その": 0.003, "よう": 0.003, "まで": 0.002,
    "です": 0.003, "ます": 0.003, "それ": 0.002,
    "これ": 0.002, "など": 0.002, "また": 0.002,
    "ため": 0.002, "もの": 0.002, "だ": 0.002,
    "ので": 0.001, "でも": 0.001, "だけ": 0.001,
    "より": 0.001, "ここ": 0.001, "あり": 0.001,
    "いう": 0.001, "なる": 0.001, "られ": 0.001,
}

_KO_UNI: dict[str, float] = {
    "의": 0.020, "이": 0.015, "는": 0.015,
    "을": 0.012, "를": 0.010, "에": 0.012,
    "가": 0.010, "로": 0.008,
    "에서": 0.006, "와": 0.005, "한": 0.005,
    "있다": 0.005, "하다": 0.005, "것": 0.004,
    "수": 0.004, "이다": 0.004, "대": 0.003,
    "또": 0.003, "그": 0.003, "위": 0.002,
    "등": 0.003, "및": 0.002, "않다": 0.002,
    "되다": 0.003, "중": 0.002, "대한": 0.002,
    "때": 0.002, "후": 0.002, "더": 0.002,
    "같다": 0.001, "만": 0.002, "보다": 0.001,
    "들": 0.002, "아니다": 0.001, "모든": 0.001,
    "이러한": 0.001, "통해": 0.001, "위해": 0.001,
    "매우": 0.001, "다른": 0.001, "새로운": 0.001,
}

_TR_UNI: dict[str, float] = {
    "bir": 0.020, "ve": 0.018, "bu": 0.012,
    "da": 0.010, "de": 0.010, "için": 0.008,
    "ile": 0.007, "olan": 0.005, "olarak": 0.005,
    "gibi": 0.004, "daha": 0.004, "çok": 0.004,
    "en": 0.004, "kadar": 0.003, "ya": 0.003,
    "o": 0.003, "ne": 0.003, "var": 0.003,
    "yok": 0.002, "ama": 0.003, "ancak": 0.002,
    "sonra": 0.002, "önce": 0.002, "her": 0.002,
    "ben": 0.002, "sen": 0.002, "biz": 0.001,
    "siz": 0.001, "onlar": 0.001, "şey": 0.002,
    "zaman": 0.002, "iç": 0.001, "üzere": 0.001,
    "tarafından": 0.001, "göre": 0.001,
    "arasında": 0.001, "karşı": 0.001,
    "yalnız": 0.001, "sadece": 0.001,
    "bile": 0.001, "hep": 0.001,
    "böyle": 0.001, "öyle": 0.001,
}

# ── Language model registry ───────────────────────────────
# EN, RU, DE, FR, ES use expanded compressed data (10K+ EN, 379+ others).
# Remaining languages use compact inline dicts above.
_UNIGRAMS: dict[str, dict[str, float]] = {
    "en": get_en_uni(), "ru": get_ru_uni(), "uk": _UK_UNI,
    "de": get_de_uni(), "fr": get_fr_uni(), "es": get_es_uni(),
    "it": _IT_UNI, "pl": _PL_UNI, "pt": _PT_UNI,
    "ar": _AR_UNI, "zh": _ZH_UNI, "ja": _JA_UNI,
    "ko": _KO_UNI, "tr": _TR_UNI,
}

_BIGRAMS: dict[str, dict[tuple[str, str], float]] = {
    "en": get_en_bi(), "ru": get_ru_bi(),
}

_LAMBDA = 0.4  # bigram interpolation weight
_SMOOTH = 1e-8  # Laplace smoothing floor

_TOK_RE = re.compile(r"[\w'']+", re.UNICODE)


def _tokenize(text: str) -> list[str]:
    """Lowercase word tokenization."""
    return [w.lower() for w in _TOK_RE.findall(text)]


class WordLanguageModel:
    """Word-level unigram/bigram language model.

    Computes perplexity, burstiness, and naturalness for
    14 languages using pre-built frequency tables.
    """

    def __init__(self, lang: str = "en") -> None:
        self.lang = lang if lang in _UNIGRAMS else "en"
        self._uni = _UNIGRAMS[self.lang]
        self._bi = _BIGRAMS.get(self.lang, {})
        # total mass for normalization
        self._uni_total = sum(self._uni.values())
        self._bi_total = sum(self._bi.values()) or 1.0
        self._vocab_size = len(self._uni) + 1

    # ── Core probability ──────────────────────────────────

    def _p_uni(self, word: str) -> float:
        """Smoothed unigram probability."""
        freq = self._uni.get(word, 0.0)
        return (freq + _SMOOTH) / (
            self._uni_total + _SMOOTH * self._vocab_size
        )

    def _p_bi(self, w1: str, w2: str) -> float:
        """Smoothed bigram probability."""
        if not self._bi:
            return self._p_uni(w2)
        freq = self._bi.get((w1, w2), 0.0)
        # Normalize by w1 frequency
        w1_freq = self._uni.get(w1, _SMOOTH)
        return (freq + _SMOOTH) / (
            w1_freq + _SMOOTH * self._vocab_size
        )

    def _p_interp(self, w_prev: str, w: str) -> float:
        """Interpolated probability."""
        return (
            _LAMBDA * self._p_bi(w_prev, w)
            + (1 - _LAMBDA) * self._p_uni(w)
        )

    # ── Perplexity ────────────────────────────────────────

    def perplexity(self, text: str) -> float:
        """Word-level perplexity of the text.

        Lower values = more predictable (AI-like).
        Typical human: 50-200, AI: 20-60.
        """
        tokens = _tokenize(text)
        if len(tokens) < 2:
            return 0.0
        log_sum = 0.0
        for i in range(1, len(tokens)):
            p = self._p_interp(tokens[i - 1], tokens[i])
            log_sum += math.log(max(p, 1e-20))
        n = len(tokens) - 1
        return math.exp(-log_sum / n) if n > 0 else 0.0

    def sentence_perplexity(self, sentence: str) -> float:
        """Perplexity for a single sentence."""
        return self.perplexity(sentence)

    def per_word_surprise(
        self, text: str,
    ) -> list[tuple[str, float]]:
        """Return (word, surprise_bits) for each word."""
        tokens = _tokenize(text)
        if len(tokens) < 2:
            return [(t, 0.0) for t in tokens]
        result: list[tuple[str, float]] = [
            (tokens[0], 0.0),
        ]
        for i in range(1, len(tokens)):
            p = self._p_interp(tokens[i - 1], tokens[i])
            bits = -math.log2(max(p, 1e-20))
            result.append((tokens[i], bits))
        return result

    # ── Burstiness ────────────────────────────────────────

    def burstiness(self, text: str) -> float:
        """Perplexity variance across sentences.

        Higher = more human-like variation.
        """
        sents = re.split(r"[.!?]+\s+", text.strip())
        sents = [s for s in sents if len(s.split()) >= 3]
        if len(sents) < 2:
            return 0.0
        pps = [self.sentence_perplexity(s) for s in sents]
        mean_pp = sum(pps) / len(pps)
        if mean_pp == 0:
            return 0.0
        variance = sum(
            (p - mean_pp) ** 2 for p in pps
        ) / len(pps)
        # Coefficient of variation
        return math.sqrt(variance) / max(mean_pp, 1e-10)

    # ── Naturalness score ─────────────────────────────────

    def naturalness_score(self, text: str) -> dict[str, Any]:
        """Full naturalness analysis.

        Returns:
            dict with: perplexity, burstiness, variance,
            naturalness (0-100), verdict.
        """
        tokens = _tokenize(text)
        if len(tokens) < 5:
            return {
                "perplexity": 0.0,
                "burstiness": 0.0,
                "variance": 0.0,
                "naturalness": 50,
                "verdict": "unknown",
            }

        pp = self.perplexity(text)
        burst = self.burstiness(text)

        # Sentence perplexities for variance
        sents = re.split(r"[.!?]+\s+", text.strip())
        sents = [s for s in sents if len(s.split()) >= 3]
        if len(sents) >= 2:
            pps = [
                self.sentence_perplexity(s) for s in sents
            ]
            mean_pp = sum(pps) / len(pps)
            var = sum(
                (p - mean_pp) ** 2 for p in pps
            ) / len(pps)
        else:
            var = 0.0

        # Score computation
        score = 0

        # Perplexity in human range (50-300): +35
        if 40 <= pp <= 400:
            score += 35
        elif 20 <= pp < 40:
            score += 15  # Borderline low
        elif pp > 400:
            score += 25  # Somewhat high but variable
        # Very low PP (<20) = likely AI → +0

        # Burstiness (human > 0.3): +30
        if burst > 0.5:
            score += 30
        elif burst > 0.3:
            score += 20
        elif burst > 0.15:
            score += 10

        # Variance: +20
        if var > 100:
            score += 20
        elif var > 30:
            score += 12
        elif var > 10:
            score += 6

        # No extremely low PP windows: +15
        if sents and len(sents) >= 2:
            pps_list = [
                self.sentence_perplexity(s)
                for s in sents
            ]
            low_count = sum(
                1 for p in pps_list if p < 15
            )
            ratio = low_count / len(pps_list)
            if ratio < 0.1:
                score += 15
            elif ratio < 0.3:
                score += 8
        else:
            score += 10

        score = max(0, min(100, score))

        if score >= 65:
            verdict = "human"
        elif score >= 35:
            verdict = "mixed"
        else:
            verdict = "ai"

        return {
            "perplexity": round(pp, 2),
            "burstiness": round(burst, 4),
            "variance": round(var, 2),
            "naturalness": score,
            "verdict": verdict,
        }


# ── Convenience functions ─────────────────────────────────

def word_perplexity(
    text: str, lang: str = "en",
) -> float:
    """Compute word-level perplexity."""
    return WordLanguageModel(lang=lang).perplexity(text)


def word_naturalness(
    text: str, lang: str = "en",
) -> dict[str, Any]:
    """Full naturalness analysis."""
    return WordLanguageModel(lang=lang).naturalness_score(
        text,
    )
