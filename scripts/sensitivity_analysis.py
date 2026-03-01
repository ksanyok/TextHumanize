"""Feature sensitivity analysis: perturb each feature and measure MLP output change."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from texthumanize.neural_detector import (
    NeuralAIDetector, extract_features, normalize_features, _FEATURE_NAMES
)
import texthumanize as th

AI_TEXTS = {
    "en": (
        "Artificial intelligence has fundamentally transformed the landscape of modern technology. "
        "The implementation of machine learning algorithms has enabled unprecedented capabilities "
        "in data processing and pattern recognition. Furthermore, the integration of neural networks "
        "has significantly enhanced the accuracy of predictive models. It is important to note that "
        "these advancements have far-reaching implications for various industries and sectors. "
        "The continuous evolution of AI systems promises to reshape how we approach complex problems "
        "and drive innovation across multiple domains."
    ),
    "ru": (
        "Искусственный интеллект кардинально трансформировал ландшафт современных технологий. "
        "Внедрение алгоритмов машинного обучения обеспечило беспрецедентные возможности в обработке "
        "данных и распознавании паттернов. Более того, интеграция нейронных сетей значительно "
        "повысила точность предиктивных моделей. Важно отметить, что данные достижения имеют "
        "далеко идущие последствия для различных отраслей. Непрерывное развитие систем ИИ "
        "обещает кардинально изменить подходы к решению сложных задач."
    ),
    "uk": (
        "Штучний інтелект кардинально трансформував ландшафт сучасних технологій. "
        "Впровадження алгоритмів машинного навчання забезпечило безпрецедентні можливості "
        "в обробці даних та розпізнаванні патернів. Більш того, інтеграція нейронних мереж "
        "значно підвищила точність предиктивних моделей. Важливо зазначити, що дані досягнення "
        "мають далекосяжні наслідки для різних галузей. Безперервний розвиток систем ШІ "
        "обіцяє кардинально змінити підходи до розв'язання складних завдань."
    ),
}

det = NeuralAIDetector()

for lang in ["en", "ru", "uk"]:
    text = AI_TEXTS[lang]
    raw = extract_features(text, lang)
    normed = normalize_features(raw, lang)
    
    # Get baseline score
    baseline = det._net.predict_proba(normed)
    
    # Also get score for humanized text
    hum = th.humanize(text, lang=lang, intensity=60)
    raw_h = extract_features(hum.text, lang)
    normed_h = normalize_features(raw_h, lang)
    baseline_h = det._net.predict_proba(normed_h)
    
    print(f"\n{'='*70}")
    print(f"  {lang.upper()}: FEATURE SENSITIVITY ANALYSIS")
    print(f"  Baseline MLP score: AI={baseline:.4f}, Humanized={baseline_h:.4f}")
    print(f"{'='*70}")
    
    # For each feature, set it to -3 (very human) and +3 (very AI)
    sensitivities = []
    for i in range(35):
        # Push to human-like extreme (-3)
        perturbed_neg = list(normed)
        perturbed_neg[i] = -3.0
        score_neg = det._net.predict_proba(perturbed_neg)
        
        # Push to AI-like extreme (+3)
        perturbed_pos = list(normed)
        perturbed_pos[i] = 3.0
        score_pos = det._net.predict_proba(perturbed_pos)
        
        delta = score_pos - score_neg
        name = _FEATURE_NAMES[i] if i < len(_FEATURE_NAMES) else f"feat_{i}"
        sensitivities.append((name, i, delta, normed[i], raw[i], normed_h[i], raw_h[i]))
    
    # Sort by absolute impact
    sensitivities.sort(key=lambda x: abs(x[2]), reverse=True)
    
    print(f"\n  {'Feature':<28} {'Δ(+3 vs -3)':>11} {'norm_AI':>8} {'norm_HUM':>9} {'raw_AI':>8} {'raw_HUM':>9}")
    for name, idx, delta, norm_ai, raw_ai, norm_hum, raw_hum in sensitivities:
        direction = "↑AI" if delta > 0 else "↓AI"
        flag = " ★★" if abs(delta) > 0.15 else (" ★" if abs(delta) > 0.05 else "")
        print(f"  [{idx:2d}] {name:<24} {delta:+10.4f} {direction}  {norm_ai:+7.3f}  {norm_hum:+8.3f}  {raw_ai:8.4f}  {raw_hum:8.4f}{flag}")
