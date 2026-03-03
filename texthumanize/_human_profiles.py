"""Human-text statistical profiles for EN / RU / UK.

ASH™ (Adaptive Statistical Humanization) — proprietary technology
developed by Oleksandr K. for TextHumanize.

These profiles describe the **statistical signature** of natural
human-written text across multiple dimensions. Collected from
large corpora of verified human writing in three genres (blog,
academic, social) per language.

Copyright (c) 2024-2026 Oleksandr K. / TextHumanize Project.
The ASH method and these profiles are proprietary.
See LICENSE for details.
"""

from __future__ import annotations

# ═══════════════════════════════════════════════════════════════
#  FORMAT
# ═══════════════════════════════════════════════════════════════
# Each profile is a dict of metric_name → {mean, std, min, max}
# describing the distribution of that metric in human text.
#
# Metrics fall into categories:
#   E_  — entropy / information-theoretic
#   B_  — burstiness / variance
#   L_  — lexical / vocabulary
#   S_  — structural / sentence-level
#   P_  — punctuation
#   D_  — discourse / flow
#   R_  — readability
#   PPL_ — perplexity-specific
# ═══════════════════════════════════════════════════════════════


def _p(mean: float, std: float, lo: float | None = None,
       hi: float | None = None) -> dict[str, float]:
    """Shorthand for profile entry."""
    return {
        "mean": mean,
        "std": std,
        "min": lo if lo is not None else max(0.0, mean - 3 * std),
        "max": hi if hi is not None else mean + 3 * std,
    }


# ═══════════════════════════════════════════════════════════════
#  ENGLISH
# ═══════════════════════════════════════════════════════════════

HUMAN_PROFILE_EN: dict[str, dict[str, float]] = {
    # ── Entropy ──
    "E_char_entropy":      _p(4.20, 0.35, 3.40, 4.90),
    "E_word_entropy":      _p(7.80, 0.60, 6.20, 9.80),
    "E_bigram_entropy":    _p(9.40, 0.70, 7.50, 11.50),

    # ── Burstiness ──
    "B_sent_len_cv":       _p(0.55, 0.15, 0.25, 1.10),      # humans vary a lot
    "B_sent_len_skew":     _p(0.80, 0.40, -0.20, 2.00),     # positive skew (some long)
    "B_word_len_cv":       _p(0.50, 0.10, 0.25, 0.80),
    "B_para_len_cv":       _p(0.45, 0.18, 0.10, 1.00),

    # ── Lexical ──
    "L_ttr":               _p(0.60, 0.12, 0.30, 0.90),
    "L_hapax_ratio":       _p(0.48, 0.10, 0.20, 0.75),
    "L_avg_word_len":      _p(4.70, 0.40, 3.80, 6.00),
    "L_yule_k":            _p(120.0, 40.0, 40.0, 250.0),
    "L_vocab_richness":    _p(0.65, 0.10, 0.35, 0.90),

    # ── Structural ──
    "S_avg_sent_len":      _p(17.0, 5.0, 6.0, 35.0),
    "S_max_sent_len":      _p(35.0, 10.0, 15.0, 80.0),
    "S_min_sent_len":      _p(4.0, 2.0, 1.0, 12.0),
    "S_sent_len_range":    _p(30.0, 10.0, 8.0, 70.0),       # max - min

    # ── Punctuation ──
    "P_comma_rate":        _p(0.045, 0.015, 0.010, 0.090),
    "P_semicolon_rate":    _p(0.003, 0.003, 0.000, 0.015),
    "P_dash_rate":         _p(0.008, 0.005, 0.000, 0.025),
    "P_question_rate":     _p(0.012, 0.010, 0.000, 0.050),
    "P_exclamation_rate":  _p(0.005, 0.006, 0.000, 0.030),

    # ── Discourse ──
    "D_starter_diversity": _p(0.75, 0.12, 0.40, 1.00),
    "D_conjunction_rate":  _p(0.025, 0.010, 0.005, 0.060),
    "D_transition_rate":   _p(0.015, 0.008, 0.002, 0.045),
    "D_ai_pattern_rate":   _p(0.002, 0.003, 0.000, 0.010),  # human: near zero

    # ── Readability ──
    "R_flesch_reading":    _p(60.0, 15.0, 20.0, 90.0),
    "R_syllables_per_word": _p(1.55, 0.15, 1.20, 2.00),

    # ── Perplexity curve (key ASH metrics) ──
    "PPL_word_mean":       _p(85.0, 30.0, 25.0, 200.0),
    "PPL_word_cv":         _p(0.70, 0.20, 0.30, 1.40),      # high variance = human
    "PPL_autocorr_lag1":   _p(0.15, 0.12, -0.20, 0.50),     # weak autocorrelation
    "PPL_peak_ratio":      _p(0.22, 0.08, 0.05, 0.45),      # % of "surprise" words
    "PPL_trough_ratio":    _p(0.25, 0.08, 0.08, 0.50),
    "PPL_neural_mean":     _p(5.50, 1.50, 2.50, 12.0),
    "PPL_neural_cv":       _p(0.45, 0.15, 0.15, 0.90),
}

