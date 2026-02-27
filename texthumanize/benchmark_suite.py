"""Benchmark suite for TextHumanize quality assessment.

Automated measurement of humanization quality across
dimensions: AI-detection evasion, naturalness preservation,
meaning retention, diversity, and processing speed.

Usage:
    from texthumanize.benchmark_suite import BenchmarkSuite

    suite = BenchmarkSuite(lang="en")
    report = suite.run_all(samples)
    print(report.summary())
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

@dataclass
class BenchmarkResult:
    """Single benchmark measurement."""
    name: str
    score: float  # 0.0 - 1.0
    details: dict[str, Any] = field(default_factory=dict)
    elapsed_ms: float = 0.0


@dataclass
class BenchmarkReport:
    """Full benchmark report."""
    results: list[BenchmarkResult] = field(
        default_factory=list,
    )
    overall_score: float = 0.0
    elapsed_ms: float = 0.0

    def summary(self) -> str:
        lines = [
            "=== TextHumanize Benchmark Report ===",
            f"Overall Score: {self.overall_score:.1%}",
            f"Total Time: {self.elapsed_ms:.0f}ms",
            "",
        ]
        for r in self.results:
            lines.append(
                f"  {r.name}: {r.score:.1%} "
                f"({r.elapsed_ms:.0f}ms)"
            )
            for k, v in r.details.items():
                lines.append(f"    {k}: {v}")
        return "\n".join(lines)


class BenchmarkSuite:
    """Automated quality benchmarking.

    Measures humanization output across multiple dimensions
    and produces a normalized report.
    """

    def __init__(
        self,
        lang: str = "en",
        *,
        verbose: bool = False,
    ) -> None:
        self.lang = lang
        self.verbose = verbose

    def run_all(
        self,
        samples: list[dict[str, str]],
    ) -> BenchmarkReport:
        """Run full benchmark suite.

        Parameters:
            samples: List of {"original": str, "humanized": str}

        Returns:
            BenchmarkReport with all measurements.
        """
        if not samples:
            return BenchmarkReport()

        start = time.monotonic()
        results: list[BenchmarkResult] = []

        results.append(self._bench_detection_evasion(samples))
        results.append(self._bench_naturalness(samples))
        results.append(self._bench_meaning_retention(samples))
        results.append(self._bench_diversity(samples))
        results.append(self._bench_length_preservation(samples))
        results.append(self._bench_perplexity(samples))

        elapsed = (time.monotonic() - start) * 1000
        weights = [0.25, 0.20, 0.20, 0.15, 0.10, 0.10]
        overall = sum(
            r.score * w for r, w in zip(results, weights)
        )

        return BenchmarkReport(
            results=results,
            overall_score=round(overall, 4),
            elapsed_ms=round(elapsed, 1),
        )

    # ── Individual benchmarks ─────────────────────────────

    def _bench_detection_evasion(
        self, samples: list[dict[str, str]],
    ) -> BenchmarkResult:
        """Measure AI detection evasion rate."""
        t0 = time.monotonic()
        try:
            from texthumanize.statistical_detector import (
                StatisticalDetector,
            )
            det = StatisticalDetector(lang=self.lang)
        except ImportError:
            return BenchmarkResult(
                name="Detection Evasion",
                score=0.5,
                details={"error": "detector not available"},
            )

        evaded = 0
        total = len(samples)
        orig_scores: list[float] = []
        hum_scores: list[float] = []

        for s in samples:
            orig = s.get("original", "")
            hum = s.get("humanized", "")
            if not orig or not hum:
                continue
            o_res = det.detect(orig)
            h_res = det.detect(hum)
            orig_scores.append(o_res.get("probability", 0.5))
            hum_scores.append(h_res.get("probability", 0.5))
            if h_res.get("verdict", "") != "ai":
                evaded += 1

        score = evaded / max(total, 1)
        elapsed = (time.monotonic() - t0) * 1000

        avg_orig = (
            sum(orig_scores) / len(orig_scores)
            if orig_scores else 0.0
        )
        avg_hum = (
            sum(hum_scores) / len(hum_scores)
            if hum_scores else 0.0
        )

        return BenchmarkResult(
            name="Detection Evasion",
            score=round(score, 4),
            details={
                "evaded": evaded,
                "total": total,
                "avg_orig_ai_prob": round(avg_orig, 3),
                "avg_hum_ai_prob": round(avg_hum, 3),
                "reduction": round(avg_orig - avg_hum, 3),
            },
            elapsed_ms=round(elapsed, 1),
        )

    def _bench_naturalness(
        self, samples: list[dict[str, str]],
    ) -> BenchmarkResult:
        """Measure output naturalness via word LM."""
        t0 = time.monotonic()
        try:
            from texthumanize.word_lm import (
                WordLanguageModel,
            )
            lm = WordLanguageModel(lang=self.lang)
        except ImportError:
            return BenchmarkResult(
                name="Naturalness",
                score=0.5,
                details={"error": "word_lm not available"},
            )

        scores: list[int] = []
        for s in samples:
            hum = s.get("humanized", "")
            if not hum:
                continue
            res = lm.naturalness_score(hum)
            scores.append(res.get("naturalness", 50))

        avg = sum(scores) / len(scores) if scores else 50
        elapsed = (time.monotonic() - t0) * 1000

        return BenchmarkResult(
            name="Naturalness",
            score=round(min(avg / 100.0, 1.0), 4),
            details={
                "avg_score": round(avg, 1),
                "min": min(scores) if scores else 0,
                "max": max(scores) if scores else 0,
            },
            elapsed_ms=round(elapsed, 1),
        )

    def _bench_meaning_retention(
        self, samples: list[dict[str, str]],
    ) -> BenchmarkResult:
        """Measure semantic similarity (meaning retention)."""
        t0 = time.monotonic()
        try:
            from texthumanize.semantic import (
                semantic_similarity,
            )
        except ImportError:
            return BenchmarkResult(
                name="Meaning Retention",
                score=0.0,
                details={"error": "semantic not available"},
            )

        scores: list[float] = []
        for s in samples:
            orig = s.get("original", "")
            hum = s.get("humanized", "")
            if not orig or not hum:
                continue
            try:
                res = semantic_similarity(
                    orig, hum,
                )
                sim = res.overall if hasattr(res, 'overall') else 0.5
                scores.append(sim)
            except Exception:
                scores.append(0.0)

        avg = sum(scores) / len(scores) if scores else 0.0
        elapsed = (time.monotonic() - t0) * 1000

        return BenchmarkResult(
            name="Meaning Retention",
            score=round(avg, 4),
            details={
                "avg_similarity": round(avg, 3),
                "samples": len(scores),
            },
            elapsed_ms=round(elapsed, 1),
        )

    def _bench_diversity(
        self, samples: list[dict[str, str]],
    ) -> BenchmarkResult:
        """Measure output diversity."""
        t0 = time.monotonic()

        if len(samples) < 2:
            return BenchmarkResult(
                name="Diversity",
                score=0.5,
                details={"error": "need 2+ samples"},
            )

        hum_texts = [
            s.get("humanized", "")
            for s in samples if s.get("humanized")
        ]

        # Measure character-level Jaccard distance
        distances = []
        for i in range(len(hum_texts)):
            for j in range(i + 1, min(i + 5, len(hum_texts))):
                a_set = set(hum_texts[i].split())
                b_set = set(hum_texts[j].split())
                if not a_set and not b_set:
                    continue
                union = a_set | b_set
                inter = a_set & b_set
                jacc = 1.0 - (
                    len(inter) / max(len(union), 1)
                )
                distances.append(jacc)

        avg_dist = (
            sum(distances) / len(distances)
            if distances else 0.0
        )
        elapsed = (time.monotonic() - t0) * 1000

        return BenchmarkResult(
            name="Diversity",
            score=round(min(avg_dist, 1.0), 4),
            details={
                "avg_jaccard_dist": round(avg_dist, 3),
                "pairs": len(distances),
            },
            elapsed_ms=round(elapsed, 1),
        )

    def _bench_length_preservation(
        self, samples: list[dict[str, str]],
    ) -> BenchmarkResult:
        """Check output length stays reasonable."""
        t0 = time.monotonic()

        ratios = []
        for s in samples:
            orig = s.get("original", "")
            hum = s.get("humanized", "")
            if not orig:
                continue
            ratio = len(hum) / max(len(orig), 1)
            ratios.append(ratio)

        avg = sum(ratios) / len(ratios) if ratios else 1.0
        # Score: 1.0 if ratio ∈ [0.8, 1.2], degrades outside
        score = max(0, 1.0 - abs(avg - 1.0) * 2)
        elapsed = (time.monotonic() - t0) * 1000

        return BenchmarkResult(
            name="Length Preservation",
            score=round(score, 4),
            details={
                "avg_ratio": round(avg, 3),
                "min_ratio": (
                    round(min(ratios), 3) if ratios else 0
                ),
                "max_ratio": (
                    round(max(ratios), 3) if ratios else 0
                ),
            },
            elapsed_ms=round(elapsed, 1),
        )

    def _bench_perplexity(
        self, samples: list[dict[str, str]],
    ) -> BenchmarkResult:
        """Measure perplexity improvement."""
        t0 = time.monotonic()
        try:
            from texthumanize.word_lm import (
                WordLanguageModel,
            )
            lm = WordLanguageModel(lang=self.lang)
        except ImportError:
            return BenchmarkResult(
                name="Perplexity Boost",
                score=0.5,
                details={"error": "word_lm not available"},
            )

        improvements = []
        for s in samples:
            orig = s.get("original", "")
            hum = s.get("humanized", "")
            if not orig or not hum:
                continue
            pp_orig = lm.perplexity(orig)
            pp_hum = lm.perplexity(hum)
            if pp_orig > 0:
                # Higher perplexity = more human-like
                improvement = (pp_hum - pp_orig) / pp_orig
                improvements.append(improvement)

        avg = (
            sum(improvements) / len(improvements)
            if improvements else 0.0
        )
        # Score: >0 means improvement
        score = min(1.0, max(0, 0.5 + avg))
        elapsed = (time.monotonic() - t0) * 1000

        return BenchmarkResult(
            name="Perplexity Boost",
            score=round(score, 4),
            details={
                "avg_improvement": f"{avg:+.1%}",
                "samples": len(improvements),
            },
            elapsed_ms=round(elapsed, 1),
        )


# ── Quick benchmark ───────────────────────────────────────

def quick_benchmark(
    original: str,
    humanized: str,
    lang: str = "en",
) -> BenchmarkReport:
    """Run benchmark on a single pair."""
    suite = BenchmarkSuite(lang=lang)
    return suite.run_all([{
        "original": original,
        "humanized": humanized,
    }])
