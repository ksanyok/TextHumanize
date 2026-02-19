"""Benchmark framework — автоматическое тестирование качества TextHumanize.

Запуск:
    python -m benchmarks.quality_bench
    python -m benchmarks.quality_bench --lang ru --profile web
    python -m benchmarks.quality_bench --verbose

Метрики:
    - AI-скор до/после (должен снижаться)
    - Читабельность до/после
    - Доля изменений (оптимум 5-35%)
    - Сохранение смысла (Jaccard)
    - Скорость обработки (символов/сек)
    - Перплексия до/после (должна расти)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

# Добавляем корень проекта в path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from texthumanize import analyze, humanize


# ═════════════════════════════════════════════════════════════
#  BENCHMARK SAMPLES
# ═════════════════════════════════════════════════════════════

SAMPLES: dict[str, list[dict]] = {
    "en": [
        {
            "name": "formal_ai",
            "text": (
                "The implementation of comprehensive solutions necessitates "
                "careful consideration of various factors. Furthermore, it is "
                "essential to ensure that all stakeholders are adequately "
                "informed. Additionally, the optimization of existing processes "
                "represents a fundamental aspect of organizational growth. "
                "Moreover, systematic evaluation demonstrates significant "
                "improvements in overall performance metrics."
            ),
            "expected_ai_high": True,
        },
        {
            "name": "natural_blog",
            "text": (
                "So I tried this new coffee shop downtown. The latte? Pretty "
                "good, actually. Not life-changing, but solid. The barista "
                "was super friendly — even remembered my name on the second "
                "visit. The vibe is kind of industrial-chic, if that's your "
                "thing. I'll probably go back next week."
            ),
            "expected_ai_high": False,
        },
        {
            "name": "mixed_content",
            "text": (
                "Climate change presents serious challenges for agriculture. "
                "Farmers are adapting by using drought-resistant crops and new "
                "irrigation techniques. But it's not just about technology — "
                "farming communities need support. Government policies play "
                "a crucial role, though progress has been uneven at best."
            ),
            "expected_ai_high": False,
        },
        {
            "name": "academic_ai",
            "text": (
                "This study examines the correlation between socioeconomic "
                "factors and educational outcomes. The methodology employed "
                "a quantitative approach utilizing standardized metrics. "
                "Results demonstrate a statistically significant relationship "
                "between variables. The findings contribute to the existing "
                "body of literature on educational equity."
            ),
            "expected_ai_high": True,
        },
    ],
    "ru": [
        {
            "name": "канцелярский_ИИ",
            "text": (
                "В рамках осуществления данного проекта необходимо обеспечить "
                "надлежащее функционирование всех систем. Кроме того, "
                "следует отметить, что комплексный подход является ключевым "
                "фактором успеха. Более того, систематический анализ "
                "демонстрирует значительные улучшения показателей."
            ),
            "expected_ai_high": True,
        },
        {
            "name": "живой_блог",
            "text": (
                "Решил попробовать новую кофейню у дома. Латте — вполне норм. "
                "Не то чтобы прямо вау, но пить можно. Бариста приветливый, "
                "запомнил меня со второго раза. Атмосфера такая... лофтовая, "
                "что ли. Наверное, зайду ещё на неделе."
            ),
            "expected_ai_high": False,
        },
        {
            "name": "смешанный",
            "text": (
                "Изменение климата создаёт реальные проблемы для сельского "
                "хозяйства. Фермеры приспосабливаются: используют засухоустойчивые "
                "сорта и новые методы полива. Но дело не только в технологиях — "
                "нужна поддержка сообществ. Роль государства важна, хотя прогресс "
                "пока неравномерный."
            ),
            "expected_ai_high": False,
        },
    ],
    "uk": [
        {
            "name": "канцелярський_ШІ",
            "text": (
                "У рамках здійснення даного проєкту необхідно забезпечити "
                "належне функціонування усіх систем. Крім того, слід зазначити, "
                "що комплексний підхід є ключовим чинником успіху. Більш того, "
                "систематичний аналіз демонструє значні покращення показників."
            ),
            "expected_ai_high": True,
        },
    ],
    "de": [
        {
            "name": "formell_KI",
            "text": (
                "Die Implementierung umfassender Lösungen erfordert eine "
                "sorgfältige Berücksichtigung verschiedener Faktoren. Darüber "
                "hinaus ist es wesentlich sicherzustellen, dass alle Beteiligten "
                "angemessen informiert sind. Zudem stellt die Optimierung "
                "bestehender Prozesse einen grundlegenden Aspekt dar."
            ),
            "expected_ai_high": True,
        },
    ],
}


# ═════════════════════════════════════════════════════════════
#  BENCHMARK RESULT
# ═════════════════════════════════════════════════════════════

@dataclass
class BenchmarkResult:
    """Результат одного benchmark прогона."""

    name: str
    lang: str
    profile: str
    intensity: int

    ai_score_before: float = 0.0
    ai_score_after: float = 0.0
    ai_score_delta: float = 0.0

    predictability_before: float = 0.0
    predictability_after: float = 0.0

    change_ratio: float = 0.0
    similarity: float = 0.0
    quality_score: float = 0.0

    chars_per_sec: float = 0.0
    processing_ms: float = 0.0

    passed_checks: int = 0
    total_checks: int = 0
    issues: list[str] = field(default_factory=list)


def run_single_benchmark(
    sample: dict,
    lang: str,
    profile: str = "web",
    intensity: int = 60,
) -> BenchmarkResult:
    """Прогнать один benchmark."""
    text = sample["text"]
    br = BenchmarkResult(
        name=sample["name"],
        lang=lang,
        profile=profile,
        intensity=intensity,
    )

    # Анализ до
    report_before = analyze(text, lang=lang)
    br.ai_score_before = report_before.artificiality_score
    br.predictability_before = report_before.predictability_score

    # Обработка
    t0 = time.perf_counter()
    result = humanize(text, lang=lang, profile=profile, intensity=intensity, seed=42)
    t1 = time.perf_counter()

    br.processing_ms = (t1 - t0) * 1000
    br.chars_per_sec = len(text) / (t1 - t0) if (t1 - t0) > 0 else 0

    # Анализ после
    report_after = analyze(result.text, lang=lang)
    br.ai_score_after = report_after.artificiality_score
    br.ai_score_delta = br.ai_score_before - br.ai_score_after
    br.predictability_after = report_after.predictability_score

    br.change_ratio = result.change_ratio
    br.similarity = result.similarity
    br.quality_score = result.quality_score

    # ─── Проверки ─────────────────────────────────────────────
    checks = 0
    passed = 0

    # 1. AI-скор должен снизиться (или остаться низким)
    checks += 1
    if sample.get("expected_ai_high"):
        if br.ai_score_after < br.ai_score_before:
            passed += 1
        else:
            br.issues.append(
                f"AI-скор не снизился: {br.ai_score_before:.0f}→{br.ai_score_after:.0f}"
            )
    else:
        # Не AI-текст — не должен стать хуже
        if br.ai_score_after <= br.ai_score_before + 10:
            passed += 1
        else:
            br.issues.append(
                f"AI-скор вырос: {br.ai_score_before:.0f}→{br.ai_score_after:.0f}"
            )

    # 2. Изменения в разумном диапазоне (1-50%)
    checks += 1
    if 0.01 <= br.change_ratio <= 0.50:
        passed += 1
    else:
        br.issues.append(f"change_ratio={br.change_ratio:.2f} вне [0.01, 0.50]")

    # 3. Similarity > 0.3 (смысл сохранён)
    checks += 1
    if br.similarity > 0.3:
        passed += 1
    else:
        br.issues.append(f"similarity={br.similarity:.2f} < 0.3")

    # 4. quality_score > 0.4
    checks += 1
    if br.quality_score > 0.4:
        passed += 1
    else:
        br.issues.append(f"quality_score={br.quality_score:.2f} < 0.4")

    # 5. Скорость > 1000 символов/сек
    checks += 1
    if br.chars_per_sec > 1000:
        passed += 1
    else:
        br.issues.append(f"chars_per_sec={br.chars_per_sec:.0f} < 1000")

    br.total_checks = checks
    br.passed_checks = passed

    return br


def run_benchmarks(
    langs: list[str] | None = None,
    profile: str = "web",
    intensity: int = 60,
    verbose: bool = False,
) -> list[BenchmarkResult]:
    """Прогнать все benchmarks."""
    if langs is None:
        langs = list(SAMPLES.keys())

    results: list[BenchmarkResult] = []

    for lang in langs:
        samples = SAMPLES.get(lang, [])
        for sample in samples:
            br = run_single_benchmark(sample, lang, profile, intensity)
            results.append(br)

            if verbose:
                status = "✓" if br.passed_checks == br.total_checks else "✗"
                print(
                    f"  {status} [{lang}] {br.name:25s} "
                    f"AI: {br.ai_score_before:4.0f}→{br.ai_score_after:4.0f} "
                    f"Δ={br.ai_score_delta:+5.0f}  "
                    f"change={br.change_ratio:.2f}  "
                    f"sim={br.similarity:.2f}  "
                    f"Q={br.quality_score:.2f}  "
                    f"{br.processing_ms:5.0f}ms  "
                    f"[{br.passed_checks}/{br.total_checks}]"
                )
                for issue in br.issues:
                    print(f"      ⚠ {issue}")

    return results


def print_summary(results: list[BenchmarkResult]) -> None:
    """Напечатать сводку benchmark-результатов."""
    total_checks = sum(r.total_checks for r in results)
    total_passed = sum(r.passed_checks for r in results)
    total_issues = sum(len(r.issues) for r in results)

    avg_delta = (
        sum(r.ai_score_delta for r in results) / len(results)
        if results else 0
    )
    avg_quality = (
        sum(r.quality_score for r in results) / len(results)
        if results else 0
    )
    avg_speed = (
        sum(r.chars_per_sec for r in results) / len(results)
        if results else 0
    )

    print("\n" + "=" * 70)
    print("  BENCHMARK SUMMARY")
    print("=" * 70)
    print(f"  Samples:       {len(results)}")
    print(f"  Checks passed: {total_passed}/{total_checks} "
          f"({total_passed/total_checks*100:.0f}%)" if total_checks else "")
    print(f"  Issues:        {total_issues}")
    print(f"  Avg AI Δ:      {avg_delta:+.1f}")
    print(f"  Avg Quality:   {avg_quality:.2f}")
    print(f"  Avg Speed:     {avg_speed:,.0f} chars/sec")
    print("=" * 70)

    if total_issues > 0:
        print("\nIssues found:")
        for r in results:
            for issue in r.issues:
                print(f"  [{r.lang}] {r.name}: {issue}")


def main():
    parser = argparse.ArgumentParser(description="TextHumanize Quality Benchmark")
    parser.add_argument("--lang", nargs="+", default=None, help="Languages to test")
    parser.add_argument("--profile", default="web", help="Profile to use")
    parser.add_argument("--intensity", type=int, default=60, help="Intensity")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    print("TextHumanize Quality Benchmark v0.8.1")
    print("-" * 40)

    results = run_benchmarks(
        langs=args.lang,
        profile=args.profile,
        intensity=args.intensity,
        verbose=args.verbose,
    )

    if args.json:
        data = [asdict(r) for r in results]
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print_summary(results)


if __name__ == "__main__":
    main()
