# TextHumanize API Reference

Complete reference for all public APIs — v0.8.0

## Installation & Updating

```bash
# First install
pip install git+https://github.com/ksanyok/TextHumanize.git@v0.8.0

# Update to latest release
pip install --upgrade git+https://github.com/ksanyok/TextHumanize.git@v0.8.0

# Or pin in requirements.txt
texthumanize @ git+https://github.com/ksanyok/TextHumanize.git@v0.8.0
```

---

## Table of Contents

- [Installation & Updating](#installation--updating)
- [Core Functions](#core-functions)
- [AI Detection](#ai-detection)
- [Paraphrasing](#paraphrasing)
- [Tone Analysis & Adjustment](#tone-analysis--adjustment)
- [Watermark Detection & Cleaning](#watermark-detection--cleaning)
- [Content Spinning](#content-spinning)
- [Coherence & Readability](#coherence--readability)
- [Style Presets](#style-presets)
- [Stylistic Fingerprinting](#stylistic-fingerprinting)
- [Auto-Tuner](#auto-tuner)
- [Pipeline & Plugins](#pipeline--plugins)
- [Profiles](#profiles)
- [Supported Languages](#supported-languages)
- [CLI Reference](#cli-reference)
- [REST API](#rest-api)
- [TypeScript / JavaScript](#typescript--javascript)

---

## Core Functions

### `humanize(text, **options) → HumanizeResult`

Main entry point. Transforms text to appear more natural using an 11-stage pipeline.

```python
from texthumanize import humanize

result = humanize(
    text="Your text here",
    lang="auto",             # auto, en, ru, uk, de, fr, es, it, pl, pt
    profile="web",           # chat, web, seo, docs, formal, academic, marketing, social, email
    intensity=60,            # 0-100
    preserve={"code_blocks": True, "urls": True, "brand_terms": ["MyBrand"]},
    constraints={"max_change_ratio": 0.4, "keep_keywords": ["SEO"]},
    seed=42,                 # For reproducibility
    target_style="student",  # Or StylisticFingerprint or STYLE_PRESETS[name]
)
```

**Parameters:**

| Parameter | Type | Default | Description |
|:----------|:-----|:--------|:------------|
| `text` | `str` | required | Input text to process |
| `lang` | `str` | `"auto"` | Language code or `"auto"` for detection |
| `profile` | `str` | `"web"` | Processing profile (see [Profiles](#profiles)) |
| `intensity` | `int` | `60` | Processing intensity 0–100 |
| `preserve` | `dict` | `{}` | Elements to protect from modification |
| `constraints` | `dict` | `{}` | Output constraints (max change ratio, keywords) |
| `seed` | `int\|None` | `None` | Random seed for reproducibility |
| `target_style` | `str\|StylisticFingerprint\|None` | `None` | Target style preset or fingerprint |

**Returns:** `HumanizeResult`

| Property | Type | Description |
|:---------|:-----|:------------|
| `text` | `str` | Processed text |
| `original` | `str` | Original input text |
| `lang` | `str` | Detected/used language |
| `profile` | `str` | Used profile |
| `intensity` | `int` | Used intensity |
| `changes` | `list[dict]` | List of applied changes `[{type, original, replacement}]` |
| `metrics_before` | `dict` | Artificiality metrics before processing |
| `metrics_after` | `dict` | Artificiality metrics after processing |
| `change_ratio` | `float` | Fraction of text changed (0–1), SequenceMatcher-based |
| `similarity` | `float` | Jaccard similarity original vs processed (0–1) |
| `quality_score` | `float` | Overall quality balancing change and preservation (0–1) |

---

### `humanize_batch(texts, **options) → list[HumanizeResult]`

Process multiple texts. Each text gets a unique seed (`base_seed + index`).

```python
from texthumanize import humanize_batch

results = humanize_batch(
    ["Text one", "Text two", "Text three"],
    lang="en",
    max_workers=4,
    on_progress=lambda i, total, r: print(f"{i+1}/{total}"),  # Optional callback
)
```

---

### `humanize_chunked(text, chunk_size=5000, **options) → HumanizeResult`

Process large text by splitting into chunks at paragraph boundaries.

```python
from texthumanize import humanize_chunked

result = humanize_chunked(long_text, chunk_size=3000, overlap=200, lang="ru")
```

---

### `analyze(text, lang="auto") → AnalysisReport`

Analyze text artificiality metrics without modifying it.

```python
from texthumanize import analyze

report = analyze("Sample text", lang="en")

# Available metrics
report.artificiality_score    # 0-100 overall AI score
report.total_words            # Word count
report.total_sentences        # Sentence count
report.avg_sentence_length    # Average words per sentence
report.sentence_length_variance  # Coefficient of variation
report.bureaucratic_ratio     # Fraction of bureaucratic words
report.connector_ratio        # Fraction of formulaic connectors
report.repetition_score       # Repetition density
report.typography_score       # Typography issues
report.burstiness_score       # Sentence length variation
report.flesch_kincaid_grade   # FK reading grade level
report.coleman_liau_index     # CL readability index
report.avg_word_length        # Average characters per word
report.avg_syllables_per_word # Average syllables per word
```

---

### `explain(result) → str`

Generate a human-readable report of all changes made by `humanize()`.

```python
from texthumanize import humanize, explain

result = humanize("Furthermore, it is important to utilize this approach.", lang="en")
print(explain(result))
```

Output:
```
=== Отчёт TextHumanize ===
Язык: en | Профиль: web | Интенсивность: 60
Доля изменений: 25.3%

--- Метрики ---
  Искусственность: 45.00 → 22.00 ↓
  Канцеляризмы: 0.12 → 0.00 ↓

--- Изменения (3) ---
  [debureaucratization] "utilize" → "use"
  [connector] "Furthermore" → "Also"
  [structure] sentence split applied
```

---

## AI Detection

### `detect_ai(text, lang="auto") → dict`

Detect whether text was AI-generated using 13 statistical metrics + ensemble boosting.

```python
from texthumanize import detect_ai

result = detect_ai("Suspicious text here", lang="auto")

print(result['score'])         # float 0.0–1.0 (AI probability)
print(result['verdict'])       # "human_written", "mixed", or "ai_generated"
print(result['confidence'])    # float 0.0–1.0 (how reliable the verdict is)
print(result['lang'])          # Detected language
print(result['metrics'])       # dict of 13 individual metric scores
print(result['explanations'])  # list of human-readable explanations
```

**Verdicts:** `score < 0.35` → `human_written` | `0.35–0.65` → `mixed` | `≥ 0.65` → `ai_generated`

---

### `detect_ai_batch(texts, lang="auto") → list[dict]`

Batch AI detection for multiple texts.

```python
results = detect_ai_batch(["Text 1", "Text 2", "Text 3"], lang="en")
```

---

### `detect_ai_sentences(text, lang="auto") → list[dict]`

Per-sentence AI detection with sliding window.

```python
from texthumanize import detect_ai_sentences

sentences = detect_ai_sentences(mixed_text, lang="en")
for s in sentences:
    print(f"{s['label']}: {s['text'][:80]}...")  # label: "ai" or "human"
```

---

### `detect_ai_mixed(text, lang="auto") → dict`

Analyze mixed content — finds AI-written and human-written segments.

```python
from texthumanize import detect_ai_mixed

report = detect_ai_mixed(text)
```

---

## Paraphrasing

### `paraphrase(text, lang="auto", intensity=0.5, seed=None) → str`

Syntactic paraphrasing: clause swaps, passive↔active, sentence splitting, adverb fronting, nominalization.

```python
from texthumanize import paraphrase

result = paraphrase("Although the study was comprehensive, the results were inconclusive.",
                    lang="en", intensity=0.8, seed=42)
```

---

## Tone Analysis & Adjustment

### `analyze_tone(text, lang="auto") → dict`

Analyze text formality level (7 levels).

```python
from texthumanize import analyze_tone

tone = analyze_tone("Shall we proceed with the implementation?", lang="en")

tone['primary_tone']   # "formal", "casual", "neutral", etc.
tone['formality']      # float 0.0 (casual) – 1.0 (formal)
tone['subjectivity']   # float 0.0 (objective) – 1.0 (subjective)
tone['confidence']     # float 0.0–1.0
tone['scores']         # dict of all tone scores
tone['markers']        # list of detected tone markers
```

Levels: `ultra_formal`, `formal`, `semi_formal`, `neutral`, `semi_casual`, `casual`, `ultra_casual`

---

### `adjust_tone(text, target, lang="auto", intensity=0.5) → str`

Shift text formality toward target level.

```python
from texthumanize import adjust_tone

casual = adjust_tone("It is imperative to proceed.", target="casual", lang="en")
formal = adjust_tone("Hey, gotta fix this ASAP!", target="formal", lang="en")
```

Targets: `very_formal`, `formal`, `neutral`, `casual`, `very_casual`, `friendly`, `academic`, `professional`, `marketing`

---

## Watermark Detection & Cleaning

### `detect_watermarks(text, lang="auto") → dict`

Detect invisible watermarks: zero-width characters, homoglyphs, invisible formatting, spacing steganography, statistical watermarks, C2PA/IPTC markers.

```python
from texthumanize import detect_watermarks

report = detect_watermarks(suspicious_text)

report['has_watermarks']      # bool
report['watermark_types']     # list of detected types
report['confidence']          # float 0.0–1.0
report['characters_removed']  # int
report['cleaned_text']        # str
report['details']             # dict with per-type info
```

---

### `clean_watermarks(text, lang="auto") → str`

Remove all detected watermarks and return clean text.

```python
from texthumanize import clean_watermarks

clean = clean_watermarks("Contaminated\u200b text\u200b here")
# → "Contaminated text here"
```

---

## Content Spinning

### `spin(text, lang="auto", intensity=0.5, seed=None) → str`

Generate a unique version using synonym substitution.

```python
from texthumanize import spin

result = spin("The system provides important data.", lang="en", seed=42)
```

### `spin_variants(text, count=5, lang="auto", intensity=0.5) → list[str]`

Generate multiple unique versions.

```python
from texthumanize import spin_variants

variants = spin_variants("Original text.", count=5, lang="en")
```

### Spintax (Low-Level)

```python
from texthumanize.spinner import ContentSpinner

spinner = ContentSpinner(lang="en", seed=42)
spintax = spinner.generate_spintax("The system provides important data.")
# → "The {system|platform} {provides|offers} {important|crucial} {data|information}."
resolved = spinner.resolve_spintax(spintax)
```

---

## Coherence & Readability

### `analyze_coherence(text, lang="auto") → dict`

Paragraph-level coherence analysis.

```python
from texthumanize import analyze_coherence

report = analyze_coherence(text, lang="en")

report['overall']                     # float 0–1 — weighted average
report['lexical_cohesion']            # float 0–1 — word overlap
report['transition_score']            # float 0–1 — logical transitions
report['topic_consistency']           # float 0–1 — topic drift
report['sentence_opening_diversity']  # float 0–1 — varied beginnings
report['paragraph_count']             # int
report['issues']                      # list of detected problems
```

---

### `full_readability(text, lang="auto") → dict`

Compute 6 readability indices.

```python
from texthumanize import full_readability

r = full_readability("Your text here.", lang="en")

r['flesch_kincaid_grade']   # US grade level
r['coleman_liau_index']     # Character-based grade level
r['ari']                    # Automated Readability Index
r['smog_index']             # SMOG complexity
r['gunning_fog']            # Gunning Fog estimate
r['dale_chall']             # Dale-Chall difficulty
```

---

## Style Presets

*New in v0.8.0*

```python
from texthumanize import humanize, STYLE_PRESETS

# Pass string name
result = humanize(text, target_style="student")

# Pass fingerprint object
result = humanize(text, target_style=STYLE_PRESETS["scientist"])

# Available presets
print(list(STYLE_PRESETS.keys()))
# → ['student', 'copywriter', 'scientist', 'journalist', 'blogger']
```

| Preset | Sentence Mean | Std Dev | Vocabulary | Complex Ratio | Use Case |
|:-------|:------------:|:-------:|:----------:|:-------------:|:---------|
| `student` | 14 | 6 | 0.65 | 25% | Essays, coursework |
| `copywriter` | 12 | 8.5 | 0.72 | 20% | Marketing, ads |
| `scientist` | 22 | 7 | 0.70 | 55% | Research papers |
| `journalist` | 16 | 7.5 | 0.72 | 35% | Articles, reports |
| `blogger` | 11 | 7 | 0.60 | 12% | Blog posts, social |

---

## Stylistic Fingerprinting

```python
from texthumanize import StylisticAnalyzer, StylisticFingerprint

# Extract fingerprint from your writing
analyzer = StylisticAnalyzer(lang="en")
my_style = analyzer.extract(my_writing_sample)

# Properties
my_style.sent_len_mean        # Average sentence length
my_style.sent_len_std         # Sentence length std deviation
my_style.complex_ratio        # Complex word ratio
my_style.vocabulary_richness  # Type-to-token ratio

# Compare styles (cosine similarity)
similarity = my_style.similarity(other_style)

# Use your style as target
result = humanize(ai_text, target_style=my_style)
```

---

## Auto-Tuner

*New in v0.8.0*

Feedback-driven parameter optimization.

```python
from texthumanize import AutoTuner

tuner = AutoTuner(history_path="history.json", max_records=500)

# Record results
tuner.record(humanize_result)

# Get smart intensity suggestion
intensity = tuner.suggest_intensity(text, lang="en")  # int 10-100

# Get full parameter suggestion
params = tuner.suggest_params(lang="en")
params.intensity          # int
params.max_change_ratio   # float
params.confidence         # float 0-1

# Review statistics
stats = tuner.summary()
# → {"total_records": 47, "avg_quality": 0.78, ...}

# Reset history
tuner.reset()
```

### How It Works

1. Groups historical results by intensity bucket (10, 20, ..., 100)
2. Computes average quality score per bucket
3. Returns the intensity that produced best average quality
4. Confidence grows from 0 → 1 as records accumulate (10+ per bucket = full confidence)
5. Optional JSON persistence — survives between sessions

---

## Pipeline & Plugins

### Direct Pipeline Usage

```python
from texthumanize import Pipeline, HumanizeOptions

pipeline = Pipeline(HumanizeOptions(lang="en", profile="web", intensity=60))
result = pipeline.run("Your text here", lang="en")
```

### Plugin System

Register custom processing stages before/after any pipeline step:

```python
# Simple function plugin
def my_plugin(text: str, lang: str) -> str:
    return text.replace("foo", "bar")

Pipeline.register_hook(my_plugin, after="typography")

# Class-based plugin
class BrandEnforcer:
    def __init__(self, brand, canonical):
        self.brand = brand
        self.canonical = canonical

    def process(self, text, lang, profile, intensity):
        import re
        return re.sub(re.escape(self.brand), self.canonical, text, flags=re.IGNORECASE)

Pipeline.register_plugin(BrandEnforcer("texthumanize", "TextHumanize"), after="typography")

# Clean up
Pipeline.clear_plugins()
```

### Pipeline Stages

```
segmentation → typography → debureaucratization → structure → repetitions →
liveliness → universal → naturalization → stylistic_alignment → validation → restore
```

---

## Profiles

| Profile | Intensity | Sentence Range | Colloquialisms | Use Case |
|:--------|:---------:|:--------------:|:--------------:|:---------|
| `chat` | High (80) | 8–18 words | High | Messaging, social media |
| `web` | Medium (60) | 10–22 words | Medium | Blog posts, articles |
| `seo` | Careful (40) | 12–25 words | None | SEO content |
| `docs` | Low (50) | 12–28 words | None | Technical documentation |
| `formal` | Minimal (30) | 15–30 words | None | Academic, legal |
| `academic` | Minimal (25) | 15–30 words | None | Research papers |
| `marketing` | Med-High (70) | 8–20 words | Medium | Sales, promo copy |
| `social` | High (85) | 6–15 words | High | Social media posts |
| `email` | Medium (50) | 10–22 words | Medium | Business emails |

---

## Supported Languages

| Code | Language | Dictionary | Morphology | Tone | AI Words |
|:----:|:---------|:----------:|:----------:|:----:|:--------:|
| `en` | English | ✅ 40+ | ✅ | ✅ | 24+ |
| `ru` | Russian | ✅ 70+ | ✅ | ✅ | 30+ |
| `uk` | Ukrainian | ✅ 50+ | ✅ | ✅ | 25+ |
| `de` | German | ✅ 64 | ✅ | ✅ | 38 |
| `fr` | French | ✅ 20 | — | ✅ | 15+ |
| `es` | Spanish | ✅ 18 | — | ✅ | 15+ |
| `pl` | Polish | ✅ 18 | — | — | 15+ |
| `pt` | Portuguese | ✅ 16 | — | — | 12+ |
| `it` | Italian | ✅ 16 | — | — | 12+ |
| `*` | Any other | Universal | — | — | — |

---

## CLI Reference

```bash
# Process text
texthumanize input.txt -l en -p web -i 70 -o output.txt

# From stdin
echo "Text" | texthumanize - -l en

# AI detection
texthumanize essay.txt --detect-ai --verbose --json

# Tone adjustment
texthumanize formal.txt --tone casual -o casual.txt

# Paraphrase
texthumanize input.txt --paraphrase -o paraphrased.txt

# Spin variants
texthumanize template.txt --variants 5

# Analyze
texthumanize article.txt --analyze
texthumanize article.txt --readability
texthumanize article.txt --coherence

# Clean watermarks
texthumanize suspect.txt --watermarks -o clean.txt

# REST API server
texthumanize dummy --api --port 8080

# Version
texthumanize --version
```

---

## REST API

Zero-dependency HTTP server with CORS support.

```bash
python -m texthumanize.api --port 8080
```

| Method | Endpoint | Description |
|:-------|:---------|:------------|
| `POST` | `/humanize` | Humanize text |
| `POST` | `/analyze` | Analyze metrics |
| `POST` | `/detect-ai` | AI detection (single or batch) |
| `POST` | `/paraphrase` | Paraphrase text |
| `POST` | `/tone/analyze` | Tone analysis |
| `POST` | `/tone/adjust` | Tone adjustment |
| `POST` | `/watermarks/detect` | Detect watermarks |
| `POST` | `/watermarks/clean` | Clean watermarks |
| `POST` | `/spin` | Spin text |
| `POST` | `/coherence` | Coherence analysis |
| `POST` | `/readability` | Readability metrics |
| `GET` | `/health` | Health check |
| `GET` | `/` | API info |

All responses include `_elapsed_ms`.

---

## TypeScript / JavaScript

```typescript
import { humanize, analyze, detectAi } from 'texthumanize';

const result = humanize('Text to process', { lang: 'en', intensity: 60 });
console.log(result.text);
console.log(result.changeRatio);

const report = analyze('Check this text');
console.log(report.artificialityScore);
```

### Available TS Modules

| Module | Class/Function | Description |
|:-------|:---------------|:------------|
| `pipeline.ts` | `Pipeline` | Full 11-stage pipeline with adaptive intensity |
| `normalizer.ts` | `TypographyNormalizer` | Dashes, quotes, spacing normalization |
| `debureaucratizer.ts` | `Debureaucratizer` | Bureaucratic replacement with seeded PRNG |
| `naturalizer.ts` | `TextNaturalizer` | AI words, burstiness, connectors |
| `analyzer.ts` | `TextAnalyzer` | Artificiality scoring |
| `detector.ts` | `detectAi()` | AI detection |
| `segmenter.ts` | `Segmenter` | Code/URL protection |

Features: seeded PRNG (xoshiro128**), adaptive intensity, graduated retry, Cyrillic-safe regex.
