"""Тест OSS бэкенда для гуманизации."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import texthumanize as th

TEXTS = {
    "en": (
        "Artificial intelligence has fundamentally transformed the landscape of modern technology. "
        "The implementation of machine learning algorithms has enabled unprecedented capabilities "
        "in data processing and pattern recognition. Furthermore, the integration of neural networks "
        "has significantly enhanced the accuracy of predictive models."
    ),
    "ru": (
        "Искусственный интеллект кардинально трансформировал ландшафт современных технологий. "
        "Внедрение алгоритмов машинного обучения обеспечило беспрецедентные возможности в обработке "
        "данных и распознавании паттернов. Более того, интеграция нейронных сетей значительно "
        "повысила точность предиктивных моделей."
    ),
    "uk": (
        "Штучний інтелект кардинально трансформував ландшафт сучасних технологій. "
        "Впровадження алгоритмів машинного навчання забезпечило безпрецедентні можливості "
        "в обробці даних та розпізнаванні патернів. Більш того, інтеграція нейронних мереж "
        "значно підвищила точність предиктивних моделей."
    ),
}

print("=" * 70)
print("ТЕСТ OSS БЭКЕНДА")
print("=" * 70)

for lang in ["en", "ru", "uk"]:
    txt = TEXTS[lang]
    det_before = th.detect_ai(txt, lang=lang)
    score_before = det_before.get("combined_score", 0)
    
    print(f"\n{'─'*50}")
    print(f"  {lang.upper()}: Оригинал AI score = {score_before:.3f}")
    
    try:
        result = th.humanize(txt, lang=lang, intensity=60, backend="oss")
        det_after = th.detect_ai(result.text, lang=lang)
        score_after = det_after.get("combined_score", 0)
        
        print(f"  OSS результат: {score_after:.3f}  (Δ={score_before-score_after:+.3f})")
        print(f"  Backend использован: oss")
        print(f"  Change ratio: {result.change_ratio:.1%}")
        print(f"  Текст (начало): {result.text[:150]}...")
    except Exception as e:
        print(f"  OSS ОШИБКА: {e}")
        print(f"  (Это нормально если OSS Gradio недоступен — используется fallback)")
        
        # Fallback: тест через humanize_ai
        try:
            result = th.humanize_ai(txt, lang=lang, enable_oss=True)
            det_after = th.detect_ai(result.text, lang=lang)
            score_after = det_after.get("combined_score", 0)
            print(f"  Fallback результат: {score_after:.3f}  (Δ={score_before-score_after:+.3f})")
        except Exception as e2:
            print(f"  Fallback тоже упал: {e2}")

print("\n\n" + "=" * 70)
print("ТЕСТ backend='auto' (попробует oss -> local)")
print("=" * 70)

for lang in ["en", "ru"]:
    txt = TEXTS[lang]
    det_before = th.detect_ai(txt, lang=lang)
    score_before = det_before.get("combined_score", 0)
    
    try:
        result = th.humanize(txt, lang=lang, intensity=60, backend="auto")
        det_after = th.detect_ai(result.text, lang=lang)
        score_after = det_after.get("combined_score", 0)
        
        print(f"\n  {lang.upper()}: {score_before:.3f} → {score_after:.3f}  (Δ={score_before-score_after:+.3f})")
        print(f"  Change ratio: {result.change_ratio:.1%}")
    except Exception as e:
        print(f"\n  {lang.upper()}: ОШИБКА auto backend: {e}")

print("\nDone.")
