"""TextHumanize Performance Benchmark — generates real numbers.

Usage:
    python benchmarks/run_benchmark.py
"""

from __future__ import annotations

import gc
import os
import sys
import time
import tracemalloc

# Ensure local package is used
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from texthumanize import (  # noqa: E402
    analyze,
    detect_ai,
    humanize,
    paraphrase,
)


# ─── Test texts ──────────────────────────────────────────────

TEXT_SHORT_EN = (
    "Furthermore, it is important to note that the implementation "
    "of comprehensive methodologies facilitates the optimization "
    "of operational processes in modern organizations."
)

TEXT_MEDIUM_EN = (
    "Furthermore, it is important to note that the implementation of "
    "comprehensive methodologies facilitates the optimization of operational "
    "processes in modern organizations. The utilization of advanced analytical "
    "frameworks enables stakeholders to make informed decisions. Additionally, "
    "the integration of cutting-edge technologies constitutes a significant "
    "advancement in terms of productivity enhancement. It should be noted that "
    "the deployment of cloud-based infrastructure provides scalable solutions "
    "for enterprise-grade applications. Moreover, the implementation of agile "
    "development practices has been shown to improve project delivery timelines."
)

TEXT_LONG_EN = TEXT_MEDIUM_EN * 5  # ~500 words

TEXT_RU = (
    "Необходимо отметить, что осуществление комплексных методологий "
    "способствует оптимизации операционных процессов в современных организациях. "
    "Данный подход является безусловно важным для достижения стратегических целей. "
    "Использование передовых аналитических фреймворков позволяет заинтересованным "
    "сторонам принимать обоснованные решения в рамках текущей деятельности."
)


# ─── Benchmark runner ────────────────────────────────────────

def bench(name: str, fn, *args, warmup: int = 1, runs: int = 5, **kwargs):
    """Run a benchmark and return timing + memory stats."""
    # Warmup
    for _ in range(warmup):
        fn(*args, **kwargs)

    gc.collect()
    tracemalloc.start()
    mem_before = tracemalloc.get_traced_memory()[0]

    times = []
    for _ in range(runs):
        t0 = time.perf_counter()
        result = fn(*args, **kwargs)
        t1 = time.perf_counter()
        times.append(t1 - t0)

    mem_after = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()

    avg_ms = sum(times) / len(times) * 1000
    min_ms = min(times) * 1000
    max_ms = max(times) * 1000
    mem_kb = (mem_after - mem_before) / 1024

    return {
        "name": name,
        "avg_ms": round(avg_ms, 1),
        "min_ms": round(min_ms, 1),
        "max_ms": round(max_ms, 1),
        "mem_peak_kb": round(mem_kb, 1),
        "runs": runs,
        "result": result,
    }


def count_words(text: str) -> int:
    return len(text.split())


def main():
    print("=" * 70)
    print("TextHumanize Performance Benchmark")
    print("=" * 70)

    from texthumanize import __version__
    print(f"Version: {__version__}")
    print(f"Python: {sys.version.split()[0]}")
    print()

    benchmarks = []

    # ── humanize() ────────────────────────────────────────────
    print("Running humanize benchmarks...")

    for label, text, lang in [
        ("Short EN (30 words)", TEXT_SHORT_EN, "en"),
        ("Medium EN (80 words)", TEXT_MEDIUM_EN, "en"),
        ("Long EN (~400 words)", TEXT_LONG_EN, "en"),
        ("Medium RU (55 words)", TEXT_RU, "ru"),
    ]:
        words = count_words(text)
        r = bench(f"humanize / {label}", humanize, text, lang=lang, seed=42)
        r["words"] = words
        r["ms_per_1k_words"] = round(r["avg_ms"] / words * 1000, 1) if words else 0
        benchmarks.append(r)
        print(f"  {label}: {r['avg_ms']:.1f}ms avg ({r['ms_per_1k_words']:.0f}ms/1K words)")

    # ── detect_ai() ──────────────────────────────────────────
    print("\nRunning detect_ai benchmarks...")

    for label, text, lang in [
        ("Short EN", TEXT_SHORT_EN, "en"),
        ("Medium EN", TEXT_MEDIUM_EN, "en"),
        ("Long EN", TEXT_LONG_EN, "en"),
    ]:
        words = count_words(text)
        r = bench(f"detect_ai / {label}", detect_ai, text, lang=lang)
        r["words"] = words
        benchmarks.append(r)
        score = r["result"].get("score", 0)
        print(f"  {label}: {r['avg_ms']:.1f}ms avg (score={score:.2f})")

    # ── analyze() ────────────────────────────────────────────
    print("\nRunning analyze benchmarks...")

    r = bench("analyze / Medium EN", analyze, TEXT_MEDIUM_EN, lang="en")
    benchmarks.append(r)
    print(f"  Medium EN: {r['avg_ms']:.1f}ms avg")

    # ── paraphrase() ─────────────────────────────────────────
    print("\nRunning paraphrase benchmarks...")

    r = bench("paraphrase / Medium EN", paraphrase, TEXT_MEDIUM_EN, lang="en", seed=42)
    benchmarks.append(r)
    print(f"  Medium EN: {r['avg_ms']:.1f}ms avg")

    # ── Cache benchmark ──────────────────────────────────────
    print("\nRunning cache benchmark...")

    # First call (cold)
    t0 = time.perf_counter()
    humanize(TEXT_MEDIUM_EN, lang="en", seed=42)
    cold_ms = (time.perf_counter() - t0) * 1000

    # Second call (warm, cached)
    t0 = time.perf_counter()
    humanize(TEXT_MEDIUM_EN, lang="en", seed=42)
    warm_ms = (time.perf_counter() - t0) * 1000

    print(f"  Cold: {cold_ms:.1f}ms → Warm (cached): {warm_ms:.3f}ms "
          f"({cold_ms/warm_ms:.0f}x speedup)")

    # ── Summary ──────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("SUMMARY TABLE")
    print("=" * 70)
    print(f"{'Benchmark':<40} {'Avg ms':>8} {'Min ms':>8} {'Max ms':>8} {'Mem KB':>8}")
    print("-" * 70)
    for b in benchmarks:
        print(f"{b['name']:<40} {b['avg_ms']:>8.1f} {b['min_ms']:>8.1f} "
              f"{b['max_ms']:>8.1f} {b['mem_peak_kb']:>8.1f}")
    print("-" * 70)


if __name__ == "__main__":
    main()
