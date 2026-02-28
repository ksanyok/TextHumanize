"""Benchmark EN bypass at different intensity levels."""
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

d_before = detect_ai(text, lang="en")
print(f"BEFORE: combined={d_before['combined_score']:.4f}")
print()

for intensity in [50, 70, 90]:
    r = humanize(text, lang="en", intensity=intensity, seed=42)
    d_after = detect_ai(r.text, lang="en")
    print(f"INT={intensity}: combined={d_after['combined_score']:.4f}  "
          f"art_before={r.metrics_before.get('artificiality_score', 0):.1f}  "
          f"art_after={r.metrics_after.get('artificiality_score', 0):.1f}")
    print(f"  Changes: {len(r.changes)}")
    if intensity == 70:
        print(f"\n  === INT=70 OUTPUT ===")
        print(f"  {r.text[:500]}...")
        print()
        # Show change types
        types = {}
        for c in r.changes:
            t = c.get("type", "unknown")
            types[t] = types.get(t, 0) + 1
        print(f"  Change types: {types}")
    print()
