"""CLI-интерфейс TextHumanize."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import Any

from texthumanize import __version__
from texthumanize.core import (
    adjust_tone,
    analyze,
    analyze_coherence,
    analyze_tone,
    detect_ai,
    detect_watermarks,
    explain,
    full_readability,
    humanize,
    paraphrase,
    spin,
    spin_variants,
)

logger = logging.getLogger(__name__)


def main():
    """Точка входа CLI."""
    parser = argparse.ArgumentParser(
        prog="texthumanize",
        description="TextHumanize — алгоритмическая гуманизация текста. "
        "Делает AI-тексты естественнее для чтения.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  texthumanize input.txt
  texthumanize input.txt -l ru -p chat -i 80
  texthumanize input.txt -o output.txt --report report.json
  texthumanize input.txt --keep "RankBot AI" "Promopilot"
  texthumanize --analyze input.txt
  texthumanize detect input.txt
  texthumanize detect input.txt --verbose
  echo "Текст" | texthumanize detect -
  echo "Текст" | texthumanize -
        """,
    )

    parser.add_argument(
        "input",
        help="Входной файл (или '-' для stdin), или 'detect' для детекции AI",
    )
    parser.add_argument(
        "-o", "--output",
        help="Выходной файл (по умолчанию stdout)",
    )
    parser.add_argument(
        "-l", "--lang",
        default="auto",
        choices=["auto", "ru", "uk", "en", "de", "fr", "es", "pl", "pt", "it"],
        help="Язык текста (по умолчанию: auto)",
    )
    parser.add_argument(
        "-p", "--profile",
        default="web",
        choices=["chat", "web", "seo", "docs", "formal",
                 "academic", "marketing", "social", "email"],
        help="Профиль обработки (по умолчанию: web)",
    )
    parser.add_argument(
        "-i", "--intensity",
        type=int,
        default=60,
        help="Интенсивность обработки 0-100 (по умолчанию: 60)",
    )
    parser.add_argument(
        "--keep",
        nargs="*",
        default=[],
        help="Ключевые слова/термины, которые нельзя менять",
    )
    parser.add_argument(
        "--brand",
        nargs="*",
        default=[],
        help="Брендовые термины для защиты",
    )
    parser.add_argument(
        "--max-change",
        type=float,
        default=0.4,
        help="Максимальная доля изменений 0-1 (по умолчанию: 0.4)",
    )
    parser.add_argument(
        "--report",
        help="Файл для сохранения отчёта (JSON)",
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Только анализ без обработки",
    )
    parser.add_argument(
        "--explain",
        action="store_true",
        help="Показать подробный отчёт об изменениях",
    )
    parser.add_argument(
        "--detect-ai",
        action="store_true",
        help="Проверка на AI-генерацию",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Подробный вывод (для detect-ai / detect)",
    )
    parser.add_argument(
        "--paraphrase",
        action="store_true",
        help="Перефразировать текст",
    )
    parser.add_argument(
        "--tone",
        metavar="TARGET",
        help="Скорректировать тональность (neutral, formal, casual, academic, marketing)",
    )
    parser.add_argument(
        "--tone-analyze",
        action="store_true",
        help="Анализ тональности",
    )
    parser.add_argument(
        "--watermarks",
        action="store_true",
        help="Обнаружить и удалить водяные знаки",
    )
    parser.add_argument(
        "--spin",
        action="store_true",
        help="Спиннинг текста",
    )
    parser.add_argument(
        "--variants",
        type=int,
        metavar="N",
        help="Генерация N вариантов спиннинга",
    )
    parser.add_argument(
        "--coherence",
        action="store_true",
        help="Анализ когерентности",
    )
    parser.add_argument(
        "--readability",
        action="store_true",
        help="Полный анализ читабельности",
    )
    parser.add_argument(
        "--api",
        action="store_true",
        help="Запустить API-сервер",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Порт API-сервера (по умолчанию: 8080)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="Сид для воспроизводимости результатов",
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"texthumanize {__version__}",
    )

    args, remaining = parser.parse_known_args()

    # ── Handle detect subcommand ──
    if args.input == 'detect':
        _handle_detect_command(args, remaining)
        return

    # ── Handle benchmark subcommand ──
    if args.input == 'benchmark':
        _handle_benchmark_command(args, remaining)
        return

    # API-сервер (не требует input)
    if getattr(args, 'api', False):
        from texthumanize.api import run_server
        run_server(port=args.port)
        return

    # Чтение входного текста
    if args.input == "-":
        text = sys.stdin.read()
    else:
        try:
            with open(args.input, "r", encoding="utf-8") as f:
                text = f.read()
        except FileNotFoundError:
            print(f"Ошибка: файл '{args.input}' не найден", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Ошибка чтения файла: {e}", file=sys.stderr)
            sys.exit(1)

    # AI Detection
    result: Any
    if getattr(args, 'detect_ai', False):
        result = detect_ai(text, lang=args.lang)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # Paraphrase
    if getattr(args, 'paraphrase', False):
        result = paraphrase(text, lang=args.lang, intensity=args.intensity / 100.0)
        _output_text(result, args)
        return

    # Tone analysis
    if getattr(args, 'tone_analyze', False):
        result = analyze_tone(text, lang=args.lang)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # Tone adjustment
    if getattr(args, 'tone', None):
        result = adjust_tone(text, target=args.tone, lang=args.lang)
        _output_text(result, args)
        return

    # Watermarks
    if getattr(args, 'watermarks', False):
        result = detect_watermarks(text, lang=args.lang)
        if result['has_watermarks']:
            print(json.dumps(result, ensure_ascii=False, indent=2), file=sys.stderr)
            _output_text(result['cleaned_text'], args)
        else:
            print('Водяные знаки не обнаружены.', file=sys.stderr)
            _output_text(text, args)
        return

    # Spin
    if getattr(args, 'spin', False):
        result = spin(text, lang=args.lang, intensity=args.intensity / 100.0)
        _output_text(result, args)
        return

    # Spin variants
    if getattr(args, 'variants', None):
        results = spin_variants(text, count=args.variants, lang=args.lang)
        for i, v in enumerate(results, 1):
            print(f"--- Вариант {i} ---")
            print(v)
            print()
        return

    # Coherence
    if getattr(args, 'coherence', False):
        result = analyze_coherence(text, lang=args.lang)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # Readability
    if getattr(args, 'readability', False):
        result = full_readability(text, lang=args.lang)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # Режим анализа
    if args.analyze:
        report = analyze(text, lang=args.lang)
        output = {
            "lang": report.lang,
            "total_chars": report.total_chars,
            "total_words": report.total_words,
            "total_sentences": report.total_sentences,
            "avg_sentence_length": round(report.avg_sentence_length, 2),
            "sentence_length_variance": round(report.sentence_length_variance, 2),
            "bureaucratic_ratio": round(report.bureaucratic_ratio, 4),
            "connector_ratio": round(report.connector_ratio, 4),
            "repetition_score": round(report.repetition_score, 4),
            "typography_score": round(report.typography_score, 4),
            "artificiality_score": round(report.artificiality_score, 2),
            "details": {
                "found_bureaucratic": report.details.get("found_bureaucratic", []),
                "found_connectors": report.details.get("found_connectors", []),
                "typography_issues": report.details.get("typography_issues", []),
            },
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return

    # Обработка
    result = humanize(
        text,
        lang=args.lang,
        profile=args.profile,
        intensity=args.intensity,
        preserve={
            "brand_terms": args.brand,
        },
        constraints={
            "max_change_ratio": args.max_change,
            "keep_keywords": args.keep,
        },
        seed=args.seed,
    )

    # Вывод результата
    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(result.text)
            print(f"Результат сохранён в {args.output}", file=sys.stderr)
        except Exception as e:
            print(f"Ошибка записи файла: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(result.text)

    # Отчёт об изменениях
    if args.explain:
        report_text = explain(result)
        print("\n" + report_text, file=sys.stderr)

    # Сохранение отчёта
    if args.report:
        report_data = {
            "lang": result.lang,
            "profile": result.profile,
            "intensity": result.intensity,
            "change_ratio": round(result.change_ratio, 4),
            "changes_count": len(result.changes),
            "changes": result.changes[:50],
            "metrics_before": result.metrics_before,
            "metrics_after": result.metrics_after,
        }
        try:
            with open(args.report, "w", encoding="utf-8") as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            print(f"Отчёт сохранён в {args.report}", file=sys.stderr)
        except Exception as e:
            print(f"Ошибка записи отчёта: {e}", file=sys.stderr)


def _handle_detect_command(args, remaining: list[str]) -> None:
    """Handle 'texthumanize detect [file] [--verbose] [--json]' command."""
    detect_input = "-"
    use_json = False
    verbose = getattr(args, 'verbose', False)

    for a in remaining:
        if a == "--json":
            use_json = True
        elif a == "--verbose":
            verbose = True
        elif not a.startswith("-"):
            detect_input = a

    if detect_input == "-":
        text = sys.stdin.read()
    else:
        try:
            with open(detect_input, "r", encoding="utf-8") as f:
                text = f.read()
        except FileNotFoundError:
            print(f"Error: file '{detect_input}' not found", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            sys.exit(1)

    lang = args.lang if hasattr(args, 'lang') else "auto"
    result = detect_ai(text, lang=lang)

    if use_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # Human-readable output
    verdict_icons = {"ai": "🤖", "human": "👤", "mixed": "🔀", "unknown": "❓"}
    icon = verdict_icons.get(result["verdict"], "")

    print(f"\n  {icon} Verdict: {result['verdict'].upper()}")
    print(f"  AI Probability: {result['score']:.1%}")
    print(f"  Confidence: {result['confidence']:.1%}")

    if verbose:
        print("\n  Metrics (0.0=human, 1.0=AI):")
        for metric, val in result["metrics"].items():
            bar = "█" * int(val * 20) + "░" * (20 - int(val * 20))
            print(f"    {metric:25s} {bar} {val:.2f}")

        if result.get("explanations"):
            print("\n  Key findings:")
            for exp in result["explanations"]:
                if exp:
                    print(f"    • {exp}")

    print()


def _handle_benchmark_command(args, remaining: list[str]) -> None:
    """Handle 'texthumanize benchmark' — run comprehensive quality/speed benchmarks."""
    import time as _time

    use_json = "--json" in remaining
    lang = args.lang if hasattr(args, "lang") and args.lang != "auto" else "en"

    # --- Sample texts for benchmarking ---
    _en_short = (
        "Furthermore, it is important to note that the "
        "implementation of this approach facilitates optimization."
    )
    _en_medium = (
        "Furthermore, it is important to note that the "
        "implementation of cloud computing facilitates the "
        "optimization of business processes. Additionally, the "
        "utilization of microservices constitutes a significant "
        "advancement. Nevertheless, considerable challenges "
        "remain in the area of security. It is worth mentioning "
        "that these challenges necessitate comprehensive "
        "solutions. Moreover, the integration of artificial "
        "intelligence provides unprecedented opportunities "
        "for automation."
    )
    _ru_short = (
        "Необходимо отметить, что данный подход является "
        "оптимальным решением для осуществления "
        "поставленных задач."
    )
    _ru_medium = (
        "Необходимо отметить, что данный подход является "
        "оптимальным решением для осуществления "
        "поставленных задач. Кроме того, следует подчеркнуть "
        "важность реализации инновационных методологий. "
        "В рамках данного исследования было установлено, что "
        "применение современных технологий способствует "
        "повышению эффективности. Тем не менее, существуют "
        "определённые ограничения, которые необходимо "
        "учитывать."
    )
    samples = {
        "en": [
            ("short", _en_short),
            ("medium", _en_medium),
            ("long", (_en_medium + " ") * 3),
        ],
        "ru": [
            ("short", _ru_short),
            ("medium", _ru_medium),
            ("long", (_ru_medium + " ") * 3),
        ],
    }

    test_samples = samples.get(lang, samples["en"])

    if not use_json:
        print("=" * 60)
        print(f"  TextHumanize Benchmark — v{__version__}")
        print(f"  Language: {lang}")
        print("=" * 60)

    total_chars = 0
    total_time_humanize = 0.0
    total_time_detect = 0.0
    quality_scores: list[float] = []
    change_ratios: list[float] = []
    ai_improvements: list[tuple[float, float]] = []
    results_data: list[dict] = []

    for label, sample_text in test_samples:
        chars = len(sample_text)
        total_chars += chars

        # Humanize benchmark
        t0 = _time.perf_counter()
        result = humanize(sample_text, lang=lang, profile="web", intensity=60, seed=42)
        t_humanize = _time.perf_counter() - t0
        total_time_humanize += t_humanize

        # AI detection benchmark (before & after)
        t0 = _time.perf_counter()
        ai_before = detect_ai(sample_text, lang=lang)
        t_detect = _time.perf_counter() - t0
        total_time_detect += t_detect

        ai_after = detect_ai(result.text, lang=lang)

        quality_scores.append(getattr(result, "quality_score", 0.0))
        change_ratios.append(getattr(result, "change_ratio", 0.0))
        ai_improvements.append((ai_before["score"], ai_after["score"]))

        row = {
            "label": label,
            "chars": chars,
            "humanize_ms": round(t_humanize * 1000, 1),
            "detect_ms": round(t_detect * 1000, 1),
            "throughput": round(chars / t_humanize) if t_humanize > 0 else 0,
            "change_ratio": round(getattr(result, "change_ratio", 0), 3),
            "quality_score": round(getattr(result, "quality_score", 0), 3),
            "ai_before": round(ai_before["score"], 3),
            "ai_after": round(ai_after["score"], 3),
            "verdict_before": ai_before["verdict"],
            "verdict_after": ai_after["verdict"],
        }
        results_data.append(row)

        if not use_json:
            print(f"\n  [{label}] {chars} chars")
            print(f"    Humanize: {row['humanize_ms']}ms ({row['throughput']:,} chars/sec)")
            print(f"    Detect:   {row['detect_ms']}ms")
            print(f"    Change:   {row['change_ratio']:.1%}")
            print(f"    Quality:  {row['quality_score']:.2f}")
            print(
                f"    AI score: {row['ai_before']:.0%}"
                f" → {row['ai_after']:.0%}"
                f" ({row['verdict_before']}"
                f" → {row['verdict_after']})"
            )

    # Determinism check
    r1 = humanize(test_samples[0][1], lang=lang, seed=12345)
    r2 = humanize(test_samples[0][1], lang=lang, seed=12345)
    deterministic = r1.text == r2.text

    # Summary
    avg_throughput = round(total_chars / total_time_humanize) if total_time_humanize > 0 else 0
    avg_quality = round(sum(quality_scores) / len(quality_scores), 3) if quality_scores else 0
    avg_change = round(sum(change_ratios) / len(change_ratios), 3) if change_ratios else 0
    avg_ai_drop = round(
        sum(b - a for b, a in ai_improvements) / len(ai_improvements), 3
    ) if ai_improvements else 0

    summary = {
        "version": __version__,
        "lang": lang,
        "total_chars": total_chars,
        "total_humanize_ms": round(total_time_humanize * 1000, 1),
        "total_detect_ms": round(total_time_detect * 1000, 1),
        "avg_throughput_chars_sec": avg_throughput,
        "avg_quality_score": avg_quality,
        "avg_change_ratio": avg_change,
        "avg_ai_score_drop": avg_ai_drop,
        "deterministic": deterministic,
        "samples": results_data,
    }

    if use_json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print("\n" + "=" * 60)
        print("  SUMMARY")
        print("=" * 60)
        print(f"  Total chars processed: {total_chars:,}")
        print(f"  Avg throughput:        {avg_throughput:,} chars/sec")
        print(f"  Avg quality score:     {avg_quality:.2f}")
        print(f"  Avg change ratio:      {avg_change:.1%}")
        print(f"  Avg AI score drop:     {avg_ai_drop:+.1%}")
        print(f"  Deterministic:         {'✅' if deterministic else '❌'}")
        print("=" * 60)


def _output_text(text: str, args) -> None:
    """Output text to file or stdout."""
    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"Результат сохранён в {args.output}", file=sys.stderr)
        except Exception as e:
            print(f"Ошибка записи файла: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print(text)


if __name__ == "__main__":
    main()
