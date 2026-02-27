# API Reference

Full Python API reference for TextHumanize.

## Core Functions

### `humanize(text, lang, profile, intensity, ...)`

Humanize text using the 17-stage pipeline.

```python
from texthumanize import humanize

result = humanize(
    text="Your text here.",
    lang="en",           # "auto", "ru", "uk", "en", "de", ...
    profile="web",       # "chat", "web", "seo", "docs", "formal", ...
    intensity=60,        # 0-100
    seed=42,             # For reproducibility
    preserve={"urls": True, "code_blocks": True},
    constraints={"max_change_ratio": 0.3, "keep_keywords": ["API"]},
    target_style="copywriter",  # Style preset
    only_flagged=False,  # Only humanize AI-flagged sentences
    custom_dict={"utilize": "use"},
)

# Returns HumanizeResult
result.text           # str — humanized text
result.original       # str — original text
result.lang           # str — detected/used language
result.profile        # str — profile used
result.intensity      # int — intensity used
result.changes        # list — changes made
result.change_ratio   # float — proportion changed
result.quality_score  # float — quality metric
result.metrics_before # dict — metrics before
result.metrics_after  # dict — metrics after
```

### `detect_ai(text, lang)`

Detect AI-generated content using 13 metrics.

```python
from texthumanize import detect_ai

result = detect_ai("Text to check.", lang="en")

result["score"]       # float 0-1 — AI probability
result["verdict"]     # "human_written" | "mixed" | "ai_generated"
result["confidence"]  # float 0-1
result["metrics"]     # dict — individual metric scores
```

### `analyze(text, lang)`

Get text analysis report.

```python
from texthumanize import analyze

report = analyze("Text to analyze.", lang="en")
report.artificiality_score  # float 0-100
report.word_count           # int
```

### `explain(result)`

Get human-readable change report.

```python
from texthumanize import humanize, explain

result = humanize("Text.", lang="en")
print(explain(result))
```

## Async Functions

### `async_humanize(text, lang, ...)`

Async version of `humanize()` for use with asyncio/FastAPI.

```python
from texthumanize import async_humanize

result = await async_humanize("Text.", lang="en", profile="web")
```

### `async_detect_ai(text, lang)`

Async version of `detect_ai()`.

```python
from texthumanize import async_detect_ai

result = await async_detect_ai("Text.", lang="en")
```

## NLP Functions

### `paraphrase(text, lang, intensity, seed)`

```python
from texthumanize import paraphrase
result = paraphrase("Text.", lang="en")
```

### `analyze_tone(text, lang)` / `adjust_tone(text, target, lang)`

```python
from texthumanize import analyze_tone, adjust_tone

tone = analyze_tone("Formal text.", lang="en")
casual = adjust_tone("Formal text.", target="casual", lang="en")
```

### `detect_watermarks(text)` / `clean_watermarks(text)`

```python
from texthumanize import detect_watermarks, clean_watermarks

found = detect_watermarks(text)
clean = clean_watermarks(text)
```

### `spin(text, lang)` / `spin_variants(text, count, lang)`

```python
from texthumanize import spin, spin_variants

result = spin("Text.", lang="en")
variants = spin_variants("Text.", count=5, lang="en")
```

### `analyze_coherence(text, lang)` / `full_readability(text, lang)`

```python
from texthumanize import analyze_coherence, full_readability

coherence = analyze_coherence("Paragraph text.", lang="en")
readability = full_readability("Text.", lang="en")
```

## Batch Functions

```python
from texthumanize import humanize_batch, humanize_chunked, detect_ai_batch

# Parallel batch
results = humanize_batch(["Text 1", "Text 2"], lang="en", max_workers=4)

# Chunked (large documents)
result = humanize_chunked(large_text, chunk_size=3000, lang="en")

# Batch AI detection
results = detect_ai_batch(["Text 1", "Text 2"], lang="en")
```

## Streaming

```python
from texthumanize import humanize_stream

for chunk in humanize_stream("Long text...", lang="en"):
    print(chunk, end="", flush=True)
```

## Pipeline & Plugins

```python
from texthumanize import Pipeline

def my_hook(text: str, lang: str) -> str:
    return text + "\n\n---\nProcessed"

Pipeline.register_hook(my_hook, after="naturalization")
Pipeline.clear_plugins()
```

## Classes

### `AutoTuner`

Feedback-based optimization.

```python
from texthumanize import AutoTuner

tuner = AutoTuner(lang="en", target_score=80)
result = tuner.tune("Text.", max_iterations=5)
```

### `BenchmarkSuite`

6-dimension quality benchmarking.

```python
from texthumanize import BenchmarkSuite

suite = BenchmarkSuite(lang="en")
report = suite.run("Text to benchmark.")
```

For complete reference, see [docs/API_REFERENCE.md](https://github.com/ksanyok/TextHumanize/blob/main/docs/API_REFERENCE.md).
