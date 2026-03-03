"""Statistical Signature Transfer™ (SST) — move text's statistical
fingerprint toward the human zone.

Part of the ASH™ (Adaptive Statistical Humanization) technology
developed by Oleksandr K. for TextHumanize.

Core idea
---------
Every document has a ~30-dimensional statistical signature: entropy,
burstiness, vocabulary richness, punctuation distribution, etc.
AI-generated text clusters tightly in one region; human text
occupies a wider, different region.

SST computes the current signature, identifies the largest gaps
from the human target, and applies **minimal edits** that move
the signature toward the human zone — a form of discrete
optimisation over the text surface.

Copyright (c) 2024-2026 Oleksandr K. / TextHumanize Project.
"""

from __future__ import annotations

import logging
import math
import random
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from texthumanize._human_profiles import (
    get_human_profile,
    metric_gaps,
    signature_distance,
)
from texthumanize.sentence_split import split_sentences
from texthumanize.word_lm import WordLanguageModel

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
#  SENTENCE-LENGTH TEMPLATES (human-like distributions)
# ═══════════════════════════════════════════════════════════════

_HUMAN_SENT_LENS: dict[str, list[int]] = {
    "en": [5, 8, 14, 22, 11, 6, 19, 28, 9, 15, 12, 7, 24, 10, 17, 6, 21, 13, 8, 31],
    "ru": [4, 7, 13, 20, 10, 5, 17, 25, 8, 14, 11, 6, 22, 9, 16, 5, 19, 12, 7, 28],
    "uk": [4, 7, 12, 19, 10, 5, 16, 24, 8, 13, 11, 6, 21, 9, 15, 5, 18, 11, 7, 27],
}


# ═══════════════════════════════════════════════════════════════
#  RESULT DATACLASS
# ═══════════════════════════════════════════════════════════════

@dataclass
class TransferResult:
    """Result of Statistical Signature Transfer™."""
    text: str
    original_text: str
    signature_before: dict[str, float] = field(default_factory=dict)
    signature_after: dict[str, float] = field(default_factory=dict)
    distance_before: float = 1.0
    distance_after: float = 1.0
    gaps_fixed: list[str] = field(default_factory=list)
    changes: list[dict[str, Any]] = field(default_factory=list)

    @property
    def improvement(self) -> float:
        """0–1: how much closer to human zone."""
        if self.distance_before <= 0:
            return 0.0
        return max(0.0, min(1.0,
            (self.distance_before - self.distance_after) / self.distance_before))


# ═══════════════════════════════════════════════════════════════
#  CORE ENGINE
# ═══════════════════════════════════════════════════════════════

