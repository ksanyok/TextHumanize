"""
Benchmark AI Detector — evaluate accuracy on sample texts.

Runs the detector on a collection of known AI and human texts
and reports precision, recall, F1-score, and per-sample details.

Usage:
    python3 examples/benchmark_detector.py
"""

from texthumanize.detectors import AIDetector


# ═══════════════════════════════════════════════════════════════
#  TEST CORPUS
# ═══════════════════════════════════════════════════════════════

SAMPLES = [
    # ── AI-generated (EN) ────────────────────────────────────
    {
        "label": "AI: Formal essay on AI",
        "expected": "ai",
        "lang": "en",
        "text": (
            "Furthermore, it is important to note that artificial intelligence "
            "has significantly transformed the landscape of modern technology. "
            "The comprehensive implementation of machine learning algorithms has "
            "fundamentally altered how we approach complex problems. Additionally, "
            "these innovative solutions leverage cutting-edge methodologies to "
            "optimize performance across a wide range of applications. Moreover, "
            "the seamless integration of AI systems into existing infrastructure "
            "has proven to be remarkably effective. Consequently, organizations "
            "that harness these transformative technologies are well-positioned "
            "to navigate the challenges of the modern era. In conclusion, the "
            "pivotal role of AI in shaping our future cannot be overstated."
        ),
    },
    {
        "label": "AI: Cybersecurity article",
        "expected": "ai",
        "lang": "en",
        "text": (
            "In today's rapidly evolving digital landscape, the importance of "
            "cybersecurity cannot be overstated. Organizations must implement "
            "robust security measures to protect their sensitive data from "
            "increasingly sophisticated threats. It is crucial to understand that "
            "a comprehensive approach to cybersecurity encompasses multiple layers "
            "of defense. Furthermore, regular security audits and vulnerability "
            "assessments are essential components of any effective security strategy. "
            "Additionally, employee training plays a pivotal role in maintaining "
            "organizational security. Therefore, investing in cybersecurity "
            "infrastructure is not merely advisable but imperative for long-term "
            "sustainability."
        ),
    },
    {
        "label": "AI: Climate change essay",
        "expected": "ai",
        "lang": "en",
        "text": (
            "Climate change represents one of the most pressing challenges facing "
            "humanity in the twenty-first century. The scientific consensus overwhelmingly "
            "supports the conclusion that human activities are the primary driver of "
            "global warming. Consequently, it is imperative that governments, corporations, "
            "and individuals take decisive action to mitigate greenhouse gas emissions. "
            "Furthermore, the implementation of renewable energy solutions has demonstrated "
            "remarkable potential in reducing our dependence on fossil fuels. Additionally, "
            "sustainable agricultural practices play a crucial role in addressing food "
            "security concerns while simultaneously reducing environmental impact. "
            "In essence, a comprehensive and collaborative approach is essential for "
            "effectively addressing the multifaceted challenges posed by climate change."
        ),
    },
    {
        "label": "AI: Education technology",
        "expected": "ai",
        "lang": "en",
        "text": (
            "The integration of technology in education has fundamentally transformed "
            "the learning experience for students across all educational levels. "
            "Digital tools and platforms facilitate personalized learning pathways "
            "that cater to individual student needs and learning styles. Moreover, "
            "the utilization of artificial intelligence in educational settings "
            "enables adaptive assessment and real-time feedback mechanisms. "
            "It is worth mentioning that online learning platforms have democratized "
            "access to quality education, particularly in underserved communities. "
            "Nevertheless, it is important to acknowledge the challenges associated "
            "with the digital divide and ensure equitable access to technological "
            "resources for all learners."
        ),
    },

    # ── Human-written (EN) ────────────────────────────────────
    {
        "label": "Human: Casual blog post",
        "expected": "human",
        "lang": "en",
        "text": (
            "So I was thinking about this the other day. You know how everyone "
            "keeps talking about AI? Well, here's the thing. Most people don't "
            "really get what it does. They hear 'artificial intelligence' and "
            "imagine robots taking over. But that's not quite it. My friend works "
            "at a tech startup, and honestly? Most of their AI just sorts emails. "
            "Yep. That's it. Pretty anticlimactic, right? Sure, there are fancier "
            "applications out there. Self-driving cars and whatnot. But the "
            "day-to-day stuff is way more boring than sci-fi movies would have "
            "you believe."
        ),
    },
    {
        "label": "Human: Cooking story",
        "expected": "human",
        "lang": "en",
        "text": (
            "I tried making sourdough bread last weekend. What a disaster. The "
            "recipe said wait until the dough doubles in size, mine barely moved "
            "after 6 hours. Turns out my kitchen was too cold? I don't know. "
            "My neighbor told me that's normal in winter. Just put it near the "
            "radiator, she said. So I did. And then I forgot about it. For 14 "
            "hours. The dough overflowed the bowl. Long story short: the bread "
            "came out looking like a pancake but honestly it tasted pretty good! "
            "Maybe not Instagram-worthy, but my kids ate it. I call that a win."
        ),
    },
    {
        "label": "Human: Forum post",
        "expected": "human",
        "lang": "en",
        "text": (
            "Has anyone else had this issue with the latest update? My app keeps "
            "crashing whenever I try to open settings. I've tried reinstalling "
            "three times now. Nothing works. Factory reset? Nope. Cleared cache? "
            "Still crashes. This is so frustrating. I paid $50 for this app and "
            "it doesn't even work anymore. The devs haven't responded to my "
            "support ticket from two weeks ago either. Starting to think I should "
            "just switch to a different app at this point. Anyone got recommendations? "
            "Needs to work offline too."
        ),
    },
    {
        "label": "Human: Personal essay",
        "expected": "human",
        "lang": "en",
        "text": (
            "Moving to a new city at 30 is weird. You're too old for the college "
            "scene but too young to just stay home every night. Making friends as "
            "an adult is genuinely hard — nobody tells you that. Back in school "
            "you just sat next to someone for a semester and boom, friends. Now? "
            "You have to deliberately schedule 'friend dates' which sounds pathetic "
            "but it's true. I joined a rock climbing gym mainly for the social "
            "aspect. Met some cool people there. Still feels awkward sometimes "
            "though. Like, do I text them? How often is too often? Am I being "
            "clingy? Adulting is complicated."
        ),
    },

    # ── Mixed/Edge cases ───────────────────────────────────────
    {
        "label": "Formal human: Research abstract",
        "expected": "human",
        "lang": "en",
        "text": (
            "The study examined 200 patients over a twelve-week period. Results "
            "showed a modest improvement in the treatment group compared to placebo. "
            "Three participants dropped out due to side effects. Blood pressure "
            "readings were taken every Monday. The data suggests some benefit, "
            "though the sample size limits our conclusions. We plan a larger trial "
            "next year. Dr. Kim noted that the dosage may need adjustment. The "
            "funding committee approved an extension through March."
        ),
    },
]