# ═══════════════════════════════════════════════════════════════
#  RUSSIAN
# ═══════════════════════════════════════════════════════════════

HUMAN_PROFILE_RU: dict[str, dict[str, float]] = {
    # ── Entropy ──
    "E_char_entropy":      _p(4.50, 0.30, 3.70, 5.30),
    "E_word_entropy":      _p(8.20, 0.55, 6.80, 10.20),
    "E_bigram_entropy":    _p(9.80, 0.65, 8.00, 12.00),

    # ── Burstiness ──
    "B_sent_len_cv":       _p(0.50, 0.14, 0.22, 1.00),
    "B_sent_len_skew":     _p(0.70, 0.35, -0.20, 1.80),
    "B_word_len_cv":       _p(0.48, 0.10, 0.25, 0.78),
    "B_para_len_cv":       _p(0.42, 0.17, 0.10, 0.95),

    # ── Lexical ──
    "L_ttr":               _p(0.65, 0.12, 0.35, 0.92),      # Russian has richer morphology
    "L_hapax_ratio":       _p(0.52, 0.10, 0.25, 0.78),
    "L_avg_word_len":      _p(5.80, 0.50, 4.50, 7.50),      # longer words than EN
    "L_yule_k":            _p(100.0, 35.0, 35.0, 220.0),
    "L_vocab_richness":    _p(0.70, 0.10, 0.40, 0.92),

    # ── Structural ──
    "S_avg_sent_len":      _p(15.0, 4.5, 5.0, 30.0),
    "S_max_sent_len":      _p(32.0, 10.0, 12.0, 70.0),
    "S_min_sent_len":      _p(3.0, 2.0, 1.0, 10.0),
    "S_sent_len_range":    _p(28.0, 10.0, 6.0, 60.0),

    # ── Punctuation (Russian uses more dashes, fewer semicolons) ──
    "P_comma_rate":        _p(0.055, 0.018, 0.015, 0.100),
    "P_semicolon_rate":    _p(0.002, 0.002, 0.000, 0.010),
    "P_dash_rate":         _p(0.012, 0.006, 0.001, 0.030),   # em-dash heavy
    "P_question_rate":     _p(0.010, 0.008, 0.000, 0.040),
    "P_exclamation_rate":  _p(0.006, 0.007, 0.000, 0.035),

    # ── Discourse ──
    "D_starter_diversity": _p(0.72, 0.12, 0.35, 1.00),
    "D_conjunction_rate":  _p(0.030, 0.012, 0.008, 0.065),
    "D_transition_rate":   _p(0.018, 0.008, 0.003, 0.050),
    "D_ai_pattern_rate":   _p(0.003, 0.004, 0.000, 0.012),

    # ── Readability ──
    "R_flesch_reading":    _p(55.0, 15.0, 15.0, 85.0),
    "R_syllables_per_word": _p(2.30, 0.20, 1.70, 3.00),

    # ── Perplexity ──
    "PPL_word_mean":       _p(95.0, 35.0, 30.0, 220.0),
    "PPL_word_cv":         _p(0.65, 0.18, 0.28, 1.30),
    "PPL_autocorr_lag1":   _p(0.12, 0.10, -0.20, 0.45),
    "PPL_peak_ratio":      _p(0.20, 0.07, 0.05, 0.40),
    "PPL_trough_ratio":    _p(0.23, 0.07, 0.07, 0.45),
    "PPL_neural_mean":     _p(6.00, 1.60, 2.80, 13.0),
    "PPL_neural_cv":       _p(0.42, 0.14, 0.14, 0.85),
}

# ═══════════════════════════════════════════════════════════════
#  UKRAINIAN
# ═══════════════════════════════════════════════════════════════

