"""Updatable dictionary system — JSON overlay for built-in language packs.

Allows users to update AI pattern dictionaries, synonyms, and other
language-specific data without modifying source code.

JSON overlay files are stored in texthumanize/data/ and loaded at runtime,
merging with the built-in language pack dicts.

Usage::

    from texthumanize.dictionaries import load_dict, update_dict, export_dict

    # Load the current merged dictionary for English
    d = load_dict("en")

    # Add custom AI patterns
    update_dict("en", {"bureaucratic": {"synergize": ["work together"]}})

    # Export current dict as JSON
    export_dict("en", "en_custom.json")
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
_OVERLAY_CACHE: dict[str, dict[str, Any]] = {}


def _ensure_data_dir() -> None:
    """Create data directory if it doesn't exist."""
    os.makedirs(_DATA_DIR, exist_ok=True)


def _overlay_path(lang: str) -> str:
    """Get path to JSON overlay file for a language."""
    return os.path.join(_DATA_DIR, f"{lang}_overlay.json")


def _load_builtin(lang: str) -> dict[str, Any]:
    """Load the built-in language pack dictionary."""
    from texthumanize.lang import get_lang_pack
    pack = get_lang_pack(lang)
    if pack is None:
        return {}
    return dict(pack)


def _load_overlay(lang: str) -> dict[str, Any]:
    """Load JSON overlay for a language, if it exists."""
    path = _overlay_path(lang)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
        logger.debug("Loaded overlay for '%s': %d keys", lang, len(data))
        return data
    except Exception as e:
        logger.warning("Could not load overlay for '%s': %s", lang, e)
        return {}


def _deep_merge(base: dict, overlay: dict) -> dict:
    """Deep merge overlay into base dict (overlay wins on conflicts).

    For list values, overlay replaces. For dict values, recurse.
    For sets, union.
    """
    result = dict(base)
    for key, val in overlay.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = _deep_merge(result[key], val)
        elif key in result and isinstance(result[key], set) and isinstance(val, (set, list)):
            result[key] = result[key] | set(val)
        else:
            result[key] = val
    return result


def load_dict(lang: str, force_reload: bool = False) -> dict[str, Any]:
    """Load merged dictionary for a language.

    Returns the built-in dict merged with any JSON overlay.
    Results are cached.
    """
    if lang in _OVERLAY_CACHE and not force_reload:
        return _OVERLAY_CACHE[lang]

    builtin = _load_builtin(lang)
    overlay = _load_overlay(lang)

    if overlay:
        merged = _deep_merge(builtin, overlay)
        logger.info("Merged %d overlay keys for '%s'", len(overlay), lang)
    else:
        merged = builtin

    _OVERLAY_CACHE[lang] = merged
    return merged


def update_dict(lang: str, updates: dict[str, Any]) -> None:
    """Update the JSON overlay for a language.

    Args:
        lang: Language code.
        updates: Dictionary of updates to merge into the overlay.
    """
    _ensure_data_dir()
    existing = _load_overlay(lang)
    merged = _deep_merge(existing, updates)

    path = _overlay_path(lang)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    # Invalidate cache
    _OVERLAY_CACHE.pop(lang, None)
    logger.info("Updated overlay for '%s': %d keys", lang, len(merged))


def export_dict(lang: str, output_path: str) -> None:
    """Export the current merged dictionary as JSON.

    Useful for inspection, backup, or sharing custom dictionaries.
    """
    merged = load_dict(lang, force_reload=True)
    # Convert sets to lists for JSON serialization
    serializable = _make_serializable(merged)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(serializable, f, ensure_ascii=False, indent=2)
    logger.info("Exported dict for '%s' to %s", lang, output_path)


def _make_serializable(obj: Any) -> Any:
    """Convert non-JSON-serializable types (sets, etc.) to JSON-safe types."""
    if isinstance(obj, set):
        return sorted(obj)
    if isinstance(obj, dict):
        return {k: _make_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_make_serializable(v) for v in obj]
    return obj


def list_overlays() -> dict[str, str]:
    """List all available JSON overlays.

    Returns dict of {lang: file_path}.
    """
    _ensure_data_dir()
    overlays = {}
    for f in os.listdir(_DATA_DIR):
        if f.endswith("_overlay.json"):
            lang = f.replace("_overlay.json", "")
            overlays[lang] = os.path.join(_DATA_DIR, f)
    return overlays


def reset_overlay(lang: str) -> None:
    """Delete the JSON overlay for a language, reverting to built-in."""
    path = _overlay_path(lang)
    if os.path.exists(path):
        os.remove(path)
    _OVERLAY_CACHE.pop(lang, None)
    logger.info("Reset overlay for '%s'", lang)
