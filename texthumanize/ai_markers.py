"""AI-marker data externalization — JSON file I/O for detection patterns.

Extracts AI-characteristic words, phrases, and patterns from hardcoded
Python dicts into external JSON files under ``texthumanize/data/``.

This enables:
    - Updating AI markers without code changes
    - Community contributions via JSON edits
    - A/B testing of different marker sets
    - Language-specific marker packs as plugins

File structure:
    texthumanize/data/
        ai_markers_en.json   — English AI words (adverbs, adjectives, verbs, etc.)
        ai_markers_ru.json   — Russian AI words
        ai_markers_uk.json   — Ukrainian AI words
        ai_markers_de.json   — German AI words (stub)
        ai_markers_meta.json — Metadata: version, update timestamp, schema info

The system loads JSON markers at runtime and merges them with any
built-in fallback, giving JSON priority over hardcoded values.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
#  Paths
# ═══════════════════════════════════════════════════════════════

_DATA_DIR = Path(__file__).parent / "data"
_MARKER_PREFIX = "ai_markers_"
_MARKER_SUFFIX = ".json"
_META_FILE = "ai_markers_meta.json"

# Schema version for forward compatibility
_SCHEMA_VERSION = "1.0"


# ═══════════════════════════════════════════════════════════════
#  Built-in AI markers (fallback when JSON files don't exist)
# ═══════════════════════════════════════════════════════════════

_BUILTIN_AI_MARKERS: dict[str, dict[str, list[str]]] = {
    "en": {
        "adverbs": [
            "significantly", "substantially", "considerably", "remarkably",
            "exceptionally", "tremendously", "profoundly", "fundamentally",
            "essentially", "particularly", "specifically", "notably",
            "increasingly", "effectively", "ultimately", "consequently",
            "inherently", "intrinsically", "predominantly", "invariably",
        ],
        "adjectives": [
            "comprehensive", "crucial", "pivotal", "paramount",
            "innovative", "robust", "seamless", "holistic",
            "cutting-edge", "state-of-the-art", "groundbreaking",
            "transformative", "synergistic", "multifaceted",
            "nuanced", "intricate", "meticulous", "imperative",
        ],
        "verbs": [
            "utilize", "leverage", "facilitate", "implement",
            "foster", "enhance", "streamline", "optimize",
            "underscore", "delve", "navigate", "harness",
            "exemplify", "spearhead", "revolutionize", "catalyze",
            "necessitate", "elucidate", "delineate", "substantiate",
        ],
        "connectors": [
            "however", "furthermore", "moreover", "nevertheless",
            "nonetheless", "additionally", "consequently", "therefore",
            "thus", "hence", "accordingly", "subsequently",
            "in conclusion", "to summarize", "in essence",
            "it is important to note", "it is worth mentioning",
        ],
        "phrases": [
            "plays a crucial role", "is of paramount importance",
            "in today's world", "in the modern era",
            "a wide range of", "it goes without saying",
            "in light of", "due to the fact that",
            "at the end of the day", "it is important to note that",
            "it should be noted that", "it is worth mentioning that",
            "first and foremost", "last but not least",
            "in order to", "with regard to", "as a matter of fact",
        ],
    },
    "ru": {
        "adverbs": [
            "значительно", "существенно", "чрезвычайно", "безусловно",
            "несомненно", "неоспоримо", "принципиально", "непосредственно",
            "кардинально", "всесторонне", "исключительно", "преимущественно",
        ],
        "adjectives": [
            "комплексный", "всеобъемлющий", "инновационный", "ключевой",
            "основополагающий", "первостепенный", "фундаментальный",
            "принципиальный", "многогранный", "всесторонний",
        ],
        "verbs": [
            "осуществлять", "реализовывать", "способствовать",
            "обеспечивать", "характеризоваться", "представлять собой",
            "являться", "функционировать", "оказывать влияние",
        ],
        "connectors": [
            "однако", "тем не менее", "вместе с тем", "кроме того",
            "более того", "помимо этого", "таким образом",
            "следовательно", "безусловно", "несомненно",
            "в заключение", "подводя итог", "исходя из вышесказанного",
            "необходимо отметить", "стоит подчеркнуть",
        ],
        "phrases": [
            "играет ключевую роль", "имеет первостепенное значение",
            "в современном мире", "на сегодняшний день",
            "широкий спектр", "не подлежит сомнению",
            "является одним из", "представляет собой",
            "в рамках данного", "с учётом того что",
            "необходимо подчеркнуть", "следует отметить",
        ],
    },
    "uk": {
        "adverbs": [
            "значно", "суттєво", "надзвичайно", "безумовно",
            "безсумнівно", "незаперечно", "принципово", "безпосередньо",
            "кардинально", "всебічно", "виключно", "переважно",
        ],
        "adjectives": [
            "комплексний", "всеосяжний", "інноваційний", "ключовий",
            "основоположний", "першочерговий", "фундаментальний",
            "принциповий", "багатогранний", "всебічний",
        ],
        "connectors": [
            "однак", "тим не менш", "разом з тим", "крім того",
            "більш того", "окрім цього", "таким чином",
            "отже", "безумовно", "безсумнівно",
            "на завершення", "підсумовуючи",
            "необхідно зазначити", "варто підкреслити",
        ],
        "phrases": [
            "відіграє ключову роль", "має першочергове значення",
            "у сучасному світі", "на сьогоднішній день",
            "широкий спектр", "є одним з",
            "являє собою", "у рамках даного",
        ],
    },
    "de": {
        "adverbs": [
            "erheblich", "wesentlich", "grundlegend", "insbesondere",
            "zweifellos", "unbestreitbar", "maßgeblich", "zunehmend",
        ],
        "adjectives": [
            "umfassend", "entscheidend", "innovativ", "grundlegend",
            "weitreichend", "vielfältig", "bedeutend", "wesentlich",
        ],
        "connectors": [
            "jedoch", "darüber hinaus", "außerdem", "nichtsdestotrotz",
            "folglich", "demzufolge", "zusammenfassend",
            "es ist wichtig zu beachten", "abschließend",
        ],
        "phrases": [
            "spielt eine entscheidende Rolle",
            "ist von größter Bedeutung",
            "in der heutigen Welt",
            "ein breites Spektrum",
        ],
    },
    "es": {
        "adverbs": [
            "significativamente", "sustancialmente", "considerablemente",
            "fundamentalmente", "esencialmente", "particularmente",
            "predominantemente", "inherentemente",
        ],
        "adjectives": [
            "integral", "crucial", "innovador", "robusto",
            "holístico", "transformador", "multifacético", "imperativo",
        ],
        "connectors": [
            "sin embargo", "además", "no obstante", "por lo tanto",
            "en consecuencia", "asimismo", "en conclusión",
            "cabe destacar", "vale la pena mencionar",
        ],
        "phrases": [
            "juega un papel crucial",
            "es de suma importancia",
            "en el mundo actual",
            "una amplia gama de",
        ],
    },
    "fr": {
        "adverbs": [
            "considérablement", "fondamentalement", "essentiellement",
            "particulièrement", "incontestablement", "intrinsèquement",
        ],
        "adjectives": [
            "compréhensif", "crucial", "innovant", "fondamental",
            "holistique", "transformateur", "multifacette",
        ],
        "connectors": [
            "cependant", "de plus", "néanmoins", "par conséquent",
            "en outre", "ainsi", "en conclusion",
            "il convient de noter", "il est important de souligner",
        ],
        "phrases": [
            "joue un rôle crucial",
            "est d'une importance capitale",
            "dans le monde actuel",
            "un large éventail de",
        ],
    },
    "pl": {
        "adverbs": [
            "znacząco", "istotnie", "zasadniczo", "fundamentalnie",
            "niewątpliwie", "bezsprzecznie", "szczególnie",
        ],
        "adjectives": [
            "kompleksowy", "kluczowy", "innowacyjny", "fundamentalny",
            "wieloaspektowy", "wszechstronny",
        ],
        "connectors": [
            "jednakże", "ponadto", "niemniej jednak", "w związku z tym",
            "podsumowując", "należy podkreślić",
        ],
    },
    "pt": {
        "adverbs": [
            "significativamente", "substancialmente", "consideravelmente",
            "fundamentalmente", "essencialmente", "particularmente",
        ],
        "adjectives": [
            "abrangente", "crucial", "inovador", "robusto",
            "holístico", "transformador", "multifacetado",
        ],
        "connectors": [
            "no entanto", "além disso", "contudo", "portanto",
            "consequentemente", "em conclusão",
            "vale a pena mencionar",
        ],
    },
    "it": {
        "adverbs": [
            "significativamente", "sostanzialmente", "considerevolmente",
            "fondamentalmente", "essenzialmente", "particolarmente",
        ],
        "adjectives": [
            "completo", "cruciale", "innovativo", "robusto",
            "olistico", "trasformativo", "sfaccettato",
        ],
        "connectors": [
            "tuttavia", "inoltre", "ciononostante", "pertanto",
            "di conseguenza", "in conclusione",
            "è importante notare",
        ],
    },
}


# ═══════════════════════════════════════════════════════════════
#  Cache
# ═══════════════════════════════════════════════════════════════

_marker_cache: dict[str, dict[str, list[str]]] = {}
_cache_loaded = False


# ═══════════════════════════════════════════════════════════════
#  Core loader
# ═══════════════════════════════════════════════════════════════


def _marker_path(lang: str) -> Path:
    """Path to JSON marker file for a language."""
    return _DATA_DIR / f"{_MARKER_PREFIX}{lang}{_MARKER_SUFFIX}"


def _ensure_data_dir() -> None:
    """Create data directory if it doesn't exist."""
    _DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_ai_markers(lang: str) -> dict[str, set[str]]:
    """Load AI markers for a language.

    Priority: JSON file > built-in fallback.
    Returns dict of category → set of marker strings.

    Args:
        lang: language code ("en", "ru", "uk", etc.)

    Returns:
        Dict mapping category names to sets of marker words/phrases
    """
    # Check cache first
    global _cache_loaded
    if lang in _marker_cache:
        return {k: set(v) for k, v in _marker_cache[lang].items()}

    # Try loading from JSON file
    path = _marker_path(lang)
    markers: Optional[dict[str, list[str]]] = None

    if path.exists():
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            markers = data.get("markers", data)
            logger.debug("Loaded AI markers from %s", path)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to read %s: %s", path, e)

    # Fall back to built-in
    if markers is None:
        builtin = _BUILTIN_AI_MARKERS.get(lang)
        if builtin:
            markers = builtin
            logger.debug("Using built-in AI markers for '%s'", lang)
        else:
            logger.debug("No AI markers available for '%s'", lang)
            return {}

    # Cache it
    _marker_cache[lang] = markers
    return {k: set(v) for k, v in markers.items()}


