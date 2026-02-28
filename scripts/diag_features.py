"""Diagnostic: show individual detector scores and key neural features."""
import sys
sys.path.insert(0, ".")

from texthumanize import humanize
from texthumanize.core import detect_ai

text = (
    "Furthermore, this comprehensive analysis demonstrates that implementing "
    "sophisticated methodological frameworks necessitates careful consideration "
    "of various interconnected parameters. It is important to note that the "
    "utilization of advanced computational techniques has fundamentally "
    "transformed our understanding of complex systems. Additionally, the "
    "integration of these innovative approaches facilitates enhanced operational "
    "efficiency across multiple domains of scientific inquiry.\n\n"
    "Moreover, the systematic evaluation of empirical evidence suggests that "
    "adopting rigorous analytical protocols yields significant improvements in "
    "research outcomes. The implementation of state-of-the-art algorithms "
    "enables researchers to process vast quantities of data with unprecedented "
    "accuracy. Furthermore, it is crucial to acknowledge that the convergence "
    "of interdisciplinary perspectives provides a more holistic understanding "
    "of the phenomena under investigation.\n\n"
    "In conclusion, the aforementioned findings underscore the paramount "
    "importance of embracing technological advancements in contemporary research "
    "paradigms. These developments not only enhance the precision of our "
    "analyses but also open new avenues for groundbreaking discoveries. "
    "Consequently, it is imperative that the scientific community continues to "
    "invest in cutting-edge methodologies to address the increasingly complex "
    "challenges of the modern era."
)

# Before
d = detect_ai(text, lang="en")
print("=== BEFORE ===")
print(f"  combined:   {d['combined_score']:.4f}")
print(f"  heuristic:  {d.get('heur_score', '?')}")
print(f"  statistical:{d.get('stat_score', '?')}")
print(f"  neural:     {d.get('neural_score', '?')}")

# After
r = humanize(text, lang="en", intensity=70, seed=42)
d2 = detect_ai(r.text, lang="en")
print(f"\n=== AFTER (INT=70) ===")
print(f"  combined:   {d2['combined_score']:.4f}")
print(f"  heuristic:  {d2.get('heur_score', '?')}")
print(f"  statistical:{d2.get('stat_score', '?')}")
print(f"  neural:     {d2.get('neural_score', '?')}")

# Show all keys
print(f"\n  Keys: {list(d2.keys())}")
print(f"  heuristic:  {d2.get('heuristic_score', '?')}")
print(f"  stat_prob:   {d2.get('stat_probability', '?')}")
print(f"  neural_prob: {d2.get('neural_probability', '?')}")
print(f"  perplexity:  {d2.get('neural_perplexity_score', '?')}")

# Repeat for before
print(f"\n  BEFORE heuristic:  {d.get('heuristic_score', '?')}")
print(f"  BEFORE stat_prob:   {d.get('stat_probability', '?')}")
print(f"  BEFORE neural_prob: {d.get('neural_probability', '?')}")
print(f"  BEFORE perplexity:  {d.get('neural_perplexity_score', '?')}")

# Feature analysis for neural
from texthumanize.neural_detector import NeuralAIDetector, _FEATURE_NAMES, extract_features
nd = NeuralAIDetector()
feats_before_dict = nd.extract_features(text, "en")
feats_after_dict = nd.extract_features(r.text, "en")

print(f"\n=== NEURAL FEATURES (before → after) ===")
for name in _FEATURE_NAMES:
    b = feats_before_dict.get(name, 0)
    a = feats_after_dict.get(name, 0)
    delta = a - b
    marker = " ***" if abs(delta) > 0.3 else ""
    print(f"  {name:30s}: {b:+8.4f} → {a:+8.4f}  (Δ{delta:+.4f}){marker}")
