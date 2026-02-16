"""CLI-интерфейс TextHumanize."""

from __future__ import annotations

import argparse
import json
import sys

from texthumanize import __version__
from texthumanize.core import humanize, analyze, explain


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
  echo "Текст" | texthumanize -
        """,
    )

    parser.add_argument(
        "input",
        help="Входной файл (или '-' для stdin)",
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
        choices=["chat", "web", "seo", "docs", "formal"],
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
        "--seed",
        type=int,
        help="Сид для воспроизводимости результатов",
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"texthumanize {__version__}",
    )

    args = parser.parse_args()

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


if __name__ == "__main__":
    main()
