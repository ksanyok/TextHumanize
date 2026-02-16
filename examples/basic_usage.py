"""
Базовое использование TextHumanize.

Примеры: гуманизация текста, анализ, отчёт.
"""

from texthumanize import humanize, analyze, explain


def main():
    # ========================================================
    # 1. Простая гуманизация
    # ========================================================

    text_ru = (
        "В настоящее время искусственный интеллект является одной из "
        "наиболее перспективных технологий. Данная технология осуществляет "
        "обработку больших объёмов данных. Однако необходимо отметить, что "
        "внедрение ИИ представляет собой сложную задачу. Более того, "
        "функционирование систем ИИ обеспечивает значительное повышение "
        "эффективности. Таким образом, данная технология является "
        "чрезвычайно важной."
    )

    print("=" * 60)
    print("1. Простая гуманизация (RU, web, intensity=60)")
    print("=" * 60)
    print("\nОРИГИНАЛ:")
    print(text_ru)

    result = humanize(text_ru, lang="ru", profile="web", intensity=60)

    print("\nРЕЗУЛЬТАТ:")
    print(result.text)
    print(f"\nИзменений: {result.change_ratio:.1%}")

    # ========================================================
    # 2. Анализ текста
    # ========================================================

    print("\n" + "=" * 60)
    print("2. Анализ текста")
    print("=" * 60)

    report = analyze(text_ru, lang="ru")

    print(f"Балл искусственности: {report.artificiality_score:.1f}/100")
    print(f"Средняя длина предложения: {report.avg_sentence_length:.1f} слов")
    print(f"Канцеляризмы: {report.bureaucratic_ratio:.1%}")
    print(f"ИИ-связки: {report.connector_ratio:.1%}")
    print(f"Повторяемость: {report.repetition_score:.2f}")
    print(f"Типографика: {report.typography_score:.2f}")

    # ========================================================
    # 3. Подробный отчёт
    # ========================================================

    print("\n" + "=" * 60)
    print("3. Подробный отчёт")
    print("=" * 60)

    result = humanize(text_ru, lang="ru", profile="web", intensity=70)
    print(explain(result))

    # ========================================================
    # 4. Разные профили
    # ========================================================

    print("\n" + "=" * 60)
    print("4. Сравнение профилей")
    print("=" * 60)

    for profile in ["chat", "web", "seo", "docs", "formal"]:
        r = humanize(text_ru, lang="ru", profile=profile, intensity=60, seed=42)
        print(f"\n[{profile}] ({r.change_ratio:.0%} изменений):")
        print(f"  {r.text[:120]}...")

    # ========================================================
    # 5. Воспроизводимость (seed)
    # ========================================================

    print("\n" + "=" * 60)
    print("5. Воспроизводимость")
    print("=" * 60)

    r1 = humanize(text_ru, lang="ru", seed=42)
    r2 = humanize(text_ru, lang="ru", seed=42)

    print(f"Результаты идентичны: {r1.text == r2.text}")

    # ========================================================
    # 6. Украинский язык
    # ========================================================

    text_uk = (
        "Даний текст є прикладом використання штучного інтелекту. "
        "Однак необхідно зазначити, що здійснення обробки тексту "
        "являє собою складний процес."
    )

    print("\n" + "=" * 60)
    print("6. Украинский язык")
    print("=" * 60)

    result = humanize(text_uk, lang="uk", profile="web", intensity=70)
    print(f"Оригінал: {text_uk[:80]}...")
    print(f"Результат: {result.text[:80]}...")

    # ========================================================
    # 7. Английский язык
    # ========================================================

    text_en = (
        "This text utilizes a comprehensive methodology for the "
        "implementation of text processing. Furthermore, it is "
        "important to note that the facilitation of this process "
        "necessitates considerable effort."
    )

    print("\n" + "=" * 60)
    print("7. English")
    print("=" * 60)

    result = humanize(text_en, lang="en", profile="web", intensity=70)
    print(f"Original: {text_en[:80]}...")
    print(f"Result:   {result.text[:80]}...")


if __name__ == "__main__":
    main()
