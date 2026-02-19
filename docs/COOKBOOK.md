# TextHumanize Cookbook

Practical recipes for common use cases.

---

## Recipe 1: Basic Text Humanization

```python
from texthumanize import humanize

text = """The implementation of artificial intelligence systems 
necessitates a comprehensive understanding of the underlying 
methodologies. Furthermore, it is essential to ensure that 
the optimization processes are conducted systematically."""

result = humanize(text, lang="en", intensity=60)
print(result.text)
print(f"AI score: {result.metrics_before['artificiality_score']} → {result.metrics_after['artificiality_score']}")
print(f"Change ratio: {result.change_ratio:.1%}")
```

---

## Recipe 2: SEO-Safe Processing

Preserve keywords while humanizing:

```python
result = humanize(
    text,
    profile="seo",
    constraints={
        "keep_keywords": ["artificial intelligence", "optimization"],
        "max_change_ratio": 0.25,
    },
)
```

---

## Recipe 3: Target a Student Writing Style

```python
from texthumanize import humanize, STYLE_PRESETS

result = humanize(
    scientific_text,
    target_style="student",
    intensity=70,
)
# Output will have shorter sentences, simpler vocabulary
```

---

## Recipe 4: Batch Processing

```python
from texthumanize import humanize_batch

texts = [paragraph1, paragraph2, paragraph3]
results = humanize_batch(texts, lang="en", max_workers=4)

for r in results:
    print(f"Quality: {r.quality_score:.2f}")
```

---

## Recipe 5: Large Document Processing

```python
from texthumanize import humanize_chunked

# Splits at paragraph boundaries, processes in chunks
result = humanize_chunked(
    large_document,
    chunk_size=3000,  # chars per chunk
    lang="ru",
)
```

---

## Recipe 6: AI Detection Pipeline

```python
from texthumanize import detect_ai, detect_ai_sentences

# Quick check
verdict = detect_ai(text)
print(f"Verdict: {verdict['verdict']} ({verdict['score']}%)")

# Per-sentence breakdown
sentences = detect_ai_sentences(text)
for s in sentences:
    if s['label'] == 'ai':
        print(f"  AI: {s['text'][:80]}...")
```

---

## Recipe 7: Auto-Tuning Pipeline

```python
from texthumanize import humanize, AutoTuner

tuner = AutoTuner(history_path="tune_history.json")

# Process multiple texts, recording each result
for text in my_texts:
    intensity = tuner.suggest_intensity(text, lang="en")
    result = humanize(text, lang="en", intensity=intensity)
    tuner.record(result)

# Check accumulated stats
stats = tuner.summary()
print(f"Processed: {stats['total_records']} texts")
print(f"Suggested params: {tuner.suggest_params(lang='en').to_dict()}")
```

---

## Recipe 8: Reproducible Results

```python
# Same seed = same output every time
result1 = humanize(text, seed=42)
result2 = humanize(text, seed=42)
assert result1.text == result2.text
```

---

## Recipe 9: Custom Pipeline Plugin

```python
from texthumanize import Pipeline, HumanizeOptions

def add_emoji(text: str, lang: str) -> str:
    """Add a relevant emoji to the first sentence."""
    return "✨ " + text

pipeline = Pipeline(HumanizeOptions(lang="en"))
pipeline.register_plugin("typography", add_emoji, before=False)

result = pipeline.run("Boring text here.", lang="en")
print(result.text)  # "✨ Boring text here."
```

---

## Recipe 10: Multi-Language Processing

```python
from texthumanize import humanize

# Auto-detect language
texts = {
    "en": "The implementation utilizes comprehensive methodologies.",
    "ru": "Осуществление данной задачи является приоритетным.",
    "de": "Die Implementierung erfordert eine umfassende Analyse.",
}

for label, text in texts.items():
    result = humanize(text, lang="auto")
    print(f"[{result.lang}] {result.text}")
```

---

## Recipe 11: Tone Adjustment

```python
from texthumanize import analyze_tone, adjust_tone

# Check current tone
tone = analyze_tone("Hey, check this out! It's awesome!")
print(f"Current: {tone['level']} (score: {tone['score']})")

# Make it more formal
formal = adjust_tone("Hey, check this out!", target="formal")
print(formal)
```

---

## Recipe 12: Watermark Detection & Cleaning

```python
from texthumanize import detect_watermarks, clean_watermarks

# Check for hidden watermarks
result = detect_watermarks(suspicious_text)
if result["has_watermark"]:
    print(f"Found: {result['types']}")
    clean = clean_watermarks(suspicious_text)
```

---

## Recipe 13: Text Spinning

```python
from texthumanize import spin, spin_variants

# Single variant
variant = spin(text, lang="en", intensity=0.5)

# Multiple variants
variants = spin_variants(text, count=5, lang="en")
for i, v in enumerate(variants):
    print(f"Variant {i+1}: {v[:100]}...")
```

---

## Recipe 14: Stylistic Fingerprinting

```python
from texthumanize import StylisticAnalyzer, StylisticFingerprint

# Extract style from a sample
analyzer = StylisticAnalyzer(lang="en")
my_style = analyzer.extract(my_writing_sample)

# Use as target
result = humanize(ai_text, target_style=my_style)

# Compare two styles
similarity = my_style.similarity(other_style)
print(f"Style similarity: {similarity:.1%}")
```
