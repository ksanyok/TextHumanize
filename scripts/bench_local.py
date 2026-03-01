"""Benchmark local backend speed + quality."""
import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import texthumanize as th

texts = {
    'en': 'Artificial intelligence has transformed modern technology. Machine learning enables new capabilities in data processing.',
    'ru': 'Искусственный интеллект трансформировал современные технологии. Машинное обучение обеспечило новые возможности в обработке данных.',
    'uk': 'Штучний інтелект трансформував сучасні технології. Машинне навчання забезпечило нові можливості в обробці даних.',
}

print("=== LOCAL BACKEND BENCHMARK ===\n")
for lang, txt in texts.items():
    orig_d = th.detect_ai(txt, lang=lang)
    orig = orig_d.get('combined_score', orig_d.get('score', 0))
    
    start = time.time()
    r = th.humanize(txt, lang=lang, intensity=40)
    elapsed = time.time() - start
    
    d = th.detect_ai(r.text, lang=lang)
    score = d.get('combined_score', d.get('score', 0))
    
    verdict = d.get('verdict', '?')
    print(f"{lang.upper()}: {orig:.3f} → {score:.3f} (Δ={orig-score:+.3f}) [{verdict}] time={elapsed:.3f}s ratio={r.change_ratio:.1%}")

# Adaptive
print("\n=== ADAPTIVE ===\n")
for lang, txt in texts.items():
    orig_d = th.detect_ai(txt, lang=lang)
    orig = orig_d.get('combined_score', orig_d.get('score', 0))
    
    start = time.time()
    r = th.humanize_until_human(txt, lang=lang, intensity=40, target_score=0.40, max_attempts=2, strategy="adaptive")
    elapsed = time.time() - start
    
    d = th.detect_ai(r.text, lang=lang)
    score = d.get('combined_score', d.get('score', 0))
    verdict = d.get('verdict', '?')
    print(f"{lang.upper()}: {orig:.3f} → {score:.3f} (Δ={orig-score:+.3f}) [{verdict}] time={elapsed:.3f}s ratio={r.change_ratio:.1%}")
