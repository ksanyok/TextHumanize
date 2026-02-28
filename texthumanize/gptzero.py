"""GPTZero API integration for external AI-detection validation.

Provides a client for the GPTZero API (https://gptzero.me) to validate
AI-generated text detection against an industry-standard external detector.

Usage:
    from texthumanize.gptzero import GPTZeroClient

    client = GPTZeroClient(api_key="your-key")
    result = client.detect("Some text to check...")
    print(result.ai_probability)  # 0.0–1.0

The client supports:
    - Single document detection
    - Batch detection (up to 50 documents)
    - Sentence-level scanning
    - Rate limiting and retry logic
    - Caching of recent results

Requires a GPTZero API key (free tier: 10K words/month).
Set via GPTZERO_API_KEY environment variable or pass directly.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
#  Constants
# ═══════════════════════════════════════════════════════════════

_GPTZERO_API_URL = "https://api.gptzero.me/v2/predict"
_GPTZERO_BATCH_URL = "https://api.gptzero.me/v2/predict/files"
_DEFAULT_TIMEOUT = 30
_MAX_RETRIES = 3
_RETRY_DELAY = 2.0
_CACHE_MAX_SIZE = 256  # LRU cache size


# ═══════════════════════════════════════════════════════════════
#  Result data classes
# ═══════════════════════════════════════════════════════════════


@dataclass
class SentenceResult:
    """Per-sentence AI detection result."""
    text: str
    ai_probability: float
    generated_probability: float  # alias
    highlight: bool  # True if flagged as AI-generated


@dataclass
class GPTZeroResult:
    """Result from GPTZero API detection."""

    # Document-level scores
    ai_probability: float  # 0.0 = human, 1.0 = AI
    human_probability: float
    mixed_probability: float

    # Classification
    predicted_class: str  # "human", "ai", "mixed"

    # Per-sentence breakdown
    sentences: list[SentenceResult] = field(default_factory=list)

    # Metadata
    scan_id: str = ""
    model_version: str = ""
    raw_response: dict[str, Any] = field(default_factory=dict)

    @property
    def is_ai(self) -> bool:
        return self.predicted_class == "ai"

    @property
    def is_human(self) -> bool:
        return self.predicted_class == "human"

    @property
    def is_mixed(self) -> bool:
        return self.predicted_class == "mixed"


@dataclass
class BatchResult:
    """Result from batch GPTZero detection."""
    results: list[GPTZeroResult] = field(default_factory=list)
    total_documents: int = 0
    processing_time: float = 0.0


# ═══════════════════════════════════════════════════════════════
#  GPTZero API Client
# ═══════════════════════════════════════════════════════════════


class GPTZeroClient:
    """Client for the GPTZero AI text detection API.

    Supports single-document and batch detection with automatic retry,
    rate limiting, and LRU caching of results.

    Example:
        >>> client = GPTZeroClient()  # uses GPTZERO_API_KEY env var
        >>> result = client.detect("Hello, this is some text.")
        >>> print(result.ai_probability)
        0.02
        >>> print(result.predicted_class)
        'human'
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: int = _DEFAULT_TIMEOUT,
        max_retries: int = _MAX_RETRIES,
        cache_enabled: bool = True,
    ) -> None:
        self.api_key = api_key or os.environ.get("GPTZERO_API_KEY", "")
        self.timeout = timeout
        self.max_retries = max_retries
        self._cache_enabled = cache_enabled
        self._cache: dict[str, GPTZeroResult] = {}
        self._cache_order: list[str] = []
        self._last_request_time: float = 0.0
        self._min_request_interval: float = 0.5  # seconds between requests

    @property
    def is_configured(self) -> bool:
        """Check if API key is available."""
        return bool(self.api_key)

    def detect(self, text: str, include_sentences: bool = True) -> GPTZeroResult:
        """Detect AI-generated content in a single document.

        Args:
            text: The text to analyze (minimum 50 characters recommended)
            include_sentences: Include per-sentence analysis

        Returns:
            GPTZeroResult with detection scores

        Raises:
            ValueError: If text is empty or API key is missing
            ConnectionError: If API is unreachable after retries
        """
        if not text or not text.strip():
            raise ValueError("Text must not be empty")

        if not self.api_key:
            raise ValueError(
                "GPTZero API key required. Set GPTZERO_API_KEY environment variable "
                "or pass api_key to GPTZeroClient()."
            )

        # Check cache
        cache_key = self._cache_key(text)
        if self._cache_enabled and cache_key in self._cache:
            logger.debug("GPTZero cache hit")
            return self._cache[cache_key]

        # Rate limiting
        self._rate_limit()

        # Build request
        payload = {
            "document": text,
            "version": "2024-04-04",
        }
        if not include_sentences:
            payload["multilingual"] = "false"

        # Execute with retry
        response = self._request(_GPTZERO_API_URL, payload)
        result = self._parse_response(response)

        # Cache result
        if self._cache_enabled:
            self._cache_put(cache_key, result)

        return result

    def detect_batch(self, texts: list[str]) -> BatchResult:
        """Detect AI content in multiple documents.

        Args:
            texts: List of texts (max 50 per batch)

        Returns:
            BatchResult with per-document results
        """
        if not texts:
            return BatchResult()

        if len(texts) > 50:
            raise ValueError("Maximum 50 documents per batch")

        start_time = time.monotonic()
        results: list[GPTZeroResult] = []

        # GPTZero batch API expects individual requests
        for text in texts:
            try:
                result = self.detect(text)
                results.append(result)
            except Exception as exc:
                logger.warning("Batch item failed: %s", exc)
                results.append(GPTZeroResult(
                    ai_probability=0.0,
                    human_probability=0.0,
                    mixed_probability=0.0,
                    predicted_class="error",
                ))

        elapsed = time.monotonic() - start_time
        return BatchResult(
            results=results,
            total_documents=len(texts),
            processing_time=elapsed,
        )

    def validate_against_local(
        self,
        text: str,
        local_score: float,
    ) -> dict[str, Any]:
        """Compare local AI detection score against GPTZero.

        Args:
            text: Text to check
            local_score: Local detector's AI probability (0–1)

        Returns:
            Dict with comparison metrics
        """
        external = self.detect(text)

        agreement = 1.0 - abs(local_score - external.ai_probability)
        local_class = "ai" if local_score > 0.5 else "human"
        classes_match = local_class == external.predicted_class

        return {
            "local_score": local_score,
            "gptzero_score": external.ai_probability,
            "gptzero_class": external.predicted_class,
            "agreement": agreement,
            "classes_match": classes_match,
            "delta": abs(local_score - external.ai_probability),
            "sentences_flagged": sum(1 for s in external.sentences if s.highlight),
            "total_sentences": len(external.sentences),
        }

    # ─── Internal methods ──────────────────────────────────────

    def _request(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Make HTTP request with retry logic."""
        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-api-key": self.api_key,
        }

        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries):
            try:
                req = urllib.request.Request(url, data=data, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    body = resp.read().decode("utf-8")
                    return json.loads(body)  # type: ignore[no-any-return]
            except urllib.error.HTTPError as e:
                last_error = e
                if e.code == 429:
                    # Rate limited — wait longer
                    wait = _RETRY_DELAY * (2 ** attempt)
                    logger.warning("GPTZero rate limited, waiting %.1fs", wait)
                    time.sleep(wait)
                elif e.code >= 500:
                    # Server error — retry
                    time.sleep(_RETRY_DELAY)
                else:
                    raise ConnectionError(f"GPTZero API error {e.code}: {e.reason}") from e
            except urllib.error.URLError as e:
                last_error = e
                logger.warning("GPTZero connection error (attempt %d): %s", attempt + 1, e)
                time.sleep(_RETRY_DELAY)
            except Exception as e:
                last_error = e
                logger.warning("GPTZero request error (attempt %d): %s", attempt + 1, e)
                time.sleep(_RETRY_DELAY)

        raise ConnectionError(
            f"GPTZero API unreachable after {self.max_retries} attempts: {last_error}"
        )

    def _parse_response(self, resp: dict[str, Any]) -> GPTZeroResult:
        """Parse GPTZero API response into structured result."""
        documents = resp.get("documents", [{}])
        doc = documents[0] if documents else {}

        # Extract class probabilities
        class_probs = doc.get("class_probabilities", {})
        ai_prob = class_probs.get("ai", doc.get("completely_generated_prob", 0.0))
        human_prob = class_probs.get("human", 1.0 - ai_prob)
        mixed_prob = class_probs.get("mixed", 0.0)

        # Predicted class
        predicted = doc.get("predicted_class", "unknown")
        if predicted == "unknown":
            if ai_prob > 0.5:
                predicted = "ai"
            elif mixed_prob > 0.3:
                predicted = "mixed"
            else:
                predicted = "human"

        # Per-sentence analysis
        sentences: list[SentenceResult] = []
        for sent in doc.get("sentences", []):
            sentences.append(SentenceResult(
                text=sent.get("sentence", ""),
                ai_probability=sent.get("generated_prob", 0.0),
                generated_probability=sent.get("generated_prob", 0.0),
                highlight=sent.get("highlight_sentence_for_ai", False),
            ))

        return GPTZeroResult(
            ai_probability=ai_prob,
            human_probability=human_prob,
            mixed_probability=mixed_prob,
            predicted_class=predicted,
            sentences=sentences,
            scan_id=resp.get("scan_id", ""),
            model_version=doc.get("model_version", ""),
            raw_response=resp,
        )

    def _rate_limit(self) -> None:
        """Enforce minimum interval between requests."""
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.monotonic()

    def _cache_key(self, text: str) -> str:
        """Generate cache key from text content."""
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def _cache_put(self, key: str, value: GPTZeroResult) -> None:
        """Put result in LRU cache."""
        if key in self._cache:
            self._cache_order.remove(key)
        elif len(self._cache) >= _CACHE_MAX_SIZE:
            # Evict oldest
            oldest = self._cache_order.pop(0)
            del self._cache[oldest]
        self._cache[key] = value
        self._cache_order.append(key)
