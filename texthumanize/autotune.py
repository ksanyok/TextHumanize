"""Auto-tune — feedback loop for adaptive parameter optimization.

Stores processing history and adjusts pipeline parameters to converge
on optimal quality. Works entirely offline / rule-based, no ML.

Usage:

    from texthumanize import humanize
    from texthumanize.autotune import AutoTuner

    tuner = AutoTuner()
    result = humanize(text, intensity=tuner.suggest_intensity(text, lang="en"))
    tuner.record(result)
    # After accumulating 10+ records the tuner adapts parameters
    params = tuner.suggest_params(lang="en")
"""

from __future__ import annotations

import json
import logging
import statistics
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

@dataclass
class TuneRecord:
    """Single processing record for the feedback loop."""

    lang: str
    profile: str
    intensity: int
    ai_before: float
    ai_after: float
    change_ratio: float
    quality_score: float
    timestamp: float = 0.0

    def __post_init__(self) -> None:
        if self.timestamp == 0.0:
            self.timestamp = time.time()

@dataclass
class TuneParams:
    """Suggested pipeline parameters based on feedback history."""

    intensity: int = 60
    max_change_ratio: float = 0.40
    confidence: float = 0.0  # 0-1, increases with more records

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

class AutoTuner:
    """Feedback-driven parameter optimizer.

    Collects processing results and adjusts recommended parameters
    to maximize quality while keeping change_ratio within bounds.

    Args:
        history_path: Optional path to persist history as JSON.
            If None, history is kept in-memory only.
        max_records: Maximum number of records to retain.
    """

    def __init__(
        self,
        history_path: str | Path | None = None,
        max_records: int = 500,
    ) -> None:
        self._records: list[TuneRecord] = []
        self._max_records = max_records
        self._history_path = Path(history_path) if history_path else None

        if self._history_path and self._history_path.exists():
            self._load()

    # ─── Public API ───────────────────────────────────────────

    def record(self, result: Any) -> None:
        """Record a HumanizeResult for future parameter optimization.

        Args:
            result: A ``HumanizeResult`` from ``humanize()``.
        """
        rec = TuneRecord(
            lang=getattr(result, "lang", "en"),
            profile=getattr(result, "profile", "web"),
            intensity=getattr(result, "intensity", 60),
            ai_before=_get_metric(result, "artificiality_score", "metrics_before"),
            ai_after=_get_metric(result, "artificiality_score", "metrics_after"),
            change_ratio=getattr(result, "change_ratio", 0.0),
            quality_score=getattr(result, "quality_score", 0.0),
        )
        self._records.append(rec)

        # Trim old records
        if len(self._records) > self._max_records:
            self._records = self._records[-self._max_records:]

        if self._history_path:
            self._save()

    def suggest_intensity(
        self,
        text: str,
        lang: str = "en",
        profile: str = "web",
    ) -> int:
        """Suggest optimal intensity based on feedback history.

        Args:
            text: The text about to be processed.
            lang: Language code.
            profile: Processing profile.

        Returns:
            Recommended intensity value (0-100).
        """
        params = self.suggest_params(lang=lang, profile=profile)
        return params.intensity

    def suggest_params(
        self,
        lang: str = "en",
        profile: str | None = None,
    ) -> TuneParams:
        """Suggest optimal parameters based on accumulated history.

        Analyzes past results to find the intensity that produces
        the best quality_score while keeping change_ratio < 0.4.

        Args:
            lang: Language code.
            profile: Optional profile filter.

        Returns:
            TuneParams with recommended settings.
        """
        # Filter relevant records
        relevant = [
            r for r in self._records
            if r.lang == lang and (profile is None or r.profile == profile)
        ]

        if len(relevant) < 3:
            # Not enough data — return defaults
            return TuneParams(intensity=60, max_change_ratio=0.40, confidence=0.0)

        # ── Find the sweet spot ───────────────────────────────
        # Group by intensity bucket (round to nearest 10)
        buckets: dict[int, list[TuneRecord]] = {}
        for rec in relevant:
            bucket = round(rec.intensity / 10) * 10
            buckets.setdefault(bucket, []).append(rec)

        best_intensity = 60
        best_quality = 0.0

        for bucket_intensity, recs in buckets.items():
            avg_quality = statistics.mean(r.quality_score for r in recs)
            avg_change = statistics.mean(r.change_ratio for r in recs)
            # Penalize if average change_ratio is too high
            if avg_change > 0.35:
                avg_quality *= 0.7
            if avg_quality > best_quality:
                best_quality = avg_quality
                best_intensity = bucket_intensity

        # ── Optimal max_change_ratio ──────────────────────────
        good_records = [
            r for r in relevant if r.quality_score > 0.6
        ]
        if good_records:
            change_ratios = [r.change_ratio for r in good_records]
            optimal_max_change = min(
                0.45,
                max(0.20, statistics.quantiles(change_ratios, n=4)[-1] + 0.05)
                if len(change_ratios) >= 4
                else 0.40,
            )
        else:
            optimal_max_change = 0.40

        # Confidence scales with record count
        confidence = min(1.0, len(relevant) / 30.0)

        return TuneParams(
            intensity=best_intensity,
            max_change_ratio=round(optimal_max_change, 2),
            confidence=round(confidence, 2),
        )

    def summary(self) -> dict[str, Any]:
        """Summary statistics of the feedback history.

        Returns:
            Dict with counts, averages, and per-lang breakdown.
        """
        if not self._records:
            return {"total_records": 0}

        by_lang: dict[str, list[TuneRecord]] = {}
        for rec in self._records:
            by_lang.setdefault(rec.lang, []).append(rec)

        lang_stats = {}
        for lang, recs in by_lang.items():
            lang_stats[lang] = {
                "count": len(recs),
                "avg_quality": round(statistics.mean(r.quality_score for r in recs), 3),
                "avg_change_ratio": round(statistics.mean(r.change_ratio for r in recs), 3),
                "avg_ai_delta": round(
                    statistics.mean(r.ai_before - r.ai_after for r in recs), 1,
                ),
                "suggested": self.suggest_params(lang=lang).to_dict(),
            }

        return {
            "total_records": len(self._records),
            "languages": lang_stats,
        }

    def reset(self) -> None:
        """Clear all history."""
        self._records.clear()
        if self._history_path and self._history_path.exists():
            self._history_path.unlink()

    # ─── Persistence ──────────────────────────────────────────

    def _save(self) -> None:
        """Persist history to JSON file."""
        if not self._history_path:
            return
        self._history_path.parent.mkdir(parents=True, exist_ok=True)
        data = [asdict(r) for r in self._records]
        self._history_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _load(self) -> None:
        """Load history from JSON file."""
        if not self._history_path or not self._history_path.exists():
            return
        try:
            data = json.loads(self._history_path.read_text(encoding="utf-8"))
            self._records = [TuneRecord(**d) for d in data]
        except (json.JSONDecodeError, TypeError, KeyError):
            self._records = []

def _get_metric(result: Any, key: str, section: str) -> float:
    """Extract metric from HumanizeResult."""
    metrics = getattr(result, section, {})
    if isinstance(metrics, dict):
        return float(metrics.get(key, 0.0))
    return 0.0