class SignatureTransfer:
    """Transfer text's statistical signature toward human zone.

    ASH™ Statistical Signature Transfer™ — proprietary technology.

    Usage::

        sst = SignatureTransfer(lang="en")
        result = sst.transfer(text, intensity=0.6)
        print(f"Distance: {result.distance_before:.3f} → {result.distance_after:.3f}")
    """

    def __init__(
        self,
        lang: str = "en",
        seed: int | None = None,
    ) -> None:
        self.lang = lang
        self.seed = seed
        self._rng = random.Random(seed)
        self._lm = WordLanguageModel(lang)
        self._profile = get_human_profile(lang)

    # ── Public API ──

    def transfer(
        self,
        text: str,
        intensity: float = 0.6,
    ) -> TransferResult:
        """Move text's statistical signature toward the human zone.

        Parameters
        ----------
        text : str
            Input text.
        intensity : float
            0.0–1.0.  Higher = more aggressive changes.

        Returns
        -------
        TransferResult
        """
        if not text or not text.strip():
            return TransferResult(text=text, original_text=text)

        # Step 1: Compute current signature
        sig_before = self._compute_signature(text)
        dist_before = signature_distance(sig_before, self._profile)

        # Step 2: Identify top gaps
        gaps = metric_gaps(sig_before, self._profile)
        if not gaps:
            return TransferResult(
                text=text, original_text=text,
                signature_before=sig_before,
                signature_after=sig_before,
                distance_before=dist_before,
                distance_after=dist_before,
            )

        # Step 3: Apply targeted fixes for top-N gaps
        max_fixes = max(1, int(len(gaps) * intensity))
        top_gaps = gaps[:max_fixes]

        result_text = text
        changes: list[dict[str, Any]] = []
        fixed: list[str] = []

        for metric_name, z_score, direction in top_gaps:
            if z_score < 0.5:  # skip small gaps
                continue

            new_text, fix_changes = self._fix_gap(
                result_text, metric_name, direction, intensity, z_score
            )
            if new_text != result_text:
                result_text = new_text
                changes.extend(fix_changes)
                fixed.append(metric_name)

        # Step 4: Measure result
        sig_after = self._compute_signature(result_text)
        dist_after = signature_distance(sig_after, self._profile)

        return TransferResult(
            text=result_text,
            original_text=text,
            signature_before=sig_before,
            signature_after=sig_after,
            distance_before=dist_before,
            distance_after=dist_after,
            gaps_fixed=fixed,
            changes=changes,
        )

    def compute_signature(self, text: str) -> dict[str, float]:
        """Compute the statistical signature of text (public).

        Returns dict mapping metric names to their values.
        """
        return self._compute_signature(text)

    def distance_to_human(self, text: str) -> float:
        """How far is this text from the human zone? (0=human, 1=AI)."""
        sig = self._compute_signature(text)
        return signature_distance(sig, self._profile)

    # ── Signature Computation ──

    def _compute_signature(self, text: str) -> dict[str, float]:
        """Compute ~30 statistical metrics of the text."""
        sig: dict[str, float] = {}

        sentences = split_sentences(text, self.lang)
        words = text.split()
        chars = list(text)
        n_words = len(words)
        n_sents = len(sentences)

        if n_words < 5:
            return sig

        # ── Entropy metrics ──
        sig["E_char_entropy"] = self._char_entropy(text)
        sig["E_word_entropy"] = self._word_entropy(words)
        sig["E_bigram_entropy"] = self._bigram_entropy(words)

        # ── Burstiness ──
        sent_lens = [len(s.split()) for s in sentences]
        if sent_lens:
            mean_sl = sum(sent_lens) / len(sent_lens)
            if mean_sl > 0 and len(sent_lens) > 1:
                var_sl = sum((x - mean_sl) ** 2 for x in sent_lens) / len(sent_lens)
                sig["B_sent_len_cv"] = (var_sl ** 0.5) / mean_sl
            else:
                sig["B_sent_len_cv"] = 0.0

            if len(sent_lens) > 2:
                sig["B_sent_len_skew"] = self._skewness(sent_lens)
            else:
                sig["B_sent_len_skew"] = 0.0

        word_lens = [len(w) for w in words]
        mean_wl = sum(word_lens) / max(1, len(word_lens))
        if mean_wl > 0:
            var_wl = sum((x - mean_wl) ** 2 for x in word_lens) / max(1, len(word_lens))
            sig["B_word_len_cv"] = (var_wl ** 0.5) / mean_wl
        else:
            sig["B_word_len_cv"] = 0.0

        # Para burstiness
        paras = [p for p in text.split("\n\n") if p.strip()]
        if len(paras) > 1:
            para_lens = [len(p.split()) for p in paras]
            mean_pl = sum(para_lens) / len(para_lens)
            if mean_pl > 0:
                var_pl = sum((x - mean_pl) ** 2 for x in para_lens) / len(para_lens)
                sig["B_para_len_cv"] = (var_pl ** 0.5) / mean_pl
            else:
                sig["B_para_len_cv"] = 0.0
        else:
            sig["B_para_len_cv"] = 0.0

        # ── Lexical ──
        lower_words = [w.lower() for w in words]
        word_freq = Counter(lower_words)
        unique = len(word_freq)

        sig["L_ttr"] = unique / max(1, n_words)
        sig["L_hapax_ratio"] = sum(1 for c in word_freq.values() if c == 1) / max(1, unique)
        sig["L_avg_word_len"] = mean_wl
        sig["L_yule_k"] = self._yule_k(word_freq, n_words)
        sig["L_vocab_richness"] = min(1.0, unique / max(1, n_words ** 0.5))

        # ── Structural ──
        if sent_lens:
            sig["S_avg_sent_len"] = mean_sl if 'mean_sl' in dir() else sum(sent_lens) / len(sent_lens)
            sig["S_max_sent_len"] = float(max(sent_lens))
            sig["S_min_sent_len"] = float(min(sent_lens))
            sig["S_sent_len_range"] = float(max(sent_lens) - min(sent_lens))

        # ── Punctuation ──
        n_chars = max(1, len(chars))
        sig["P_comma_rate"] = text.count(",") / n_chars
        sig["P_semicolon_rate"] = text.count(";") / n_chars
        sig["P_dash_rate"] = (text.count("—") + text.count("–") + text.count(" - ")) / n_chars
        sig["P_question_rate"] = text.count("?") / n_chars
        sig["P_exclamation_rate"] = text.count("!") / n_chars

        # ── Discourse ──
        if n_sents > 0:
            starters = set()
            for s in sentences:
                w = s.strip().split()
                if w:
                    starters.add(w[0].lower())
            sig["D_starter_diversity"] = len(starters) / max(1, n_sents)

        # Conjunction/transition rates
        conj_en = {"and", "but", "or", "nor", "yet", "so", "for"}
        conj_ru = {"и", "а", "но", "или", "да", "ни", "же", "однако", "зато"}
        conj_uk = {"і", "й", "а", "але", "або", "чи", "та", "ні", "проте", "зате"}
        conjs = conj_en if self.lang == "en" else (conj_ru if self.lang == "ru" else conj_uk)
        sig["D_conjunction_rate"] = sum(1 for w in lower_words if w in conjs) / max(1, n_words)

        trans_en = {"however", "therefore", "furthermore", "additionally", "moreover",
                    "consequently", "nevertheless", "meanwhile", "subsequently"}
        trans_ru = {"однако", "поэтому", "кроме того", "более того",
                    "следовательно", "тем не менее", "между тем"}
        trans_uk = {"однак", "тому", "крім того", "більш того",
                    "отже", "тим не менш", "тим часом"}
        transitions = trans_en if self.lang == "en" else (trans_ru if self.lang == "ru" else trans_uk)
        sig["D_transition_rate"] = sum(1 for w in lower_words if w in transitions) / max(1, n_words)

        # AI pattern rate
        ai_en = {"furthermore", "additionally", "it is important to note",
                 "it should be noted", "in conclusion", "in summary",
                 "it is worth mentioning", "it is crucial"}
        ai_ru = {"необходимо отметить", "следует подчеркнуть", "важно отметить",
                 "стоит отметить", "в заключение", "подводя итог"}
        ai_uk = {"необхідно зазначити", "слід підкреслити", "важливо зазначити",
                 "варто зазначити", "підсумовуючи", "на завершення"}
        ai_pats = ai_en if self.lang == "en" else (ai_ru if self.lang == "ru" else ai_uk)
        text_lower = text.lower()
        ai_count = sum(1 for p in ai_pats if p in text_lower)
        sig["D_ai_pattern_rate"] = ai_count / max(1, n_sents)

        # ── Readability ──
        sig["R_flesch_reading"] = self._flesch_reading(text, sentences, words)
        sig["R_syllables_per_word"] = self._avg_syllables(words)

        # ── Perplexity (from LM) ──
        try:
            ppl = self._lm.perplexity(text)
            sig["PPL_word_mean"] = ppl
        except Exception:
            sig["PPL_word_mean"] = 50.0

        sent_ppls = []
        for s in sentences[:20]:  # limit for performance
            try:
                sent_ppls.append(self._lm.sentence_perplexity(s))
            except Exception:
                sent_ppls.append(50.0)

        if sent_ppls:
            mean_ppl = sum(sent_ppls) / len(sent_ppls)
            if mean_ppl > 0 and len(sent_ppls) > 1:
                var_p = sum((x - mean_ppl) ** 2 for x in sent_ppls) / len(sent_ppls)
                sig["PPL_word_cv"] = (var_p ** 0.5) / mean_ppl
            else:
                sig["PPL_word_cv"] = 0.0

            if len(sent_ppls) > 2:
                ac = self._autocorr(sent_ppls)
                sig["PPL_autocorr_lag1"] = ac
            else:
                sig["PPL_autocorr_lag1"] = 0.0

            threshold = mean_ppl * 1.5
            sig["PPL_peak_ratio"] = sum(1 for p in sent_ppls if p > threshold) / max(1, len(sent_ppls))

        return sig

    # ── Gap Fixers ──

    def _fix_gap(
        self,
        text: str,
        metric: str,
        direction: float,
        intensity: float,
        z_score: float,
    ) -> tuple[str, list[dict[str, Any]]]:
        """Apply a targeted fix for a specific metric gap."""
        changes: list[dict] = []

        if metric.startswith("B_sent_len"):
            return self._fix_sentence_length_variance(text, direction, intensity, changes)
        elif metric == "D_ai_pattern_rate":
            return self._fix_ai_patterns(text, intensity, changes)
        elif metric == "D_starter_diversity":
            return self._fix_starter_diversity(text, intensity, changes)
        elif metric.startswith("P_"):
            return self._fix_punctuation(text, metric, direction, intensity, changes)
        elif metric == "L_ttr" or metric == "L_vocab_richness":
            return self._fix_vocabulary(text, direction, intensity, changes)
        elif metric.startswith("E_"):
            return self._fix_entropy(text, direction, intensity, changes)

        return text, changes

    def _fix_sentence_length_variance(
        self, text: str, direction: float, intensity: float,
        changes: list[dict],
    ) -> tuple[str, list[dict]]:
        """Increase or decrease sentence length variance."""
        sentences = split_sentences(text, self.lang)
        if len(sentences) < 3:
            return text, changes

        sent_lens = [len(s.split()) for s in sentences]
        mean_len = sum(sent_lens) / len(sent_lens)

        # direction > 0 means we need MORE variance
        if direction > 0:
            # Find the most "average" sentences and split/extend them
            template = _HUMAN_SENT_LENS.get(self.lang, _HUMAN_SENT_LENS["en"])

            new_sents = list(sentences)
            modified = False

            for i, (sent, slen) in enumerate(zip(sentences, sent_lens)):
                target_len = template[i % len(template)]
                diff = abs(slen - target_len)

                if diff < 3:
                    continue

                if slen > target_len + 5 and slen > 15:
                    # Split long sentence
                    words = sent.split()
                    mid = len(words) // 2
                    # Find a good split point near middle
                    for offset in range(min(5, mid)):
                        for j in [mid + offset, mid - offset]:
                            if 0 < j < len(words) and words[j - 1].endswith((",", ";", "—", "–")):
                                first = " ".join(words[:j]).rstrip(",;—–") + "."
                                second = " ".join(words[j:])
                                if second:
                                    second = second[0].upper() + second[1:]
                                new_sents[i] = first + " " + second
                                modified = True
                                changes.append({
                                    "type": "sst_sent_split",
                                    "sentence_idx": i,
                                    "original_len": slen,
                                })
                                break
                        if modified:
                            break

                elif slen < target_len - 5 and slen < 8 and i < len(sentences) - 1:
                    # Merge with next short sentence
                    next_len = sent_lens[i + 1] if i + 1 < len(sent_lens) else 99
                    if next_len < 12:
                        merged = sent.rstrip(".!?") + ", " + sentences[i + 1][0].lower() + sentences[i + 1][1:]
                        new_sents[i] = merged
                        new_sents[i + 1] = ""
                        modified = True
                        changes.append({
                            "type": "sst_sent_merge",
                            "sentence_idx": i,
                        })

                if len(changes) >= max(1, int(intensity * 3)):
                    break

            if modified:
                result = self._rejoin_from_sents(text, sentences, new_sents)
                return result, changes

        return text, changes

    def _fix_ai_patterns(
        self, text: str, intensity: float, changes: list[dict],
    ) -> tuple[str, list[dict]]:
        """Remove AI-typical patterns."""
        replacements_en = {
            "it is important to note that": ["notably,", "worth noting:", ""],
            "it should be noted that": ["note that", ""],
            "furthermore,": ["also,", "besides,", "what's more,"],
            "additionally,": ["also,", "plus,", "on top of that,"],
            "in conclusion,": ["to wrap up,", "all in all,", ""],
            "it is worth mentioning that": ["interestingly,", ""],
            "it is crucial to": ["we need to", "it matters to"],
            "in order to": ["to", "so as to", "for"],
            "as a matter of fact,": ["in fact,", "actually,", "really,"],
            "due to the fact that": ["because", "since", "as"],
            "in the event that": ["if", "should", "in case"],
            "at this point in time": ["now", "currently", "right now"],
            "a significant amount of": ["a lot of", "much", "plenty of"],
            "has the ability to": ["can", "is able to"],
            "it is evident that": ["clearly,", "evidently,", ""],
            "it can be observed that": ["we see that", "we notice", ""],
            "this demonstrates that": ["this shows", "this means"],
            "in light of": ["given", "considering", "because of"],
            "prior to": ["before", "ahead of"],
            "subsequent to": ["after", "following"],
            "in the context of": ["regarding", "about", "when it comes to"],
            "with respect to": ["about", "regarding", "on"],
            "for the purpose of": ["to", "for", "in order to"],
            "notwithstanding": ["despite", "still", "even so"],
            "consequently,": ["so,", "as a result,", "hence,"],
            "on the other hand,": ["then again,", "but", "however,"],
        }
        replacements_ru = {
            "необходимо отметить, что": ["заметим, что", "стоит сказать:", ""],
            "следует подчеркнуть, что": ["подчеркнём:", ""],
            "важно отметить, что": ["замечу:", "причём", ""],
            "кроме того,": ["ещё", "плюс к тому,", "вдобавок,"],
            "в заключение": ["подытоживая", "в итоге", ""],
            "для того чтобы": ["чтобы", "ради того чтобы"],
            "в связи с тем, что": ["потому что", "так как", "поскольку"],
            "на сегодняшний день": ["сейчас", "в наши дни", "нынче"],
            "в настоящее время": ["сейчас", "теперь", "на данный момент"],
            "в первую очередь": ["прежде всего", "главное —"],
            "с точки зрения": ["по мнению", "на взгляд"],
            "в рамках": ["в ходе", "в контексте", "внутри"],
            "представляется возможным": ["можно", "есть шанс", "реально"],
            "является": ["— это", "считается", "представляет собой"],
            "осуществлять": ["делать", "выполнять", "проводить"],
            "данный": ["этот", "такой", "настоящий"],
            "вышеупомянутый": ["указанный", "упомянутый", "этот"],
            "нижеследующий": ["следующий", "описанный далее"],
            "по причине того, что": ["из-за того что", "потому что"],
            "таким образом,": ["итак,", "значит,", "стало быть,"],
            "тем не менее,": ["и всё же", "впрочем,", "однако"],
            "в целом,": ["в общем,", "обобщая,", "одним словом,"],
            "безусловно,": ["конечно,", "разумеется,", "само собой,"],
            "вследствие": ["из-за", "по причине", "в результате"],
        }
        replacements_uk = {
            "необхідно зазначити, що": ["зауважимо:", "варто сказати:", ""],
            "слід підкреслити, що": ["підкреслимо:", ""],
            "важливо зазначити, що": ["зверніть увагу:", "причому", ""],
            "крім того,": ["ще", "на додачу,", "до того ж,"],
            "підсумовуючи": ["отож", "зрештою", ""],
            "для того щоб": ["щоб", "аби", "задля того щоб"],
            "у зв'язку з тим, що": ["тому що", "бо", "оскільки"],
            "на сьогоднішній день": ["зараз", "нині", "сьогодні"],
            "у теперішній час": ["зараз", "тепер", "наразі"],
            "у першу чергу": ["насамперед", "передусім"],
            "з точки зору": ["на думку", "на погляд"],
            "у межах": ["у ході", "в контексті", "в рамках"],
            "є можливим": ["можна", "є змога", "реально"],
            "являє собою": ["— це", "є", "становить"],
            "здійснювати": ["робити", "виконувати", "проводити"],
            "даний": ["цей", "такий", "зазначений"],
            "вищезгаданий": ["згаданий", "попередній", "цей"],
            "нижченаведений": ["наступний", "описаний далі"],
            "з причини того, що": ["через те що", "бо", "тому що"],
            "таким чином,": ["отже,", "відтак,", "себто,"],
            "тим не менш,": ["і все ж", "утім,", "однак"],
            "загалом,": ["у цілому,", "узагальнюючи,", "одним словом,"],
            "безумовно,": ["звісно,", "безперечно,", "певна річ,"],
            "внаслідок": ["через", "з причини", "у результаті"],
        }

        reps = (replacements_en if self.lang == "en"
                else replacements_ru if self.lang == "ru"
                else replacements_uk)

        result = text
        for pattern, alternatives in reps.items():
            if pattern.lower() in result.lower():
                idx = result.lower().find(pattern.lower())
                original_fragment = result[idx:idx + len(pattern)]
                replacement = self._rng.choice(alternatives)
                result = result[:idx] + replacement + result[idx + len(pattern):]
                changes.append({
                    "type": "sst_ai_pattern_removal",
                    "original": original_fragment,
                    "replacement": replacement,
                })
                if len(changes) >= max(1, int(intensity * 4)):
                    break

        return result, changes

    def _fix_starter_diversity(
        self, text: str, intensity: float, changes: list[dict],
    ) -> tuple[str, list[dict]]:
        """Vary sentence beginnings."""
        sentences = split_sentences(text, self.lang)
        if len(sentences) < 3:
            return text, changes

        starters = [s.strip().split()[0].lower() for s in sentences if s.strip()]
        counter = Counter(starters)

        # Find repeated starters
        repeated = {s for s, c in counter.items() if c > 1}
        if not repeated:
            return text, changes

        new_sents = list(sentences)
        diversifiers = {
            "en": ["In particular,", "Notably,", "At this point,", "That is,",
                    "Meanwhile,", "For instance,", "To clarify,", "In short,",
                    "As it turns out,", "Interestingly,", "On a related note,",
                    "Put simply,", "What matters here is", "To illustrate,",
                    "Looking closer,", "As a side note,", "Practically speaking,",
                    "On the bright side,", "In hindsight,", "As we can see,",
                    "Oddly enough,", "Right now,", "In essence,", "Above all,"],
            "ru": ["В частности,", "Примечательно,", "При этом,", "То есть,",
                    "Между тем,", "К примеру,", "Иначе говоря,", "Словом,",
                    "Как оказалось,", "Любопытно,", "К слову,",
                    "Проще говоря,", "Суть в том, что", "Для наглядности,",
                    "Если присмотреться,", "Кстати,", "На практике,",
                    "С другой стороны,", "Оглядываясь назад,", "Как видим,",
                    "Как ни странно,", "Сейчас", "По существу,", "Прежде всего,"],
            "uk": ["Зокрема,", "Примітно,", "При цьому,", "Тобто,",
                    "Тим часом,", "Наприклад,", "Іншими словами,", "Одне слово,",
                    "Як виявилось,", "Цікаво,", "До речі,",
                    "Простіше кажучи,", "Суть у тому, що", "Для наочності,",
                    "Якщо придивитися,", "До слова,", "На практиці,",
                    "З іншого боку,", "Озираючись назад,", "Як бачимо,",
                    "Як не дивно,", "Наразі", "По суті,", "Насамперед,"],
        }

        pool = diversifiers.get(self.lang, diversifiers["en"])
        seen_fix = set()
        for i, sent in enumerate(sentences):
            first = sent.strip().split()[0].lower() if sent.strip() else ""
            if first in repeated and first not in seen_fix:
                seen_fix.add(first)
                prefix = self._rng.choice(pool)
                new_sents[i] = prefix + " " + sent[0].lower() + sent[1:]
                changes.append({
                    "type": "sst_starter_diversify",
                    "sentence_idx": i,
                    "prefix": prefix,
                })
                if len(changes) >= max(1, int(intensity * 3)):
                    break

        result = self._rejoin_from_sents(text, sentences, new_sents)
        return result, changes

    def _fix_punctuation(
        self, text: str, metric: str, direction: float,
        intensity: float, changes: list[dict],
    ) -> tuple[str, list[dict]]:
        """Adjust punctuation rates toward human norms."""
        # direction > 0 means need MORE of this punctuation
        if metric == "P_dash_rate" and direction > 0:
            # Add dashes (humans use more dashes than AI)
            sentences = split_sentences(text, self.lang)
            new_sents = list(sentences)
            for i, sent in enumerate(sentences):
                words = sent.split()
                if len(words) > 8 and "—" not in sent and " - " not in sent:
                    # Insert a dash parenthetical
                    mid = len(words) // 2
                    dash = " —" if self.lang in ("ru", "uk") else " —"
                    new_sents[i] = " ".join(words[:mid]) + dash + " " + " ".join(words[mid:])
                    changes.append({
                        "type": "sst_punct_dash",
                        "sentence_idx": i,
                    })
                    if len(changes) >= max(1, int(intensity * 2)):
                        break

            return self._rejoin_from_sents(text, sentences, new_sents), changes

        elif metric == "P_question_rate" and direction > 0:
            # Convert some declarative sentences to rhetorical questions
            sentences = split_sentences(text, self.lang)
            new_sents = list(sentences)
            for i, sent in enumerate(sentences):
                if sent.endswith(".") and len(sent.split()) > 5 and "?" not in sent:
                    q_starters = {
                        "en": "But isn't it true that ",
                        "ru": "Разве не так, что ",
                        "uk": "Хіба не так, що ",
                    }
                    starter = q_starters.get(self.lang, q_starters["en"])
                    new_sents[i] = starter + sent[0].lower() + sent[1:-1] + "?"
                    changes.append({
                        "type": "sst_punct_question",
                        "sentence_idx": i,
                    })
                    break  # Only one question

            return self._rejoin_from_sents(text, sentences, new_sents), changes

        return text, changes

    def _fix_vocabulary(
        self, text: str, direction: float, intensity: float,
        changes: list[dict],
    ) -> tuple[str, list[dict]]:
        """Improve vocabulary diversity."""
        # If direction > 0: need more vocabulary richness
        if direction <= 0:
            return text, changes

        words = text.split()
        lower_words = [w.lower().strip(".,;:!?") for w in words]
        freq = Counter(lower_words)

        # Find most repeated content words (not stop words)
        stop = {"the", "a", "an", "is", "are", "was", "were", "in", "on", "at",
                "to", "for", "of", "and", "or", "but", "not", "it", "this", "that",
                "и", "в", "на", "с", "по", "к", "из", "о", "не", "что", "это",
                "і", "з", "до", "із", "про", "що", "це"}
        repeated = [(w, c) for w, c in freq.items()
                    if c > 2 and w not in stop and len(w) > 3]
        repeated.sort(key=lambda x: x[1], reverse=True)

        if not repeated:
            return text, changes

        # Replace some occurrences with synonyms (simple approach)
        from texthumanize.perplexity_sculptor import _SURPRISE_SYNONYMS
        syns = _SURPRISE_SYNONYMS.get(self.lang, {})

        result = text
        for word, count in repeated[:3]:
            if word in syns:
                alts = syns[word]
                replacement = self._rng.choice(alts)
                # Replace only one occurrence (not the first)
                parts = result.split(word)
                if len(parts) > 2:
                    # Replace second occurrence
                    result = parts[0] + word + replacement.join(parts[1:3]) + word.join(parts[3:])
                    changes.append({
                        "type": "sst_vocab_diversify",
                        "word": word,
                        "replacement": replacement,
                    })

        return result, changes

    def _fix_entropy(
        self, text: str, direction: float, intensity: float,
        changes: list[dict],
    ) -> tuple[str, list[dict]]:
        """Increase text entropy."""
        if direction <= 0:
            return text, changes

        # Add variety: insert parenthetical remarks
        parentheticals = {
            "en": ["(at least in theory)", "(roughly speaking)", "(give or take)",
                   "(in a way)", "(to some extent)", "(more or less)"],
            "ru": ["(по крайней мере, теоретически)", "(грубо говоря)",
                   "(плюс-минус)", "(в некотором роде)", "(до определённой степени)"],
            "uk": ["(принаймні теоретично)", "(грубо кажучи)",
                   "(плюс-мінус)", "(у певному сенсі)", "(до певної міри)"],
        }

        pool = parentheticals.get(self.lang, parentheticals["en"])
        sentences = split_sentences(text, self.lang)
        if len(sentences) < 2:
            return text, changes

        new_sents = list(sentences)
        idx = self._rng.randint(0, len(sentences) - 1)
        words = new_sents[idx].split()
        if len(words) > 6:
            insert_pos = len(words) // 2
            remark = self._rng.choice(pool)
            words.insert(insert_pos, remark)
            new_sents[idx] = " ".join(words)
            changes.append({
                "type": "sst_entropy_remark",
                "sentence_idx": idx,
                "remark": remark,
            })

        return self._rejoin_from_sents(text, sentences, new_sents), changes

    # ── Helpers ──

    def _rejoin_from_sents(
        self, original: str, old_sents: list[str], new_sents: list[str],
    ) -> str:
        result = original
        for old, new in zip(old_sents, new_sents):
            if old != new and new:
                result = result.replace(old, new, 1)
            elif not new and old:
                # Sentence was deleted (merged)
                result = result.replace(old, "", 1)
        return re.sub(r'\n{3,}', '\n\n', result).strip()

    @staticmethod
    def _char_entropy(text: str) -> float:
        if not text:
            return 0.0
        freq = Counter(text.lower())
        n = len(text)
        return -sum(
            (c / n) * math.log2(c / n) for c in freq.values() if c > 0
        )

    @staticmethod
    def _word_entropy(words: list[str]) -> float:
        if not words:
            return 0.0
        freq = Counter(w.lower() for w in words)
        n = len(words)
        return -sum(
            (c / n) * math.log2(c / n) for c in freq.values() if c > 0
        )

    @staticmethod
    def _bigram_entropy(words: list[str]) -> float:
        if len(words) < 2:
            return 0.0
        bigrams = [(words[i].lower(), words[i + 1].lower()) for i in range(len(words) - 1)]
        freq = Counter(bigrams)
        n = len(bigrams)
        return -sum(
            (c / n) * math.log2(c / n) for c in freq.values() if c > 0
        )

    @staticmethod
    def _skewness(data: list[int | float]) -> float:
        n = len(data)
        if n < 3:
            return 0.0
        mean = sum(data) / n
        m2 = sum((x - mean) ** 2 for x in data) / n
        m3 = sum((x - mean) ** 3 for x in data) / n
        if m2 == 0:
            return 0.0
        return m3 / (m2 ** 1.5)

    @staticmethod
    def _yule_k(freq: Counter, n: int) -> float:
        if n < 2:
            return 0.0
        m1 = len(freq)
        m2 = sum(v * v for v in freq.values())
        if m1 == 0:
            return 0.0
        return 10000 * (m2 - m1) / max(1, m1 * m1)

    @staticmethod
    def _flesch_reading(text: str, sentences: list[str], words: list[str]) -> float:
        n_sents = max(1, len(sentences))
        n_words = max(1, len(words))
        n_syllables = sum(max(1, len(re.findall(r'[aeiouyаеёиоуыэюяіїєґ]', w.lower()))) for w in words)
        return 206.835 - 1.015 * (n_words / n_sents) - 84.6 * (n_syllables / n_words)

    @staticmethod
    def _avg_syllables(words: list[str]) -> float:
        if not words:
            return 0.0
        total = sum(max(1, len(re.findall(r'[aeiouyаеёиоуыэюяіїєґ]', w.lower()))) for w in words)
        return total / len(words)

    @staticmethod
    def _autocorr(data: list[float]) -> float:
        n = len(data)
        if n < 3:
            return 0.0
        mean = sum(data) / n
        var = sum((x - mean) ** 2 for x in data)
        if var == 0:
            return 0.0
        cov = sum((data[i] - mean) * (data[i + 1] - mean) for i in range(n - 1))
        return cov / var


# ═══════════════════════════════════════════════════════════════
#  MODULE-LEVEL CONVENIENCE
# ═══════════════════════════════════════════════════════════════

def transfer_signature(
    text: str,
    lang: str = "en",
    intensity: float = 0.6,
    seed: int | None = None,
) -> TransferResult:
    """Move text's statistical signature toward the human zone.

    ASH™ Statistical Signature Transfer™.
    """
    return SignatureTransfer(lang=lang, seed=seed).transfer(text, intensity)


def compute_text_signature(
    text: str,
    lang: str = "en",
) -> dict[str, float]:
    """Compute ~30-dimensional statistical signature of text."""
    return SignatureTransfer(lang=lang).compute_signature(text)
