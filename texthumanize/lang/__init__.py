"""Языковые пакеты TextHumanize.

Поддерживает 14 языков с полными словарями
(RU, UK, EN, DE, FR, ES, PL, PT, IT, AR, ZH, JA, KO, TR)
и любые другие языки через универсальный процессор.
"""

from texthumanize.lang.ar import LANG_AR
from texthumanize.lang.de import LANG_DE
from texthumanize.lang.en import LANG_EN
from texthumanize.lang.es import LANG_ES
from texthumanize.lang.fr import LANG_FR
from texthumanize.lang.it import LANG_IT
from texthumanize.lang.ja import LANG_JA
from texthumanize.lang.ko import LANG_KO
from texthumanize.lang.pl import LANG_PL
from texthumanize.lang.pt import LANG_PT
from texthumanize.lang.ru import LANG_RU
from texthumanize.lang.tr import LANG_TR
from texthumanize.lang.uk import LANG_UK
from texthumanize.lang.zh import LANG_ZH

LANGUAGES = {
    "ar": LANG_AR,
    "ru": LANG_RU,
    "uk": LANG_UK,
    "en": LANG_EN,
    "de": LANG_DE,
    "fr": LANG_FR,
    "es": LANG_ES,
    "pl": LANG_PL,
    "pt": LANG_PT,
    "it": LANG_IT,
    "zh": LANG_ZH,
    "ja": LANG_JA,
    "ko": LANG_KO,
    "tr": LANG_TR,
}

# ── Language tiers ─────────────────────────────────────────

# Tier 1: Full detection + full humanization (deep grammar, syntax rewriting)
TIER1_LANGUAGES = {"en", "ru", "uk", "de"}

# Tier 2: Good detection + basic humanization (markers, patterns, no syntax rewrite)
TIER2_LANGUAGES = {"fr", "es", "it", "pl", "pt"}

# Tier 3: Basic detection + minimal humanization (universal processor only)
TIER3_LANGUAGES = {"ar", "zh", "ja", "ko", "tr"}

# Backward compat: DEEP_LANGUAGES = tier 1 only (was incorrectly set(LANGUAGES.keys()))
DEEP_LANGUAGES = TIER1_LANGUAGES

# All languages with at least marker-based detection support
DETECTION_LANGUAGES = TIER1_LANGUAGES | TIER2_LANGUAGES

# Минимальный пустой языковой пакет для неизвестных языков
_EMPTY_LANG_PACK = {
    "code": "unknown",
    "name": "Unknown",
    "trigrams": [],
    "stop_words": set(),
    "bureaucratic": {},
    "bureaucratic_phrases": {},
    "ai_connectors": {},
    "synonyms": {},
    "sentence_starters": {},
    "colloquial_markers": [],
    "abbreviations": [],
    "profile_targets": {
        "chat": {"avg_len": (6, 16), "variance": 0.5},
        "web": {"avg_len": (8, 22), "variance": 0.4},
        "seo": {"avg_len": (10, 24), "variance": 0.3},
        "docs": {"avg_len": (10, 26), "variance": 0.3},
        "formal": {"avg_len": (12, 30), "variance": 0.25},
    },
    "conjunctions": [],
    "split_conjunctions": [],
}


def get_lang_pack(lang: str) -> dict:
    """Получить языковой пакет по коду языка.

    Для языков с полными словарями (ru, uk, en, de, fr, es, pl, pt, it,
    ar, zh, ja, ko, tr) возвращает полный пакет. Для остальных — пустой
    минимальный пакет, обработка идёт через универсальный процессор
    и натурализатор.
    """
    if lang in LANGUAGES:
        return LANGUAGES[lang]
    # Для неизвестных языков — пустой пакет (обработка через universal.py)
    pack = dict(_EMPTY_LANG_PACK)
    pack["code"] = lang
    pack["name"] = lang.upper()
    return pack


def has_deep_support(lang: str) -> bool:
    """Проверить, есть ли для языка полный словарь (Tier 1)."""
    return lang in DEEP_LANGUAGES


def get_language_tier(lang: str) -> int:
    """Return language tier: 1 (full), 2 (good), 3 (basic), 0 (unknown)."""
    if lang in TIER1_LANGUAGES:
        return 1
    if lang in TIER2_LANGUAGES:
        return 2
    if lang in TIER3_LANGUAGES:
        return 3
    return 0


def has_detection_support(lang: str) -> bool:
    """Check if language has marker-based detection (Tier 1 + 2)."""
    return lang in DETECTION_LANGUAGES