def load_all_markers() -> dict[str, dict[str, set[str]]]:
    """Load AI markers for all available languages.

    Returns:
        Dict mapping lang code → category → set of markers
    """
    all_langs = set(_BUILTIN_AI_MARKERS.keys())

    # Also check for JSON files
    if _DATA_DIR.exists():
        for f in _DATA_DIR.iterdir():
            if f.name.startswith(_MARKER_PREFIX) and f.name.endswith(_MARKER_SUFFIX):
                lang = f.name[len(_MARKER_PREFIX):-len(_MARKER_SUFFIX)]
                all_langs.add(lang)

    return {lang: load_ai_markers(lang) for lang in sorted(all_langs)}


# ═══════════════════════════════════════════════════════════════
#  Export / Import
# ═══════════════════════════════════════════════════════════════


def export_markers_to_json(
    lang: Optional[str] = None,
    output_dir: Optional[str] = None,
) -> list[str]:
    """Export AI markers to JSON files.

    Args:
        lang: Specific language to export (None = all)
        output_dir: Output directory (None = texthumanize/data/)

    Returns:
        List of created file paths
    """
    out_dir = Path(output_dir) if output_dir else _DATA_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    langs = [lang] if lang else list(_BUILTIN_AI_MARKERS.keys())
    created: list[str] = []

    for lng in langs:
        builtin = _BUILTIN_AI_MARKERS.get(lng)
        if not builtin:
            continue

        data = {
            "schema_version": _SCHEMA_VERSION,
            "language": lng,
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "markers": {
                category: sorted(words)
                for category, words in builtin.items()
            },
            "stats": {
                category: len(words)
                for category, words in builtin.items()
            },
        }

        path = out_dir / f"{_MARKER_PREFIX}{lng}{_MARKER_SUFFIX}"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        created.append(str(path))
        logger.info("Exported AI markers: %s (%d categories)",
                     path, len(builtin))

    # Write meta file
    meta = {
        "schema_version": _SCHEMA_VERSION,
        "languages": langs,
        "exported_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_languages": len(langs),
        "total_markers": sum(
            sum(len(v) for v in _BUILTIN_AI_MARKERS.get(l, {}).values())
            for l in langs
        ),
    }
    meta_path = out_dir / _META_FILE
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    created.append(str(meta_path))

    return created