def run_benchmark():
    """Run the benchmark and print results."""
    detector = AIDetector(lang="en")

    print("=" * 80)
    print("AI DETECTOR BENCHMARK")
    print("=" * 80)
    print()

    tp = fp = tn = fn = 0
    results = []

    for sample in SAMPLES:
        result = detector.detect(sample["text"], lang=sample["lang"])

        is_ai_expected = sample["expected"] == "ai"
        is_ai_predicted = result.verdict == "ai"
        is_mixed = result.verdict == "mixed"

        if is_ai_expected and is_ai_predicted:
            tp += 1
            status = "TP"
        elif is_ai_expected and not is_ai_predicted:
            fn += 1
            status = "FN" if not is_mixed else "FN~"
        elif not is_ai_expected and is_ai_predicted:
            fp += 1
            status = "FP"
        else:
            tn += 1
            status = "TN" if not is_mixed else "TN~"

        results.append({
            "label": sample["label"],
            "expected": sample["expected"],
            "verdict": result.verdict,
            "prob": result.ai_probability,
            "confidence": result.confidence,
            "status": status,
        })

    # Print per-sample results
    print(f"{'Label':<35s} | {'Expected':>8s} | {'Verdict':>7s} | {'Prob':>6s} | {'Conf':>6s} | Status")
    print("-" * 80)
    for r in results:
        print(
            f"{r['label']:<35s} | {r['expected']:>8s} | {r['verdict']:>7s} | "
            f"{r['prob']:>5.1%} | {r['confidence']:>5.1%} | {r['status']}"
        )

    print()
    print("=" * 80)
    print(f"CONFUSION MATRIX:  TP={tp}  FP={fp}  TN={tn}  FN={fn}")

    total = tp + fp + tn + fn
    accuracy = (tp + tn) / total if total > 0 else 0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    print(f"Accuracy:  {accuracy:.1%}")
    print(f"Precision: {precision:.1%}")
    print(f"Recall:    {recall:.1%}")
    print(f"F1-Score:  {f1:.1%}")
    print("=" * 80)

    # Classification thresholds
    print(f"\nThresholds: human < 0.45 < mixed < 0.75 < ai")
    print(f"Note: 'mixed' verdicts count as errors in strict evaluation.")


if __name__ == "__main__":
    run_benchmark()