HUMAN_PROFILE_UK: dict[str, dict[str, float]] = {
    # ── Entropy ──
    "E_char_entropy":      _p(4.45, 0.32, 3.65, 5.30),
    "E_word_entropy":      _p(8.10, 0.58, 6.70, 10.10),
    "E_bigram_entropy":    _p(9.70, 0.68, 7.80, 11.80),

    # ── Burstiness ──
    "B_sent_len_cv":       _p(0.52, 0.14, 0.24, 1.05),
    "B_sent_len_skew":     _p(0.72, 0.38, -0.20, 1.90),
    "B_word_len_cv":       _p(0.47, 0.10, 0.24, 0.76),
    "B_para_len_cv":       _p(0.43, 0.17, 0.10, 0.97),

    # ── Lexical ──
    "L_ttr":               _p(0.67, 0.12, 0.36, 0.93),
    "L_hapax_ratio":       _p(0.53, 0.10, 0.26, 0.80),
    "L_avg_word_len":      _p(5.90, 0.50, 4.60, 7.60),
    "L_yule_k":            _p(105.0, 37.0, 36.0, 230.0),
    "L_vocab_richness":    _p(0.71, 0.10, 0.42, 0.93),

    # ── Structural ──
    "S_avg_sent_len":      _p(14.5, 4.5, 5.0, 28.0),
    "S_max_sent_len":      _p(30.0, 9.0, 12.0, 65.0),
    "S_min_sent_len":      _p(3.0, 2.0, 1.0, 10.0),
    "S_sent_len_range":    _p(27.0, 9.0, 6.0, 55.0),

    # ── Punctuation ──
    "P_comma_rate":        _p(0.052, 0.017, 0.014, 0.095),
    "P_semicolon_rate":    _p(0.002, 0.002, 0.000, 0.010),
    "P_dash_rate":         _p(0.013, 0.006, 0.001, 0.032),
    "P_question_rate":     _p(0.010, 0.008, 0.000, 0.042),
    "P_exclamation_rate":  _p(0.006, 0.007, 0.000, 0.035),

    # ── Discourse ──
    "D_starter_diversity": _p(0.70, 0.12, 0.34, 1.00),
    "D_conjunction_rate":  _p(0.028, 0.011, 0.007, 0.062),
    "D_transition_rate":   _p(0.016, 0.008, 0.003, 0.048),
    "D_ai_pattern_rate":   _p(0.003, 0.004, 0.000, 0.012),

    # ── Readability ──
    "R_flesch_reading":    _p(53.0, 14.0, 14.0, 82.0),
    "R_syllables_per_word": _p(2.40, 0.22, 1.80, 3.10),

    # ── Perplexity ──
    "PPL_word_mean":       _p(100.0, 38.0, 32.0, 230.0),
    "PPL_word_cv":         _p(0.63, 0.18, 0.26, 1.25),
    "PPL_autocorr_lag1":   _p(0.13, 0.11, -0.20, 0.48),
    "PPL_peak_ratio":      _p(0.21, 0.07, 0.05, 0.42),
    "PPL_trough_ratio":    _p(0.24, 0.07, 0.07, 0.47),
    "PPL_neural_mean":     _p(6.20, 1.70, 3.00, 13.5),
    "PPL_neural_cv":       _p(0.40, 0.14, 0.13, 0.82),
}

# ═══════════════════════════════════════════════════════════════
#  AI-TEXT PROFILES (for comparison / detection)
# ═══════════════════════════════════════════════════════════════

AI_PROFILE_EN: dict[str, dict[str, float]] = {
    "E_char_entropy":      _p(3.90, 0.20, 3.40, 4.40),
    "E_word_entropy":      _p(7.20, 0.40, 6.20, 8.20),
    "E_bigram_entropy":    _p(8.60, 0.45, 7.50, 9.80),
    "B_sent_len_cv":       _p(0.25, 0.08, 0.10, 0.50),       # very uniform
    "B_sent_len_skew":     _p(0.20, 0.15, -0.10, 0.60),
    "L_ttr":               _p(0.52, 0.08, 0.35, 0.72),
    "L_hapax_ratio":       _p(0.38, 0.07, 0.20, 0.58),
    "S_avg_sent_len":      _p(20.0, 3.0, 12.0, 30.0),
    "D_ai_pattern_rate":   _p(0.025, 0.015, 0.005, 0.070),   # many AI markers
    "PPL_word_mean":       _p(35.0, 12.0, 15.0, 70.0),       # low perplexity
    "PPL_word_cv":         _p(0.30, 0.10, 0.10, 0.55),       # smooth curve
    "PPL_autocorr_lag1":   _p(0.40, 0.12, 0.15, 0.70),       # predictable
    "PPL_peak_ratio":      _p(0.08, 0.04, 0.02, 0.20),       # few surprises
    "PPL_neural_mean":     _p(3.00, 0.80, 1.50, 5.50),
    "PPL_neural_cv":       _p(0.20, 0.08, 0.05, 0.40),
}

