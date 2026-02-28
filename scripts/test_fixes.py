#!/usr/bin/env python3
"""Quick validation of Phase 0 fixes."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from texthumanize import detect_ai

tests = {
    "en": (
        "Artificial intelligence plays a crucial role in today's world. "
        "Furthermore, comprehensive data analysis facilitates significant "
        "process improvement. It is important to note that this technology "
        "has far-reaching implications. Nevertheless, ethical considerations "
        "must be carefully addressed. Consequently, the integration of AI "
        "systems is of paramount importance. In conclusion, optimization "
        "through machine learning represents a fundamental paradigm shift."
    ),
    "ru": (
        "\u0418\u0441\u043a\u0443\u0441\u0441\u0442\u0432\u0435\u043d\u043d\u044b\u0439 \u0438\u043d\u0442\u0435\u043b\u043b\u0435\u043a\u0442 \u0438\u0433\u0440\u0430\u0435\u0442 \u043a\u043b\u044e\u0447\u0435\u0432\u0443\u044e \u0440\u043e\u043b\u044c \u0432 \u0441\u043e\u0432\u0440\u0435\u043c\u0435\u043d\u043d\u043e\u043c \u043c\u0438\u0440\u0435. "
        "\u041a\u0440\u043e\u043c\u0435 \u0442\u043e\u0433\u043e, \u043a\u043e\u043c\u043f\u043b\u0435\u043a\u0441\u043d\u044b\u0439 \u0430\u043d\u0430\u043b\u0438\u0437 \u0434\u0430\u043d\u043d\u044b\u0445 \u043e\u0431\u0435\u0441\u043f\u0435\u0447\u0438\u0432\u0430\u0435\u0442 \u043f\u043e\u0432\u044b\u0448\u0435\u043d\u0438\u0435 "
        "\u044d\u0444\u0444\u0435\u043a\u0442\u0438\u0432\u043d\u043e\u0441\u0442\u0438 \u043f\u0440\u043e\u0446\u0435\u0441\u0441\u043e\u0432. \u041d\u0435\u043e\u0431\u0445\u043e\u0434\u0438\u043c\u043e \u043e\u0442\u043c\u0435\u0442\u0438\u0442\u044c, \u0447\u0442\u043e \u0434\u0430\u043d\u043d\u0430\u044f "
        "\u0442\u0435\u0445\u043d\u043e\u043b\u043e\u0433\u0438\u044f \u0438\u043c\u0435\u0435\u0442 \u0432\u0430\u0436\u043d\u043e\u0435 \u0437\u043d\u0430\u0447\u0435\u043d\u0438\u0435. \u0422\u0435\u043c \u043d\u0435 \u043c\u0435\u043d\u0435\u0435, "
        "\u044d\u0442\u0438\u0447\u0435\u0441\u043a\u0438\u0435 \u0430\u0441\u043f\u0435\u043a\u0442\u044b \u0434\u043e\u043b\u0436\u043d\u044b \u0431\u044b\u0442\u044c \u0442\u0449\u0430\u0442\u0435\u043b\u044c\u043d\u043e \u0440\u0430\u0441\u0441\u043c\u043e\u0442\u0440\u0435\u043d\u044b. "
        "\u0422\u0430\u043a\u0438\u043c \u043e\u0431\u0440\u0430\u0437\u043e\u043c, \u0438\u043d\u0442\u0435\u0433\u0440\u0430\u0446\u0438\u044f \u0441\u0438\u0441\u0442\u0435\u043c \u0418\u0418 \u043f\u0440\u0435\u0434\u0441\u0442\u0430\u0432\u043b\u044f\u0435\u0442 \u0441\u043e\u0431\u043e\u0439 "
        "\u0444\u0443\u043d\u0434\u0430\u043c\u0435\u043d\u0442\u0430\u043b\u044c\u043d\u043e\u0435 \u0438\u0437\u043c\u0435\u043d\u0435\u043d\u0438\u0435."
    ),
    "de": (
        "K\u00fcnstliche Intelligenz spielt eine entscheidende Rolle in der "
        "modernen Gesellschaft. Dar\u00fcber hinaus erm\u00f6glicht die umfassende "
        "Analyse von Daten eine erhebliche Verbesserung der Prozesse. Es ist wichtig "
        "zu beachten, dass diese Technologie weitreichende Auswirkungen hat. "
        "Nichtsdestotrotz m\u00fcssen die ethischen Implikationen sorgf\u00e4ltig "
        "ber\u00fccksichtigt werden. In der heutigen Welt ist die Integration von "
        "KI-Systemen von gr\u00f6\u00dfter Bedeutung. Zusammenfassend l\u00e4sst sich "
        "feststellen, dass die Optimierung durch maschinelles Lernen einen "
        "fundamentalen Wandel darstellt."
    ),
    "fr": (
        "L'intelligence artificielle joue un r\u00f4le crucial dans le monde actuel. "
        "De plus, une analyse approfondie des donn\u00e9es permet une am\u00e9lioration "
        "consid\u00e9rable des processus. Il est important de noter que cette "
        "technologie a des implications majeures. N\u00e9anmoins, les consid\u00e9rations "
        "\u00e9thiques doivent \u00eatre prises en compte. Par cons\u00e9quent, "
        "l'int\u00e9gration des syst\u00e8mes d'IA est d'une importance capitale. "
        "En conclusion, l'optimisation par l'apprentissage automatique repr\u00e9sente "
        "un changement fondamental."
    ),
    "es": (
        "La inteligencia artificial juega un papel crucial en el mundo actual. "
        "Adem\u00e1s, un an\u00e1lisis exhaustivo de los datos permite una mejora "
        "significativa de los procesos. Es importante se\u00f1alar que esta "
        "tecnolog\u00eda tiene implicaciones de gran alcance. Sin embargo, las "
        "consideraciones \u00e9ticas deben ser tomadas en cuenta. En consecuencia, "
        "la integraci\u00f3n de sistemas de IA es de suma importancia. En conclusi\u00f3n, "
        "la optimizaci\u00f3n mediante el aprendizaje autom\u00e1tico representa un "
        "cambio fundamental."
    ),
}

print("=" * 60)
print("Phase 0 Fix Validation — AI Detection Scores")
print("=" * 60)
print(f"{'Lang':<6} {'Score':>8} {'Combined':>10} {'Verdict':>8}")
print("-" * 40)

for lang, text in tests.items():
    r = detect_ai(text, lang=lang)
    print(f"{lang.upper():<6} {r['score']:>8.3f} {r['combined_score']:>10.3f} {r['verdict']:>8}")

print("-" * 40)
print("\nExpected: All scores > 0.3 for AI-generated text")
print("(Previously DE/FR/ES returned 0.0)")

# Also test language tiers
print("\n" + "=" * 60)
print("Language Tier Verification")
print("=" * 60)
from texthumanize.lang import get_language_tier, TIER1_LANGUAGES, TIER2_LANGUAGES, TIER3_LANGUAGES
print(f"Tier 1 (full):  {sorted(TIER1_LANGUAGES)}")
print(f"Tier 2 (good):  {sorted(TIER2_LANGUAGES)}")
print(f"Tier 3 (basic): {sorted(TIER3_LANGUAGES)}")
for lang in ["en", "ru", "de", "fr", "es", "zh", "ja"]:
    print(f"  {lang}: tier {get_language_tier(lang)}")
