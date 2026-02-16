"""
SEO-режим TextHumanize.

Обработка SEO-текстов с сохранением ключевых слов и минимальными изменениями.
"""

from texthumanize import humanize, explain


def main():
    seo_text = (
        "Купить iPhone 15 Pro Max в Москве с доставкой по России. "
        "В настоящее время данный смартфон является одним из наиболее "
        "востребованных устройств на рынке. Данная модель осуществляет "
        "обработку данных с высокой скоростью. Однако необходимо "
        "отметить, что стоимость iPhone 15 Pro Max представляет собой "
        "значительную сумму. Таким образом, покупка iPhone 15 с гарантией "
        "2 года является оптимальным решением. Доставка по России "
        "осуществляется в течение 3-5 рабочих дней."
    )

    print("=" * 60)
    print("SEO-режим: сохранение ключевых слов")
    print("=" * 60)

    result = humanize(
        seo_text,
        lang="ru",
        profile="seo",
        intensity=40,
        constraints={
            "keep_keywords": [
                "iPhone 15 Pro Max",
                "iPhone 15",
                "доставка по России",
                "гарантия 2 года",
                "купить",
            ],
            "max_change_ratio": 0.25,
        },
        preserve={
            "numbers": True,
            "brand_terms": ["iPhone"],
        },
        seed=42,
    )

    print("\nОРИГИНАЛ:")
    print(seo_text)

    print("\nРЕЗУЛЬТАТ:")
    print(result.text)

    print(f"\nИзменений: {result.change_ratio:.1%}")
    print(explain(result))

    # Проверка: ключевые слова сохранены
    print("\n--- Проверка ключевых слов ---")
    keywords = ["iPhone 15", "доставка по России", "купить"]
    for kw in keywords:
        found = kw.lower() in result.text.lower()
        status = "✓" if found else "✗"
        print(f"  {status} '{kw}'")


if __name__ == "__main__":
    main()