AI_PROFILE_RU: dict[str, dict[str, float]] = {
    "E_char_entropy":      _p(4.20, 0.18, 3.70, 4.70),
    "E_word_entropy":      _p(7.60, 0.38, 6.70, 8.50),
    "E_bigram_entropy":    _p(9.00, 0.42, 7.90, 10.10),
    "B_sent_len_cv":       _p(0.22, 0.07, 0.10, 0.45),
    "B_sent_len_skew":     _p(0.18, 0.14, -0.10, 0.50),
    "L_ttr":               _p(0.55, 0.08, 0.38, 0.75),
    "L_hapax_ratio":       _p(0.40, 0.07, 0.23, 0.60),
    "S_avg_sent_len":      _p(18.0, 3.0, 10.0, 28.0),
    "D_ai_pattern_rate":   _p(0.020, 0.012, 0.004, 0.060),
    "PPL_word_mean":       _p(40.0, 14.0, 18.0, 80.0),
    "PPL_word_cv":         _p(0.28, 0.09, 0.10, 0.52),
    "PPL_autocorr_lag1":   _p(0.38, 0.12, 0.14, 0.68),
    "PPL_peak_ratio":      _p(0.07, 0.04, 0.02, 0.18),
    "PPL_neural_mean":     _p(3.50, 0.90, 1.80, 6.20),
    "PPL_neural_cv":       _p(0.18, 0.07, 0.04, 0.38),
}

AI_PROFILE_UK: dict[str, dict[str, float]] = {
    "E_char_entropy":      _p(4.18, 0.20, 3.65, 4.75),
    "E_word_entropy":      _p(7.50, 0.40, 6.60, 8.40),
    "E_bigram_entropy":    _p(8.90, 0.44, 7.80, 10.00),
    "B_sent_len_cv":       _p(0.23, 0.07, 0.10, 0.47),
    "B_sent_len_skew":     _p(0.19, 0.14, -0.10, 0.52),
    "L_ttr":               _p(0.57, 0.08, 0.39, 0.77),
    "L_hapax_ratio":       _p(0.42, 0.07, 0.24, 0.62),
    "S_avg_sent_len":      _p(17.0, 3.0, 10.0, 27.0),
    "D_ai_pattern_rate":   _p(0.022, 0.013, 0.004, 0.062),
    "PPL_word_mean":       _p(42.0, 15.0, 19.0, 85.0),
    "PPL_word_cv":         _p(0.27, 0.09, 0.10, 0.50),
    "PPL_autocorr_lag1":   _p(0.39, 0.12, 0.15, 0.70),
    "PPL_peak_ratio":      _p(0.07, 0.04, 0.02, 0.19),
    "PPL_neural_mean":     _p(3.60, 0.92, 1.90, 6.50),
    "PPL_neural_cv":       _p(0.19, 0.07, 0.05, 0.39),
}


# ═══════════════════════════════════════════════════════════════
#  ACCESSORS
# ═══════════════════════════════════════════════════════════════

_HUMAN_PROFILES: dict[str, dict[str, dict[str, float]]] = {
    "en": HUMAN_PROFILE_EN,
    "ru": HUMAN_PROFILE_RU,
    "uk": HUMAN_PROFILE_UK,
}

_AI_PROFILES: dict[str, dict[str, dict[str, float]]] = {
    "en": AI_PROFILE_EN,
    "ru": AI_PROFILE_RU,
    "uk": AI_PROFILE_UK,
}


def get_human_profile(lang: str) -> dict[str, dict[str, float]]:
    """Return human-text statistical profile for the language.

    Falls back to EN if language not available.
    """
    return _HUMAN_PROFILES.get(lang, HUMAN_PROFILE_EN)


def get_ai_profile(lang: str) -> dict[str, dict[str, float]]:
    """Return AI-text statistical profile for the language."""
    return _AI_PROFILES.get(lang, AI_PROFILE_EN)


def signature_distance(
    current: dict[str, float],
    target: dict[str, dict[str, float]],
) -> float:
    """Normalized Euclidean distance between current metrics and target profile.

    Returns 0.0 = perfect match, 1.0 = maximally different.
    """
    total = 0.0
    count = 0
    for key, prof in target.items():
        if key in current:
            std = prof["std"] if prof["std"] > 0 else 1.0
            z = (current[key] - prof["mean"]) / std
            total += z * z
            count += 1
    if count == 0:
        return 1.0
    return min(1.0, (total / count) ** 0.5 / 3.0)  # 3σ → 1.0


def metric_gaps(
    current: dict[str, float],
    target: dict[str, dict[str, float]],
) -> list[tuple[str, float, float]]:
    """Return list of (metric, z_score, direction) sorted by abs(z).

    direction: +1 means current is above target, -1 means below.
    """
    gaps: list[tuple[str, float, float]] = []
    for key, prof in target.items():
        if key in current:
            std = prof["std"] if prof["std"] > 0 else 1.0
            z = (current[key] - prof["mean"]) / std
            gaps.append((key, abs(z), -1.0 if z > 0 else 1.0))
    gaps.sort(key=lambda x: x[1], reverse=True)
    return gaps
