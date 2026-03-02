<div align="center">

# TextHumanize

### The most advanced open-source text naturalization engine

**Normalize style, improve readability, and ensure brand-safe content — offline, private, and blazing fast**

<br/>

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6.svg?logo=typescript&logoColor=white)]()
[![PHP 8.1+](https://img.shields.io/badge/php-8.1+-777BB4.svg?logo=php&logoColor=white)](https://www.php.net/)
&nbsp;&nbsp;
[![CI](https://github.com/ksanyok/TextHumanize/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/ksanyok/TextHumanize/actions/workflows/ci.yml)
[![Tests](https://img.shields.io/badge/tests-1956%20passed-2ea44f.svg?logo=pytest&logoColor=white)](https://github.com/ksanyok/TextHumanize/actions/workflows/ci.yml)
&nbsp;&nbsp;
[![Zero Dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen.svg)]()
[![License](https://img.shields.io/badge/license-Dual%20(Free%20%2B%20Commercial)-blue.svg)](LICENSE)

<br/>

**58,000+ lines of code** · **94 Python modules** · **20-stage pipeline** · **14 languages + universal** · **1,956 tests**

[Quick Start](#quick-start) · [Features](#feature-matrix) · [Documentation](https://ksanyok.github.io/TextHumanize/) · [Live Demo](https://humanizekit.tester-buyreadysite.website/) · [License](#license--pricing)

</div>

---

TextHumanize is a **pure-algorithmic text processing engine** that normalizes style, improves readability, and reduces mechanical patterns in text. No neural networks, no API keys, no internet — just 58K+ lines of finely tuned rules, dictionaries, and statistical methods.

> **Honest note:** TextHumanize is a style-normalization tool, not an AI-detection bypass tool. It reduces AI-like patterns (formulaic connectors, uniform sentence length, bureaucratic vocabulary) but does not guarantee that processed text will pass external AI detectors. Quality of humanization varies by language and text type. See [Limitations](#limitations) below.

**Built-in toolkit:** AI Detection · Paraphrasing · Tone Analysis · Watermark Cleaning · Content Spinning · Coherence Analysis · Readability Scoring · Stylistic Fingerprinting · Auto-Tuner · Perplexity Analysis · Plagiarism Detection · **Async API** · **SSE Streaming**

**Platforms:** Python (full) · TypeScript/JavaScript (core) · PHP (full)

**Languages:** 🇷🇺 RU · 🇺🇦 UK · 🇬🇧 EN · 🇩🇪 DE · 🇫🇷 FR · 🇪🇸 ES · 🇵🇱 PL · 🇧🇷 PT · 🇮🇹 IT · 🇸🇦 AR · 🇨🇳 ZH · 🇯🇵 JA · 🇰🇷 KO · 🇹🇷 TR · 🌍 **any language** via universal processor

---

## Why TextHumanize?

> **Problem:** Machine-generated text has uniform sentence lengths, bureaucratic vocabulary, formulaic connectors, and low stylistic diversity — reducing readability, engagement, and brand authenticity.

> **Solution:** TextHumanize algorithmically normalizes text style while preserving meaning. Configurable intensity, deterministic output, full change reports. No cloud APIs, no rate limits, no data leaks.

| Advantage | Details |
|:----------|:--------|
| **~1,500 chars/sec** | Process a full article in 1–2 seconds |
| **100% private** | All processing is local — your text never leaves your machine |
| **Precise control** | Intensity 0–100, 9 profiles, keyword preservation, max change ratio |
| **14 languages** | Deep support for EN/RU/UK/DE; dictionaries for 14 languages; statistical processor for any other |
| **Zero dependencies** | Pure Python stdlib — no pip packages, no model downloads, starts in <100ms |
| **Reproducible** | Seed-based PRNG — same input + same seed = identical output |
| **AI detection** | 13-metric ensemble + 35-feature statistical detector — no ML required |
| **Enterprise-ready** | Dual license, 1,956 tests, CI/CD, benchmarks, on-prem deployment |

---

## Comparison with Competitors

| Criterion | TextHumanize | Online Humanizers | GPT/LLM Rewriting |
|:----------|:------------:|:-----------------:|:------------------:|
| Works offline | ✅ | ❌ | ❌ |
| Privacy | ✅ Local only | ❌ Third-party servers | ❌ Cloud API |
| Speed | **~1.5K chars/sec** | 2–10 sec (network) | ~500 chars/sec |
| Cost per 1M chars | **$0** | $10–50/month | $15–60 (GPT-4) |
| API key required | No | Yes | Yes |
| Deterministic | ✅ Seed-based | ❌ | ❌ |
| Languages | **14 + universal** | 1–3 | 10+ but expensive |
| Built-in AI detector | ✅ 13 metrics | ❌ or basic | ❌ |
| Max change control | ✅ `max_change_ratio` | ❌ | ❌ Unpredictable |
| Open source | ✅ | ❌ | ❌ |
| Self-hosted | ✅ | ❌ | ❌ |

### vs. Other Open-Source Libraries

| Feature | TextHumanize | Typical Alternatives |
|:--------|:------------:|:--------------------:|
| Pipeline stages | **20** | 2–4 |
| Languages | **14 + universal** | 1–2 |
| AI detection | ✅ 13 metrics + statistical ML | ❌ |
| Python tests | **1,956** | 10–50 |
| Codebase size | **58,000+ lines** | 500–2K |
| Platforms | Python + JS + PHP | Single |
| Plugin system | ✅ | ❌ |
| Tone analysis | ✅ 7 levels | ❌ |
| REST API | ✅ 12 endpoints | ❌ |
| Readability metrics | ✅ 6 indices | 0–1 |
| Morphological engine | ✅ 4 languages | ❌ |

---

## Installation

```bash
pip install texthumanize
```

From source:

```bash
git clone https://github.com/ksanyok/TextHumanize.git
cd TextHumanize && pip install -e .
```

<details>
<summary>PHP / TypeScript</summary>

```bash
# PHP
cd php/ && composer install

# TypeScript
cd js/ && npm install
```

</details>

---

## Quick Start

```python
from texthumanize import humanize, analyze, detect_ai, explain

# Humanize text
result = humanize("This text utilizes a comprehensive methodology for implementation.", lang="en")
print(result.text)       # → "This text uses a complete method for setup."
print(result.change_ratio)  # → 0.15
print(result.quality_score) # → 0.85

# With profile and intensity
result = humanize(text, lang="en", profile="web", intensity=70)

# AI Detection — 13-metric ensemble
ai = detect_ai("Text to check for AI generation.", lang="en")
print(f"AI: {ai['score']:.0%} | {ai['verdict']} | Confidence: {ai['confidence']:.0%}")

# Analyze text metrics
report = analyze("Text to analyze.", lang="en")
print(f"Artificiality: {report.artificiality_score:.1f}/100")

# Full change report
print(explain(result))
```

### All Features at a Glance

```python
from texthumanize import (
    humanize, humanize_batch, humanize_chunked, humanize_ai,
    detect_ai, detect_ai_batch, detect_ai_sentences, detect_ai_mixed,
    paraphrase, analyze_tone, adjust_tone,
    detect_watermarks, clean_watermarks,
    spin, spin_variants, analyze_coherence, full_readability,
    AutoTuner, BenchmarkSuite, STYLE_PRESETS,
)

# Paraphrasing
print(paraphrase("The system works efficiently.", lang="en"))

# Tone — 7-level formality scale
tone = analyze_tone("Please submit the documentation.", lang="en")
casual = adjust_tone("It is imperative to proceed.", target="casual", lang="en")

# Watermarks
clean = clean_watermarks("Te\u200bxt wi\u200bth hid\u200bden chars")

# Spinning
variants = spin_variants("Original text.", count=5, lang="en")

# Batch + chunked processing
results = humanize_batch(["Text 1", "Text 2"], lang="en", max_workers=4)
result = humanize_chunked(large_doc, chunk_size=3000, lang="ru")

# Async API — native asyncio support
from texthumanize import async_humanize, async_detect_ai
result = await async_humanize("Text to process", lang="en")
ai = await async_detect_ai("Text to check", lang="en")
```

---

## Before & After

**Before (AI-generated):**
> Furthermore, it is important to note that the implementation of cloud computing facilitates the optimization of business processes. Additionally, the utilization of microservices constitutes a significant advancement.

**After (TextHumanize, profile="web", intensity=70):**
> But cloud computing helps optimize how businesses work. Also, microservices are a big step forward.

---

## Feature Matrix

| Category | Feature | Python | JS | PHP |
|:---------|:--------|:------:|:--:|:---:|
| **Core** | `humanize()` — 20-stage pipeline | ✅ | ✅ | ✅ |
| | `humanize_batch()` — parallel processing | ✅ | — | ✅ |
| | `humanize_chunked()` — large text support | ✅ | — | ✅ |
| | `humanize_ai()` — three-tier AI + rules | ✅ | — | — |
| | `analyze()` — artificiality scoring | ✅ | ✅ | ✅ |
| | `explain()` — change report | ✅ | — | ✅ |
| **AI Detection** | `detect_ai()` — 13-metric + statistical ML | ✅ | ✅ | ✅ |
| | `detect_ai_batch()` — batch detection | ✅ | — | — |
| | `detect_ai_sentences()` — per-sentence | ✅ | — | — |
| | `detect_ai_mixed()` — mixed content | ✅ | — | — |
| **NLP** | `paraphrase()` — syntactic transforms | ✅ | — | ✅ |
| | `POSTagger` — rule-based POS (EN/RU/UK/DE) | ✅ | — | — |
| | `CJKSegmenter` — zh/ja/ko word segmentation | ✅ | — | — |
| | `SyntaxRewriter` — 8 sentence transforms | ✅ | — | — |
| | `WordLanguageModel` — perplexity (14 langs) | ✅ | — | — |
| | `CollocEngine` — PMI collocation scoring | ✅ | — | — |
| **Tone** | `analyze_tone()` — formality analysis | ✅ | — | ✅ |
| | `adjust_tone()` — 7-level adjustment | ✅ | — | ✅ |
| **Watermarks** | `detect_watermarks()` — 5 types | ✅ | — | ✅ |
| | `clean_watermarks()` — removal | ✅ | — | ✅ |
| **Spinning** | `spin()` / `spin_variants()` | ✅ | — | ✅ |
| **Analysis** | `analyze_coherence()` — paragraph flow | ✅ | — | ✅ |
| | `full_readability()` — 6 indices | ✅ | — | ✅ |
| | Stylistic fingerprinting | ✅ | — | — |
| **Quality** | `BenchmarkSuite` — 6-dimension scoring | ✅ | — | — |
| | `FingerprintRandomizer` — anti-detection | ✅ | — | — |
| **Advanced** | Style presets (5 personas) | ✅ | — | — |
| | Auto-Tuner (feedback loop) | ✅ | — | — |
| | Plugin system | ✅ | — | ✅ |
| | REST API (12 endpoints) | ✅ | — | — |
| | CLI (15+ commands) | ✅ | — | — |
| **Languages** | Full dictionary support | 14 | 2 | 14 |
| | Universal processor | ✅ | ✅ | ✅ |

---

## Profiles

| Profile | Use Case | Sentence Length | Colloquialisms | Default Intensity |
|---------|----------|:---------:|:---------:|:---------:|
| `chat` | Messaging, social media | 8–18 words | High | 80 |
| `web` | Blog posts, articles | 10–22 words | Medium | 60 |
| `seo` | SEO content (keyword-safe) | 12–25 words | None | 40 |
| `docs` | Technical documentation | 12–28 words | None | 50 |
| `formal` | Academic, legal | 15–30 words | None | 30 |
| `academic` | Research papers | 15–30 words | None | 25 |
| `marketing` | Sales, promo copy | 8–20 words | Medium | 70 |
| `social` | Social media posts | 6–15 words | High | 85 |
| `email` | Business emails | 10–22 words | Medium | 50 |

**Style presets:** `student` · `copywriter` · `scientist` · `journalist` · `blogger`

```python
result = humanize(text, profile="seo", intensity=40,
                  constraints={"keep_keywords": ["API", "cloud"]})
```

---

## Processing Pipeline

```
Input → Watermark Cleaning → Segmentation → CJK Segmentation → Typography
      → Debureaucratization → Structure → Repetitions → Liveliness
      → Paraphrasing → Syntax Rewriting → Tone Harmonization → Universal
      → Naturalization → Word LM Quality Gate → Readability → Grammar
      → Coherence Repair → Fingerprint Diversification → Validation → Output
```

**20 stages** with adaptive intensity (auto-reduces processing for already-natural text) and graduated retry (retries at lower intensity if change ratio exceeds limit).

---

## AI Detection

13-metric ensemble + 35-feature statistical detector. No ML models, no APIs.

| Metric | What It Measures |
|:-------|:----------------|
| AI Patterns | Formulaic phrases ("it is important to note", "furthermore") |
| Burstiness | Sentence length uniformity (humans vary, AI doesn't) |
| Opening Diversity | Repetitive sentence starts |
| Entropy | Word predictability (Shannon entropy) |
| Vocabulary | Lexical richness (type-to-token ratio) |
| Perplexity | Character-level predictability |
| + 7 more | Stylometry, coherence, grammar perfection, punctuation, rhythm, readability, Zipf |

**Ensemble:** Weighted sum (50%) + Strong signal detector (30%) + Majority voting (20%)

**Verdicts:** `human_written` (< 35%) · `mixed` (35–65%) · `ai_generated` (≥ 65%)

```python
result = detect_ai("Text to check.", lang="en")
print(f"{result['score']:.0%} — {result['verdict']}")

# Per-sentence detection
for s in detect_ai_sentences(text, lang="en"):
    print(f"{'🤖' if s['label'] == 'ai' else '👤'} {s['text'][:80]}")
```

---

## CLI

```bash
texthumanize input.txt -l en -p web -i 70 -o output.txt
texthumanize input.txt --detect-ai
texthumanize input.txt --analyze
texthumanize input.txt --paraphrase -o out.txt
texthumanize input.txt --tone casual
texthumanize dummy --api --port 8080
echo "Text" | texthumanize - -l en
```

## REST API

```bash
python -m texthumanize.api --port 8080
```

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/humanize` | Humanize text |
| `POST` | `/detect-ai` | AI detection (single or batch) |
| `POST` | `/analyze` | Text metrics |
| `POST` | `/paraphrase` | Paraphrase |
| `POST` | `/tone/analyze` | Tone analysis |
| `POST` | `/tone/adjust` | Tone adjustment |
| `POST` | `/watermarks/detect` | Detect watermarks |
| `POST` | `/watermarks/clean` | Clean watermarks |
| `POST` | `/spin` | Text spinning |
| `POST` | `/coherence` | Coherence analysis |
| `POST` | `/readability` | Readability metrics |
| `GET` | `/health` | Health check |

```bash
curl -X POST http://localhost:8080/humanize \
  -H "Content-Type: application/json" \
  -d '{"text": "Your text here.", "lang": "en", "profile": "web"}'
```

---

## Language Support

| Language | Code | Bureaucratic | Synonyms | Collocations |
|----------|:----:|:-----------:|:--------:|:------------:|
| Russian | `ru` | 70+ | 50+ | 408 |
| Ukrainian | `uk` | 50+ | 48 | 38 |
| English | `en` | 40+ | 35+ | 1,578 |
| German | `de` | 64 | 45 | 125 |
| French | `fr` | 20 | 20 | 128 |
| Spanish | `es` | 18 | 18 | 126 |
| Polish | `pl` | 18 | 18 | 34 |
| Portuguese | `pt` | 16 | 17 | 36 |
| Italian | `it` | 16 | 17 | 38 |
| Arabic | `ar` | 81 | 80 | — |
| Chinese | `zh` | 80 | 80 | — |
| Japanese | `ja` | 60+ | 60+ | — |
| Korean | `ko` | 60+ | 60+ | — |
| Turkish | `tr` | 60+ | 60+ | — |

**Universal processor** works for any language using statistical methods (burstiness, perplexity, punctuation normalization).

---

## Performance

All benchmarks on Apple Silicon (M-series), Python 3.12, single thread.

| Function | Text Size | Avg Latency | Peak Memory |
|----------|-----------|:-----------:|:-----------:|
| `humanize()` | 30 words | ~60 ms | 4 KB |
| `humanize()` | 80 words | ~200 ms | 4 KB |
| `humanize()` | 400 words | ~1.5 s | 6 KB |
| `detect_ai()` | 30 words | ~50 ms | 22 KB |
| `detect_ai()` | 80 words | ~150 ms | 71 KB |
| `detect_ai()` | 400 words | ~500 ms | 196 KB |
| `analyze()` | 80 words | ~500 ms | 362 KB |
| `paraphrase()` | 80 words | ~5 ms | 8 KB |

| Property | Value |
|----------|:-----:|
| LRU cache hit | **11× faster** than cold call |
| External network calls | **0** (offline-first) |
| Deterministic (same seed) | ✅ Always |
| Pipeline timeout | 30 s (configurable) |
| Rate limiting (API) | 10 req/s per IP, burst 20 |

> Run benchmarks yourself: `python benchmarks/run_benchmark.py`

---

## Plugin System

```python
from texthumanize import Pipeline, humanize

def add_disclaimer(text: str, lang: str) -> str:
    return text + "\n\n---\nProcessed by TextHumanize."

Pipeline.register_hook(add_disclaimer, after="naturalization")
result = humanize("Your text here.")
Pipeline.clear_plugins()
```

Available stages: `watermark` → `segmentation` → `typography` → `debureaucratization` → `structure` → `repetitions` → `liveliness` → `paraphrasing` → `syntax_rewriting` → `tone` → `universal` → `naturalization` → `paraphrase_engine` → `sentence_restructuring` → `entropy_injection` → `readability` → `grammar` → `coherence` → `validation` → `restore`

---

## Architecture

```
texthumanize/                    # 94 Python modules, 58,000+ lines
├── core.py                      # Facade: humanize(), analyze(), detect_ai()
├── pipeline.py                  # 20-stage pipeline + adaptive intensity
├── api.py                       # REST API server (12 endpoints)
├── cli.py                       # CLI (15+ commands)
├── exceptions.py                # Exception hierarchy
│
├── analyzer.py                  # Artificiality scoring + 6 readability metrics
├── detectors.py                 # AI detector: 13 metrics + ensemble
├── statistical_detector.py      # 35-feature ML classifier
├── pos_tagger.py                # POS tagger (EN/RU/UK/DE)
├── collocation_engine.py        # PMI collocation scoring (2,511 collocations)
├── word_lm.py                   # Word-level LM (14 langs)
│
├── normalizer.py                # Typography (stage 2)
├── decancel.py                  # Debureaucratization (stage 3)
├── structure.py                 # Sentence diversification (stage 4)
├── naturalizer.py               # Burstiness + perplexity (stage 10)
├── paraphraser_ext.py           # Semantic paraphrasing (stage 7)
├── syntax_rewriter.py           # Structural transforms (stage 7b)
├── grammar_fix.py               # Grammar correction (stage 12)
├── coherence_repair.py          # Coherence repair (stage 13)
├── validator.py                 # Quality validation (stage 14)
│
├── tone.py                      # Tone analysis & adjustment
├── watermark.py                 # Watermark detection & cleaning
├── spinner.py                   # Text spinning
├── coherence.py                 # Coherence analysis
├── morphology.py                # Morphological engine (RU/UK/EN/DE)
├── ...                          # 30+ more modules
│
└── lang/                        # 14 language packs + registry
    ├── en.py, ru.py, de.py ...  # Data only, no logic
    └── ar.py, zh.py, ja.py ...  # Including CJK + RTL
```

**Design principles:** Modular · Declarative rules · Idempotent · Safe defaults · Extensible · Zero dependencies · Lazy imports

---

## Testing & Quality

| Platform | Tests | Status |
|:---------|------:|:------:|
| **Python** | 1,956 | ✅ All passing |
| **PHP** | 223 | ✅ All passing |
| **TypeScript** | 28 | ✅ All passing |
| **Total** | **2,207** | ✅ |

```bash
pytest -q                          # 1956 passed
ruff check texthumanize/           # Lint
mypy texthumanize/                 # Type check
cd php && php vendor/bin/phpunit   # 223 tests
```

CI/CD runs on every push: Python 3.9–3.13 + PHP 8.1–8.3 matrix, ruff, mypy, pytest with coverage ≥70%.

---

## Security

| Aspect | Implementation |
|:-------|:--------------|
| Input limits | 1 MB text, 5 MB API body |
| Network calls | **Zero.** No telemetry, no analytics |
| Dependencies | **Zero.** Pure stdlib |
| Regex safety | All linear-time, no user input compiled to regex |
| Reproducibility | Seed-based PRNG, deterministic output |
| Sandboxing | Resource limits documented for production |

---

## Docker

```bash
docker build -t texthumanize .
docker run -p 8080:8080 texthumanize
```

```bash
# API mode
docker run -p 8080:8080 texthumanize --api --port 8080

# Process a file
docker run -v $(pwd):/data texthumanize /data/input.txt -o /data/output.txt
```

---

## For Business & Enterprise

| Requirement | How TextHumanize Delivers |
|:------------|:-------------------------|
| **Predictability** | Seed-based PRNG — same input + seed = identical output |
| **Privacy** | 100% local. Zero network calls. No data leaves your server |
| **Auditability** | Every call returns change_ratio, quality_score, similarity, explain() report |
| **Integration** | Python SDK · JS SDK · PHP SDK · CLI · REST API · Docker |
| **Reliability** | 2,246 tests across 3 platforms, CI/CD with ruff + mypy |
| **No vendor lock-in** | Zero dependencies. No cloud APIs, no API keys, no rate limits |
| **Language coverage** | 14 full language packs + universal processor for any language |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, testing, and PR guidelines.

---

## Limitations

TextHumanize is a **style normalization** tool. Please be aware of realistic expectations:

| Aspect | Current State | Notes |
|:-------|:-------------|:------|
| **EN humanization** | Reduces AI markers by 10–35% | Replaces bureaucratic phrases, varies sentence structure |
| **RU humanization** | Reduces AI markers by 15–30% | Good at debureaucratization, some sentences may sound awkward |
| **UK humanization** | Reduces AI markers by 20–50% | Best multilingual support after EN |
| **External AI detectors** | Not reliable bypass | GPTZero, Originality.ai, etc. use different models |
| **Short texts (< 50 words)** | Limited effect | Not enough context for meaningful transformation |
| **Performance** | ~1.5K chars/sec | Fast for batch processing, but not sub-millisecond |
| **Built-in AI detector** | Heuristic + statistical | Useful for internal scoring; not equivalent to GPTZero/Turnitin |
| **Monotonicity** | Higher intensity ≠ always lower AI score | Some transforms at high intensity may create new AI-like patterns |

**What TextHumanize does well:**
- Removes formulaic connectors ("furthermore", "it is important to note")
- Varies sentence length to add human-like burstiness
- Replaces bureaucratic vocabulary with simpler alternatives
- Deterministic, reproducible results with seed control
- 100% offline, no data leaks, zero dependencies

**What TextHumanize does NOT do:**
- Guarantee passing external AI detectors (GPTZero, Originality.ai, Turnitin)
- Rewrite text at the semantic level (it's rule-based, not LLM-based)
- Handle domain-specific jargon (medical, legal, etc.)

---

## License & Pricing

TextHumanize uses a **dual license model**:

| Use Case | License | Cost |
|:---------|:--------|:----:|
| Personal / Academic / Open-source | Free License | **Free** |
| Commercial — 1 dev, 1 project | Indie | **$199/year** |
| Commercial — up to 5 devs | Startup | **$499/year** |
| Commercial — up to 20 devs | Business | **$1,499/year** |
| Enterprise / On-prem / SLA | Enterprise | [Contact us](mailto:ksanyok@me.com) |

All commercial licenses include full source code, updates for 1 year, and email support.

**[Full licensing details →](COMMERCIAL.md)** · See [LICENSE](LICENSE) for legal text · **Contact:** [ksanyok@me.com](mailto:ksanyok@me.com)

---

<p align="center">
  <a href="https://ksanyok.github.io/TextHumanize/">Documentation</a> ·
  <a href="https://humanizekit.tester-buyreadysite.website/">Live Demo</a> ·
  <a href="https://github.com/ksanyok/TextHumanize">GitHub</a> ·
  <a href="https://github.com/ksanyok/TextHumanize/issues">Issues</a> ·
  <a href="https://github.com/ksanyok/TextHumanize/discussions">Discussions</a> ·
  <a href="COMMERCIAL.md">Commercial License</a>
</p>
