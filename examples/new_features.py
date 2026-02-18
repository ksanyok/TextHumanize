"""
TextHumanize v0.4.0 — New Features Demo.

Demonstrates: AI detection, paraphrasing, tone analysis,
watermark cleaning, text spinning, coherence analysis.
"""

from texthumanize import (
    detect_ai,
    paraphrase,
    analyze_tone,
    adjust_tone,
    detect_watermarks,
    clean_watermarks,
    spin,
    spin_variants,
    analyze_coherence,
)


def demo_ai_detection():
    """AI text detection with 12 statistical metrics."""

    print("=" * 60)
    print("1. AI Text Detection")
    print("=" * 60)

    ai_text = (
        "Furthermore, it is important to note that artificial intelligence "
        "has significantly transformed the landscape of modern technology. "
        "The comprehensive implementation of machine learning algorithms has "
        "fundamentally altered how we approach complex problems. Additionally, "
        "these innovative solutions leverage cutting-edge methodologies to "
        "optimize performance across a wide range of applications."
    )

    human_text = (
        "So I was thinking about this the other day. You know how everyone "
        "keeps talking about AI? Well here's the thing. Most people don't "
        "really get what it does. My friend works at a tech startup, and "
        "honestly? Most of their AI just sorts emails. Yep. That's it."
    )

    print("\n--- AI-generated text ---")
    result = detect_ai(ai_text, lang="en")
    print(f"  AI probability: {result['score']:.1%}")
    print(f"  Verdict: {result['verdict']}")
    print(f"  Confidence: {result['confidence']:.1%}")
    print(f"  Key signals: pattern={result['metrics']['ai_patterns']:.2f}, "
          f"burstiness={result['metrics']['burstiness']:.2f}")

    print("\n--- Human-written text ---")
    result = detect_ai(human_text, lang="en")
    print(f"  AI probability: {result['score']:.1%}")
    print(f"  Verdict: {result['verdict']}")


def demo_paraphrasing():
    """Algorithmic paraphrasing."""

    print("\n" + "=" * 60)
    print("2. Paraphrasing")
    print("=" * 60)

    text = (
        "Furthermore, it is important to note that the implementation "
        "of cloud computing facilitates optimization of business processes."
    )

    result = paraphrase(text, lang="en")
    print(f"\n  Original:    {text}")
    print(f"  Paraphrased: {result}")


def demo_tone():
    """Tone analysis and adjustment."""

    print("\n" + "=" * 60)
    print("3. Tone Analysis & Adjustment")
    print("=" * 60)

    formal = "Furthermore, it is imperative to implement this comprehensive solution promptly."
    casual = "Hey, we gotta do this thing ASAP, you know?"

    print("\n--- Formal text ---")
    tone = analyze_tone(formal, lang="en")
    print(f"  Text: {formal}")
    print(f"  Tone: {tone['primary_tone']}")
    print(f"  Formality: {tone['formality']:.2f}")

    print("\n--- Casual text ---")
    tone = analyze_tone(casual, lang="en")
    print(f"  Text: {casual}")
    print(f"  Tone: {tone['primary_tone']}")

    print("\n--- Adjusting formal -> casual ---")
    adjusted = adjust_tone(formal, target="casual", lang="en")
    print(f"  Original: {formal}")
    print(f"  Casual:   {adjusted}")

    print("\n--- Adjusting casual -> formal ---")
    adjusted = adjust_tone(casual, target="formal", lang="en")
    print(f"  Original: {casual}")
    print(f"  Formal:   {adjusted}")


def demo_watermark():
    """Watermark detection and cleaning."""

    print("\n" + "=" * 60)
    print("4. Watermark Detection & Cleaning")
    print("=" * 60)

    # Insert zero-width characters as watermark
    clean_text = "This is a clean text without watermarks."
    watermarked = "This\u200b is\u200b a\u200b watermarked\u200b text."

    print(f"\n--- Clean text ---")
    report = detect_watermarks(clean_text)
    print(f"  Text: {clean_text}")
    print(f"  Has watermark: {report['has_watermarks']}")

    print(f"\n--- Watermarked text ---")
    report = detect_watermarks(watermarked)
    print(f"  Text repr: {repr(watermarked[:50])}")
    print(f"  Has watermark: {report['has_watermarks']}")
    print(f"  Types: {report['watermark_types']}")
    print(f"  Confidence: {report['confidence']:.2f}")

    cleaned = clean_watermarks(watermarked)
    print(f"  Cleaned: {cleaned}")


def demo_spinner():
    """Text spinning and variant generation."""

    print("\n" + "=" * 60)
    print("5. Text Spinning")
    print("=" * 60)

    text = "The system provides important data for analysis and review."

    result = spin(text, lang="en")
    print(f"\n  Original:    {text}")
    print(f"  Spun:        {result}")

    # Spintax format
    from texthumanize.spinner import ContentSpinner
    spinner = ContentSpinner(lang="en", seed=42)
    spintax = spinner.generate_spintax(text)
    print(f"  Spintax:     {spintax}")

    # Multiple variants
    variants = spin_variants(text, count=3, lang="en")
    print(f"\n  Variants:")
    for i, v in enumerate(variants, 1):
        print(f"    {i}. {v}")


def demo_coherence():
    """Coherence analysis."""

    print("\n" + "=" * 60)
    print("6. Coherence Analysis")
    print("=" * 60)

    coherent = (
        "Machine learning is a subset of artificial intelligence. "
        "It allows computers to learn from data without explicit programming. "
        "Neural networks are a popular machine learning approach. "
        "They are inspired by the structure of the human brain. "
        "Deep learning uses multiple layers of neural networks. "
        "This technique has achieved remarkable results in image recognition."
    )

    report = analyze_coherence(coherent, lang="en")
    print(f"\n  Overall coherence: {report['overall']:.2f}")
    print(f"  Lexical cohesion:  {report['lexical_cohesion']:.2f}")
    print(f"  Transition score:  {report['transition_score']:.2f}")
    print(f"  Topic consistency: {report['topic_consistency']:.2f}")
    print(f"  Paragraphs:        {report['paragraph_count']}")

    if report['issues']:
        print(f"  Issues:")
        for issue in report['issues']:
            print(f"    - {issue}")


if __name__ == "__main__":
    demo_ai_detection()
    demo_paraphrasing()
    demo_tone()
    demo_watermark()
    demo_spinner()
    demo_coherence()

    print("\n" + "=" * 60)
    print("All demos completed!")
    print("=" * 60)
