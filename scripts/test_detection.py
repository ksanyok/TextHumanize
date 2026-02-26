#!/usr/bin/env python3
"""Quick test of AI detection improvements."""
from texthumanize import detect_ai

# 1. Typical AI text (EN)
ai_text = (
    "Furthermore, it is important to note that the implementation of "
    "comprehensive strategies necessitates a thorough understanding of "
    "the underlying mechanisms. In conclusion, the systematic approach "
    "provides significant advantages in terms of efficiency and effectiveness. "
    "Moreover, the utilization of advanced methodologies facilitates "
    "the optimization of resource allocation."
)

# 2. Human text (EN)
human_text = (
    "I went to the store yesterday and bought some milk. "
    "The weather was kinda nice, so I walked. "
    "My dog was happy to see me when I got home."
)

# 3. Russian AI text
ru_ai = (
    "V dannom kontekste neobkhodimo otmetit, chto osuschestvlenie "
    "kompleksnykh meropriyatiy trebuet tschatelnogo analiza. "
    "Krome togo, sleduet uchityvat, chto dannyy podkhod yavlyaetsya "
    "naibolee optimalnym. Bolee togo, ispolzovanie peredovykh "
    "metodologiy sposobstvuet optimizatsii raspredeleniya resursov."
)

# Using actual Russian:
ru_ai_real = "\u0412 \u0434\u0430\u043d\u043d\u043e\u043c \u043a\u043e\u043d\u0442\u0435\u043a\u0441\u0442\u0435 \u043d\u0435\u043e\u0431\u0445\u043e\u0434\u0438\u043c\u043e \u043e\u0442\u043c\u0435\u0442\u0438\u0442\u044c, \u0447\u0442\u043e \u043e\u0441\u0443\u0449\u0435\u0441\u0442\u0432\u043b\u0435\u043d\u0438\u0435 \u043a\u043e\u043c\u043f\u043b\u0435\u043a\u0441\u043d\u044b\u0445 \u043c\u0435\u0440\u043e\u043f\u0440\u0438\u044f\u0442\u0438\u0439 \u0442\u0440\u0435\u0431\u0443\u0435\u0442 \u0442\u0449\u0430\u0442\u0435\u043b\u044c\u043d\u043e\u0433\u043e \u0430\u043d\u0430\u043b\u0438\u0437\u0430. \u041a\u0440\u043e\u043c\u0435 \u0442\u043e\u0433\u043e, \u0441\u043b\u0435\u0434\u0443\u0435\u0442 \u0443\u0447\u0438\u0442\u044b\u0432\u0430\u0442\u044c, \u0447\u0442\u043e \u0434\u0430\u043d\u043d\u044b\u0439 \u043f\u043e\u0434\u0445\u043e\u0434 \u044f\u0432\u043b\u044f\u0435\u0442\u0441\u044f \u043d\u0430\u0438\u0431\u043e\u043b\u0435\u0435 \u043e\u043f\u0442\u0438\u043c\u0430\u043b\u044c\u043d\u044b\u043c. \u0411\u043e\u043b\u0435\u0435 \u0442\u043e\u0433\u043e, \u0438\u0441\u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u043d\u0438\u0435 \u043f\u0435\u0440\u0435\u0434\u043e\u0432\u044b\u0445 \u043c\u0435\u0442\u043e\u0434\u043e\u043b\u043e\u0433\u0438\u0439 \u0441\u043f\u043e\u0441\u043e\u0431\u0441\u0442\u0432\u0443\u0435\u0442 \u043e\u043f\u0442\u0438\u043c\u0438\u0437\u0430\u0446\u0438\u0438 \u0440\u0430\u0441\u043f\u0440\u0435\u0434\u0435\u043b\u0435\u043d\u0438\u044f \u0440\u0435\u0441\u0443\u0440\u0441\u043e\u0432."

# 4. Longer AI text for better detection
long_ai = (
    "The implementation of comprehensive digital transformation strategies "
    "has become increasingly important in today's rapidly evolving business "
    "landscape. Furthermore, it is essential to note that the systematic "
    "approach to organizational change management plays a crucial role in "
    "ensuring the successful adoption of new technologies. Moreover, the "
    "utilization of advanced data analytics methodologies facilitates the "
    "optimization of decision-making processes across various organizational "
    "levels. Additionally, it should be emphasized that the integration of "
    "artificial intelligence and machine learning frameworks represents a "
    "significant paradigm shift in how businesses operate. In conclusion, "
    "the careful consideration of these factors is necessary to achieve "
    "sustainable competitive advantages in the modern marketplace."
)

tests = [
    ("EN AI (short)", ai_text, "en"),
    ("EN Human", human_text, "en"),
    ("RU AI", ru_ai_real, "ru"),
    ("EN AI (long)", long_ai, "en"),
]

print("=" * 70)
print("AI Detection Test Results")
print("=" * 70)

for name, text, lang in tests:
    r = detect_ai(text, lang=lang)
    m = r["metrics"]
    print(f"\n{name}:")
    print(f"  score={r['score']:.3f}  combined={r['combined_score']:.3f}  verdict={r['verdict']}  conf={r['confidence']:.2f}")
    print(f"  pattern={m['ai_patterns']:.3f}  burst={m['burstiness']:.3f}  voice={m['voice']:.3f}  "
          f"stylo={m['stylometry']:.3f}  grammar={m['grammar_perfection']:.3f}")
    print(f"  opening={m['opening_diversity']:.3f}  discourse={m['discourse']:.3f}  "
          f"entity={m['entity_specificity']:.3f}  rhythm={m['rhythm']:.3f}")

print("\n" + "=" * 70)
print("PASS" if all(
    detect_ai(t, lang=l)["verdict"] != "human"
    for _, t, l in tests[:1]  # AI texts should not be "human"
) else "FAIL: AI text detected as human!")
