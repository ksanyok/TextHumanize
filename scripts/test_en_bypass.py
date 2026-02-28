"""Quick test: EN bypass measurement."""
import logging
logging.basicConfig(level=logging.WARNING)

from texthumanize import humanize
from texthumanize.core import detect_ai

ai_text = (
    "Artificial intelligence has become an increasingly important technology "
    "in the modern world. It is transforming various industries and sectors. "
    "Furthermore, the implementation of AI systems has demonstrated significant "
    "improvements in efficiency and productivity. There are numerous applications "
    "that utilize machine learning algorithms to process large amounts of data. "
    "This technology is not without its challenges, however. Nevertheless, the "
    "benefits of AI are substantial and will continue to grow in the near future. "
    "In conclusion, AI represents a paradigm shift in how we approach "
    "problem-solving and innovation."
)

# Before
score_before = detect_ai(ai_text, lang="en")
print(f"Before: {score_before['combined_score']:.3f} ({score_before['verdict']})")

# Humanize at different intensities
for intensity in [50, 70, 90]:
    result = humanize(ai_text, lang="en", intensity=intensity, seed=42)
    score_after = detect_ai(result.text, lang="en")
    changes = [c['type'] for c in result.changes]
    has_restructure = any('contraction' in c or 'register' in c or 'reshaping' in c or 'discourse' in c for c in changes)
    print(f"\nIntensity={intensity}: {score_before['combined_score']:.3f} -> {score_after['combined_score']:.3f} ({score_after['verdict']}) CR={result.change_ratio:.3f}")
    print(f"  Changes: {changes}")
    print(f"  Restructure fired: {has_restructure}")
    print(f"  Text: {result.text[:200]}")
