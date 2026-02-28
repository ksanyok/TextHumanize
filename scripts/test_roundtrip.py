#!/usr/bin/env python3
"""Full round-trip validation: detect → humanize → re-detect."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from texthumanize import detect_ai, humanize

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
    "de": (
        "K\u00fcnstliche Intelligenz spielt eine entscheidende Rolle in der "
        "modernen Gesellschaft. Dar\u00fcber hinaus erm\u00f6glicht die umfassende "
        "Analyse von Daten eine erhebliche Verbesserung der Prozesse. Es ist "
        "wichtig zu beachten, dass diese Technologie weitreichende Auswirkungen hat. "
        "Nichtsdestotrotz m\u00fcssen die ethischen Implikationen sorgf\u00e4ltig "
        "ber\u00fccksichtigt werden. In der heutigen Welt ist die Integration von "
        "KI-Systemen von gr\u00f6\u00dfter Bedeutung."
    ),
    "fr": (
        "L'intelligence artificielle joue un r\u00f4le crucial dans le monde actuel. "
        "De plus, une analyse approfondie des donn\u00e9es permet une am\u00e9lioration "
        "consid\u00e9rable des processus. Il est important de noter que cette "
        "technologie a des implications majeures. N\u00e9anmoins, les consid\u00e9rations "
        "\u00e9thiques doivent \u00eatre prises en compte. En conclusion, l'optimisation "
        "par l'apprentissage automatique repr\u00e9sente un changement fondamental."
    ),
    "es": (
        "La inteligencia artificial juega un papel crucial en el mundo actual. "
        "Adem\u00e1s, un an\u00e1lisis exhaustivo de los datos permite una mejora "
        "significativa de los procesos. Es importante se\u00f1alar que esta "
        "tecnolog\u00eda tiene implicaciones de gran alcance. Sin embargo, las "
        "consideraciones \u00e9ticas deben ser tomadas en cuenta. En conclusi\u00f3n, "
        "la optimizaci\u00f3n mediante el aprendizaje autom\u00e1tico representa "
        "un cambio fundamental."
    ),
}

print("=" * 70)
print("FULL ROUND-TRIP: DETECT \u2192 HUMANIZE \u2192 RE-DETECT")
print("=" * 70)
print(f"{'Lang':<5} {'Before':>8} {'After':>8} {'Drop':>8} {'Change%':>8} {'Verdict':>10}")
print("-" * 55)

for lang, text in tests.items():
    before = detect_ai(text, lang=lang)
    result = humanize(text, lang=lang, intensity=70, seed=42)
    after = detect_ai(result.text, lang=lang)

    score_before = before["score"]
    score_after = after["score"]
    drop = score_before - score_after
    change_pct = result.change_ratio * 100

    verdict_before = before["verdict"]
    verdict_after = after["verdict"]

    print(f"{lang.upper():<5} {score_before:>8.3f} {score_after:>8.3f} {drop:>+8.3f} {change_pct:>7.1f}% {verdict_before:>5}\u2192{verdict_after:<5}")

print("-" * 55)
print("\nGoal: Score drops >0.2, verdict changes from 'ai' to 'mixed'/'human'")