def import_markers_from_json(
    path: str,
    merge: bool = True,
) -> dict[str, list[str]]:
    """Import AI markers from a JSON file.

    Args:
        path: Path to JSON marker file
        merge: If True, merge with existing markers; if False, replace

    Returns:
        The loaded markers dict

    Raises:
        FileNotFoundError: If the file doesn't exist
        json.JSONDecodeError: If the file has invalid JSON
    """
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    markers = data.get("markers", data)
    lang = data.get("language", "")

    if not lang:
        # Try to extract from filename
        name = Path(path).stem
        if name.startswith(_MARKER_PREFIX):
            lang = name[len(_MARKER_PREFIX):]

    if lang and merge:
        existing = _BUILTIN_AI_MARKERS.get(lang, {})
        for category, words in existing.items():
            if category not in markers:
                markers[category] = list(words)  # type: ignore[assignment]
            else:
                merged = set(markers[category]) | set(words)
                markers[category] = sorted(merged)  # type: ignore[assignment]

    # Update cache
    if lang:
        _marker_cache[lang] = markers

    return dict(markers)


def update_markers(
    lang: str,
    category: str,
    words: list[str],
    mode: str = "add",
) -> dict[str, list[str]]:
    """Update AI markers for a language and save to JSON.

    Args:
        lang: Language code
        category: Category name (e.g., "adverbs", "phrases")
        words: Words/phrases to add or remove
        mode: "add" or "remove"

    Returns:
        Updated markers for the language
    """
    current = load_ai_markers(lang)
    current_list = {k: sorted(v) for k, v in current.items()}

    if category not in current_list:
        current_list[category] = []

    existing = set(current_list[category])
    if mode == "add":
        existing.update(words)
    elif mode == "remove":
        existing -= set(words)
    current_list[category] = sorted(existing)

    # Save to JSON
    _ensure_data_dir()
    data = {
        "schema_version": _SCHEMA_VERSION,
        "language": lang,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "markers": current_list,
        "stats": {k: len(v) for k, v in current_list.items()},
    }

    path = _marker_path(lang)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Update cache
    _marker_cache[lang] = current_list
    logger.info("Updated %s markers for '%s': %s %d words",
                 category, lang, mode, len(words))

    return current_list


def get_available_languages() -> list[str]:
    """List all languages with AI markers available."""
    langs = set(_BUILTIN_AI_MARKERS.keys())
    if _DATA_DIR.exists():
        for f in _DATA_DIR.iterdir():
            if f.name.startswith(_MARKER_PREFIX) and f.name.endswith(_MARKER_SUFFIX):
                lang = f.name[len(_MARKER_PREFIX):-len(_MARKER_SUFFIX)]
                langs.add(lang)
    return sorted(langs)


def clear_cache() -> None:
    """Clear the marker cache (forces reload from files)."""
    global _cache_loaded
    _marker_cache.clear()
    _cache_loaded = False
