"""
Unified synonym database — merges all sources into one API.

Sources (loaded lazily in priority order):
  1. _data/synonyms.json.gz  → Compressed combined archive (3 MB)
  2. _massive_synonyms.py    → Fallback: Moby Thesaurus (30K EN) + API
  3. _wikt_synonyms.py       → Fallback: Wiktionary dumps (128K RU/UK)
  4. _curated_synonyms.py    → Hand-curated RU (500+) / UK (400+)

Total: EN ~30K, RU ~128K, UK ~1.7K root words.

Usage:
    from texthumanize._synonym_db import SynonymDB
    db = SynonymDB()
    db.get("important", "en")       # → ['eminent', 'significant', ...]
    db.get("важный", "ru")          # → ['значимый', 'суттєвий', ...]
    db.random_synonym("big", "en")  # → random synonym
    len(db)                         # → total root words
    db.stats()                      # → {"en": 30058, "ru": 127492, "uk": 1761}
"""

from __future__ import annotations

import gzip
import json
import logging
import random
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).parent / "_data"
_COMPRESSED_FILE = _DATA_DIR / "synonyms.json.gz"


class SynonymDB:
    """Unified synonym database with lazy loading and frequency filtering.

    Synonyms are ranked by word frequency — common words first,
    archaic/rare words filtered out. This prevents bizarre replacements
    like 'vast' → 'brobdingnagian' from Moby Thesaurus.
    """

    _instance: Optional[SynonymDB] = None
    _loaded = False

    def __new__(cls) -> SynonymDB:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if not self._loaded:
            self._data: dict[str, dict[str, list[str]]] = {"en": {}, "ru": {}, "uk": {}}
            self._freq: dict[str, dict[str, float]] = {}
            self._load()
            self._load_frequencies()
            self._filter_and_rank_all()
            SynonymDB._loaded = True

    def _load(self) -> None:
        """Load synonym data — prefers compressed archive, falls back to .py."""
        if _COMPRESSED_FILE.exists():
            self._load_compressed()
        else:
            self._load_py_modules()

        # Always merge curated data (small, high quality)
        try:
            from texthumanize._curated_synonyms import RU_CURATED, UK_CURATED
            self._merge("ru", RU_CURATED)
            self._merge("uk", UK_CURATED)
        except ImportError:
            pass

    def _load_compressed(self) -> None:
        """Load from the compressed .json.gz archive (fast, 3 MB)."""
        try:
            with gzip.open(_COMPRESSED_FILE, "rb") as f:
                bundle = json.loads(f.read().decode("utf-8"))

            # Massive (Moby EN + Datamuse + API RU/UK)
            if "massive" in bundle:
                for lang in ("en", "ru", "uk"):
                    if lang in bundle["massive"]:
                        self._data[lang].update(bundle["massive"][lang])

            # Wiktionary offline dumps (128K RU + 1.4K UK)
            if "wikt" in bundle:
                for lang in ("ru", "uk"):
                    if lang in bundle["wikt"]:
                        self._merge(lang, bundle["wikt"][lang])

            # Curated in bundle (optional)
            if "curated" in bundle:
                for lang in ("ru", "uk"):
                    if lang in bundle["curated"]:
                        self._merge(lang, bundle["curated"][lang])

            logger.debug("SynonymDB: loaded from compressed archive")
        except Exception:
            logger.warning("SynonymDB: compressed load failed, falling back to .py", exc_info=True)
            self._load_py_modules()

    def _load_py_modules(self) -> None:
        """Fallback: load from individual .py source files."""
        try:
            from texthumanize._massive_synonyms import EN_SYNONYMS, RU_SYNONYMS, UK_SYNONYMS
            self._data["en"].update(EN_SYNONYMS)
            self._data["ru"].update(RU_SYNONYMS)
            self._data["uk"].update(UK_SYNONYMS)
        except ImportError:
            pass

        try:
            from texthumanize._wikt_synonyms import WIKT_SYNONYMS
            for lang in ("ru", "uk"):
                if lang in WIKT_SYNONYMS:
                    self._merge(lang, WIKT_SYNONYMS[lang])
        except ImportError:
            pass

    def _merge(self, lang: str, data: dict[str, list[str]]) -> None:
        """Merge new data into existing, deduplicating synonyms."""
        db = self._data[lang]
        for word, syns in data.items():
            if word in db:
                existing = set(db[word])
                for s in syns:
                    if s not in existing:
                        db[word].append(s)
                        existing.add(s)
            else:
                db[word] = list(syns)

    def _load_frequencies(self) -> None:
        """Load real word frequency data for quality filtering.

        Prefers _data/word_freq.json.gz (48K EN, 20K RU, 20K UK from
        wordfreq corpus — real frequency data). Falls back to the old
        _word_freq_data.py (10K EN synthetic) if archive not found.
        """
        freq_file = _DATA_DIR / "word_freq.json.gz"
        if freq_file.exists():
            try:
                with gzip.open(freq_file, "rt", encoding="utf-8") as f:
                    data = json.load(f)
                for lang in ("en", "ru", "uk"):
                    if lang in data:
                        self._freq[lang] = data[lang]
                logger.debug("SynonymDB: loaded real freq data (%d EN, %d RU, %d UK)",
                             len(self._freq.get("en", {})),
                             len(self._freq.get("ru", {})),
                             len(self._freq.get("uk", {})))
                return
            except Exception:
                logger.warning("SynonymDB: freq archive load failed", exc_info=True)

        # Fallback to old synthetic data
        try:
            from texthumanize._word_freq_data import get_en_uni, get_ru_uni, get_uk_uni
            self._freq["en"] = get_en_uni()
            self._freq["ru"] = get_ru_uni()
            self._freq["uk"] = get_uk_uni()
        except ImportError:
            pass

    # Words that should NEVER be used as synonyms (archaic, offensive,
    # overly literary, Latin/Greek, multi-word, ethnonyms/language names
    # that Moby Thesaurus lists as hyponyms rather than synonyms, etc.)
    _BLACKLIST_PATTERNS: tuple[str, ...] = (
        # Latin/Greek/French terms
        "ab ovo", "ad hoc", "au fait", "bona fide", "de facto",
        "in toto", "ipso facto", "modus operandi", "prima facie",
        # Extremely archaic / literary
        "gongoresque", "gongoristic", "marinistic", "euphuistic",
        "brobdingnagian", "atlantean", "cyclopean", "gargantuan",
        "herculean", "homeric", "pantagruelian", "rabelaisian",
        "brummagem", "colorable",
        # Technical jargon unlikely in normal text
        "anschluss", "welfarism",
        # ── Ethnonyms, nationality/language names ──
        # Moby Thesaurus lists these as "related words" for category terms
        # like "language", "country" etc. They are hyponyms, NOT synonyms.
        "afghan", "afrikaans", "afrikaner", "albanian", "algonquin",
        "alsatian", "american", "amerindian", "anglo-saxon", "arabian",
        "arabic", "aramaic", "armenian", "australian", "austrian",
        "aztec", "babylonian", "bantu", "basque", "bengali",
        "berber", "bohemian", "bolivian", "brazilian", "breton",
        "british", "bugandan", "burmese", "bushman", "cambodian",
        "cantonese", "castilian", "catalan", "caucasian", "celtic",
        "cherokee", "chickasaw", "chinese", "colombian", "coptic",
        "cornish", "corsican", "czech", "danish", "dravidian",
        "dutch", "egyptian", "english", "eskimo", "estonian",
        "ethiopian", "fijian", "finnish", "flemish", "french",
        "frisian", "gaelic", "gallic", "georgian", "german",
        "germanic", "gothic", "greek", "guarani", "gypsy",
        "haitian", "hawaiian", "hebrew", "hellenic", "hindi",
        "hindustani", "hungarian", "icelandic", "indian",
        "indonesian", "inuit", "iranian", "iraqi", "irish",
        "iroquois", "italian", "jamaican", "japanese", "javanese",
        "jewish", "korean", "kurdish", "laotian", "latin",
        "latvian", "lebanese", "libyan", "lithuanian", "malay",
        "malaysian", "maltese", "mandarin", "maori", "mayan",
        "melanesian", "mesopotamian", "mexican", "mongol",
        "mongolian", "moorish", "moroccan", "navajo", "nepalese",
        "nigerian", "norse", "norwegian", "ottoman", "pakistani",
        "palestinian", "papuan", "paraguayan", "persian",
        "peruvian", "philippine", "phoenician", "polish",
        "polynesian", "portuguese", "prussian", "quechua",
        "romanian", "roman", "russian", "samoan", "sanskrit",
        "sardinian", "scandinavian", "scottish", "serbian",
        "siberian", "sinhalese", "slavic", "slovenian",
        "somali", "spanish", "sumerian", "sundanese", "swahili",
        "swedish", "syrian", "tahitian", "taiwanese", "tamil",
        "thai", "tibetan", "tongan", "tunisian", "turkish",
        "turkmen", "ukrainian", "urdu", "uzbek", "venetian",
        "vietnamese", "welsh", "yiddish", "zulu",
        # ── Historical/cultural proper nouns ──
        "byzantine", "elizabethan", "victorian", "shakespearean",
        "neanderthal", "arthurian", "napoleonic", "jeffersonian",
        "jacobean", "edwardian", "gregorian", "julian",
    )

    _BLACKLIST_SET: frozenset[str] | None = None

    @classmethod
    def _get_blacklist(cls) -> frozenset[str]:
        if cls._BLACKLIST_SET is None:
            cls._BLACKLIST_SET = frozenset(cls._BLACKLIST_PATTERNS)
        return cls._BLACKLIST_SET

    @classmethod
    def _is_bad_synonym(cls, word: str, lang: str = "en") -> bool:
        """Check if a synonym is likely archaic, literary, or multi-word."""
        # Multi-word phrases (Moby has "first and foremost" etc.)
        if " " in word and len(word.split()) > 2:
            return True
        # Too short — for EN, need 3+ chars (avoids "af", "mo" artifacts)
        min_len = 3 if lang == "en" else 2
        if len(word) < min_len:
            return True
        # Too long (likely a phrase or technical term)
        if len(word) > 20:
            return True
        # Has non-letter characters (except hyphen and apostrophe)
        for ch in word:
            if not (ch.isalpha() or ch in "-' "):
                return True
        # Explicit blacklist (O(1) lookup)
        if word.lower() in cls._get_blacklist():
            return True
        return False

    def _filter_and_rank_all(self) -> None:
        """Filter out rare/archaic synonyms and rank by frequency.

        Strategy per language:
          EN (Moby Thesaurus — noisy, thematic associations):
            STRICT — only keep synonyms found in 48K corpus-frequency list.
            Moby contains related-but-not-synonym words; dropping unknowns
            is the safest approach.

          RU (Wiktionary — clean, real synonyms):
            MODERATE — freq-known first (sorted), then up to 4 unknowns.
            Wiktionary synonyms are generally correct, just rare.

          UK (Wiktionary — small but clean):
            RELAXED — keep all after basic filtering (data already sparse).

        All languages: sort by frequency, cap at 12.
        """
        for lang, db in self._data.items():
            freq = self._freq.get(lang, {})
            to_delete = []

            for word, syns in db.items():
                # Step 1: Remove obviously bad synonyms
                clean = [s for s in syns if not self._is_bad_synonym(s, lang)]

                if freq and lang == "en":
                    # EN: STRICT — only known synonyms
                    known = [(s, freq[s]) for s in clean if s in freq]
                    known.sort(key=lambda x: x[1], reverse=True)
                    ranked = [s for s, _ in known]

                elif freq and lang in ("ru", "uk"):
                    # RU/UK: MODERATE — known first, then some unknowns
                    known = [(s, freq[s]) for s in clean if s in freq]
                    unknown = [s for s in clean if s not in freq]
                    known.sort(key=lambda x: x[1], reverse=True)
                    max_unknown = 4 if lang == "ru" else 6
                    ranked = [s for s, _ in known] + unknown[:max_unknown]

                else:
                    ranked = clean

                # Remove self-references
                ranked = [s for s in ranked if s != word]

                # Cap at 12
                if ranked:
                    db[word] = ranked[:12]
                else:
                    to_delete.append(word)

            # Clean up words with no valid synonyms
            for w in to_delete:
                del db[w]
            if to_delete:
                logger.debug("SynonymDB: removed %d %s words with 0 valid synonyms",
                             len(to_delete), lang.upper())

    def get(self, word: str, lang: str = "en") -> list[str]:
        """Get synonyms for a word. Returns empty list if not found."""
        db = self._data.get(lang, {})
        return list(db.get(word, []) or db.get(word.lower(), []))

    def random_synonym(self, word: str, lang: str = "en") -> Optional[str]:
        """Get a random synonym, or None if no synonyms available."""
        syns = self.get(word, lang)
        return random.choice(syns) if syns else None

    def has(self, word: str, lang: str = "en") -> bool:
        """Check if a word has synonyms in the database."""
        db = self._data.get(lang, {})
        return word in db or word.lower() in db

    def keys(self, lang: str = "en") -> list[str]:
        """Get all root words for a language."""
        return list(self._data.get(lang, {}).keys())

    def stats(self) -> dict[str, int]:
        """Get count of root words per language."""
        return {lang: len(db) for lang, db in self._data.items()}

    def total_synonyms(self) -> dict[str, int]:
        """Get total synonym count per language."""
        return {
            lang: sum(len(v) for v in db.values())
            for lang, db in self._data.items()
        }

    def __len__(self) -> int:
        return sum(len(db) for db in self._data.values())

    def __repr__(self) -> str:
        s = self.stats()
        return f"SynonymDB(en={s['en']}, ru={s['ru']}, uk={s['uk']})"
