"""Test neural detector on known human text."""
import sys
sys.path.insert(0, ".")
from texthumanize.core import detect_ai

samples = {
    "human_casual": (
        "I was walking down the street yesterday when I noticed something weird. "
        "The old bookshop on the corner? Gone. Just like that. Someone said it "
        "was being replaced by another coffee shop — as if we needed more of "
        "those. Honestly, the whole neighborhood has changed so much in the past "
        "year or two."
    ),
    "human_formal": (
        "The results from this experiment were, frankly, a bit of a mess. We "
        "tried three different approaches and none of them gave consistent "
        "numbers. My coauthor thinks the temperature sensor drifted, which — "
        "honestly — would explain a lot. Still, the third batch showed some "
        "promise, especially around the 400nm wavelength. We'll need to re-run "
        "the whole thing next week."
    ),
    "human_essay": (
        "Look, I get it — Shakespeare is supposed to be this towering genius of "
        "English literature. But have you actually tried reading Titus "
        "Andronicus? It's basically a slasher movie written in iambic "
        "pentameter. People lose hands, tongues get cut out, and there's a pie "
        "made of human flesh. I'm not saying it's bad, exactly. It's just... "
        "not what you expect from the guy who wrote Sonnet 18."
    ),
}

for name, text in samples.items():
    d = detect_ai(text, lang="en")
    print(f"{name:15s}: combined={d['combined_score']:.4f}  "
          f"neural={d['neural_probability']:.4f}  "
          f"stat={d['stat_probability']:.4f}  "
          f"heur={d['heuristic_score']:.4f}")
