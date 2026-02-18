# TextHumanize

**Algorithmic text naturalization library — transforms machine-generated text into natural, human-like prose**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![PHP 8.1+](https://img.shields.io/badge/php-8.1+-purple.svg)](https://www.php.net/)
[![Tests](https://img.shields.io/badge/tests-500%20passed-green.svg)]()
[![Coverage](https://img.shields.io/badge/coverage-85%25-brightgreen.svg)]()
[![Ruff](https://img.shields.io/badge/linting-ruff-261230.svg)](https://github.com/astral-sh/ruff)
[![mypy](https://img.shields.io/badge/types-mypy-blue.svg)](https://mypy-lang.org/)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen.svg)](https://pre-commit.com/)
[![Zero Dependencies](https://img.shields.io/badge/dependencies-0-brightgreen.svg)]()
[![License](https://img.shields.io/badge/license-Personal%20Use-orange.svg)](LICENSE)

---

TextHumanize is a pure-Python text processing library that normalizes typography, simplifies bureaucratic language, diversifies sentence structure, increases burstiness and perplexity, and replaces formulaic phrases with natural alternatives. Includes **AI text detection**, **paraphrasing**, **tone analysis**, **watermark cleaning**, **text spinning**, and **coherence analysis**. Available for **Python** and **PHP**.

**Full language support:** Russian · Ukrainian · English · German · French · Spanish · Polish · Portuguese · Italian

**Universal processor:** works with any language using statistical methods (no dictionaries required).

---

## Table of Contents

- [Features](#features)
- [Why TextHumanize?](#why-texthumanize)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Before & After Examples](#before--after-examples)
- [API Reference](#api-reference)
  - [humanize()](#humanizetext-options)
  - [humanize_chunked()](#humanize_chunkedtext-chunk_size5000-options)
  - [analyze()](#analyzetext-lang)
  - [explain()](#explainresult)
  - [detect_ai()](#detect_aitext-lang)
  - [detect_ai_batch()](#detect_ai_batchtexts-lang)
  - [paraphrase()](#paraphrasetext-lang-intensity-seed)
  - [analyze_tone()](#analyze_tonetext-lang)
  - [adjust_tone()](#adjust_tonetext-target-lang-intensity)
  - [detect_watermarks()](#detect_watermarkstext-lang)
  - [clean_watermarks()](#clean_watermarkstext-lang)
  - [spin()](#spintext-lang-intensity-seed)
  - [spin_variants()](#spin_variantstext-count-lang-intensity)
  - [analyze_coherence()](#analyze_coherencetext-lang)
  - [full_readability()](#full_readabilitytext-lang)
- [Profiles](#profiles)
- [Parameters](#parameters)
- [Plugin System](#plugin-system)
- [Chunk Processing](#chunk-processing)
- [CLI Reference](#cli-reference)
- [REST API Server](#rest-api-server)
- [Processing Pipeline](#processing-pipeline)
- [AI Detection — How It Works](#ai-detection--how-it-works)
- [Language Support](#language-support)
- [SEO Mode](#seo-mode)
- [Readability Metrics](#readability-metrics)
- [Paraphrasing Engine](#paraphrasing-engine)
- [Tone Analysis & Adjustment](#tone-analysis--adjustment)
- [Watermark Detection & Cleaning](#watermark-detection--cleaning)
- [Text Spinning](#text-spinning)
- [Coherence Analysis](#coherence-analysis)
- [Morphological Engine](#morphological-engine)
- [Smart Sentence Splitter](#smart-sentence-splitter)
- [Context-Aware Synonyms](#context-aware-synonyms)
- [Using Individual Modules](#using-individual-modules)
- [Performance & Benchmarks](#performance--benchmarks)
- [Testing](#testing)
- [Architecture](#architecture)
- [PHP Library](#php-library)
- [Code Quality & Tooling](#code-quality--tooling)
- [Migration Guide (v0.4 → v0.5)](#migration-guide-v04--v05)
- [FAQ & Troubleshooting](#faq--troubleshooting)
- [Contributing](#contributing)
- [Support the Project](#support-the-project)
- [License](#license)

---

## Features

TextHumanize addresses common patterns found in machine-generated text:

| Pattern | Before | After |
|---------|--------|-------|
| **Em dashes** | `text — example` | `text - example` |
| **Typographic quotes** | `«text»` | `"text"` |
| **Bureaucratic words** | `utilize`, `implement` | `use`, `do` |
| **Formulaic connectors** | `However`, `Furthermore` | `But`, `Also` |
| **Uniform sentences** | All 15-20 words | Varied 5-25 words |
| **Word repetition** | `important... important...` | Synonym substitution |
| **Overly perfect punctuation** | Frequent `;` and `:` | Simplified punctuation |
| **Low perplexity** | Predictable word choice | Natural variation |
| **Boilerplate phrases** | `it is important to note` | `notably`, `by the way` |
| **AI watermarks** | Hidden zero-width chars | Cleaned text |

### Key Advantages

- **Fast** — pure algorithmic processing, zero network requests
- **Private** — all processing happens locally, data never leaves your system
- **Controllable** — fine-tuned via intensity, profiles, and keyword preservation
- **9 languages + universal** — RU, UK, EN, DE, FR, ES, PL, PT, IT + any other
- **Zero dependencies** — Python standard library only
- **Extensible** — plugin system for custom pipeline stages
- **Large text support** — chunk processing for texts of any size
- **AI detection** — 12-metric statistical AI text detector, no ML required
- **Paraphrasing** — algorithmic sentence-level paraphrasing
- **Tone control** — analyze and adjust text formality (7 levels)
- **Watermark cleaning** — detect and remove invisible text watermarks
- **Text spinning** — generate unique content variants with spintax
- **Coherence analysis** — assess text structure and paragraph flow
- **Readability metrics** — Flesch-Kincaid, Coleman-Liau, ARI, SMOG, Gunning Fog, Dale-Chall
- **Morphological engine** — rule-based lemmatization for RU, UK, EN, DE
- **Smart sentence splitting** — handles abbreviations, decimals, initials correctly
- **Context-aware synonyms** — word-sense disambiguation without ML
- **REST API** — built-in HTTP server with 12 JSON endpoints

---

## Why TextHumanize?

| Feature | TextHumanize | Online Tools | GPT Rewrite |
|---------|:------------:|:------------:|:-----------:|
| Works offline | ✅ | ❌ | ❌ |
| Zero dependencies | ✅ | ❌ | ❌ |
| Data never leaves device | ✅ | ❌ | ❌ |
| Reproducible (seed) | ✅ | ❌ | ❌ |
| 9 languages | ✅ | ≈ 1-3 | ✅ |
| Fast (ms, not seconds) | ✅ | ❌ | ❌ |
| Fine control (intensity/profile) | ✅ | ❌ | ~ |
| Built-in AI detector | ✅ | ❌ | ❌ |
| Plugin system | ✅ | ❌ | ❌ |
| Free & open source | ✅ | ❌ | ❌ |
| No API key required | ✅ | ❌ | ❌ |
| PHP port included | ✅ | ❌ | ❌ |

---

## Installation

### pip (recommended)

```bash
pip install texthumanize
```

### From source

```bash
git clone https://github.com/ksanyok/TextHumanize.git
cd TextHumanize
pip install -e .
```

### PHP

```bash
cd php/
composer install
```

### Verify installation

```python
import texthumanize
print(texthumanize.__version__)  # 0.4.0
```

---

## Quick Start

```python
from texthumanize import humanize, analyze, explain

# Basic usage — one line
result = humanize("This text utilizes a comprehensive methodology for implementation.")
print(result.text)
# → "This text uses a complete method for setup."

# With options
result = humanize(
    "Furthermore, it is important to note that the implementation facilitates optimization.",
    lang="en",           # auto-detect or specify
    profile="web",       # chat, web, seo, docs, formal
    intensity=70,        # 0 (mild) to 100 (maximum)
)
print(result.text)
print(f"Changed: {result.change_ratio:.0%}")

# Analyze text metrics
report = analyze("Text to analyze for naturalness.", lang="en")
print(f"Artificiality score: {report.artificiality_score:.1f}/100")
print(f"Flesch-Kincaid grade: {report.flesch_kincaid_grade:.1f}")

# Get detailed explanation of changes
result = humanize("Furthermore, it is important to utilize this approach.")
print(explain(result))
```

### Quick Examples for Each Feature

```python
from texthumanize import (
    detect_ai, paraphrase, analyze_tone, adjust_tone,
    detect_watermarks, clean_watermarks, spin, spin_variants,
    analyze_coherence, full_readability,
)

# AI Detection
ai = detect_ai("Text to check for AI generation.", lang="en")
print(f"AI probability: {ai['score']:.0%} → {ai['verdict']}")

# Paraphrasing
print(paraphrase("The system works efficiently.", lang="en"))

# Tone Analysis
tone = analyze_tone("Please submit the documentation.", lang="en")
print(f"Tone: {tone['primary_tone']}, formality: {tone['formality']:.2f}")

# Tone Adjustment
casual = adjust_tone("It is imperative to proceed.", target="casual", lang="en")
print(casual)

# Watermark Cleaning
clean = clean_watermarks("Te\u200bxt wi\u200bth hid\u200bden chars")
print(clean)

# Text Spinning
unique = spin("The system provides important data.", lang="en")
print(unique)

# Coherence Analysis
coh = analyze_coherence("First part.\n\nSecond part.\n\nConclusion.", lang="en")
print(f"Coherence: {coh['overall']:.2f}")

# Full Readability
read = full_readability("Your text here.", lang="en")
print(read)
```

---

## Before & After Examples

### English — Blog Post

**Before (AI-generated):**
> Furthermore, it is important to note that the implementation of cloud computing facilitates the optimization of business processes. Additionally, the utilization of microservices constitutes a significant advancement. Nevertheless, considerable challenges remain in the area of security. It is worth mentioning that these challenges necessitate comprehensive solutions.

**After (TextHumanize, profile="web", intensity=70):**
> But cloud computing helps optimize how businesses work. Also, microservices are a big step forward. Still, security is tough. These challenges need thorough solutions.

**Changes:** 4 bureaucratic replacements, 2 connector swaps, sentence structure diversified.

### Russian — Documentation

**Before:**
> Данный документ является руководством по осуществлению настройки программного обеспечения. Необходимо осуществить установку всех компонентов. Кроме того, следует обратить внимание на конфигурационные параметры.

**After (profile="docs", intensity=60):**
> Этот документ - руководство по настройке ПО. Нужно установить все компоненты. Также стоит обратить внимание на параметры конфигурации.

### Ukrainian — Web Content

**Before:**
> Даний матеріал є яскравим прикладом здійснення сучасних підходів. Крім того, необхідно зазначити важливість впровадження інноваційних рішень.

**After (profile="web", intensity=65):**
> Цей матеріал - яскравий приклад сучасних підходів. Також важливо впроваджувати інноваційні рішення.

---

## API Reference

### `humanize(text, **options)`

Main function — transforms text to sound more natural.

```python
from texthumanize import humanize

result = humanize(
    text="Your text here",
    lang="auto",        # auto-detect or specify: en, ru, de, fr, es, etc.
    profile="web",      # chat, web, seo, docs, formal, academic, marketing, social, email
    intensity=60,       # 0 (no changes) to 100 (maximum)
    preserve={          # protect specific elements
        "code_blocks": True,
        "urls": True,
        "emails": True,
        "brand_terms": ["MyBrand"],
    },
    constraints={       # output constraints
        "max_change_ratio": 0.4,
        "keep_keywords": ["SEO", "API"],
    },
    seed=42,            # reproducible results
)

# Result object
print(result.text)           # processed text
print(result.original)       # original text (unchanged)
print(result.lang)           # detected/specified language
print(result.profile)        # profile used
print(result.intensity)      # intensity used
print(result.change_ratio)   # fraction of text changed (0.0-1.0)
print(result.changes)        # list of individual changes [{type, original, replacement}]
print(result.metrics_before) # metrics before processing
print(result.metrics_after)  # metrics after processing
```

**Returns:** `HumanizeResult` dataclass.

### `humanize_chunked(text, chunk_size=5000, **options)`

Process large texts by splitting into chunks at paragraph boundaries. Each chunk is processed independently with its own seed variation, then reassembled.

```python
from texthumanize import humanize_chunked

# Process a 50,000-character document
with open("large_document.txt") as f:
    text = f.read()

result = humanize_chunked(
    text,
    chunk_size=5000,     # characters per chunk (default)
    overlap=200,         # character overlap for context
    lang="en",
    profile="docs",
    intensity=50,
)
print(result.text)
print(f"Total changes: {len(result.changes)}")
```

**Returns:** `HumanizeResult` dataclass.

### `analyze(text, lang)`

Analyze text and return naturalness metrics.

```python
from texthumanize import analyze

report = analyze("Text to analyze.", lang="en")

# All available metrics
print(f"Artificiality:         {report.artificiality_score:.1f}/100")
print(f"Total words:           {report.total_words}")
print(f"Total sentences:       {report.total_sentences}")
print(f"Avg sentence length:   {report.avg_sentence_length:.1f} words")
print(f"Sentence length var:   {report.sentence_length_variance:.2f}")
print(f"Bureaucratic ratio:    {report.bureaucratic_ratio:.3f}")
print(f"Connector ratio:       {report.connector_ratio:.3f}")
print(f"Repetition score:      {report.repetition_score:.3f}")
print(f"Typography score:      {report.typography_score:.3f}")
print(f"Burstiness:            {report.burstiness_score:.3f}")
print(f"Flesch-Kincaid grade:  {report.flesch_kincaid_grade:.1f}")
print(f"Coleman-Liau index:    {report.coleman_liau_index:.1f}")
print(f"Avg word length:       {report.avg_word_length:.1f}")
print(f"Avg syllables/word:    {report.avg_syllables_per_word:.1f}")
```

**Returns:** `AnalysisReport` dataclass.

### `explain(result)`

Generate a human-readable report of all changes made by `humanize()`.

```python
from texthumanize import humanize, explain

result = humanize("Furthermore, it is important to utilize this approach.", lang="en")
report = explain(result)
print(report)
```

**Output:**
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

**Returns:** `str`

### `detect_ai(text, lang)`

Detect AI-generated text using 12 independent statistical metrics without any ML dependencies.

```python
from texthumanize import detect_ai

result = detect_ai("Your text to analyze.", lang="auto")

print(f"AI probability:  {result['score']:.1%}")
print(f"Verdict:         {result['verdict']}")    # "human", "mixed", "ai", or "unknown"
print(f"Confidence:      {result['confidence']:.1%}")
print(f"Language:        {result['lang']}")

# Detailed per-metric scores (0.0 = human-like, 1.0 = AI-like)
metrics = result['metrics']
for name, score in metrics.items():
    print(f"  {name:30s} {score:.3f}")

# Human-readable explanations
for exp in result['explanations']:
    print(f"  → {exp}")
```

**Returns:** `dict` with keys: `score`, `verdict`, `confidence`, `metrics`, `explanations`, `lang`.

### `detect_ai_batch(texts, lang)`

Batch AI detection for multiple texts.

```python
from texthumanize import detect_ai_batch

texts = [
    "First text to check.",
    "Second text to check.",
    "Third text to check.",
]
results = detect_ai_batch(texts, lang="en")
for i, r in enumerate(results):
    print(f"Text {i+1}: {r['verdict']} ({r['score']:.0%})")
```

**Returns:** `list[dict]`

### `paraphrase(text, lang, intensity, seed)`

Paraphrase text while preserving meaning. Uses syntactic transformations: clause swaps, passive↔active, sentence splitting, adverb fronting, nominalization.

```python
from texthumanize import paraphrase

result = paraphrase(
    "Furthermore, it is important to note this fact.",
    lang="en",
    intensity=0.5,   # 0.0-1.0: fraction of sentences to transform
    seed=42,         # optional: reproducible results
)
print(result)
```

**Returns:** `str`

### `analyze_tone(text, lang)`

Analyze text tone, formality level, and subjectivity.

```python
from texthumanize import analyze_tone

tone = analyze_tone("Shall we proceed with the implementation?", lang="en")

print(f"Primary tone:   {tone['primary_tone']}")     # formal, casual, academic, etc.
print(f"Formality:      {tone['formality']:.2f}")     # 0=casual, 1=formal
print(f"Subjectivity:   {tone['subjectivity']:.2f}")  # 0=objective, 1=subjective
print(f"Confidence:     {tone['confidence']:.2f}")
print(f"Scores:         {tone['scores']}")            # dict of all tone scores
print(f"Markers found:  {tone['markers']}")           # detected tone markers
```

**Returns:** `dict`

### `adjust_tone(text, target, lang, intensity)`

Adjust text to a target tone level.

```python
from texthumanize import adjust_tone

# Make formal text casual
casual = adjust_tone(
    "It is imperative to implement this solution immediately.",
    target="casual",     # very_formal, formal, neutral, casual, very_casual
    lang="en",
    intensity=0.5,       # 0.0-1.0: strength of adjustment
)
print(casual)

# Make casual text formal
formal = adjust_tone(
    "Hey, we gotta fix this ASAP!",
    target="formal",
    lang="en",
)
print(formal)
```

Available targets: `very_formal`, `formal`, `neutral`, `casual`, `very_casual`, `friendly`, `academic`, `professional`, `marketing`.

**Returns:** `str`

### `detect_watermarks(text, lang)`

Detect invisible watermarks: zero-width characters, homoglyphs, invisible formatting, statistical AI watermarks.

```python
from texthumanize import detect_watermarks

report = detect_watermarks("Text with\u200bhidden\u200bcharacters")

print(f"Has watermarks:     {report['has_watermarks']}")
print(f"Types found:        {report['watermark_types']}")
print(f"Confidence:         {report['confidence']:.2f}")
print(f"Characters removed: {report['characters_removed']}")
print(f"Cleaned text:       {report['cleaned_text']}")
print(f"Details:            {report['details']}")
```

**Returns:** `dict`

### `clean_watermarks(text, lang)`

Remove all detected watermarks and return clean text.

```python
from texthumanize import clean_watermarks

clean = clean_watermarks("Contaminated\u200b text\u200b here")
print(clean)  # "Contaminated text here"
```

**Returns:** `str`

### `spin(text, lang, intensity, seed)`

Generate a unique version of text using synonym substitution.

```python
from texthumanize import spin

result = spin("The system provides important data for analysis.", lang="en")
print(result)
# → e.g. "The platform offers crucial information for examination."
```

**Returns:** `str`

### `spin_variants(text, count, lang, intensity)`

Generate multiple unique versions of the same text.

```python
from texthumanize import spin_variants

variants = spin_variants(
    "The system provides important data.",
    count=5,
    lang="en",
    intensity=0.5,
)
for i, v in enumerate(variants, 1):
    print(f"  #{i}: {v}")
```

**Returns:** `list[str]`

### `analyze_coherence(text, lang)`

Analyze text coherence — how well sentences and paragraphs flow together.

```python
from texthumanize import analyze_coherence

text = """
Introduction paragraph here.

Main content paragraph with details.

Conclusion summarizing the points.
"""

report = analyze_coherence(text, lang="en")

print(f"Overall coherence:        {report['overall']:.2f}")
print(f"Lexical cohesion:         {report['lexical_cohesion']:.2f}")
print(f"Transition score:         {report['transition_score']:.2f}")
print(f"Topic consistency:        {report['topic_consistency']:.2f}")
print(f"Opening diversity:        {report['sentence_opening_diversity']:.2f}")
print(f"Paragraphs:               {report['paragraph_count']}")
print(f"Avg paragraph length:     {report['avg_paragraph_length']:.1f}")

if report['issues']:
    print("Issues:")
    for issue in report['issues']:
        print(f"  - {issue}")
```

**Returns:** `dict`

### `full_readability(text, lang)`

Compute all readability indices at once.

```python
from texthumanize import full_readability

r = full_readability("Your text here with multiple sentences. Each one helps.", lang="en")

# Available indices
print(f"Flesch-Kincaid Grade: {r.get('flesch_kincaid_grade', 0):.1f}")
print(f"Coleman-Liau:         {r.get('coleman_liau_index', 0):.1f}")
print(f"ARI:                  {r.get('ari', 0):.1f}")
print(f"SMOG:                 {r.get('smog_index', 0):.1f}")
print(f"Gunning Fog:          {r.get('gunning_fog', 0):.1f}")
print(f"Dale-Chall:           {r.get('dale_chall', 0):.1f}")
```

**Returns:** `dict`

---

## Profiles

Nine built-in profiles control the processing style:

| Profile | Use Case | Sentence Length | Colloquialisms | Intensity Default |
|---------|----------|:---------:|:---------:|:---------:|
| `chat` | Messaging, social media | 8-18 words | High | 80 |
| `web` | Blog posts, articles | 10-22 words | Medium | 60 |
| `seo` | SEO content | 12-25 words | None | 40 |
| `docs` | Technical documentation | 12-28 words | None | 50 |
| `formal` | Academic, legal | 15-30 words | None | 30 |
| `academic` | Research papers | 15-30 words | None | 25 |
| `marketing` | Sales, promo copy | 8-20 words | Medium | 70 |
| `social` | Social media posts | 6-15 words | High | 85 |
| `email` | Business emails | 10-22 words | Medium | 50 |

```python
# Conversational style for social media
result = humanize(text, profile="chat", intensity=80)

# SEO-safe mode (preserves keywords, minimal changes)
result = humanize(text, profile="seo", intensity=40,
                  constraints={"keep_keywords": ["API", "cloud"]})

# Academic writing
result = humanize(text, profile="academic", intensity=25)

# Marketing copy — energetic and engaging
result = humanize(text, profile="marketing", intensity=70)
```

### Profile Comparison

Given the input: *"Furthermore, it is important to note that the implementation of this approach facilitates comprehensive optimization."*

| Profile | Output |
|---------|--------|
| `chat` | *"This approach helps optimize things a lot."* |
| `web` | *"Also, this approach helps with thorough optimization."* |
| `seo` | *"This approach facilitates comprehensive optimization."* |
| `formal` | *"Notably, implementing this approach facilitates optimization."* |

---

## Parameters

### Intensity (0-100)

Controls how aggressively text is modified:

| Range | Effect | Best For |
|-------|--------|----------|
| 0-20 | Typography normalization only | Legal, contracts |
| 20-40 | + light debureaucratization | Documentation |
| 40-60 | + structure diversification & connector swaps | Blog posts |
| 60-80 | + synonym replacement, natural phrasing | Web content |
| 80-100 | + maximum variation, colloquial insertions | Chat, social |

```python
# Minimal — only fix typography
result = humanize(text, intensity=10)

# Moderate — safe for most content
result = humanize(text, intensity=50)

# Maximum — full rewrite
result = humanize(text, intensity=95)
```

### Preserve Options

Protect specific elements from modification:

```python
preserve = {
    "code_blocks": True,    # protect ```code``` blocks
    "urls": True,           # protect URLs
    "emails": True,         # protect email addresses
    "hashtags": True,       # protect #hashtags
    "mentions": True,       # protect @mentions
    "markdown": True,       # protect markdown formatting
    "html": True,           # protect HTML tags
    "numbers": False,       # protect numbers (default: False)
    "brand_terms": [        # exact terms to protect (case-sensitive)
        "TextHumanize",
        "MyBrand",
        "ProductName™",
    ],
}
```

### Constraints

Set limits on processing:

```python
constraints = {
    "max_change_ratio": 0.4,            # max 40% of text changed
    "min_sentence_length": 3,           # minimum words per sentence
    "keep_keywords": ["SEO", "API"],    # keywords preserved exactly
}
```

### Seed (Reproducibility)

```python
# Same seed = same result every time
r1 = humanize("Text here.", seed=42)
r2 = humanize("Text here.", seed=42)
assert r1.text == r2.text  # guaranteed
```

---

## Plugin System

Register custom processing stages that run before or after any built-in stage:

```python
from texthumanize import Pipeline, humanize

# Simple hook function
def add_disclaimer(text: str, lang: str) -> str:
    return text + "\n\n---\nProcessed by TextHumanize."

Pipeline.register_hook(add_disclaimer, after="naturalization")

# Plugin class with full context
class BrandEnforcer:
    def __init__(self, brand: str, canonical: str):
        self.brand = brand
        self.canonical = canonical

    def process(self, text: str, lang: str, profile: str, intensity: int) -> str:
        import re
        return re.sub(re.escape(self.brand), self.canonical, text, flags=re.IGNORECASE)

Pipeline.register_plugin(
    BrandEnforcer("texthumanize", "TextHumanize"),
    after="typography",
)

# Process text — plugins run automatically
result = humanize("texthumanize is great.")
print(result.text)  # "TextHumanize is great. ..."

# Clean up when done
Pipeline.clear_plugins()
```

### Available Stage Names

```
segmentation → typography → debureaucratization → structure → repetitions →
liveliness → universal → naturalization → validation → restore
```

You can attach plugins `before` or `after` any of these stages.

---

## Chunk Processing

For large documents (articles, books, reports), use `humanize_chunked` to process text in manageable pieces:

```python
from texthumanize import humanize_chunked

# Automatically splits at paragraph boundaries
result = humanize_chunked(
    very_long_text,
    chunk_size=5000,    # characters per chunk
    overlap=200,        # context overlap
    lang="en",
    profile="docs",
    intensity=50,
    seed=42,            # base seed, each chunk gets seed+i
)
print(f"Processed {len(result.text)} characters")
```

Each chunk is processed independently with its own seed for variation, then reassembled into the final text. The chunk boundary detection preserves paragraph integrity.

---

## CLI Reference

### Basic Usage

```bash
# Process a file (output to stdout)
texthumanize input.txt

# Process with options
texthumanize input.txt -l en -p web -i 70

# Save to file
texthumanize input.txt -o output.txt

# Process from stdin
echo "Text to process" | texthumanize - -l en
cat article.txt | texthumanize -
```

### All CLI Options

```bash
texthumanize [input] [options]

Positional:
  input                     Input file path (or '-' for stdin)

Options:
  -o, --output FILE         Output file (default: stdout)
  -l, --lang LANG           Language: auto, en, ru, uk, de, fr, es, pl, pt, it
  -p, --profile PROFILE     Profile: chat, web, seo, docs, formal, academic,
                            marketing, social, email
  -i, --intensity N         Processing intensity 0-100 (default: 60)
  --keep WORD [WORD ...]    Keywords to preserve
  --brand TERM [TERM ...]   Brand terms to protect
  --max-change RATIO        Maximum change ratio 0-1 (default: 0.4)
  --seed N                  Random seed for reproducibility
  --report FILE             Save JSON report to file

Analysis modes:
  --analyze                 Analyze text metrics (no processing)
  --explain                 Show detailed change report
  --detect-ai               Check for AI-generated text
  --tone-analyze            Analyze text tone
  --readability             Full readability analysis
  --coherence               Coherence analysis

Transform modes:
  --paraphrase              Paraphrase the text
  --tone TARGET             Adjust tone (formal, casual, neutral, etc.)
  --watermarks              Detect and clean watermarks
  --spin                    Generate a spun version
  --variants N              Generate N spin variants

Server:
  --api                     Start REST API server
  --port N                  API server port (default: 8080)

Other:
  -v, --version             Show version
```

### CLI Examples

```bash
# Analyze a file
texthumanize article.txt --analyze -l en

# Check for AI generation
texthumanize essay.txt --detect-ai

# Paraphrase with output file
texthumanize input.txt --paraphrase -o paraphrased.txt

# Adjust tone to casual
texthumanize formal_email.txt --tone casual -o casual_email.txt

# Clean watermarks
texthumanize suspect.txt --watermarks -o clean.txt

# Generate 5 spin variants
texthumanize template.txt --variants 5

# Start API server
texthumanize dummy --api --port 9090
```

---

## REST API Server

TextHumanize includes a zero-dependency HTTP server for JSON API access:

```bash
# Start server
python -m texthumanize.api --port 8080

# Or via CLI
texthumanize dummy --api --port 8080
```

### Endpoints

All `POST` endpoints accept JSON body with `{"text": "..."}` and return JSON.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/humanize` | Humanize text |
| `POST` | `/analyze` | Analyze text metrics |
| `POST` | `/detect-ai` | AI detection (single or batch) |
| `POST` | `/paraphrase` | Paraphrase text |
| `POST` | `/tone/analyze` | Tone analysis |
| `POST` | `/tone/adjust` | Tone adjustment |
| `POST` | `/watermarks/detect` | Detect watermarks |
| `POST` | `/watermarks/clean` | Clean watermarks |
| `POST` | `/spin` | Spin text (single or multi) |
| `POST` | `/coherence` | Coherence analysis |
| `POST` | `/readability` | Readability metrics |
| `GET` | `/health` | Server health check |
| `GET` | `/` | API info & endpoint list |

### Usage with curl

```bash
# Humanize
curl -X POST http://localhost:8080/humanize \
  -H "Content-Type: application/json" \
  -d '{"text": "Furthermore, it is important to utilize this.", "lang": "en", "profile": "web"}'

# AI Detection
curl -X POST http://localhost:8080/detect-ai \
  -H "Content-Type: application/json" \
  -d '{"text": "Text to check."}'

# Batch AI Detection
curl -X POST http://localhost:8080/detect-ai \
  -H "Content-Type: application/json" \
  -d '{"texts": ["First text.", "Second text."]}'

# Tone Adjustment
curl -X POST http://localhost:8080/tone/adjust \
  -H "Content-Type: application/json" \
  -d '{"text": "Formal text here.", "target": "casual"}'

# Health Check
curl http://localhost:8080/health
```

### Usage with Python requests

```python
import requests

API = "http://localhost:8080"

# Humanize
r = requests.post(f"{API}/humanize", json={
    "text": "Text to process.",
    "lang": "en",
    "profile": "web",
    "intensity": 60,
})
print(r.json()["text"])

# AI Detection
r = requests.post(f"{API}/detect-ai", json={"text": "Check this text."})
print(r.json()["verdict"])
```

All responses include `_elapsed_ms` field with processing time in milliseconds.

---

## Processing Pipeline

TextHumanize uses a 10-stage pipeline:

```
Input Text
  │
  ├─ 1. Segmentation        ─ protect code blocks, URLs, emails, brands
  │
  ├─ 2. Typography           ─ normalize dashes, quotes, ellipses, punctuation
  │
  ├─ 3. Debureaucratization  ─ replace bureaucratic/formal words  [dictionary]
  │
  ├─ 4. Structure            ─ diversify sentence openings         [dictionary]
  │
  ├─ 5. Repetitions          ─ reduce word/phrase repetitions       [dictionary + context]
  │
  ├─ 6. Liveliness           ─ inject natural phrasing              [dictionary]
  │
  ├─ 7. Universal            ─ statistical processing               [any language]
  │
  ├─ 8. Naturalization       ─ burstiness, perplexity, rhythm       [KEY STAGE]
  │
  ├─ 9. Validation           ─ quality check, rollback if needed
  │
  └─ 10. Restore             ─ restore protected segments
  │
Output Text
```

**Stages 3-6** require full dictionary support (9 languages).
**Stages 2, 7-8** work for any language, including those without dictionaries.
**Stage 9** rolls back changes if quality degrades (configurable via `max_change_ratio`).

---

## AI Detection — How It Works

The AI detection engine uses **12 independent statistical metrics**, each measuring a different aspect of text naturalness. No machine learning models, neural networks, or external APIs are used.

### Metrics Explained

| # | Metric | What It Measures | Weight |
|---|--------|-----------------|:------:|
| 1 | **AI Patterns** | Formulaic phrases ("it is important to note", "furthermore") | 20% |
| 2 | **Burstiness** | Sentence length variation (humans vary more than AI) | 14% |
| 3 | **Opening Diversity** | How varied sentence beginnings are | 9% |
| 4 | **Entropy** | Word predictability (AI text has lower entropy) | 8% |
| 5 | **Stylometry** | Word length distribution consistency | 8% |
| 6 | **Coherence** | Paragraph transition smoothness | 8% |
| 7 | **Vocabulary** | Type-to-token ratio, lexical richness | 7% |
| 8 | **Grammar Perfection** | Too-perfect grammar is suspicious | 6% |
| 9 | **Punctuation** | Punctuation diversity and distribution | 6% |
| 10 | **Rhythm** | Syllabic rhythm patterns | 6% |
| 11 | **Readability** | Consistency of reading level across paragraphs | 5% |
| 12 | **Zipf** | Word frequency distribution (Zipf's law adherence) | 3% |

### Scoring

Each metric produces a score from 0.0 (human-like) to 1.0 (AI-like). The weighted average is passed through a calibrated sigmoid function (center=0.45, steepness=8.0) to produce the final AI probability.

**Verdicts:**
- `score < 0.35` → **"human"** — text appears naturally written
- `0.35 ≤ score < 0.65` → **"mixed"** — uncertain or partially AI
- `score ≥ 0.65` → **"ai"** — text shows strong AI patterns

### Benchmark Results

Tested on a curated benchmark of 9 samples (4 AI-generated, 5 human-written):

```
┌──────────────────┬─────────────────┐
│ Metric           │ Value           │
├──────────────────┼─────────────────┤
│ Accuracy         │ 100%            │
│ Precision        │ 100%            │
│ Recall           │ 100%            │
│ F1 Score         │ 1.000           │
│ True Positives   │ 4               │
│ False Positives  │ 0               │
│ True Negatives   │ 5               │
│ False Negatives  │ 0               │
└──────────────────┴─────────────────┘
```

### Example: AI vs Human Text

```python
from texthumanize import detect_ai

# AI-generated text (GPT-like)
ai_text = """
Furthermore, it is important to note that the implementation of artificial 
intelligence constitutes a significant paradigm shift. Additionally, the 
utilization of machine learning facilitates comprehensive optimization 
of various processes. Nevertheless, it is worth mentioning that 
considerable challenges remain.
"""
result = detect_ai(ai_text, lang="en")
print(f"AI: {result['score']:.0%}")  # ~87-89%

# Human-written casual text
human_text = """
I tried that new coffee shop downtown yesterday. Their espresso was 
actually decent - not as burnt as the place on 5th. The barista 
was nice too, recommended this Ethiopian blend I'd never heard of. 
Might go back this weekend.
"""
result = detect_ai(human_text, lang="en")
print(f"AI: {result['score']:.0%}")  # ~20-27%
```

### Recommendations

- **Best accuracy:** texts of 100+ words
- **Short texts** (< 50 words): results may be less reliable
- **Formal texts:** may score slightly higher even if human-written
- **Multiple metrics** help even when individual ones are uncertain

---

## Language Support

### Full Dictionary Support (9 languages)

Each language pack includes:
- Bureaucratic word → natural replacements
- Formulaic connector alternatives
- Synonym dictionaries (context-aware)
- Sentence starter variations
- Colloquial markers
- Abbreviation lists (for sentence splitting)
- Language-specific trigrams (for detection)
- Stop words
- Profile-specific sentence length targets
- Perplexity boosters

| Language | Code | Bureaucratic | Connectors | Synonyms | Abbreviations |
|----------|:----:|:-----:|:------:|:------:|:------:|
| Russian | `ru` | 70+ | 25+ | 50+ | 15+ |
| Ukrainian | `uk` | 50+ | 24 | 48 | 12+ |
| English | `en` | 40+ | 25 | 35+ | 20+ |
| German | `de` | 22 | 12 | 26 | 10+ |
| French | `fr` | 20 | 12 | 20 | 8+ |
| Spanish | `es` | 18 | 12 | 18 | 8+ |
| Polish | `pl` | 18 | 12 | 18 | 8+ |
| Portuguese | `pt` | 16 | 12 | 17 | 6+ |
| Italian | `it` | 16 | 12 | 17 | 6+ |

### Universal Processor

For any language not in the dictionary list, TextHumanize uses statistical methods:
- Sentence length variation (burstiness injection)
- Punctuation normalization
- Whitespace regularization
- Perplexity boosting
- Fragment insertion

```python
# Works with any language — no dictionaries needed
result = humanize("日本語のテキスト", lang="ja")
result = humanize("Текст на казахском", lang="kk")
result = humanize("متن فارسی", lang="fa")
result = humanize("Đây là văn bản tiếng Việt", lang="vi")
```

### Auto-Detection

```python
# Language is detected automatically
result = humanize("Этот текст автоматически определяется как русский.")
print(result.lang)  # "ru"

result = humanize("This text is automatically detected as English.")
print(result.lang)  # "en"
```

---

## SEO Mode

The `seo` profile is designed for content that must preserve search ranking:

```python
result = humanize(
    text,
    profile="seo",
    intensity=40,            # lower intensity for safety
    constraints={
        "max_change_ratio": 0.3,
        "keep_keywords": ["cloud computing", "API", "microservices"],
    },
)
```

### SEO Mode Features

| Feature | Behavior |
|---------|----------|
| Keyword preservation | All specified keywords kept exactly |
| Intensity cap | Limited to safe levels |
| Colloquialisms | None inserted |
| Structure changes | Minimal |
| Sentence length | Stays within 12-25 words (optimal for SEO) |
| Synonyms | Only for non-keyword terms |
| Readability | Grade 6-8 target maintained |

### SEO Workflow Example

```python
from texthumanize import humanize, analyze, detect_ai

# 1. Analyze original
report = analyze(seo_text, lang="en")
print(f"Artificiality before: {report.artificiality_score:.0f}/100")

# 2. Humanize with SEO protection
result = humanize(seo_text, profile="seo", intensity=35,
                  constraints={"keep_keywords": ["cloud", "scalability"]})

# 3. Verify keywords preserved
for kw in ["cloud", "scalability"]:
    assert kw in result.text, f"Keyword '{kw}' was modified!"

# 4. Check AI detection improvement
ai_before = detect_ai(seo_text, lang="en")
ai_after = detect_ai(result.text, lang="en")
print(f"AI score: {ai_before['score']:.0%} → {ai_after['score']:.0%}")
```

---

## Readability Metrics

TextHumanize includes 6 readability indices:

| Index | Range | Measures |
|-------|-------|----------|
| **Flesch-Kincaid Grade** | 0-18+ | US grade level needed to read |
| **Coleman-Liau** | 0-18+ | Grade level (character-based) |
| **ARI** | 0-14+ | Automated Readability Index |
| **SMOG** | 3-18+ | Complexity from polysyllabic words |
| **Gunning Fog** | 6-20+ | Complexity estimate |
| **Dale-Chall** | 0-10+ | Difficulty using common word list |

```python
from texthumanize import analyze, full_readability

# Quick readability from analyze()
report = analyze("Your text here.", lang="en")
print(f"Flesch-Kincaid: {report.flesch_kincaid_grade:.1f}")
print(f"Coleman-Liau:   {report.coleman_liau_index:.1f}")

# Full readability with all indices
r = full_readability("Your text with multiple sentences. Each one counts.", lang="en")
for metric, value in r.items():
    print(f"  {metric}: {value}")
```

### Readability Grade Interpretation

| Grade | Level | Audience |
|:-----:|-------|----------|
| 5-6 | Easy | General public |
| 7-8 | Standard | Web content, blogs |
| 9-10 | Moderate | Business writing |
| 11-12 | Difficult | Academic papers |
| 13+ | Complex | Technical/legal |

---

## Paraphrasing Engine

The paraphrasing engine uses syntactic transformations (no ML):

### Transformations Applied

| Transformation | Example |
|---------------|---------|
| **Clause swap** | "Although X, Y." → "Y, although X." |
| **Passive→Active** | "The report was written by John." → "John wrote the report." |
| **Sentence splitting** | "X, and Y, and Z." → "X. Y. Z." |
| **Adverb fronting** | "He quickly ran." → "Quickly, he ran." |
| **Nominalization** | "He decided to go." → "His decision was to go." |

```python
from texthumanize import paraphrase

original = "Although the study was comprehensive, the results were inconclusive."
result = paraphrase(original, lang="en", intensity=0.8)
print(result)
# → e.g. "The results were inconclusive, although the study was comprehensive."
```

---

## Tone Analysis & Adjustment

### Tone Levels

| Tone | Formality | Example |
|------|:---------:|---------|
| `very_formal` | 0.9+ | "The undersigned hereby acknowledges..." |
| `formal` | 0.7-0.9 | "Please submit the required documentation." |
| `neutral` | 0.4-0.7 | "Send us the documents." |
| `casual` | 0.2-0.4 | "Just send over the docs." |
| `very_casual` | 0.0-0.2 | "Shoot me the docs!" |

### Markers Detected

For English: `hereby`, `pursuant`, `constitutes`, `facilitate`, `implement`, `utilize`, `gonna`, `wanna`, `hey`, `awesome`, etc.

For Russian: `настоящим`, `осуществить`, `однако`, `привет`, `круто`, etc.

```python
from texthumanize import analyze_tone, adjust_tone

# Analyze
tone = analyze_tone("Pursuant to our agreement, please facilitate the transfer.", lang="en")
print(tone['primary_tone'])  # "formal"
print(tone['formality'])     # ~0.85

# Adjust down
casual = adjust_tone("Pursuant to our agreement, please facilitate the transfer.",
                     target="casual", lang="en")
print(casual)  # → "Based on our agreement, go ahead and start the transfer."
```

---

## Watermark Detection & Cleaning

### What It Detects

| Type | Description | Example |
|------|-------------|---------|
| **Zero-width chars** | U+200B, U+200C, U+200D, U+FEFF | Invisible between words |
| **Homoglyphs** | Cyrillic/Latin lookalikes | `а` (Cyrillic) vs `a` (Latin) |
| **Invisible formatting** | Invisible Unicode chars | U+2060, U+2061, etc. |
| **Spacing steganography** | Unusual space patterns | Extra spaces encoding data |
| **Statistical watermarks** | AI watermark patterns | Token probability anomalies |

```python
from texthumanize import detect_watermarks, clean_watermarks

# Full detection
report = detect_watermarks(suspicious_text, lang="en")
if report['has_watermarks']:
    print(f"Found: {report['watermark_types']}")
    print(f"Confidence: {report['confidence']:.0%}")
    print(f"Cleaned: {report['cleaned_text']}")
else:
    print("No watermarks detected")

# Quick clean
clean = clean_watermarks(suspicious_text)
```

---

## Text Spinning

Generate unique content variants using dictionary-based synonym replacement.

### Spintax

The spinner can output spintax format for use in other tools:

```python
from texthumanize.spinner import ContentSpinner

spinner = ContentSpinner(lang="en", seed=42)

# Generate spintax
spintax = spinner.generate_spintax("The system provides important data.")
print(spintax)
# → "The {system|platform} {provides|offers} {important|crucial} {data|information}."

# Resolve spintax to one variant
resolved = spinner.resolve_spintax(spintax)
print(resolved)
```

### High-Level API

```python
from texthumanize import spin, spin_variants

# Single variant
unique = spin("Original text here.", lang="en", intensity=0.6, seed=42)

# Multiple variants
variants = spin_variants("Original text.", count=5, lang="en")
for v in variants:
    print(v)
```

---

## Coherence Analysis

Measures how well text flows at the paragraph level.

### Metrics

| Metric | Range | Description |
|--------|:-----:|-------------|
| `overall` | 0-1 | Weighted average of all coherence metrics |
| `lexical_cohesion` | 0-1 | Word overlap between adjacent sentences |
| `transition_score` | 0-1 | Quality of logical transitions |
| `topic_consistency` | 0-1 | How consistent the topic is throughout |
| `sentence_opening_diversity` | 0-1 | Variety in sentence beginnings |

### Issues Detected

The analyzer flags specific problems:
- "Weak transition between paragraph 2 and 3"
- "Topic drift detected at paragraph 4"
- "Repetitive sentence openings in paragraph 1"
- "Paragraph too short (1 sentence)"

```python
from texthumanize import analyze_coherence

report = analyze_coherence(article_text, lang="en")
print(f"Overall: {report['overall']:.2f}")

if report['overall'] < 0.5:
    print("Text coherence is low. Issues:")
    for issue in report['issues']:
        print(f"  - {issue}")
```

---

## Morphological Engine

Built-in lemmatization for RU, UK, EN, DE — no external libraries needed.

### Supported Operations

| Operation | Languages | Example |
|-----------|-----------|---------|
| Lemmatization | RU, UK, EN, DE | "running" → "run" |
| Form generation | RU, UK, EN, DE | "run" → ["runs", "running", "ran"] |
| Case handling | RU, UK, DE | Automatic declension matching |
| Compound words | DE | Splitting German compounds |

### Usage in Synonym Matching

The morphological engine is used internally by the repetition reducer to ensure synonym forms match the original grammatically:

```python
# Internal usage — synonyms match morphological forms
# "They were implementing..." → "They were doing..." (not "They were do...")
```

Direct usage:

```python
from texthumanize.morphology import MorphologicalEngine

morph = MorphologicalEngine(lang="en")
print(morph.lemmatize("running"))   # "run"
print(morph.lemmatize("houses"))    # "house"
print(morph.lemmatize("better"))    # "good"
```

---

## Smart Sentence Splitter

Handles edge cases that naive regex splitting gets wrong:

| Case | Input | Correct Split |
|------|-------|--------------|
| Abbreviations | "Dr. Smith went home." | 1 sentence |
| Decimals | "Temperature is 36.6 degrees." | 1 sentence |
| Initials | "J.K. Rowling wrote it." | 1 sentence |
| Ellipsis | "Well... Maybe not." | 2 sentences |
| Direct speech | '"Hello," she said.' | 1 sentence |
| URLs | "Visit example.com today." | 1 sentence |

```python
from texthumanize.sentence_split import split_sentences

text = "Dr. Smith arrived at 3 p.m. He brought the report."
sents = split_sentences(text, lang="en")
print(sents)  # ['Dr. Smith arrived at 3 p.m.', 'He brought the report.']
```

The smart splitter is integrated into all pipeline stages that need sentence-level processing.

---

## Context-Aware Synonyms

Word-sense disambiguation (WSD) without ML. Chooses the best synonym based on surrounding context.

### How It Works

1. **Topic detection** — classifies text as technology, business, casual, or neutral
2. **Collocation scoring** — checks expected word pairs ("make decision" not "make choice")
3. **Context window** — examines surrounding words to determine word sense

```python
from texthumanize.context import ContextualSynonyms

ctx = ContextualSynonyms(lang="en", seed=42)
ctx.detect_topic("The server handles API requests efficiently.")

# Choose best synonym for "important" in tech context
best = ctx.choose_synonym("important", ["significant", "crucial", "key", "vital"],
                          "This is an important update to the system.")
print(best)  # "key" or "crucial" (tech-appropriate)
```

---

## Using Individual Modules

Each module can be used independently:

```python
# Typography normalization only
from texthumanize.normalizer import TypographyNormalizer
norm = TypographyNormalizer(profile="web")
result = norm.normalize("Text — with dashes and «quotes»...")
# → 'Text - with dashes and "quotes"...'

# Debureaucratization only
from texthumanize.decancel import Debureaucratizer
db = Debureaucratizer(lang="en", profile="chat", intensity=80)
result = db.process("This text utilizes a comprehensive methodology.")
# → "This text uses a complete method."

# Structure diversification
from texthumanize.structure import StructureDiversifier
sd = StructureDiversifier(lang="en", profile="web", intensity=60)
result = sd.process("Furthermore, X. Additionally, Y. Moreover, Z.")

# Sentence splitting
from texthumanize.sentence_split import split_sentences
sents = split_sentences("Dr. Smith said hello. She left.", lang="en")

# AI detection (low-level)
from texthumanize.detectors import detect_ai
result = detect_ai("Text to check.", lang="en")
print(result.ai_probability, result.verdict)

# Tone analysis (low-level)
from texthumanize.tone import analyze_tone
report = analyze_tone("Formal text here.", lang="en")
print(report.primary_tone, report.formality)

# Content spinning
from texthumanize.spinner import ContentSpinner
spinner = ContentSpinner(lang="en", seed=42)
spintax = spinner.generate_spintax("The system works well.")

# Analysis only
from texthumanize.analyzer import TextAnalyzer
analyzer = TextAnalyzer(lang="en")
report = analyzer.analyze("Text to analyze.")
```

---

## Performance & Benchmarks

All benchmarks on Apple Silicon (M1 Pro), Python 3.12, single thread.

### Processing Speed

| Text Size | Time | Words/sec |
|-----------|------|-----------|
| 100 words | ~3ms | ~33,000 |
| 500 words | ~8ms | ~62,000 |
| 1,000 words | ~15ms | ~66,000 |
| 5,000 words | ~60ms | ~83,000 |
| 10,000 words | ~120ms | ~83,000 |

### AI Detection Speed

| Text Size | Time |
|-----------|------|
| 100 words | ~5ms |
| 500 words | ~12ms |
| 1,000 words | ~20ms |

### Memory Usage

- Base import: ~2MB
- Per text processing: negligible overhead
- No model files to load

### Test Suite Performance

```
500 tests in 2.21 seconds
Coverage: 85%
```

---

## Testing

```bash
# Run all tests (500 tests)
pytest

# With coverage report
pytest --cov=texthumanize --cov-report=term-missing

# Quick run (no coverage)
pytest -q

# Verbose
pytest -v

# Lint check
ruff check texthumanize/

# Type check
mypy texthumanize/

# Pre-commit hooks
pre-commit run --all-files

# Specific test suite
pytest tests/test_core.py             # Core humanize/analyze
pytest tests/test_golden.py            # Golden master tests
pytest tests/test_segmenter.py         # Segmenter protection
pytest tests/test_normalizer.py        # Typography normalization
pytest tests/test_decancel.py          # Debureaucratization
pytest tests/test_structure.py         # Structure diversification
pytest tests/test_multilang.py         # Multi-language support
pytest tests/test_naturalizer.py       # Style naturalization
pytest tests/test_detectors.py         # AI detection
pytest tests/test_morphology_ext.py    # Morphological engine (extended)
pytest tests/test_coverage_boost.py    # Coherence/paraphrase/watermark
pytest tests/test_sentence_split.py    # Sentence splitter
pytest tests/test_tone.py              # Tone analysis
pytest tests/test_watermark.py         # Watermark detection
pytest tests/test_spinner.py           # Content spinning
pytest tests/test_coherence.py         # Coherence analysis
pytest tests/test_paraphrase.py        # Paraphrasing
pytest tests/test_context.py           # Context-aware synonyms
pytest tests/test_tokenizer.py         # Tokenizer
pytest tests/test_api_wrappers.py      # API wrapper functions
pytest tests/test_cli.py               # CLI interface
```

### Coverage Summary

| Module | Coverage |
|--------|:--------:|
| core.py | 98% |
| decancel.py | 97% |
| segmenter.py | 98% |
| lang_detect.py | 96% |
| coherence.py | 96% |
| tokenizer.py | 95% |
| spinner.py | 94% |
| normalizer.py | 94% |
| tone.py | 94% |
| morphology.py | 93% |
| analyzer.py | 93% |
| detectors.py | 90% |
| utils.py | 90% |
| repetitions.py | 88% |
| structure.py | 88% |
| paraphrase.py | 87% |
| watermark.py | 87% |
| liveliness.py | 86% |
| validator.py | 86% |
| cli.py | 85% |
| lang/ | 100% |
| **Overall** | **85%** |

---

## Architecture

```
texthumanize/
├── __init__.py          # Public API exports (16 functions + 4 classes)
├── core.py              # API facade: humanize(), analyze(), detect_ai(), etc.
├── api.py               # REST API: zero-dependency HTTP server, 12 endpoints
├── cli.py               # CLI interface with 15+ commands
├── pipeline.py          # 10-stage pipeline + plugin system
│
├── analyzer.py          # Artificiality scoring + 6 readability metrics
├── tokenizer.py         # Paragraph/sentence/word tokenization
├── sentence_split.py    # Smart sentence splitter (abbreviations, decimals)
│
├── segmenter.py         # Code/URL/email/brand protection
├── normalizer.py        # Typography normalization
├── decancel.py          # Debureaucratization
├── structure.py         # Sentence structure diversification
├── repetitions.py       # Repetition reduction (context-aware)
├── liveliness.py        # Natural phrasing injection
├── universal.py         # Universal processor (any language)
├── naturalizer.py       # Style naturalization (burstiness, perplexity)
├── validator.py         # Quality validation + automatic rollback
│
├── detectors.py         # AI text detector (12 statistical metrics)
├── paraphrase.py        # Syntactic paraphrasing engine
├── tone.py              # Tone analysis & adjustment (7 levels)
├── watermark.py         # Watermark detection & cleaning
├── spinner.py           # Text spinning & spintax generation
├── coherence.py         # Coherence & paragraph flow analysis
├── morphology.py        # Morphological engine (RU/UK/EN/DE)
├── context.py           # Context-aware synonym selection (WSD)
│
├── lang_detect.py       # Language detection (9 languages)
├── utils.py             # Options, profiles, result classes
├── __main__.py          # python -m texthumanize
│
└── lang/                # Language packs (data only, no logic)
    ├── __init__.py      # Registry + fallback
    ├── ru.py            # Russian (70+ bureaucratic, 50+ synonyms)
    ├── uk.py            # Ukrainian
    ├── en.py            # English
    ├── de.py            # German
    ├── fr.py            # French
    ├── es.py            # Spanish
    ├── pl.py            # Polish
    ├── pt.py            # Portuguese
    └── it.py            # Italian
```

### Design Principles

| Principle | Description |
|-----------|-------------|
| **Modularity** | Each pipeline stage is a separate module |
| **Declarative rules** | Language packs contain only data, not logic |
| **Idempotent** | Re-processing doesn't degrade quality |
| **Safe defaults** | Validator auto-rolls back harmful changes |
| **Extensible** | Add languages, profiles, or stages via plugins |
| **Portable** | Declarative architecture enables easy porting |
| **Zero dependencies** | Pure Python stdlib only |
| **Lazy imports** | New modules loaded on first use, fast startup |

---

## PHP Library

A full PHP port is available in the `php/` directory with identical functionality.

### PHP Quick Start

```php
<?php
use TextHumanize\TextHumanize;

// Basic usage
$result = TextHumanize::humanize("Text to process", profile: 'web');
echo $result->processed;

// Chunk processing for large texts
$result = TextHumanize::humanizeChunked($longText, chunkSize: 5000);

// Analysis
$report = TextHumanize::analyze("Text to analyze");
echo $report->artificialityScore;

// Explanation
$explanation = TextHumanize::explain("Text to explain");
```

### PHP Modules

The PHP port includes all new v0.4.0 modules:

| Module | PHP Class |
|--------|-----------|
| AI Detection | `AIDetector` |
| Sentence Splitting | `SentenceSplitter` |
| Paraphrasing | `Paraphraser` |
| Tone Analysis | `ToneAnalyzer` |
| Watermark Detection | `WatermarkDetector` |
| Content Spinning | `ContentSpinner` |
| Coherence Analysis | `CoherenceAnalyzer` |

### PHP Installation

```bash
cd php/
composer install
php vendor/bin/phpunit  # run tests
```

See [php/README.md](php/README.md) for full PHP documentation.

---

## Code Quality & Tooling

### Linting

TextHumanize enforces strict code quality with [ruff](https://github.com/astral-sh/ruff):

```bash
# Check all code (0 errors)
ruff check texthumanize/

# Auto-fix safe issues
ruff check --fix texthumanize/
```

Rules enabled: `E` (pycodestyle), `F` (Pyflakes), `W` (warnings), `I` (isort). Line length: 100 chars.

### Type Checking

PEP 561 compliant — ships `py.typed` marker for downstream type checkers:

```bash
mypy texthumanize/
```

Configuration in `pyproject.toml`:
- `python_version = "3.9"` — minimum supported version
- `check_untyped_defs = true` — checks function bodies even without annotations
- `warn_return_any = true` — warns on `Any` return types

### Pre-commit Hooks

Automatic quality checks on every commit:

```bash
pre-commit install        # one-time setup
pre-commit run --all-files # manual run
```

Hooks configured:
- Trailing whitespace removal
- End-of-file fixer
- YAML/TOML validation
- Large file prevention
- Merge conflict detection
- Ruff lint + format check

### CI/CD Pipeline

GitHub Actions runs on every push/PR:

| Step | Description |
|------|-------------|
| **Lint** | `ruff check` — zero errors enforced |
| **Test** | `pytest` across Python 3.9–3.12 + PHP 8.1–8.3 |
| **Coverage** | `pytest-cov` — 85% minimum |
| **Types** | `mypy` on Python 3.12 (non-blocking) |

---

## Migration Guide (v0.4 → v0.5)

### What's New in v0.5

1. **500 tests** — up from 382, covering 85% of codebase (was 80%)
2. **Zero lint errors** — `ruff check` passes cleanly (67 errors fixed)
3. **Type checking** — PEP 561 `py.typed` marker, mypy configuration
4. **Pre-commit hooks** — ruff + formatting checks on every commit
5. **Enhanced CI/CD** — ruff lint step + mypy type check + XML coverage output
6. **pytest fixtures** — `conftest.py` with 12 reusable fixtures for all tests
7. **PHP fixes** — type safety improvements in SentenceSplitter and ToneAnalyzer

### Breaking Changes

**None.** v0.5.0 is fully backward-compatible with v0.4.0. All existing code works without changes.

### Developer Tooling Setup

```bash
# Install dev dependencies (new in 0.5)
pip install -e ".[dev]"

# Set up pre-commit hooks
pre-commit install

# Verify everything passes
ruff check texthumanize/   # 0 errors
pytest -q                  # 500 passed
```

---

## FAQ & Troubleshooting

### General

**Q: Does TextHumanize use the internet?**
No. All processing is 100% local. No API calls, no data sent anywhere.

**Q: Does it require GPU or large models?**
No. Pure algorithmic processing using Python standard library only.

**Q: Can I use it commercially?**
The current license is Personal Use Only. Contact the author for commercial licensing.

**Q: Which Python versions are supported?**
Python 3.9 through 3.12+ (tested in CI/CD).

### Processing

**Q: My text isn't changing much. Why?**
Increase `intensity` (e.g., 80-100) or use a more aggressive profile like `chat`. The `seo` and `formal` profiles intentionally make fewer changes.

**Q: Can I undo changes?**
The `explain(result)` function shows all changes. The original text is always available in `result.original`.

**Q: How do I protect specific words from changing?**
Use `constraints={"keep_keywords": ["word1", "word2"]}` or `preserve={"brand_terms": ["Brand"]}`.

**Q: The output has too many colloquialisms.**
Switch to `profile="docs"` or `profile="formal"` and lower the intensity.

### AI Detection

**Q: The detector says my text is AI-generated but it's not.**
Formal, academic, or legal text can score higher due to formulaic patterns. This is expected. The detector works best on general-purpose text (blogs, articles, essays).

**Q: How accurate is the AI detector?**
On our benchmark: F1=100% (4 AI texts, 5 human texts correctly classified). Real-world accuracy depends on text type and length. Best results with 100+ words.

**Q: Does it detect ChatGPT/GPT-4/Claude specifically?**
It detects statistical patterns common to all LLMs, not any specific model. It works for GPT-3.5, GPT-4, Claude, Gemini, etc.

### Languages

**Q: My language isn't in the supported list.**
Use `lang="xx"` (your ISO code) — the universal processor will handle typography normalization, sentence variation, and burstiness without language-specific dictionaries.

**Q: Can I add a new language?**
Yes! Create a new file in `texthumanize/lang/` following the existing pattern. See any existing language file (e.g., `en.py`) as a template.

### CLI & API

**Q: How do I start the REST API?**
```bash
python -m texthumanize.api --port 8080
# or
texthumanize dummy --api --port 8080
```

**Q: Is there WebSocket support?**
Not yet. The current API is HTTP/REST only.

---

## Contributing

Contributions are welcome:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Write tests for new functionality
4. Ensure all tests pass: `pytest`
5. Commit changes: `git commit -m 'Add my feature'`
6. Push: `git push origin feature/my-feature`
7. Open a Pull Request

### Areas for Improvement

- **Dictionaries** — expand bureaucratic and synonym dictionaries for all languages
- **Languages** — add new language packs (Japanese, Chinese, Arabic, Korean, etc.)
- **Tests** — more edge cases and golden tests, push coverage past 90%
- **Documentation** — tutorials, video walkthroughs, blog posts
- **Ports** — Node.js, Go, Rust implementations
- **API** — WebSocket support, authentication, rate limiting
- **Morphology** — expand to more languages (FR, ES, PL, PT, IT)
- **AI Detector** — larger benchmark suite, more metrics

### Development Setup

```bash
git clone https://github.com/ksanyok/TextHumanize.git
cd TextHumanize
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
ruff check texthumanize/
pytest --cov=texthumanize
```

---

## Support the Project

If you find TextHumanize useful, consider supporting the development:

[![PayPal](https://img.shields.io/badge/PayPal-Donate-blue.svg?logo=paypal)](https://www.paypal.com/cgi-bin/webscr?cmd=_donations&business=ksanyok%40me.com&item_name=TextHumanize&currency_code=USD)

- Star the repository
- Report bugs and suggest features
- Improve documentation
- Add language packs

---

## License

TextHumanize Personal Use License. See [LICENSE](LICENSE).

This library is licensed for **personal, non-commercial use only**. Commercial use requires a separate license — contact the author for details.

---

<p align="center">
  <a href="https://github.com/ksanyok/TextHumanize">GitHub</a> ·
  <a href="https://github.com/ksanyok/TextHumanize/issues">Issues</a> ·
  <a href="https://github.com/ksanyok/TextHumanize/discussions">Discussions</a>
</p>
