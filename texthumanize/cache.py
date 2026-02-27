"""Thread-safe LRU result cache for TextHumanize.

Caches results of expensive operations (humanize, detect_ai, analyze)
keyed by (text_hash, params). Uses SHA-256 hash of text content for
memory efficiency — full texts are never stored in the cache.

Usage:
    from texthumanize.cache import result_cache, cache_stats

    # Cache is used automatically by core functions when enabled.
    # To clear:
    result_cache.clear()

    # To check stats:
    print(cache_stats())  # {"hits": 42, "misses": 10, "size": 52}
"""

from __future__ import annotations

import hashlib
import logging
import threading
from collections import OrderedDict
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_MAX_SIZE = 256


class _LRUCache:
    """Thread-safe LRU cache with configurable max size."""

    def __init__(self, max_size: int = _DEFAULT_MAX_SIZE) -> None:
        self._max_size = max_size
        self._data: OrderedDict[str, Any] = OrderedDict()
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def _make_key(self, text: str, **params: Any) -> str:
        """Create a cache key from text hash + sorted params."""
        h = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
        param_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        return f"{h}:{param_str}"

    def get(self, text: str, **params: Any) -> Any | None:
        """Get cached result, or None if not found."""
        key = self._make_key(text, **params)
        with self._lock:
            if key in self._data:
                self._data.move_to_end(key)
                self._hits += 1
                return self._data[key]
            self._misses += 1
            return None

    def put(self, text: str, result: Any, **params: Any) -> None:
        """Store a result in cache."""
        key = self._make_key(text, **params)
        with self._lock:
            if key in self._data:
                self._data.move_to_end(key)
            else:
                if len(self._data) >= self._max_size:
                    self._data.popitem(last=False)
            self._data[key] = result

    def clear(self) -> None:
        """Clear all cached entries."""
        with self._lock:
            self._data.clear()
            self._hits = 0
            self._misses = 0

    def stats(self) -> dict[str, int]:
        """Return cache statistics."""
        with self._lock:
            return {
                "hits": self._hits,
                "misses": self._misses,
                "size": len(self._data),
                "max_size": self._max_size,
            }


# Global cache instance — used by core functions
result_cache = _LRUCache(max_size=_DEFAULT_MAX_SIZE)


def cache_stats() -> dict[str, int]:
    """Return current cache statistics."""
    return result_cache.stats()
