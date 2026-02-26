<div align="center">

# TextHumanize

### The most advanced open-source text naturalization engine

**Normalize style, improve readability, and ensure brand-safe content — offline, private, and blazing fast**

<br/>

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6.svg?logo=typescript&logoColor=white)]()
[![PHP 8.1+](https://img.shields.io/badge/php-8.1+-777BB4.svg?logo=php&logoColor=white)](https://www.php.net/)
&nbsp;&nbsp;
[![Python Tests](https://img.shields.io/badge/tests-1696%20passed-2ea44f.svg?logo=pytest&logoColor=white)]()
[![PHP Tests](https://img.shields.io/badge/tests-223%20passed-2ea44f.svg?logo=php&logoColor=white)]()
[![JS Tests](https://img.shields.io/badge/tests-28%20passed-2ea44f.svg?logo=vitest&logoColor=white)]()
&nbsp;&nbsp;
[![Coverage](https://img.shields.io/badge/coverage-99%25-brightgreen.svg)]()
[![Benchmark](https://img.shields.io/badge/benchmark-100%25-brightgreen.svg)]()

[![mypy](https://img.shields.io/badge/types-mypy%20clean-blue.svg)](https://mypy-lang.org/)
[![Ruff](https://img.shields.io/badge/linting-ruff-261230.svg)](https://github.com/astral-sh/ruff)
[![pre-commit](https://img.shields.io/badge/pre--commit-enabled-brightgreen.svg)](https://pre-commit.com/)
[![Zero Dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen.svg)]()
[![License](https://img.shields.io/badge/license-Dual%20(Free%20%2B%20Commercial)-blue.svg)](LICENSE)

<br/>

**40,000+ lines of code** · **72 Python modules** · **17-stage pipeline** · **14 languages + universal**

[Quick Start](#quick-start) · [API Reference](#api-reference) · [AI Detection](#ai-detection--how-it-works) · [Cookbook](docs/COOKBOOK.md)

</div>

---

TextHumanize is a **pure-algorithmic text processing engine** that normalizes style, improves readability, and removes mechanical patterns from text. No neural networks, no API keys, no internet — just 40K+ lines of finely tuned rules, dictionaries, and statistical methods.

It normalizes typography, simplifies bureaucratic language, diversifies sentence structure, increases burstiness and perplexity, replaces formulaic phrases, and applies context-aware synonym substitution — all while preserving semantic meaning.

### Built-in AI toolkit:
**AI Detection** · **Paraphrasing** · **Tone Analysis & Adjustment** · **Watermark Detection & Cleaning** · **Content Spinning** · **Coherence Analysis** · **Readability Scoring** · **Stylistic Fingerprinting** · **Auto-Tuner** · **Perplexity Analysis** · **Plagiarism Detection** · **Dictionary Training** · **Streaming & Variants**

### Available for:
**Python** (full) · **TypeScript/JavaScript** (core pipeline) · **PHP** (full)

### Languages:
🇷🇺 Russian · 🇺🇦 Ukrainian · 🇬🇧 English · 🇩🇪 German · 🇫🇷 French · 🇪🇸 Spanish · 🇵🇱 Polish · 🇧🇷 Portuguese · 🇮🇹 Italian · �🇦 Arabic · 🇨🇳 Chinese · 🇯🇵 Japanese · 🇰🇷 Korean · 🇹🇷 Turkish · �🌍 **any language** via universal processor

---

## Table of Contents

- [Why TextHumanize?](#why-texthumanize)
- [Feature Overview](#feature-overview)
- [Comparison with Competitors](#comparison-with-competitors)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Before & After Examples](#before--after-examples)
- [AI Detection — Deep Dive](#ai-detection--how-it-works)
- [API Reference](#api-reference)
- [Style Presets](#style-presets)
- [Auto-Tuner (Feedback Loop)](#auto-tuner-feedback-loop)
- [Profiles](#profiles)
- [Parameters](#parameters)
- [Plugin System](#plugin-system)
- [Chunk Processing](#chunk-processing)
- [CLI Reference](#cli-reference)
- [REST API Server](#rest-api-server)
- [Processing Pipeline](#processing-pipeline)
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
- [Perplexity Analysis](#perplexity-analysis)
- [Plagiarism Detection](#plagiarism-detection)
- [Dictionary Training](#dictionary-training)
- [Sentence-Level Humanization](#sentence-level-humanization)
- [Multi-Variant Output](#multi-variant-output)
- [Streaming API](#streaming-api)
- [Context-Aware Synonyms](#context-aware-synonyms)
- [Stylistic Fingerprinting](#stylistic-fingerprinting)
- [Using Individual Modules](#using-individual-modules)
- [Performance & Benchmarks](#performance--benchmarks)
- [Testing](#testing)
- [Architecture](#architecture)
- [TypeScript / JavaScript Port](#typescript--javascript-port)
- [PHP Library](#php-library)
- [What's New in v0.8.0](#whats-new-in-v080)
- [Code Quality & Tooling](#code-quality--tooling)
- [FAQ & Troubleshooting](#faq--troubleshooting)
- [Contributing](#contributing)
- [Security & Limits](#security--limits)
- [For Business & Enterprise](#for-business--enterprise)
- [Support the Project](#support-the-project)
- [License & Pricing](#license--pricing)

---

## Why TextHumanize?

> **The problem:** Machine-generated and template-based text often has uniform sentence lengths, bureaucratic vocabulary, formulaic connectors, and low stylistic diversity. This reduces readability, engagement, and brand authenticity.

> **The solution:** TextHumanize algorithmically normalizes text style while preserving the original meaning. Configurable intensity, deterministic output, full change reports. No cloud APIs, no rate limits, no data leaks.

### Core Advantages

| Advantage | Details |
|:----------|:--------|
| 🚀 **Blazing fast** | 30,000+ chars/sec — process a full article in milliseconds, not seconds |
| 🔒 **100% private** | All processing is local. Your text never leaves your machine |
| 🎯 **Precise control** | Intensity 0–100, 9 profiles, keyword preservation, max change ratio |
| 🌍 **14 languages + universal** | Full dictionaries for 14 languages; statistical processor for any other |
| 📦 **Zero dependencies** | Pure Python stdlib — no pip packages, no model downloads |
| 🔁 **Reproducible** | Seed-based PRNG — same input + same seed = identical output |
| 🔌 **Extensible** | Plugin system to inject custom stages before/after any pipeline step |
| 🧠 **Built-in AI detector** | 13-metric ensemble with 100% benchmark accuracy — no ML required |
| 📊 **Self-optimizing** | Auto-Tuner learns optimal parameters from your processing history |
| 🎭 **Style presets** | Target a specific persona: student, copywriter, scientist, journalist, blogger |
| 📚 **Multi-platform** | Python + TypeScript/JavaScript + PHP — one codebase, three ecosystems |
| 🛡️ **Semantic guards** | Context-aware replacement with echo checks and negative collocations |
| 📝 **Change report** | Every call returns what was changed, change ratio, quality score, similarity |
| 🏢 **Enterprise-ready** | Dual license, 1,584 tests, 99% coverage, CI/CD, benchmarks, on-prem |

---

## Feature Overview

### Text Transformation

| What TextHumanize Fixes | Before (AI) | After (Human-like) |
|:------------------------|:------------|:-------------------|
| Em dashes | `text — example` | `text - example` |
| Typographic quotes | `«text»` | `"text"` |
| Bureaucratic vocabulary | `utilize`, `implement`, `facilitate` | `use`, `do`, `help` |
| Formulaic connectors | `However`, `Furthermore`, `Additionally` | `But`, `Also`, `Plus` |
| Uniform sentence length | All 15–20 words | Varied 5–25 words |
| Word repetitions | `important… important…` | Context-aware synonyms |
| Perfect punctuation | Frequent `;` and `:` | Simplified, natural |
| Low perplexity | Predictable word choice | Natural variation |
| Boilerplate phrases | `it is important to note that` | `notably`, `by the way` |
| AI watermarks | Hidden zero-width characters | Cleaned text |

### Full Feature Matrix

| Category | Feature | Python | TS/JS | PHP |
|:---------|:--------|:------:|:-----:|:---:|
| **Core** | `humanize()` — 17-stage pipeline | ✅ | ✅ | ✅ |
| | `humanize_batch()` — parallel processing | ✅ | — | ✅ |
| | `humanize_chunked()` — large text support | ✅ | — | ✅ |
| | `analyze()` — artificiality scoring | ✅ | ✅ | ✅ |
| | `explain()` — change report | ✅ | — | ✅ |
| **AI Detection** | `detect_ai()` — 13-metric + statistical ML | ✅ | ✅ | ✅ |
| | `detect_ai_batch()` — batch detection | ✅ | — | — |
| | `detect_ai_sentences()` — per-sentence | ✅ | — | — |
| | `detect_ai_mixed()` — mixed content | ✅ | — | — |
| | `detect_ai_statistical()` — 35-feature ML | ✅ | — | — |
| **Paraphrasing** | `paraphrase()` — syntactic transforms | ✅ | — | ✅ |
| **Tone** | `analyze_tone()` — formality analysis | ✅ | — | ✅ |
| | `adjust_tone()` — 7-level adjustment | ✅ | — | ✅ |
| **Watermarks** | `detect_watermarks()` — 5 types | ✅ | — | ✅ |
| | `clean_watermarks()` — removal | ✅ | — | ✅ |
| **Spinning** | `spin()` / `spin_variants()` | ✅ | — | ✅ |
| **Analysis** | `analyze_coherence()` — paragraph flow | ✅ | — | ✅ |
| | `full_readability()` — 6 indices | ✅ | — | ✅ |
| | Stylistic fingerprinting | ✅ | — | — |
| **NLP** | `POSTagger` — rule-based POS tagger (EN/RU/UK/DE) | ✅ | — | — |
| | `CJKSegmenter` — Chinese/Japanese/Korean word segmentation | ✅ | — | — |
| | `SyntaxRewriter` — 8 sentence-level transforms | ✅ | — | — |
| | `WordLanguageModel` — word-level LM (14 langs) | ✅ | — | — |
| | `CollocEngine` — PMI collocation scoring | ✅ | — | — |
| **AI Backend** | `humanize_ai()` — three-tier AI rewriting | ✅ | — | — |
| | OpenAI API integration | ✅ | — | — |
| | OSS model fallback (rate-limited) | ✅ | — | — |
| **Quality** | `BenchmarkSuite` — 6-dimension quality scoring | ✅ | — | — |
| | `FingerprintRandomizer` — anti-detection diversity | ✅ | — | — |
| **Advanced** | Style presets (5 personas) | ✅ | — | — |
| | Auto-Tuner (feedback loop) | ✅ | — | — |
| | Plugin system | ✅ | — | ✅ |
| | REST API server (12 endpoints) | ✅ | — | — |
| | CLI (15+ commands) | ✅ | — | — |
| **Languages** | Full dictionary support | 14 | 2 | 14 |
| | Universal processor | ✅ | ✅ | ✅ |

---

## Comparison with Competitors

### vs. Online Text-Processing Services

| Criterion | TextHumanize | Online Humanizers |
|:----------|:------------:|:-----------------:|
| Works offline | ✅ | ❌ — requires internet |
| Privacy | ✅ Your text stays local | ❌ Uploaded to third-party servers |
| Speed | **~3 ms** per paragraph | 2–10 seconds (network latency) |
| Cost | **Free** | $10–50/month subscription |
| API key required | No | Yes |
| Rate limits | None | Typically 10K–50K words/month |
| Reproducible results | ✅ Seed-based | ❌ Different every time |
| Fine control | Intensity, profiles, keywords, plugins | Usually none |
| Languages | **9 + universal** | 1–3 |
| Self-hosted | ✅ | ❌ |
| Built-in AI detector | ✅ 13-metric ensemble | Some (basic) |
| Paraphrasing | ✅ | Some |
| Tone adjustment | ✅ | ❌ |
| Watermark cleaning | ✅ | ❌ |
| Open source | ✅ | ❌ |

### vs. GPT/LLM-based Rewriting

| Criterion | TextHumanize | GPT Rewrite |
|:----------|:------------:|:-----------:|
| Works offline | ✅ | ❌ |
| Zero dependencies | ✅ | ❌ Requires API key + billing |
| Deterministic | ✅ Same seed = same output | ❌ Non-deterministic |
| Speed | **30K+ chars/sec** | ~500 chars/sec (API) |
| Cost per 1M chars | **$0** | ~$15–60 (GPT-4) |
| Preserves meaning | ✅ Controlled change ratio | ⚠️ May hallucinate |
| Max change control | ✅ `max_change_ratio` | ❌ Unpredictable |
| Self-contained | ✅ pip install, done | ❌ Needs OpenAI account |
| Deterministic output | ✅ Seed-based | ❌ Non-deterministic |

### vs. Other Open-Source Libraries

| Feature | TextHumanize v0.8 | Typical Alternatives |
|:--------|:------------------:|:--------------------:|
| Pipeline stages | **17** | 2–4 |
| Languages | **9 + universal + CJK** | 1–2 |
| AI detection built-in | ✅ 13 metrics + ensemble | ❌ |
| Total test count | **1,696** (Py+PHP+JS) | 10–50 |
| Test coverage | **99%** | Unknown |
| Benchmark pass rate | **100%** (45/45) | No benchmark |
| Codebase size | **40K+ lines** | 500–2K |
| Platforms | Python + JS + PHP | Single |
| Plugin system | ✅ | ❌ |
| Tone analysis | ✅ 7 levels | ❌ |
| Watermark cleaning | ✅ 5 types | ❌ |
| Paraphrasing | ✅ Syntactic | ❌ |
| Coherence analysis | ✅ | ❌ |
| Auto-tuner | ✅ | ❌ |
| Style presets | ✅ 5 personas | ❌ |
| Documentation | README + API Ref + Cookbook | README only |
| REST API | ✅ 12 endpoints | ❌ |
| Readability metrics | ✅ 6 indices | 0–1 |
| Morphological engine | ✅ 4 languages | ❌ |
| Context-aware synonyms | ✅ WSD | Simple random |
| Reproducibility | ✅ Seed-based | ❌ |

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

### PHP (Composer)

```bash
composer require ksanyok/text-humanize
```

Если пакет ещё недоступен на Packagist, добавьте VCS-репозиторий в `composer.json` вашего проекта:

```json
{
    "repositories": [
        {
            "type": "vcs",
            "url": "https://github.com/ksanyok/TextHumanize"
        }
    ],
    "require": {
        "ksanyok/text-humanize": "^0.11"
    }
}
```

Или установите из исходников:

```bash
cd php/
composer install
```

### TypeScript / JavaScript

```bash
cd js/
npm install
```

### Verify installation

```python
import texthumanize
print(texthumanize.__version__)  # 0.11.0
```

### Updating to latest version

#### Python

```bash
# Update to latest
pip install --upgrade texthumanize

# Update to specific version
pip install texthumanize==0.8.0
```

#### From source (GitHub)

```bash
cd TextHumanize
git pull origin main
pip install -e .
```

#### PHP

```bash
# Via Composer
composer require ksanyok/text-humanize

# Если пакет не на Packagist — добавьте VCS-репозиторий:
composer config repositories.texthumanize vcs https://github.com/ksanyok/TextHumanize
composer require ksanyok/text-humanize:^0.11

# Или обновите из исходников
cd php/
git pull origin main
composer install
```

#### TypeScript / JavaScript

```bash
# Via npm (if published to npm)
npm install texthumanize@latest

# From source
cd js/
git pull origin main
npm install && npm run build
```

#### Install specific release from GitHub

```bash
# Python — install directly from a GitHub release tag
pip install git+https://github.com/ksanyok/TextHumanize.git@v0.8.0

# Or download a release archive
pip install https://github.com/ksanyok/TextHumanize/archive/refs/tags/v0.8.0.tar.gz
```

> **Tip:** Pin your version in `requirements.txt` for reproducible builds:
> ```
> texthumanize @ git+https://github.com/ksanyok/TextHumanize.git@v0.8.0
> ```

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
    lang="en",             # auto-detect or specify
    profile="web",         # chat, web, seo, docs, formal, academic, marketing, social, email
    intensity=70,          # 0 (mild) to 100 (maximum)
    target_style="student" # preset: student, copywriter, scientist, journalist, blogger
)
print(result.text)
print(f"Changed: {result.change_ratio:.0%}")
print(f"Quality: {result.quality_score:.2f}")

# Analyze text metrics
report = analyze("Text to analyze for naturalness.", lang="en")
print(f"Artificiality score: {report.artificiality_score:.1f}/100")
print(f"Flesch-Kincaid grade: {report.flesch_kincaid_grade:.1f}")

# Get detailed explanation of changes
result = humanize("Furthermore, it is important to utilize this approach.")
print(explain(result))
```

### All Features at a Glance

```python
from texthumanize import (
    humanize, humanize_batch, humanize_chunked,
    detect_ai, detect_ai_sentences, paraphrase,
    analyze_tone, adjust_tone,
    detect_watermarks, clean_watermarks,
    spin, spin_variants, analyze_coherence, full_readability,
    STYLE_PRESETS, AutoTuner,
)

# AI Detection — 13-metric ensemble, no ML
ai = detect_ai("Text to check for AI generation.", lang="en")
print(f"AI probability: {ai['score']:.0%} | Verdict: {ai['verdict']}")
print(f"Confidence: {ai['confidence']:.0%}")

# Per-sentence AI detection
for s in detect_ai_sentences("First sentence. Second sentence.", lang="en"):
    print(f"  {s['label']}: {s['text'][:60]}...")

# Paraphrasing — syntactic transformations
print(paraphrase("The system works efficiently.", lang="en"))

# Tone Analysis — 7-level formality scale
tone = analyze_tone("Please submit the documentation.", lang="en")
print(f"Tone: {tone['primary_tone']}, formality: {tone['formality']:.2f}")

# Tone Adjustment
casual = adjust_tone("It is imperative to proceed.", target="casual", lang="en")
print(casual)

# Watermark Cleaning — zero-width chars, homoglyphs, steganography
clean = clean_watermarks("Te\u200bxt wi\u200bth hid\u200bden chars")
print(clean)

# Text Spinning — generate unique variants
unique = spin("The system provides important data.", lang="en")
variants = spin_variants("Original text.", count=5, lang="en")

# Coherence Analysis
coh = analyze_coherence("First part.\n\nSecond part.\n\nConclusion.", lang="en")
print(f"Coherence: {coh['overall']:.2f}")

# Style Presets
result = humanize(text, target_style="copywriter")  # student | scientist | journalist | blogger

# Auto-Tuner — learns optimal parameters
tuner = AutoTuner(history_path="history.json")
intensity = tuner.suggest_intensity(text, lang="en")
result = humanize(text, intensity=intensity)
tuner.record(result)

# Batch processing
results = humanize_batch(["Text 1", "Text 2", "Text 3"], lang="en", max_workers=4)

# Large documents — splits at paragraph boundaries
result = humanize_chunked(large_document, chunk_size=3000, lang="ru")

# Full readability — 6 indices
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

### `humanize_batch(texts, **options)`

Process multiple texts in a single call. Each text gets a unique seed (`base_seed + index`) for reproducibility.

```python
from texthumanize import humanize_batch

texts = [
    "Furthermore, it is important to note...",
    "Additionally, it should be mentioned...",
    "Moreover, one must consider...",
]
results = humanize_batch(texts, lang="en", profile="web", seed=42)

for r in results:
    print(f"Similarity: {r.similarity:.2f}, Quality: {r.quality_score:.2f}")
    print(r.text)
```

**Returns:** `list[HumanizeResult]`.

### `HumanizeResult` Properties

| Property | Type | Description |
|---|---|---|
| `text` | `str` | Processed text |
| `original` | `str` | Original text |
| `change_ratio` | `float` | Word-level change ratio (0..1) |
| `similarity` | `float` | Jaccard similarity original vs processed (0..1) |
| `quality_score` | `float` | Overall quality balancing change and preservation (0..1) |
| `changes` | `list` | List of changes made |

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

Detect AI-generated text using 13 independent statistical metrics with ensemble boosting, without any ML dependencies.

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

## v0.15.0 — New Modules & APIs

### `humanize_ai(text, lang, **options)`

Three-tier AI-powered humanization: OpenAI → OSS model → built-in rules.

```python
from texthumanize import humanize_ai

# Default: uses built-in rules (zero dependencies)
result = humanize_ai("AI-generated text here.", lang="en")
print(result.text)

# With OpenAI API (best quality):
result = humanize_ai(
    "Text to humanize.",
    lang="en",
    openai_api_key="sk-...",
    openai_model="gpt-4o-mini",
)

# With OSS model (free, rate-limited):
result = humanize_ai("Text to humanize.", lang="en", enable_oss=True)
```

### `StatisticalDetector` — ML-based AI Detection

35-feature classifier with logistic regression, integrated into `detect_ai()`.

```python
from texthumanize import StatisticalDetector, detect_ai_statistical

# Standalone usage
det = StatisticalDetector(lang="en")
result = det.detect("Text to analyze for AI patterns.")
print(f"Probability: {result['probability']:.1%}")
print(f"Verdict: {result['verdict']}")  # human / mixed / ai

# Or convenience function
result = detect_ai_statistical("Your text here.", lang="en")
```

### `POSTagger` — Rule-based POS Tagging

Part-of-speech tagger for EN (500+ exceptions), RU/UK (200+), DE (300+).

```python
from texthumanize import POSTagger

tagger = POSTagger(lang="en")
for word, tag in tagger.tag("The quick brown fox jumps"):
    print(f"{word:12s} → {tag}")
# The          → DET
# quick        → ADJ
# brown        → ADJ
# fox          → NOUN
# jumps        → VERB
```

### `CJKSegmenter` — Chinese/Japanese/Korean Word Segmentation

```python
from texthumanize import CJKSegmenter, is_cjk_text, detect_cjk_lang

seg = CJKSegmenter(lang="zh")
words = seg.segment("我们是中国人")  # ['我们', '是', '中国', '人']

is_cjk_text("这是中文")      # True
detect_cjk_lang("東京は大きい")  # "ja"
```

### `SyntaxRewriter` — Sentence-level Transforms

8 transformations: active↔passive, clause inversion, enumeration reorder, adverb migration, etc.

```python
from texthumanize import SyntaxRewriter

sr = SyntaxRewriter(lang="en", seed=42)
variants = sr.rewrite("The team completed the project on time.")
for v in variants:
    print(v)
```

### `WordLanguageModel` — Word-level Perplexity

14-language word-level unigram/bigram LM with naturalness scoring.

```python
from texthumanize import WordLanguageModel, word_perplexity, word_naturalness

lm = WordLanguageModel(lang="en")
pp = lm.perplexity("Some text to measure complexity")
score = lm.naturalness_score("Your multi-sentence text here. Another one.")
print(f"Verdict: {score['verdict']}")  # human / mixed / ai

# Convenience:
pp = word_perplexity("Quick check.", lang="en")
ns = word_naturalness("Full analysis.", lang="en")
```

### `CollocEngine` — Collocation-Aware Synonym Ranking

PMI-based scoring for choosing the most natural synonym in context.

```python
from texthumanize import CollocEngine

eng = CollocEngine(lang="en")
best = eng.best_synonym("important", ["crucial", "key", "significant"], context=["decision"])
print(best)  # "crucial" (strongest collocation with "decision")
```

### `FingerprintRandomizer` — Anti-Detection Diversity

Prevents detectable patterns in humanized output.

```python
from texthumanize import FingerprintRandomizer

r = FingerprintRandomizer(seed=42, jitter_level=0.3)
text1 = r.diversify_output("Some humanized text.")
text2 = r.diversify_output("Some humanized text.")  # different each time
```

### `BenchmarkSuite` — Quality Measurement

6-dimension automated quality benchmarking.

```python
from texthumanize import BenchmarkSuite, quick_benchmark

# Quick single-pair benchmark:
report = quick_benchmark("Original AI text.", "Humanized version.")
print(report.summary())

# Full suite:
suite = BenchmarkSuite(lang="en")
report = suite.run_all([
    {"original": "AI text 1.", "humanized": "Human text 1."},
    {"original": "AI text 2.", "humanized": "Human text 2."},
])
print(f"Overall score: {report.overall_score:.1f}/100")
```

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
watermark → segmentation → typography → debureaucratization → structure →
repetitions → liveliness → universal → naturalization → validation → restore
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

TextHumanize uses a **17-stage pipeline** with adaptive intensity:

```
Input Text
  │
  ├─ 0.  Watermark Cleaning       ─ remove zero-width chars, homoglyphs    [auto]
  │
  ├─ 1.  Segmentation             ─ protect code blocks, URLs, emails, brands
  │
  ├─ 1b. CJK Segmentation         ─ word-boundary injection for CJK text   [auto, zh/ja/ko]
  │
  ├─ 2.  Typography               ─ normalize dashes, quotes, ellipses, punctuation
  │
  ├─ 3.  Debureaucratization      ─ replace bureaucratic/formal words     [dictionary, 15% budget]
  │
  ├─ 4.  Structure                ─ diversify sentence openings            [dictionary]
  │
  ├─ 5.  Repetitions              ─ reduce word/phrase repetitions          [dictionary + context + morphology]
  │
  ├─ 6.  Liveliness               ─ inject natural phrasing                [dictionary]
  │
  ├─ 7.  Paraphrasing             ─ semantic sentence-level transforms     [syntax trees]
  │
  ├─ 7b. Syntax Rewriting         ─ structural sentence transforms         [POS-tagged]
  │
  ├─ 8.  Tone Harmonization       ─ align tone consistency                 [context-aware]
  │
  ├─ 9.  Universal                ─ statistical processing                 [any language]
  │
  ├─ 10. Naturalization           ─ burstiness, perplexity, rhythm         [KEY STAGE, collocation-aware]
  │
  ├─ 10b.Word LM Quality Gate     ─ perplexity check, rollback if degraded [advisory]
  │
  ├─ 11. Readability Optimization ─ improve sentence readability           [adaptive]
  │
  ├─ 12. Grammar Correction       ─ fix grammar issues                     [rule-based]
  │
  ├─ 13. Coherence Repair         ─ repair paragraph flow & transitions    [context-aware]
  │
  ├─ 13b.Fingerprint Diversify    ─ anti-fingerprint micro-variations      [typography]
  │
  ├─ 14. Validation               ─ quality check, graduated retry
  │
  └─ 15. Restore                  ─ restore protected segments
  │
Output Text
```

### Adaptive Intensity

The pipeline automatically adjusts processing based on how "AI-like" the input is:

| AI Score | Behavior | Why |
|:---------|:---------|:----|
| ≤ 5% | **Typography only** — skips all semantic stages | Text is already natural, don't touch it |
| ≤ 10% | Intensity × 0.2 | Very light touch needed |
| ≤ 15% | Intensity × 0.35 | Minor adjustments |
| ≤ 25% | Intensity × 0.5 | Moderate processing |
| > 25% | Full intensity | Text needs substantial work |

### Graduated Retry

If processing exceeds `max_change_ratio`, the pipeline automatically retries at lower intensity (×0.4, then ×0.15) instead of discarding all changes. This ensures maximum quality within constraints.

**Stages 3–6** require full dictionary support (14 languages).
**Stages 2, 7–9** work for any language, including those without dictionaries.
**Stage 14** validates quality and retries if needed (configurable via `max_change_ratio`).

---

## AI Detection — How It Works

TextHumanize includes a **production-grade AI text detector** that rivals commercial solutions like GPTZero and Originality.ai — but runs **100% locally**, requires **no API key**, and has **zero dependencies**.

### Architecture

The detector uses a **3-layer ensemble** of 13 independent statistical metrics. No machine learning models, no neural networks, no external APIs.

```
                          ┌─────────────────────────┐
                          │    13 Metric Analyzers   │
                          │  (each produces 0.0–1.0) │
                          └────────────┬────────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    ▼                  ▼                  ▼
            ┌──────────────┐  ┌───────────────┐  ┌──────────────┐
            │ Weighted Sum │  │ Strong Signal │  │   Majority   │
            │   (50%)      │  │  Detector     │  │   Voting     │
            │              │  │   (30%)       │  │   (20%)      │
            └──────┬───────┘  └───────┬───────┘  └──────┬───────┘
                   │                  │                  │
                   └──────────────────┼──────────────────┘
                                      ▼
                              ┌──────────────┐
                              │  Final Score  │
                              │  + Verdict    │
                              │  + Confidence │
                              └──────────────┘
```

### The 13 Metrics

| # | Metric | What It Detects | Weight | How It Works |
|:-:|:-------|:----------------|:------:|:-------------|
| 1 | **AI Patterns** | "it is important to note", "furthermore", etc. | 20% | 100+ formulaic phrase patterns per language |
| 2 | **Burstiness** | Sentence length uniformity | 14% | Coefficient of variation — humans vary, AI doesn't |
| 3 | **Opening Diversity** | Repetitive sentence starts | 9% | Unique first-word ratio across sentences |
| 4 | **Entropy** | Word predictability | 8% | Shannon entropy of word distribution |
| 5 | **Stylometry** | Word length consistency | 8% | Std deviation of character counts per word |
| 6 | **Coherence** | Paragraph transitions | 8% | Lexical overlap and connector analysis |
| 7 | **Vocabulary** | Lexical richness | 7% | Type-to-token ratio (unique vs total words) |
| 8 | **Grammar Perfection** | Suspiciously perfect grammar | 6% | 9 indicators: Oxford commas, fragments, etc. |
| 9 | **Punctuation** | Punctuation diversity | 6% | Distribution of , ; : ! ? — across text |
| 10 | **Rhythm** | Syllabic patterns | 6% | Syllable-per-word variation across sentences |
| 11 | **Perplexity** | Character-level predictability | 6% | Trigram model with Laplace smoothing |
| 12 | **Readability** | Reading level consistency | 5% | Variance of readability across paragraphs |
| 13 | **Zipf** | Word frequency distribution | 3% | Log-log linear regression with R² fit |

### Ensemble Boosting

Three classifiers vote on the final score:

1. **Weighted Sum (50%)** — classic weighted average of all 13 metrics
2. **Strong Signal Detector (30%)** — triggers when any single metric is extremely high (>0.85) — catches obvious AI even when the average is moderate
3. **Majority Voting (20%)** — counts how many metrics individually vote "AI" (>0.5) — robust against outlier metrics

### Confidence Scoring

Confidence reflects how reliable the verdict is:

| Factor | Weight | Description |
|:-------|:------:|:------------|
| Text length | 35% | Longer text = more reliable analysis |
| Metric agreement | 20% | Higher when all metrics agree |
| Extreme bonus | — | +0.6 × distance from 0.5 midpoint |
| Agreement ratio | 25% | What fraction of metrics agree on AI/human |

### Verdicts

| Score | Verdict | Interpretation |
|:-----:|:--------|:---------------|
| < 35% | `human_written` | Text appears naturally written |
| 35–65% | `mixed` | Uncertain — partially AI or heavily edited |
| ≥ 65% | `ai_generated` | Strong AI patterns detected |

### Benchmark Results

Tested on a curated benchmark of 11 labeled samples (5 AI, 5 human, 1 mixed):

```
┌──────────────────────────────────────────────┐
│          AI Detection Benchmark              │
├──────────────────┬───────────────────────────┤
│ Accuracy         │ 100%                      │
│ Precision        │ 100%                      │
│ Recall           │ 100%                      │
│ F1 Score         │ 1.000                     │
│ True Positives   │ 5                         │
│ False Positives  │ 0                         │
│ True Negatives   │ 5                         │
│ False Negatives  │ 0                         │
│ Mixed (correct)  │ 1/1                       │
└──────────────────┴───────────────────────────┘
```

### Detection Modes

```python
from texthumanize import detect_ai, detect_ai_batch, detect_ai_sentences, detect_ai_mixed

# Standard detection
result = detect_ai("Your text here.", lang="en")
print(f"AI: {result['score']:.0%} | {result['verdict']} | Confidence: {result['confidence']:.0%}")

# Per-metric breakdown
for name, score in result['metrics'].items():
    bar = "█" * int(score * 20)
    print(f"  {name:30s} {score:.2f} {bar}")

# Human-readable explanations
for exp in result['explanations']:
    print(f"  → {exp}")

# Batch detection — process many texts at once
results = detect_ai_batch(["Text 1", "Text 2", "Text 3"])

# Per-sentence detection — find AI sentences in mixed content
sentences = detect_ai_sentences(mixed_text)
for s in sentences:
    emoji = "🤖" if s['label'] == 'ai' else "👤"
    print(f"  {emoji} {s['text'][:80]}...")

# Mixed content analysis
report = detect_ai_mixed(text_with_ai_and_human_parts)
```

### Example: AI vs Human

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
print(f"Score: {result['score']:.0%}")   # → ~87-89% — AI detected
print(f"Verdict: {result['verdict']}")   # → "ai_generated"

# Human-written casual text
human_text = """
I tried that new coffee shop downtown yesterday. Their espresso was 
actually decent - not as burnt as the place on 5th. The barista 
was nice too, recommended this Ethiopian blend I'd never heard of. 
Might go back this weekend.
"""
result = detect_ai(human_text, lang="en")
print(f"Score: {result['score']:.0%}")   # → ~20-27% — Human confirmed
print(f"Verdict: {result['verdict']}")   # → "human_written"
```

### Comparison with Commercial Detectors

| Feature | TextHumanize | GPTZero | Originality.ai |
|:--------|:------------:|:-------:|:--------------:|
| Works offline | ✅ | ❌ | ❌ |
| Free | ✅ | Freemium | $14.95/mo |
| API key required | ❌ | ✅ | ✅ |
| Languages | 14 | ~5 | English-focused |
| Metrics | 13 | Undisclosed | Undisclosed |
| Per-sentence breakdown | ✅ | ✅ | ❌ |
| Batch detection | ✅ | ✅ | ✅ |
| Self-hosted | ✅ | ❌ | ❌ |
| Reproducible | ✅ | ❌ | ❌ |
| Mixed content analysis | ✅ | ✅ | ❌ |
| Zero dependencies | ✅ | Cloud-based | Cloud-based |

### Tips for Best Results

- **100+ words** — best accuracy for texts of substantial length
- **Short texts** (< 50 words) — results may be less reliable
- **Formal texts** — may score slightly higher even if human-written (expected behavior for legal, academic style)
- **Multiple metrics** — the ensemble approach helps even when individual signals are weak

---

## Language Support

### Full Dictionary Support (14 languages)

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

| Language | Code | Bureaucratic | Connectors | Synonyms | AI Words | Abbreviations |
|----------|:----:|:-----:|:------:|:------:|:------:|:------:|
| Russian | `ru` | 70+ | 25+ | 50+ | 30+ | 15+ |
| Ukrainian | `uk` | 50+ | 24 | 48 | 25+ | 12+ |
| English | `en` | 40+ | 25 | 35+ | 24+ | 20+ |
| German | `de` | 64 | 20 | 45 | 38 | 10+ |
| French | `fr` | 20 | 12 | 20 | 15+ | 8+ |
| Spanish | `es` | 18 | 12 | 18 | 15+ | 8+ |
| Polish | `pl` | 18 | 12 | 18 | 15+ | 8+ |
| Portuguese | `pt` | 16 | 12 | 17 | 12+ | 6+ |
| Italian | `it` | 16 | 12 | 17 | 12+ | 6+ |
| Arabic | `ar` | 81 | 49 | 80 | 40+ | 47 |
| Chinese | `zh` | 80 | 36 | 80 | 40+ | 32 |
| Japanese | `ja` | 60+ | 30+ | 60+ | 30+ | 25+ |
| Korean | `ko` | 60+ | 30+ | 60+ | 30+ | 25+ |
| Turkish | `tr` | 60+ | 30+ | 60+ | 30+ | 25+ |

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

## Perplexity Analysis

Character-level trigram cross-entropy model for measuring text naturalness — fully offline, no ML dependencies.

```python
from texthumanize import perplexity_score, cross_entropy

# Quick cross-entropy measurement
ce = cross_entropy("The quick brown fox jumps over the lazy dog.", lang="en")
print(f"Cross-entropy: {ce:.2f} bits")

# Full analysis with naturalness score and verdict
result = perplexity_score(
    "It is important to note that AI-generated text tends to be uniform.",
    lang="en",
)
print(f"Naturalness: {result['naturalness']}/100")
print(f"Verdict: {result['verdict']}")  # "human", "mixed", or "ai"
print(f"Burstiness: {result['burstiness_score']:.2f}")
```

| Return Field | Description |
|---|---|
| `cross_entropy` | Bits per character against language model |
| `perplexity` | 2^cross_entropy — lower = more predictable |
| `local_variance` | Entropy variance across text windows |
| `burstiness_score` | Human-like variability (higher = more natural) |
| `naturalness` | Score 0–100 (100 = fully natural) |
| `verdict` | `"human"`, `"mixed"`, `"ai"`, or `"unknown"` |

---

## Plagiarism Detection

Offline originality analysis via n-gram fingerprinting and self-similarity scoring.

```python
from texthumanize import check_originality, compare_originality

# Check text originality (self-repetition analysis)
report = check_originality(
    "Your text here...",
    reference_texts=["Optional reference corpus..."],
)
print(f"Originality: {report.originality_score}%")
print(f"Verdict: {report.verdict}")  # "original", "moderate_overlap", "high_overlap"
print(f"Fingerprint: {report.fingerprint_hash}")

# Compare humanized output against original
divergence = compare_originality(
    "The humanized version of the text.",
    "The original AI-generated text.",
)
print(f"Divergence: {divergence['divergence']:.1%}")
print(f"Sufficiently different: {divergence['is_sufficiently_different']}")
```

---

## Dictionary Training

Analyze a corpus to detect overused AI phrases and build custom replacement dictionaries.

```python
from texthumanize import train_from_corpus, export_custom_dict

# Analyze your text corpus
texts = [
    "Furthermore, it is important to note that...",
    "Moreover, the results clearly demonstrate...",
    # ... more texts
]
result = train_from_corpus(texts, lang="en", min_frequency=2)

print(f"Overused phrases: {result.overused_phrases}")
print(f"AI patterns found: {len(result.repeated_patterns)}")
print(f"Type-token ratio: {result.vocabulary_stats['type_token_ratio']:.2f}")

# Export as custom dictionary for humanize()
custom_dict = export_custom_dict(result)
from texthumanize import humanize
r = humanize("Your text...", custom_dict=custom_dict)
```

---

## Sentence-Level Humanization

Process text at sentence granularity — only rewrite sentences that score above an AI probability threshold.

```python
from texthumanize import humanize_sentences

result = humanize_sentences(
    "Human-written intro. AI-generated middle part. Another natural sentence.",
    lang="en",
    ai_threshold=0.6,    # Only process sentences with >60% AI probability
    intensity=70,
)

print(f"Kept human: {result['human_kept']} sentences")
print(f"Processed AI: {result['ai_processed']} sentences")
for s in result["sentences"]:
    print(f"  [{s['action']}] {s['original'][:50]}... → AI: {s['ai_probability']:.0%}")
```

---

## Multi-Variant Output

Generate multiple humanization variants and pick the best one.

```python
from texthumanize import humanize_variants

variants = humanize_variants(
    "AI-generated text to humanize.",
    lang="en",
    variants=5,     # Generate 5 different versions
    seed=42,        # Reproducible base seed
)

# Results sorted by quality (best first)
for v in variants:
    print(f"Variant {v['variant_id']}: score={v['ai_score']:.2f}, "
          f"changes={v['change_ratio']:.0%}")
    print(f"  {v['text'][:80]}...")
```

---

## Streaming API

Process large texts chunk-by-chunk with progress tracking.

```python
from texthumanize import humanize_stream

for chunk in humanize_stream("Very long text...", lang="en"):
    print(f"[{chunk['progress']:.0%}] {chunk['chunk'][:60]}...")
    if chunk["is_last"]:
        print("Done!")
```

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

## Style Presets

*New in v0.8.0*

Target a specific writing style using preset fingerprints. The pipeline adapts sentence length, vocabulary complexity, and punctuation patterns to match the chosen persona — producing output that reads like it was written by a real student, journalist, or scientist.

```python
from texthumanize import humanize, STYLE_PRESETS

# Just pass a string — that's it
result = humanize(text, target_style="student")

# Or use the fingerprint object directly
result = humanize(text, target_style=STYLE_PRESETS["scientist"])

# Custom fingerprint from your own writing sample
from texthumanize import StylisticAnalyzer
analyzer = StylisticAnalyzer(lang="en")
my_style = analyzer.extract(my_writing_sample)
result = humanize(text, target_style=my_style)
```

### Available Presets

| Preset | Avg Sentence | Sentence Variance | Vocabulary Richness | Complex Words | Best For |
|:-------|:------------:|:-----------------:|:-------------------:|:-------------:|:---------|
| 🎓 `student` | 14 words | σ=6 | 65% | 25% | Essays, homework, coursework |
| ✍️ `copywriter` | 12 words | σ=8.5 | 72% | 20% | Marketing copy, ads, landing pages |
| 🔬 `scientist` | 22 words | σ=7 | 70% | 55% | Research papers, dissertations |
| 📰 `journalist` | 16 words | σ=7.5 | 72% | 35% | News articles, reports, features |
| 💬 `blogger` | 11 words | σ=7 | 60% | 12% | Blog posts, social media, casual writing |

### How It Works

1. The preset defines a **stylistic fingerprint** — a vector of text metrics (sentence length mean/std, vocabulary richness, complex word ratio)
2. After the main pipeline processes text, the **stylistic alignment stage** adjusts output to match the target fingerprint
3. Sentences are split, merged, or reorganized to match the target distribution
4. The result reads naturally in the target style while preserving original meaning

---

## Auto-Tuner (Feedback Loop)

*New in v0.8.0*

The Auto-Tuner learns optimal processing parameters from your history. Instead of guessing the right intensity, let it figure it out from data.

```python
from texthumanize import humanize, AutoTuner

# Create tuner with persistent storage
tuner = AutoTuner(history_path="~/.texthumanize_history.json", max_records=500)

# Process & record
for text in my_texts:
    intensity = tuner.suggest_intensity(text, lang="en")  # Smart suggestion
    result = humanize(text, lang="en", intensity=intensity)
    tuner.record(result)  # Learn from this result

# After 10+ records, suggestions become data-driven
params = tuner.suggest_params(lang="en")
print(f"Optimal intensity: {params.intensity}")
print(f"Max change ratio: {params.max_change_ratio:.2f}")
print(f"Confidence: {params.confidence:.0%}")

# Review accumulated statistics
stats = tuner.summary()
# → {"total_records": 47, "avg_quality": 0.78, "avg_ai_reduction": 42, ...}

# Reset if needed
tuner.reset()
```

### How It Works

1. Each `record()` call saves: language, profile, intensity, AI score before/after, change ratio, quality score, timestamp
2. `suggest_intensity()` groups historical records by intensity bucket (10, 20, 30, ..., 100)
3. For each bucket, it computes average quality score
4. Returns the intensity with the highest average quality
5. Confidence increases from 0 to 1 as more data accumulates (10+ records per bucket = full confidence)

---

## Stylistic Fingerprinting

*New in v0.7.0+*

Extract and compare writing styles using statistical fingerprints. Use this to match AI-generated text to your personal writing style, or compare two texts for stylistic similarity.

```python
from texthumanize import StylisticAnalyzer, StylisticFingerprint

# Extract fingerprint from a writing sample
analyzer = StylisticAnalyzer(lang="en")
my_style = analyzer.extract(my_writing_sample)

# Fingerprint contains:
print(f"Avg sentence length: {my_style.sent_len_mean:.1f} words")
print(f"Sentence length std: {my_style.sent_len_std:.1f}")
print(f"Complex word ratio: {my_style.complex_ratio:.2f}")
print(f"Vocabulary richness: {my_style.vocabulary_richness:.2f}")

# Compare two styles (cosine similarity)
similarity = my_style.similarity(other_style)
print(f"Style match: {similarity:.1%}")

# Use as target for humanization
result = humanize(ai_text, target_style=my_style)
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

All benchmarks on Apple Silicon (M1 Pro), Python 3.12, single thread. Reproducible via `python3 benchmarks/full_benchmark.py`.

### Processing Speed

| Text Size | Humanize Time | AI Detection Time | Throughput |
|-----------|:-------------:|:-----------------:|:----------:|
| 100 words (~900 chars) | ~24ms | ~2ms | ~38,000 chars/sec |
| 500 words (~3,600 chars) | ~138ms | ~6ms | ~26,000 chars/sec |
| 1,000 words (~6,000 chars) | ~213ms | ~9ms | ~28,000 chars/sec |

### Quality Benchmark

Tested on 45 curated samples across 14 languages, multiple profiles, and edge cases:

```
┌──────────────────────────────────────────────────┐
│          TextHumanize Quality Benchmark           │
├────────────────────┬─────────────────────────────┤
│ Pass rate          │ 100% (45/45)                │
│ Avg quality score  │ 0.75                        │
│ Avg speed          │ 51,459 chars/sec            │
│ Issues found       │ 0                           │
│ Languages tested   │ 9                           │
│ Profiles tested    │ 9                           │
└────────────────────┴─────────────────────────────┘
```

### Predictability (Determinism)

TextHumanize is fully deterministic — the core corporate requirement:

```python
result1 = humanize(text, seed=12345)
result2 = humanize(text, seed=12345)
assert result1.text == result2.text  # Always True
```

| Property | Value |
|----------|:-----:|
| Same seed → identical output | ✅ Always |
| Different seed → different output | ✅ Always |
| No network calls | ✅ |
| No randomness from external sources | ✅ |

### Memory Usage

| Scenario | Memory |
|----------|:------:|
| Base import | ~2 MB |
| Processing 30K chars | ~2.5 MB peak |
| No model files to load | ✅ |

### Change Report (explain)

Every `humanize()` call returns a structured result with full audit trail:

```python
result = humanize(text, seed=42, profile="web")
print(result.change_ratio)   # 0.15 — 15% of words changed
print(result.quality_score)  # 0.85 — quality score 0..1
print(result.similarity)     # 0.87 — Jaccard similarity with original

# Full human-readable report
print(explain(result))
# === Report ===
# Language: en | Profile: web | Intensity: 60
# Change ratio: 15.0%
# --- Metrics ---
#   Artificiality: 57.2 → 46.1 ↓
#   Bureaucratisms: 0.18 → 0.05 ↓
#   AI connectors: 0.12 → 0.00 ↓
# --- Changes (5) ---
#   [debureaucratize] "implementation" → "setup"
#   [debureaucratize] "utilization" → "use"
#   ...
```

---

## Testing

### Test Suite Overview

| Platform | Tests | Status | Time |
|:---------|------:|:------:|:-----|
| **Python** | 1,333 | ✅ All passing | ~1.5s |
| **PHP** | 223 | ✅ All passing | ~2s |
| **TypeScript** | 28 | ✅ All passing | ~1s |
| **Total** | **1,584** | ✅ | — |

```bash
# Run all Python tests
pytest -q                           # 1333 passed in 1.53s

# With coverage report
pytest --cov=texthumanize --cov-report=term-missing

# Lint + type check
ruff check texthumanize/            # 0 errors
mypy texthumanize/                  # 0 errors

# Pre-commit hooks
pre-commit run --all-files

# PHP tests
cd php && php vendor/bin/phpunit    # 223 tests, 825 assertions

# TypeScript tests
cd js && npx vitest run             # 28 tests
```

### Coverage Summary (Python)

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
| stylistic.py | 95% |
| autotune.py | 92% |
| detectors.py | 90% |
| utils.py | 90% |
| repetitions.py | 88% |
| structure.py | 88% |
| paraphrase.py | 87% |
| watermark.py | 87% |
| context.py | 90% |
| liveliness.py | 86% |
| validator.py | 86% |
| pipeline.py | 92% |
| cli.py | 85% |
| lang/ | 100% |
| **Overall** | **99%** |

---

## Architecture

```
texthumanize/                   # 72 Python modules, 40,677 lines
├── __init__.py                 # Public API: 25 functions + 5 classes
├── core.py                     # Facade: humanize(), analyze(), detect_ai(), etc.
├── api.py                      # REST API: zero-dependency HTTP server, 12 endpoints
├── cli.py                      # CLI: 15+ commands
├── pipeline.py                 # 17-stage pipeline + adaptive intensity + graduated retry
│
├── analyzer.py                 # Artificiality scoring + 6 readability metrics
├── tokenizer.py                # Paragraph/sentence/word tokenization
├── sentence_split.py           # Smart sentence splitter (abbreviations, decimals)
│
├── segmenter.py                # Code/URL/email/brand protection (stage 1)
├── cjk_segmenter.py            # CJK word segmentation — zh/ja/ko (stage 1b)
├── normalizer.py               # Typography normalization (stage 2)
├── decancel.py                 # Debureaucratization + 15% budget + echo check (stage 3)
├── structure.py                # Sentence structure diversification (stage 4)
├── repetitions.py              # Repetition reduction + morphology (stage 5)
├── liveliness.py               # Natural phrasing injection (stage 6)
├── paraphraser_ext.py          # Semantic paraphrasing — syntax trees (stage 7)
├── syntax_rewriter.py          # Structural sentence transforms — POS-tagged (stage 7b)
├── tone_harmonizer.py          # Tone harmonization (stage 8)
├── universal.py                # Universal processor — any language (stage 9)
├── naturalizer.py              # Key stage: burstiness, perplexity, collocation-aware synonyms (stage 10)
├── word_lm.py                  # Word language model — perplexity quality gate (stage 10b)
├── readability_opt.py          # Readability optimization (stage 11)
├── grammar_fix.py              # Grammar correction (stage 12)
├── coherence_repair.py         # Coherence repair (stage 13)
├── fingerprint_randomizer.py   # Anti-fingerprint diversification (stage 13b)
├── validator.py                # Quality validation + graduated retry (stage 14)
│
├── detectors.py                # AI detector: 13 metrics + ensemble boosting
├── statistical_detector.py     # Statistical AI detection (feature weights + ensemble)
├── pos_tagger.py               # Rule-based POS tagger (en/de/ru/uk)
├── collocation_engine.py       # Collocation scoring — context-aware synonym ranking
├── benchmark_suite.py          # Benchmarking suite — quality metrics
├── ai_backend.py               # AI backend — OpenAI + OSS Gradio providers
│
├── paraphrase.py               # Syntactic paraphrasing engine
├── tone.py                     # Tone analysis & adjustment (7 levels)
├── watermark.py                # Watermark detection & cleaning (5 types)
├── spinner.py                  # Text spinning & spintax generation
├── coherence.py                # Coherence & paragraph flow analysis
├── morphology.py               # Morphological engine (RU/UK/EN/DE)
├── context.py                  # Context-aware synonyms (WSD + negative collocations)
├── stylistic.py                # Stylistic fingerprinting + presets
├── autotune.py                 # Auto-Tuner (feedback loop + JSON persistence)
│
├── lang_detect.py              # Language detection (14 languages)
├── utils.py                    # Options, profiles, result classes
├── __main__.py                 # python -m texthumanize
│
└── lang/                       # Language packs (data only, no logic)
    ├── __init__.py             # Registry + fallback
    ├── ru.py                   # Russian (70+ bureaucratic, 50+ synonyms)
    ├── uk.py                   # Ukrainian (50+ bureaucratic, 48 synonyms)
    ├── en.py                   # English (40+ bureaucratic, 35+ synonyms)
    ├── de.py                   # German (64 bureaucratic, 45 synonyms, 38 AI words)
    ├── fr.py                   # French
    ├── es.py                   # Spanish
    ├── pl.py                   # Polish
    ├── pt.py                   # Portuguese
    ├── it.py                   # Italian
    ├── ar.py                   # Arabic (81 bureaucratic, 80 synonyms)
    ├── zh.py                   # Chinese Simplified (80 bureaucratic, 80 synonyms)
    ├── ja.py                   # Japanese (keigo→casual register)
    ├── ko.py                   # Korean (honorific→casual register)
    └── tr.py                   # Turkish (Ottoman→modern Turkish)
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

## TypeScript / JavaScript Port

The `js/` directory contains a TypeScript port of the core pipeline with full processing stages:

```typescript
import { humanize, analyze } from 'texthumanize';

const result = humanize('Text to process', { lang: 'en', intensity: 60 });
console.log(result.text);
console.log(`Changed: ${(result.changeRatio * 100).toFixed(0)}%`);

const report = analyze('Text to check');
console.log(`AI score: ${report.artificialityScore}%`);
```

### JS/TS Modules

| Module | Description |
|:-------|:------------|
| `pipeline.ts` | Full 11-stage pipeline with adaptive intensity |
| `normalizer.ts` | Typography normalization (dashes, quotes, spacing) |
| `debureaucratizer.ts` | Bureaucratic word replacement with seeded PRNG |
| `naturalizer.ts` | AI word replacement, burstiness, connectors |
| `analyzer.ts` | Text analysis and artificiality scoring |
| `detector.ts` | AI detection with statistical metrics |
| `segmenter.ts` | Code/URL/email protection |

Features:
- **Seeded PRNG** (xoshiro128**) — reproducible results
- **Adaptive intensity** — same algorithm as Python (AI ≤ 5% → typography only)
- **Graduated retry** — retries at lower intensity if change ratio exceeds limit
- **Cyrillic-safe regex** — lookbehind/lookahead instead of `\b` for Cyrillic support
- **28 tests** (vitest) — all passing, TS compiles clean

```bash
cd js/
npm install
npx vitest run    # 28 tests
npx tsc --noEmit  # type check
```

---

## PHP Library

A full PHP port is available in the `php/` directory — 10,000 lines, 223 tests, 825 assertions.

### PHP Quick Start

```php
<?php
use TextHumanize\TextHumanize;

// Basic usage
$result = TextHumanize::humanize("Text to process", profile: 'web');
echo $result->processed;

// Chunk processing for large texts
$result = TextHumanize::humanizeChunked($longText, chunkSize: 5000);

// AI detection
$ai = TextHumanize::detectAI("Suspicious text", lang: 'en');
echo $ai['verdict'];  // "ai_generated"

// Batch processing
$results = TextHumanize::humanizeBatch([$text1, $text2, $text3]);

// Tone analysis & adjustment
$tone = TextHumanize::analyzeTone("Formal text", lang: 'en');
$casual = TextHumanize::adjustTone("Formal text", target: 'casual');
```

### PHP Modules

| Module | PHP Class | Tests |
|:-------|:----------|:-----:|
| Core Pipeline | `TextHumanize`, `Pipeline` | ✅ |
| AI Detection | `AIDetector` | ✅ |
| Sentence Splitting | `SentenceSplitter` | ✅ |
| Paraphrasing | `Paraphraser` | ✅ |
| Tone Analysis | `ToneAnalyzer` | ✅ |
| Watermark Detection | `WatermarkDetector` | ✅ |
| Content Spinning | `ContentSpinner` | ✅ |
| Coherence Analysis | `CoherenceAnalyzer` | ✅ |
| Language Packs | 14 languages | ✅ |

```bash
cd php/
composer install
php vendor/bin/phpunit  # 223 tests, 825 assertions
```

See [php/README.md](php/README.md) for full PHP documentation.

---

## What's New in v0.8.0

A summary of everything added since v0.5.0:

### v0.8.0 — Style Presets, Auto-Tuner, Semantic Guards

| Feature | Description |
|:--------|:------------|
| 🎭 Style Presets | 5 personas: student, copywriter, scientist, journalist, blogger |
| 📊 Auto-Tuner | Feedback loop — learns optimal intensity from history |
| 🛡️ Semantic Guards | Echo check prevents introducing duplicate words; 20+ context patterns |
| ⚡ Typography fast path | AI ≤ 5% → skip all semantic stages, apply typography only |
| 🟦 JS/TS full pipeline | Normalizer, Debureaucratizer, Naturalizer — full adaptive pipeline |
| 📖 Documentation | API Reference, 14-recipe Cookbook, updated README |
| 🇩🇪 German expanded | Bureaucratic 22→64, synonyms 26→45, AI words 20→38 |
| 🔧 change_ratio fix | SequenceMatcher replaces broken positional comparison |
| ♻️ Graduated retry | Pipeline retries at ×0.4, ×0.15 instead of full rollback |

### v0.7.0 — AI Detection 2.0, C2PA, Streaming

| Feature | Description |
|:--------|:------------|
| 🧠 13th metric | Perplexity score (character-level trigram model) |
| 🎯 Ensemble boosting | 3-classifier aggregation: weighted + strong signal + majority |
| 📈 Benchmark suite | 11 labeled samples, 100% accuracy |
| 🔌 CLI `detect` | `texthumanize detect file.txt --verbose --json` |
| 📡 Streaming callback | `on_progress(index, total, result)` for batch processing |
| 🏷️ C2PA watermarks | Detect content provenance markers (C2PA, IPTC, XMP) |
| 🗣️ Tone: 4 new langs | UK, DE, FR, ES tone replacement pairs |
| 📊 Zipf rewrite | Log-log regression with R² goodness-of-fit |

### v0.6.0 — Batch Processing, Quality Metrics, 99% Coverage

| Feature | Description |
|:--------|:------------|
| 📦 Batch processing | `humanize_batch()` with unique seeds per text |
| 📐 Quality score | Balances sufficient change with meaning preservation |
| 📏 Similarity metric | Jaccard similarity (0..1) original vs processed |
| 🧪 1,255 Python tests | Up from 500, 99% coverage |
| 🐘 223 PHP tests | Up from 30, covering all modules |
| 🔒 mypy clean | 0 type errors across all 38 source files |

### v0.5.0 — Code Quality, Pre-commit, PEP 561

| Feature | Description |
|:--------|:------------|
| 🧹 0 lint errors | 67 ruff errors fixed |
| ✅ PEP 561 | `py.typed` marker for downstream type checkers |
| 🪝 Pre-commit hooks | Ruff lint/format, trailing whitespace, YAML/TOML checks |
| 🔬 conftest.py | 12 reusable pytest fixtures |

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

## FAQ & Troubleshooting

### General

**Q: Does TextHumanize use the internet?**
No. All processing is 100% local. No API calls, no data sent anywhere.

**Q: Does it require GPU or large models?**
No. Pure algorithmic processing using Python standard library only. Starts in <100ms.

**Q: What makes it better than online humanizers?**
Speed (56K chars/sec vs 2-10 seconds), privacy (offline), control (intensity, profiles, seeds), and it's free.

**Q: Which Python versions are supported?**
Python 3.9 through 3.12+ (tested in CI/CD matrix).

### Processing

**Q: My text isn't changing much. Why?**
Increase `intensity` (e.g., 80-100) or use a more aggressive profile like `chat`. The `seo` and `formal` profiles intentionally make fewer changes. Also check if the text already has a low AI score — the adaptive pipeline deliberately reduces changes for natural text.

**Q: How do I target a specific writing style?**
Use `target_style="student"` (or `copywriter`, `scientist`, `journalist`, `blogger`). You can also extract a custom fingerprint from your writing sample with `StylisticAnalyzer`.

**Q: Can I undo changes?**
The `explain(result)` function shows all changes. The original text is always in `result.original`.

**Q: How do I protect specific words from changing?**
Use `constraints={"keep_keywords": ["word1", "word2"]}` or `preserve={"brand_terms": ["Brand"]}`.

### AI Detection

**Q: How accurate is the AI detector?**
100% on our benchmark (11 samples: 5 AI, 5 human, 1 mixed). Uses 13 independent metrics with ensemble boosting. Best results with 100+ words.

**Q: Does it detect ChatGPT/GPT-4/Claude?**
It detects statistical patterns common to all LLMs, not any specific model. Works for GPT-3.5, GPT-4, Claude, Gemini, Llama, etc.

**Q: Can I use the detector and humanizer together?**
Yes — the typical pipeline is: detect (score high) → humanize → detect again (score low).

### Languages

**Q: My language isn't supported.**
Use `lang="xx"` — the universal processor handles typography, sentence variation, and burstiness without dictionaries. Adding a full language pack is easy — just create a file in `texthumanize/lang/`.

### API

**Q: How do I start the REST API?**
```bash
python -m texthumanize.api --port 8080
```

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

## Security & Limits

### Input Limits

| Parameter | Default | Configurable | Notes |
|:----------|:-------:|:------------:|:------|
| Max input length | 500 KB | Yes (`max_input_size`) | Texts above this limit should be processed via chunk API |
| Max sentence length | 5,000 chars | Internal | Sentences exceeding this are passed through unchanged |
| Max paragraph count | None | — | No hard limit; memory usage scales linearly |

### Resource Consumption

- **Memory**: ~2.5 MB peak for a 10 KB text; scales linearly with input size  
- **CPU**: Single-threaded, no background workers or child processes  
- **Disk**: Zero disk I/O during processing (all dictionaries are in-memory)  
- **Network**: Zero network calls. Ever. No telemetry, no analytics, no phone-home  

### Regex Safety (ReDoS)

All regular expressions in the library are:

1. **Bounded** — no unbounded repetitions on overlapping character classes  
2. **Linear-time** — worst-case O(n) execution for any input string  
3. **Fuzz-tested** — CI runs property-based tests with random Unicode strings up to 100 KB  

No user input is ever compiled into a regex pattern.

### Sandboxing Recommendations

For production deployments processing untrusted input:

```python
import resource, signal

# Limit memory to 256 MB
resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024, 256 * 1024 * 1024))

# Limit CPU time to 10 seconds per call
signal.alarm(10)

result = humanize(untrusted_text, lang="en")

signal.alarm(0)  # Cancel alarm after success
```

### Threat Model

| Threat | Mitigation |
|:-------|:-----------|
| Denial of service via large input | Use chunk API or enforce `max_input_size` |
| ReDoS via crafted patterns | All regexes are linear-time; no user input compiled to regex |
| Data exfiltration | Zero network calls; all processing is local |
| Supply-chain attack | Zero runtime dependencies; pure stdlib |
| Non-deterministic output in audit | Seed-based PRNG guarantees reproducibility |

### Testing & Quality Assurance

- **1,584 tests** across Python, PHP, and TypeScript  
- **99% code coverage** (Python)  
- **Property-based fuzzing** with random Unicode, empty strings, extremely long inputs  
- **Golden tests** — reference outputs checked against known-good baselines  
- **CI/CD** — ruff linting + mypy type checking on every commit  

---

## For Business & Enterprise

TextHumanize is designed for production use in corporate environments:

| Corporate Requirement | How TextHumanize Delivers |
|:----------------------|:-------------------------|
| **Predictability** | Seed-based PRNG — same input + seed = identical output. Always. |
| **Privacy & Security** | 100% local processing. Zero network calls. No data leaves your server. |
| **Auditability** | Every call returns `change_ratio`, `quality_score`, `similarity`, and a full `explain()` report of what was changed and why. |
| **Modes** | `normalize` (typography only) · `style_soft` (mild humanization) · `rewrite` (full pipeline). Control via `intensity` (0–100) and `profile` (9 options). |
| **Integration** | Python SDK · TypeScript/JavaScript SDK · PHP SDK · CLI · REST API. Drop into any pipeline. |
| **Reliability** | 1,584 tests across 3 platforms, 99% code coverage, CI/CD with ruff + mypy. |
| **No vendor lock-in** | Zero dependencies. Pure stdlib. No cloud APIs, no API keys, no rate limits. |
| **Language coverage** | 9 full language packs + universal statistical processor for any language. |
| **Licensing** | Clear dual license. [Commercial tiers from $199/year →](COMMERCIAL.md) |

### Processing Modes

```python
# Mode 1: Typography only (normalize) — safest, no semantic changes
result = humanize(text, intensity=5)  # Only fixes quotes, dashes, spaces

# Mode 2: Soft style (style_soft) — light humanization
result = humanize(text, intensity=30, profile="docs")

# Mode 3: Full rewrite — maximum humanization
result = humanize(text, intensity=80, profile="web")

# Every mode returns an audit trail
print(result.change_ratio)   # What % was changed
print(result.quality_score)  # Quality metric
print(explain(result))       # Detailed diff report
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

## License & Pricing

TextHumanize uses a **dual license model**:

| Use Case | License | Cost |
|:---------|:--------|:----:|
| Personal projects | Free License | **Free** |
| Academic / Research | Free License | **Free** |
| Open-source (non-commercial) | Free License | **Free** |
| Evaluation / Testing | Free License | **Free** |
| Commercial — 1 dev, 1 project | Indie | **$199/year** |
| Commercial — up to 5 devs | Startup | **$499/year** |
| Commercial — up to 20 devs | Business | **$1,499/year** |
| Enterprise / On-prem / SLA | Enterprise | [Contact us](mailto:ksanyok@me.com) |

All commercial licenses include full source code, updates for 1 year, and email support.

👉 **[Full licensing details & FAQ →](COMMERCIAL.md)**

See [LICENSE](LICENSE) for the complete legal text.

**Contact:** [ksanyok@me.com](mailto:ksanyok@me.com)

---

<p align="center">
  <a href="https://github.com/ksanyok/TextHumanize">GitHub</a> ·
  <a href="https://github.com/ksanyok/TextHumanize/issues">Issues</a> ·
  <a href="https://github.com/ksanyok/TextHumanize/discussions">Discussions</a> ·
  <a href="COMMERCIAL.md">Commercial License</a>
</p>
