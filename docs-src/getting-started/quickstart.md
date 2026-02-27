# Quick Start

## Basic Humanization

```python
from texthumanize import humanize

result = humanize(
    "Furthermore, it is important to note that the implementation "
    "of cloud computing facilitates the optimization of business processes.",
    lang="en",
    profile="web",
    intensity=70,
)

print(result.text)           # Humanized text
print(result.change_ratio)   # e.g. 0.15
print(result.quality_score)  # e.g. 0.85
```

## AI Detection

```python
from texthumanize import detect_ai

ai = detect_ai("Text to check for AI generation.", lang="en")
print(f"AI: {ai['score']:.0%} | {ai['verdict']} | Confidence: {ai['confidence']:.0%}")
```

Verdicts: `human_written` (< 35%) · `mixed` (35–65%) · `ai_generated` (≥ 65%)

## Text Analysis

```python
from texthumanize import analyze

report = analyze("Text to analyze.", lang="en")
print(f"Artificiality: {report.artificiality_score:.1f}/100")
```

## Change Report

```python
from texthumanize import humanize, explain

result = humanize("Your text here.", lang="en")
print(explain(result))
```

## All-in-One Example

```python
from texthumanize import (
    humanize, humanize_batch, detect_ai,
    paraphrase, analyze_tone, adjust_tone,
    clean_watermarks, spin_variants,
)

# Batch processing (parallel)
results = humanize_batch(["Text 1", "Text 2"], lang="en", max_workers=4)

# Paraphrasing
print(paraphrase("The system works efficiently.", lang="en"))

# Tone analysis and adjustment
tone = analyze_tone("Please submit the documentation.", lang="en")
casual = adjust_tone("It is imperative to proceed.", target="casual", lang="en")

# Watermark cleaning
clean = clean_watermarks("Te\u200bxt wi\u200bth hid\u200bden chars")

# Content spinning
variants = spin_variants("Original text.", count=5, lang="en")
```

## Async Usage

```python
import asyncio
from texthumanize import async_humanize, async_detect_ai

async def main():
    result = await async_humanize("Your text here.", lang="en")
    print(result.text)

    ai = await async_detect_ai("Check this text.", lang="en")
    print(ai["verdict"])

asyncio.run(main())
```

## Reproducible Output

```python
# Same seed = same output, every time
r1 = humanize("Text here.", lang="en", seed=42)
r2 = humanize("Text here.", lang="en", seed=42)
assert r1.text == r2.text  # Always true
```
