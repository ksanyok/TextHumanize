"""
Продвинутое использование TextHumanize.

Примеры: отдельные модули, батч-обработка, экспорт правил.
"""

import json

from texthumanize import humanize, analyze
from texthumanize.normalizer import TypographyNormalizer
from texthumanize.decancel import Debureaucratizer
from texthumanize.segmenter import Segmenter
from texthumanize.analyzer import TextAnalyzer
from texthumanize.lang import get_lang_pack


def demo_individual_modules():
    """Использование отдельных модулей."""

    print("=" * 60)
    print("1. Отдельные модули")
    print("=" * 60)

    # --- Только типографика ---
    norm = TypographyNormalizer(profile="web")
    text = "Текст — с тире и «кавычками»… Пример!"
    result = norm.normalize(text)
    print(f"\n[Типографика web]")
    print(f"  Было:  {text}")
    print(f"  Стало: {result}")

    norm_formal = TypographyNormalizer(profile="formal")
    result_formal = norm_formal.normalize(text)
    print(f"\n[Типографика formal]")
    print(f"  Было:  {text}")
    print(f"  Стало: {result_formal}")

    # --- Только деканцеляризация ---
    lang_pack = get_lang_pack("ru")
    db = Debureaucratizer(lang_pack=lang_pack, profile="chat", intensity=90)
    text = "Данный процесс осуществляется посредством использования современных технологий."
    result, changes = db.process(text)
    print(f"\n[Деканцеляризация]")
    print(f"  Было:  {text}")
    print(f"  Стало: {result}")
    print(f"  Изменения: {changes}")

    # --- Сегментация ---
    seg = Segmenter()
    text = "Смотрите пример на https://example.com и пишите на test@mail.com"
    protected, placeholders = seg.protect(text)
    print(f"\n[Сегментация]")
    print(f"  Было:  {text}")
    print(f"  Защищено: {protected}")
    restored = seg.restore(protected, placeholders)
    print(f"  Восстановлено: {restored}")

    # --- Анализатор ---
    analyzer = TextAnalyzer(lang_pack=lang_pack)
    text = (
        "Данный текст является примером. Однако необходимо отметить, "
        "что осуществление обработки представляет собой сложный процесс."
    )
    report = analyzer.analyze(text)
    print(f"\n[Анализ]")
    print(f"  Искусственность: {report['artificiality_score']:.1f}/100")
    print(f"  Канцеляризмы: {report['bureaucratic_ratio']:.1%}")
    print(f"  ИИ-связки: {report['connector_ratio']:.1%}")


def demo_batch_processing():
    """Батч-обработка нескольких текстов."""

    print("\n" + "=" * 60)
    print("2. Батч-обработка")
    print("=" * 60)

    texts = [
        (
            "В настоящее время данная технология является передовой. "
            "Однако необходимо учитывать определённые ограничения."
        ),
        (
            "Даний підхід є найбільш оптимальним для обробки даних. "
            "Таким чином, здійснення аналізу забезпечує якісний результат."
        ),
        (
            "This comprehensive methodology facilitates the implementation "
            "of advanced algorithms. Furthermore, it ensures optimal results."
        ),
    ]

    for i, text in enumerate(texts, 1):
        result = humanize(text, seed=42)  # auto-detect language
        print(f"\n[Текст {i}] Язык: {result.lang}, Изменений: {result.change_ratio:.1%}")
        print(f"  Было:  {text[:80]}...")
        print(f"  Стало: {result.text[:80]}...")


def demo_metrics_comparison():
    """Сравнение метрик до и после обработки."""

    print("\n" + "=" * 60)
    print("3. Сравнение метрик")
    print("=" * 60)

    text = (
        "В настоящее время данная технология является одной из наиболее "
        "перспективных. Данная технология осуществляет обработку данных. "
        "Однако данная технология представляет собой сложную систему. "
        "Более того, данная технология обеспечивает высокую эффективность. "
        "Таким образом, данная технология является важной."
    )

    report_before = analyze(text, lang="ru")
    result = humanize(text, lang="ru", profile="web", intensity=80, seed=42)
    report_after = analyze(result.text, lang="ru")

    print(f"\n{'Метрика':<30} {'До':>10} {'После':>10} {'Δ':>10}")
    print("-" * 62)
    for key in ["artificiality_score", "bureaucratic_ratio", "connector_ratio", "repetition_score"]:
        before = getattr(report_before, key)
        after = getattr(report_after, key)
        delta = after - before
        sign = "↓" if delta < 0 else "↑" if delta > 0 else "="
        print(f"  {key:<28} {before:>10.2f} {after:>10.2f} {delta:>+9.2f} {sign}")


def demo_export_rules():
    """Экспорт языковых правил в JSON."""

    print("\n" + "=" * 60)
    print("4. Экспорт правил в JSON")
    print("=" * 60)

    lang_pack = get_lang_pack("ru")

    # Подготовка для JSON (set → list)
    export = {}
    for key, value in lang_pack.items():
        if isinstance(value, set):
            export[key] = sorted(list(value))
        elif isinstance(value, dict):
            inner = {}
            for k, v in value.items():
                if isinstance(v, (list, tuple)):
                    inner[k] = list(v)
                else:
                    inner[k] = v
            export[key] = inner
        else:
            export[key] = value

    json_str = json.dumps(export, ensure_ascii=False, indent=2)
    print(f"\nJSON размер: {len(json_str)} символов")
    print(f"Ключи: {', '.join(export.keys())}")
    print(f"\nПример (bureaucratic, первые 5):")
    items = list(lang_pack.get("bureaucratic", {}).items())[:5]
    for word, replacements in items:
        print(f"  {word} → {replacements}")


if __name__ == "__main__":
    demo_individual_modules()
    demo_batch_processing()
    demo_metrics_comparison()
    demo_export_rules()
