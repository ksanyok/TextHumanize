"""Compare features between humanized output and genuine human text."""
import sys
sys.path.insert(0, ".")
from texthumanize import humanize
from texthumanize.neural_detector import NeuralAIDetector, _FEATURE_NAMES, _FEATURE_MEAN, _FEATURE_STD

nd = NeuralAIDetector()

ai_text = (
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

human_text = (
    "I was walking down the street yesterday when I noticed something weird. "
    "The old bookshop on the corner? Gone. Just like that. Someone said it "
    "was being replaced by another coffee shop — as if we needed more of "
    "those. Honestly, the whole neighborhood has changed so much in the past "
    "year or two.\n\n"
    "Look, I get it — Shakespeare is supposed to be this towering genius of "
    "English literature. But have you actually tried reading Titus "
    "Andronicus? It's basically a slasher movie written in iambic "
    "pentameter. People lose hands, tongues get cut out, and there's a pie "
    "made of human flesh. I'm not saying it's bad, exactly. It's just... "
    "not what you expect from the guy who wrote Sonnet 18.\n\n"
    "The results from this experiment were, frankly, a bit of a mess. We "
    "tried three different approaches and none of them gave consistent "
    "numbers. My coauthor thinks the temperature sensor drifted, which — "
    "honestly — would explain a lot. Still, the third batch showed some "
    "promise, especially around the 400nm wavelength."
)

r = humanize(ai_text, lang="en", intensity=70, seed=42)

feats_human = nd.extract_features(human_text, "en")
feats_humanized = nd.extract_features(r.text, "en")
feats_ai = nd.extract_features(ai_text, "en")

print(f"{'Feature':30s} | {'AI(raw)':>10s} | {'Humanized':>10s} | {'Human':>10s} | {'Gap':>10s}")
print("-" * 85)
for i, name in enumerate(_FEATURE_NAMES):
    ai = feats_ai.get(name, 0)
    hm = feats_humanized.get(name, 0)
    hu = feats_human.get(name, 0)
    # Gap = how far the humanized is from human (negative = closer to AI)
    gap_ai = abs(ai - hu)
    gap_hm = abs(hm - hu)
    arrow = "<<<" if gap_hm > gap_ai * 0.8 else "OK" if gap_hm < gap_ai * 0.3 else ""
    print(f"  {name:30s} | {ai:10.4f} | {hm:10.4f} | {hu:10.4f} | {arrow}")
