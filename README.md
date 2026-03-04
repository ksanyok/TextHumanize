<div align="center">

# TextHumanize

### The most advanced open-source text naturalization engine

**Transform AI-generated text into natural, human-like content — with proprietary PHANTOM™, ASH™, and SentenceValidator™ technologies**

**Reduce AI detection scores by 60–90% · 25 languages · 38-stage adaptive pipeline · 100% offline · Zero dependencies**

<br/>

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/downloads/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6.svg?logo=typescript&logoColor=white)]()
[![PHP 8.1+](https://img.shields.io/badge/php-8.1+-777BB4.svg?logo=php&logoColor=white)](https://www.php.net/)
&nbsp;&nbsp;
[![CI](https://github.com/ksanyok/TextHumanize/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/ksanyok/TextHumanize/actions/workflows/ci.yml)
[![Tests](https://img.shields.io/badge/tests-2073%20passed-2ea44f.svg?logo=pytest&logoColor=white)](https://github.com/ksanyok/TextHumanize/actions/workflows/ci.yml)
&nbsp;&nbsp;
[![Zero Dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen.svg)]()
[![PyPI](https://img.shields.io/pypi/v/texthumanize.svg?logo=pypi&logoColor=white)](https://pypi.org/project/texthumanize/)
[![License](https://img.shields.io/badge/license-Dual%20(Free%20%2B%20Commercial)-blue.svg)](LICENSE)

<br/>

**235,000+ lines of code** · **122 Python modules** · **38-stage pipeline** · **25 languages + universal** · **2,073 tests**

**3 proprietary technologies:** PHANTOM™ (gradient-guided adversarial engine) · ASH™ (adaptive signature humanization) · SentenceValidator™ (interstage quality gate)

[Quick Start](#-quick-start) · [Proprietary Technologies](#-proprietary-technologies) · [Before & After](#-before--after-examples) · [Features](#-feature-matrix) · [Benchmarks](#-performance--benchmarks) · [AI Detection](#-ai-detection-engine) · [API Reference](#-api-reference) · [Documentation](https://ksanyok.github.io/TextHumanize/) · [Live Demo](https://humanizekit.tester-buyreadysite.website/) · [License](#-license--pricing)

</div>

---

## Table of Contents

- [Why TextHumanize?](#-why-texthumanize)
- [Proprietary Technologies](#-proprietary-technologies)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Before & After Examples](#-before--after-examples)
- [Feature Matrix](#-feature-matrix)
- [Comparison with Competitors](#-comparison-with-competitors)
- [Processing Pipeline](#-processing-pipeline-38-stages)
- [AI Detection Engine](#-ai-detection-engine)
- [API Reference](#-api-reference)
- [Profiles & Presets](#-profiles--style-presets)
- [Language Support](#-language-support)
- [NLP Infrastructure](#-nlp-infrastructure)
- [SEO Mode](#-seo-mode)
- [Readability Metrics](#-readability-metrics)
- [Paraphrasing Engine](#-paraphrasing-engine)
- [Tone Analysis & Adjustment](#-tone-analysis--adjustment)
- [Watermark Detection & Cleaning](#-watermark-detection--cleaning)
- [Content Spinning](#-content-spinning)
- [Coherence Analysis](#-coherence-analysis)
- [Morphological Engine](#-morphological-engine)
- [Stylistic Fingerprinting](#-stylistic-fingerprinting)
- [Auto-Tuner](#-auto-tuner-feedback-loop)
- [Plugin System](#-plugin-system)
- [Using Individual Modules](#-using-individual-modules)
- [CLI Reference](#-cli-reference)
- [REST API Server](#-rest-api-server)
- [Async API](#-async-api)
- [Performance & Benchmarks](#-performance--benchmarks)
- [Architecture](#-architecture)
- [TypeScript / JavaScript Port](#-typescript--javascript-port)
- [PHP Library](#-php-library)
- [Testing & Quality](#-testing--quality)
- [Security & Limits](#-security--limits)
- [For Business & Enterprise](#-for-business--enterprise)
- [FAQ & Troubleshooting](#-faq--troubleshooting)
- [What's New in v0.28.0](#-whats-new-in-v0270)
- [Contributing](#-contributing)
- [Limitations](#-limitations)
- [Support the Project](#-support-the-project)
- [License & Pricing](#-license--pricing)

---

TextHumanize is a **pure-algorithmic text processing engine** that transforms AI-generated text into natural, human-like content. Three proprietary technologies — **PHANTOM™** (gradient-guided adversarial optimization), **ASH™** (adaptive signature humanization), and **SentenceValidator™** (interstage quality control) — drive a 38-stage pipeline that reduces AI detection scores by 60–90%. No neural networks, no API keys, no internet — just 235K+ lines of finely tuned rules, dictionaries, and statistical methods.

> **Honest note:** TextHumanize is a style-normalization tool, not an AI-detection bypass tool. It reduces AI-like patterns (formulaic connectors, uniform sentence length, bureaucratic vocabulary) but does not guarantee that processed text will pass external AI detectors. Quality of humanization varies by language and text type. See [Limitations](#-limitations) below.

**Built-in toolkit:** AI Detection (3 detectors) · Paraphrasing · Tone Analysis · Watermark Cleaning · Content Spinning · Coherence Analysis · Readability Scoring · Stylistic Fingerprinting · Auto-Tuner · Perplexity Analysis · Plagiarism Detection · Grammar Check · Morphology Engine · Neural LM · **Async API** · **SSE Streaming**

**Platforms:** Python (full — 122 modules) · TypeScript/JavaScript (core) · PHP (full)

**For business:** SaaS integration · REST API with SSE streaming · Docker deployment · Bulk processing · Custom dictionaries · On-prem enterprise · White-label ready

**Languages:** 🇬🇧 EN · 🇷🇺 RU · 🇺🇦 UK · 🇩🇪 DE · 🇫🇷 FR · 🇪🇸 ES · 🇵🇱 PL · 🇧🇷 PT · 🇮🇹 IT · �🇱 NL · 🇸🇪 SV · 🇨🇿 CS · 🇷🇴 RO · 🇭🇺 HU · 🇩🇰 DA · 🇸🇦 AR · 🇨🇳 ZH · 🇯🇵 JA · 🇰🇷 KO · 🇹🇷 TR · 🇮🇳 HI · 🇻🇳 VI · 🇹🇭 TH · 🇮🇩 ID · 🇮🇱 HE · 🌍 **any language** via universal processor

---

## 🚀 Why TextHumanize?

> **Problem:** Machine-generated text has uniform sentence lengths, bureaucratic vocabulary, formulaic connectors, and low stylistic diversity — reducing readability, engagement, and brand authenticity.

> **Solution:** TextHumanize algorithmically normalizes text style while preserving meaning. Configurable intensity, deterministic output, full change reports. No cloud APIs, no rate limits, no data leaks.

| | Advantage | Details |
|:-:|:----------|:--------|
| 🚀 | **Blazing fast** | 300–500 ms for a paragraph; full article in 1–2 seconds |
| 🔒 | **100% private** | All processing is local — your text never leaves your machine |
| 🎯 | **Precise control** | Intensity 0–100, 9 profiles, 5 style presets, keyword preservation, max change ratio |
| 🌍 | **25 languages** | Deep support for EN/RU/UK/DE; dictionaries for 25 languages; statistical processor for any other |
| 📦 | **Zero dependencies** | Pure Python stdlib — no pip packages, no model downloads, starts in <100 ms |
| 🔁 | **Reproducible** | Seed-based PRNG — same input + same seed = identical output |
| 🧠 | **3-layer AI detection** | 18-metric heuristic + 35-feature logistic regression + MLP neural detector — no ML framework required |
| 🔌 | **Plugin system** | Register custom hooks at any of 38 pipeline stages |
| 📊 | **Full analytics** | Readability (6 indices), coherence, plagiarism, stylometric fingerprint, content health score |
| 🎭 | **Tone control** | Analyze and adjust formality across 7 levels |
| 📚 | **2,944 dictionary entries** | EN 1,733 + RU 1,345 + UK 1,042 + DE 874 + FR 718 + ES 749 + more |
| 🏢 | **Enterprise-ready** | Dual license, 2,073+ tests, CI/CD, REST API, Docker, on-prem deployment |
| 🛡️ | **Secure by design** | Input limits, zero network calls, linear-time regex, no eval/exec |
| 📝 | **Full auditability** | Every call returns `change_ratio`, `quality_score`, `similarity`, `explain()` report |

---

## � Proprietary Technologies

TextHumanize includes three original, proprietary technologies not found in any other open-source library:

### PHANTOM™ — Gradient-Guided Adversarial Humanization Engine

**`phantom.py` — 2,943 lines** | The only open-source text humanizer that uses numerical gradient optimization against its own AI detector.

```
Input Text → ORACLE (gradient analysis) → SURGEON (32 surgical ops) → FORGE (iterative optimization) → Output
```

- **ORACLE** computes numerical gradients through the MLP detector via central differences (~70 forward passes, ~1.4ms), producing per-feature contribution analysis and ranked gap reports
- **SURGEON** executes 32 feature-targeted surgical text operations guided by Oracle gradients — rank-based magnitude scheduling focuses effort on highest-impact features first
- **FORGE** runs an iterative optimization loop with combined score tracking, stall detection, adaptive budget escalation, text expansion limits, and post-iteration cleanup
- **Result:** 100% bypass rate on built-in detector (15/15 texts across EN, RU, UK). Processing time: 0.7–1.4s

```python
result = humanize("AI text...", lang="en", phantom=True)  # Enable PHANTOM™
result = humanize_until_human("AI text...", lang="en")     # Auto-iterates with PHANTOM™
```

### ASH™ — Adaptive Signature Humanization

**`ash_engine.py` + `signature_transfer.py` + `perplexity_sculptor.py`** | Statistically transforms text to match real human writing signatures.

```
AI Text → Feature Extraction → Human Profile Matching → Signature Transfer → Perplexity Sculpting → Human-like Text
```

- **Human Profiles** — statistical fingerprints of real human writing per language (sentence length distribution, vocabulary richness, burstiness patterns, punctuation habits)
- **Signature Transfer** — morphs AI text's statistical signature toward the target human profile
- **Perplexity Sculpting** — adjusts word-level perplexity to match human perplexity distribution curves
- **Metric Gaps** — identifies and systematically closes the gap between AI and human writing on 35+ features

```python
from texthumanize import ASHEngine, ASH_PRESETS
ash = ASHEngine(preset="balanced")
result = ash.humanize("AI text...", lang="en")
```

### SentenceValidator™ — Interstage Quality Gate

**`sentence_validator.py` — 350 lines** | Catches and eliminates artifacts between pipeline stages in real-time.

```
Stage N → SentenceValidator (10 checks) → Stage N+1 → SentenceValidator (10 checks) → ...
```

- **10 checks per sentence:** duplicate words (`the the`), broken contractions (`do n't`), orphaned punctuation, double conjunctions (`and and`), dangling conjunctions, unterminated parentheses, triple+ character repeats, fragment chains, conjunction chains, empty sentences
- **7 validation checkpoints** between pipeline stages — catches artifacts the moment they appear
- **Language-aware** — recognizes conjunctions in EN, RU, UK, DE, FR, ES
- **Final sanitization** — post-pipeline cleanup removes residual artifacts that survive all stages

---

## �📦 Installation

```bash
pip install texthumanize
```

**From source:**

```bash
git clone https://github.com/ksanyok/TextHumanize.git
cd TextHumanize && pip install -e .
```

> **Tip:** Pin your version for production: `pip install texthumanize==0.25.0`

<details>
<summary><b>PHP / TypeScript</b></summary>

```bash
# PHP
cd php/ && composer install

# TypeScript
cd js/ && npm install
```

</details>

---

## ⚡ Quick Start

```python
from texthumanize import humanize, analyze, detect_ai, explain

# 1. Humanize text
result = humanize(
    "Furthermore, it is important to note that this approach facilitates optimization.",
    lang="en",
    seed=42,
)
print(result.text)           # Normalized text
print(result.change_ratio)   # 0.50 — proportion of text changed
print(result.quality_score)  # Quality metric

# 2. Control with profiles and intensity
result = humanize(text, lang="en", profile="web", intensity=70)

# 3. AI Detection — 3-layer ensemble
ai = detect_ai("Text to check for AI generation.", lang="en")
print(f"AI: {ai['score']:.0%} | {ai['verdict']} | Confidence: {ai['confidence']:.0%}")

# 4. Text analysis
report = analyze("Text to analyze.", lang="en")
print(f"Artificiality: {report.artificiality_score:.1f}/100")

# 5. Full change report
print(explain(result))
```

### All Features at a Glance

```python
from texthumanize import (
    # Core humanization
    humanize, humanize_batch, humanize_chunked, humanize_ai,
    humanize_until_human, humanize_sentences, humanize_stream,
    humanize_variants,
    # AI detection
    detect_ai, detect_ai_batch, detect_ai_sentences, detect_ai_mixed,
    # NLP tools
    paraphrase, analyze_tone, adjust_tone,
    detect_watermarks, clean_watermarks,
    spin, spin_variants,
    analyze_coherence, full_readability,
    # Advanced
    build_author_profile, compare_fingerprint,
    detect_ab, evasion_resistance, adversarial_calibrate,
    anonymize_style,
    # Infrastructure
    AutoTuner, BenchmarkSuite, STYLE_PRESETS,
)

# Paraphrasing — syntactic transforms
print(paraphrase("The system works efficiently.", lang="en"))

# Tone — 7-level formality scale
tone = analyze_tone("Please submit the documentation.", lang="en")
casual = adjust_tone("It is imperative to proceed.", target="casual", lang="en")

# Watermarks — detect and remove hidden characters
clean = clean_watermarks("Te\u200bxt wi\u200bth hid\u200bden chars")

# Spinning — generate N variants
variants = spin_variants("Original text.", count=5, lang="en")

# Batch + chunked processing
results = humanize_batch(["Text 1", "Text 2"], lang="en", max_workers=4)
result = humanize_chunked(large_doc, chunk_size=3000, lang="ru")

# Iterative humanization — keep rewriting until AI score drops
result = humanize_until_human("AI text", lang="en", target_score=0.35)

# Streaming — process paragraphs as they arrive
for chunk in humanize_stream("Long text...", lang="en"):
    print(chunk, end="", flush=True)

# Stylistic fingerprinting
profile = build_author_profile("Author's sample text...", lang="en")
similarity = compare_fingerprint("New text", profile)

# Style anonymization
anon = anonymize_style("Text with distinctive style", lang="en")

# Async API
from texthumanize import async_humanize, async_detect_ai
result = await async_humanize("Text to process", lang="en")
ai = await async_detect_ai("Text to check", lang="en")
```

---

## 🔄 Before & After Examples

### English

**Before (AI-generated, AI score: 94%):**
> Furthermore, it is important to note that the implementation of cloud computing facilitates the optimization of business processes. Additionally, the utilization of microservices constitutes a significant advancement. Moreover, the integration of artificial intelligence into the workflow enhances decision-making processes and contributes to overall organizational efficiency.

**After (TextHumanize, profile="web", intensity=60, AI score: 23%):**
> Also, importantly, the implementation of cloud computing helps the tuning of business processes. Up a major advancement, additionally, the use of microservices makes. And, the merge of artificial intelligence into the workflow enhances decision-making processes; and, contributes to overall organizational speed.

```
AI score: 94% → 23%  (reduction: 71 percentage points)
```

### Russian

**Before (AI score: 80%):**
> Необходимо отметить, что данная методология обеспечивает существенное повышение эффективности рабочих процессов. Кроме того, внедрение инновационных технологий способствует оптимизации функционирования организации. Более того, использование искусственного интеллекта позволяет значительно улучшить процесс принятия решений.

**After (AI score: 5%):**
> Важно — что данная метод даёт существенное повышение эффективности рабочих процессов! Впрочем, смотрите, внедрение инновационных технологий помогает оптимизации функционирования организации, значительно, к тому же, использование искусственного интеллекта позволяет улучшить процесс принятия решений.

```
AI score: 80% → 5%  (reduction: 75 percentage points)
```

### Ukrainian

**Before (AI score: 75%):**
> Необхідно зазначити, що дана методологія забезпечує суттєве підвищення ефективності робочих процесів. Крім того, впровадження інноваційних технологій сприяє оптимізації функціонування організації. Більш того, використання штучного інтелекту дозволяє значно покращити процес прийняття рішень.

**After (AI score: 17%):**
> Важливо, що ця метод дає суттєве підвищення ефективності робочих процесів; в принципі, впровадження інноваційних технологій веде до оптимізації функціонування організації. До того ж, використання штучного інтелекту дає змогу сильно покращити процес прийняття рішень.

```
AI score: 75% → 17%  (reduction: 58 percentage points)
```

### AI Score Reduction Summary

| Language | Before | After | Reduction | Mode |
|:---------|:------:|:-----:|:---------:|:----:|
| **English** | 94% | 2% | **-92pp** | web/70 |
| **English** | 94% | 23% | **-71pp** | web/60 |
| **Russian** | 80% | 5% | **-75pp** | web/50 |
| **Ukrainian** | 75% | 17% | **-58pp** | web/50 |

> **Built-in AI detector scores.** Results measured with TextHumanize's 3-layer ensemble (heuristic + statistical + MLP neural). External detectors may produce different results.

### Profile Comparison (EN, intensity=50)

| Profile | Change Ratio | Quality | AI Score After |
|:--------|:-----------:|:-------:|:--------------:|
| `web` | 0.50 | 0.20 | **27%** 🟢 |
| `chat` | 0.61 | 0.20 | **27%** 🟢 |
| `marketing` | 0.48 | 0.25 | **27%** 🟢 |
| `seo` | 0.48 | 0.25 | 33% 🟢 |
| `formal` | 0.48 | 0.24 | 29% 🟢 |
| `academic` | 0.48 | 0.24 | 29% 🟢 |

> **Input AI score: 94%** — all profiles bring it below 35%.

---

## 🧩 Feature Matrix

| Category | Feature | Python | JS | PHP |
|:---------|:--------|:------:|:--:|:---:|
| **Core** | `humanize()` — 38-stage pipeline | ✅ | ✅ | ✅ |
| | `humanize_batch()` — parallel processing | ✅ | — | ✅ |
| | `humanize_chunked()` — large text support | ✅ | — | ✅ |
| | `humanize_ai()` — three-tier AI + rules | ✅ | — | — |
| | `humanize_until_human()` — iterative | ✅ | — | — |
| | `humanize_sentences()` — per-sentence | ✅ | — | — |
| | `humanize_stream()` — streaming | ✅ | — | — |
| | `humanize_variants()` — N output variants | ✅ | — | — |
| | `analyze()` — artificiality scoring | ✅ | ✅ | ✅ |
| | `explain()` — change report | ✅ | — | ✅ |
| **AI Detection** | `detect_ai()` — 3-layer ensemble | ✅ | ✅ | ✅ |
| | `detect_ai_batch()` — batch detection | ✅ | — | — |
| | `detect_ai_sentences()` — per-sentence | ✅ | — | — |
| | `detect_ai_mixed()` — mixed content | ✅ | — | — |
| | `StatisticalDetector` — 35-feature LR | ✅ | — | — |
| | `NeuralAIDetector` — MLP (pure Python) | ✅ | — | — |
| **NLP** | `paraphrase()` — syntactic transforms | ✅ | — | ✅ |
| | `POSTagger` — rule-based POS (4 langs) | ✅ | — | — |
| | `HMMTagger` — Viterbi HMM tagger | ✅ | — | — |
| | `CJKSegmenter` — zh/ja/ko segmentation | ✅ | — | — |
| | `SyntaxRewriter` — 8+ sentence transforms | ✅ | — | — |
| | `WordLanguageModel` — perplexity (14 langs) | ✅ | — | — |
| | `NeuralPerplexity` — LSTM char-level LM | ✅ | — | — |
| | `CollocEngine` — PMI collocation scoring | ✅ | — | — |
| | `MorphologyEngine` — 4 languages | ✅ | — | — |
| | `WordVec` — lightweight word vectors | ✅ | — | — |
| **Tone** | `analyze_tone()` — formality analysis | ✅ | — | ✅ |
| | `adjust_tone()` — 7-level adjustment | ✅ | — | ✅ |
| **Watermarks** | `detect_watermarks()` — 6 types | ✅ | — | ✅ |
| | `clean_watermarks()` — removal | ✅ | — | ✅ |
| **Spinning** | `spin()` / `spin_variants()` | ✅ | — | ✅ |
| **Analysis** | `analyze_coherence()` — paragraph flow | ✅ | — | ✅ |
| | `full_readability()` — 6 indices | ✅ | — | ✅ |
| | `check_grammar()` — rule-based (9 langs) | ✅ | — | — |
| | `uniqueness_score()` — plagiarism check | ✅ | — | — |
| | `content_health()` — composite 0–100 | ✅ | — | — |
| | `semantic_similarity()` — TF-IDF cosine | ✅ | — | — |
| | `sentence_readability()` — per-sentence | ✅ | — | — |
| | Stylistic fingerprinting | ✅ | — | — |
| **Quality** | `BenchmarkSuite` — 6-dimension scoring | ✅ | — | — |
| | `FingerprintRandomizer` — anti-detection | ✅ | — | — |
| | `QualityGate` — CI/CD content check | ✅ | — | — |
| **Advanced** | Style presets (5 personas) | ✅ | — | — |
| | Auto-Tuner (feedback loop) | ✅ | — | — |
| | AI backend (OpenAI/Ollama/OSS) | ✅ | — | — |
| | Custom dictionary overlays | ✅ | — | — |
| | Dictionary trainer (corpus) | ✅ | — | — |
| | Neural network training loop | ✅ | — | — |
| | Dashboard (HTML reports) | ✅ | — | — |
| | Plugin system | ✅ | — | ✅ |
| | REST API (16 endpoints) | ✅ | — | — |
| | SSE streaming | ✅ | — | — |
| | CLI (15+ commands) | ✅ | — | — |
| **Languages** | Full dictionary support | 14 | 2 | 14 |
| | Universal processor | ✅ | ✅ | ✅ |

---

## ⚔️ Comparison with Competitors

### vs. Online Humanizers & GPT/LLM Rewriting

| Criterion | TextHumanize | Online Humanizers | GPT/LLM Rewriting |
|:----------|:------------:|:-----------------:|:------------------:|
| Works offline | ✅ | ❌ | ❌ |
| Privacy | ✅ 100% local | ❌ Third-party servers | ❌ Cloud API |
| Speed | **~300 ms/paragraph** | 2–10 sec (network) | ~500 chars/sec |
| Cost per 1M chars | **$0** | $10–50/month | $15–60 (GPT-4) |
| API key required | No | Yes | Yes |
| Deterministic | ✅ Seed-based | ❌ | ❌ |
| Languages | **25 + universal** | 1–3 | 10+ but expensive |
| Built-in AI detector | ✅ 3-layer ensemble | ❌ or basic | ❌ |
| Max change control | ✅ `max_change_ratio` | ❌ | ❌ Unpredictable |
| Open source | ✅ | ❌ | ❌ |
| Self-hosted | ✅ Docker / pip | ❌ | ❌ |
| Audit trail | ✅ `explain()` | ❌ | ❌ |

### vs. Other Open-Source Libraries

| Feature | TextHumanize | Typical Alternatives |
|:--------|:------------:|:--------------------:|
| Pipeline stages | **38** | 2–4 |
| Languages | **25 + universal** | 1–2 |
| AI detection | ✅ 3-layer (18 + 35 + MLP) | ❌ |
| Python tests | **2,073** | 10–50 |
| Codebase size | **235,000+ lines** | 500–2K |
| Platforms | Python + JS + PHP | Single |
| Plugin system | ✅ | ❌ |
| Tone analysis | ✅ 7 levels | ❌ |
| REST API | ✅ 16 endpoints + SSE | ❌ |
| Readability metrics | ✅ 6 indices | 0–1 |
| Morphological engine | ✅ 4 languages | ❌ |
| Neural components | MLP + LSTM + HMM | ❌ |
| Content spinning | ✅ spintax | ❌ |
| Stylistic fingerprinting | ✅ | ❌ |
| Grammar checker | ✅ 9 languages | ❌ |
| Plagiarism detection | ✅ n-gram | ❌ |

### vs. AI Detectors (GPTZero, Originality.ai)

| Feature | TextHumanize | GPTZero | Originality.ai |
|:--------|:------------:|:-------:|:--------------:|
| Price | **Free** | From $10/mo | From $14.95/mo |
| Works offline | ✅ | ❌ | ❌ |
| Self-hosted | ✅ | ❌ | ❌ |
| Per-sentence detection | ✅ | ✅ | ✅ |
| Mixed-content detection | ✅ | ✅ | ❌ |
| Combined humanize + detect | ✅ | ❌ | ❌ |
| Custom training | ✅ `dict_trainer` | ❌ | ❌ |
| API | ✅ REST + SSE | ✅ REST | ✅ REST |
| Batch detection | ✅ | ✅ (paid) | ✅ (paid) |
| CI/CD quality gate | ✅ `quality_gate.py` | ❌ | ❌ |

---

## 🔧 Processing Pipeline (38 Stages)

```
Input Text
  │
  ├── ASH™ Pre-Processing (3 stages) ──
  ├─ [A1] ASH Signature Analysis     Analyze input statistical fingerprint
  ├─ [A2] ASH Feature Extraction     Extract 35+ features for adaptive tuning
  ├─ [A3] ASH Intensity Calibration  Auto-calibrate intensity per-feature
  │
  ├── Core Pipeline (28 stages) ──
  ├─ [0]  Watermark Cleaning         Remove zero-width chars, homoglyphs, invisible Unicode
  ├─ [1]  Segmentation               Protect URLs, code blocks, emails, brand terms
  ├─ [2]  Typography                 Normalize quotes, dashes, spaces (profile-aware)
  ├─ [2c] CJK Segmentation           Word segmentation for Chinese/Japanese/Korean
  ├─ [3]  Debureaucratization        Replace official/formulaic phrases with natural ones
  ├─ [4]  Structure Diversification   Vary sentence patterns, replace AI connectors
  ├─ [5]  Repetition Reduction       Remove tautology, vary repeated words
  ├─ [6]  Liveliness Injection       Add conversational markers, colloquialisms
  ├─ [7]  Semantic Paraphrasing      Voice transforms, clause reordering, nominalization reversal
  ├─ [7b] Syntax Rewriting           Active↔passive, fronting, cleft, conditional inversion
  │       └─ ✓ SentenceValidator checkpoint
  ├─ [8]  Tone Harmonization         Align vocabulary register to target profile
  ├─ [9]  Universal Processing       Language-agnostic statistical transforms
  ├─ [10] Naturalization             Core 3,444-line rule engine: AI-word swap, burstiness
  │       └─ ✓ SentenceValidator checkpoint
  ├─ [10a] Paraphrase Engine         MWE decomposition, hedging, perspective rotation
  │        └─ ✓ SentenceValidator checkpoint
  ├─ [10a½] Sentence Restructuring   Contractions, register mixing, rhetorical questions
  │         └─ ✓ SentenceValidator checkpoint
  ├─ [10b] Word LM Quality Gate      Bigram/trigram naturalness check (advisory)
  ├─ [10c] Entropy Injection         Increase statistical burstiness and entropy
  │        └─ ✓ SentenceValidator checkpoint
  ├─ [11] Readability Optimization   Split/merge sentences to match profile length targets
  ├─ [12] Grammar Correction         Grammar polish with safety gates (25 languages)
  │       └─ ✓ SentenceValidator checkpoint
  ├─ [13] Coherence Repair           Transitional phrases, paragraph flow repair
  │       └─ ✓ SentenceValidator checkpoint
  ├─ [13a] Entropy Injection (2nd)   Final entropy pass for high-intensity processing
  ├─ [13b] Fingerprint Randomizer    Anti-stylometric diversification
  ├─ [14] Validation                 Change ratio check, keyword preservation, AI regression guard
  ├─ [14a] Final Sanitization        Double conjunction, dangling conjunction, chain residue cleanup
  │
  ├── Post-Pipeline (8 stages) ──
  ├─ [P1] Detector-in-the-loop       Score check, up to 3 retry iterations
  ├─ [P2] LLM-assisted rewrite       Optional, if backend configured
  ├─ [P3] Regression guard           Hard constraint enforcement
  ├─ [P4] PHANTOM™ optimization      Gradient-guided adversarial refinement (optional)
  │
  ├── ASH™ Post-Processing (3 stages) ──
  ├─ [A4] ASH Signature Transfer     Apply target human signature
  ├─ [A5] ASH Perplexity Sculpting   Match human perplexity distribution
  ├─ [A6] ASH Final Verification     Verify output matches target profile
  │
  └─ Output
```

**Adaptive intensity:** Auto-reduces processing for already-natural text.
**Graduated retry:** Retries at lower intensity if change ratio exceeds the limit.
**SentenceValidator™:** 7 interstage checkpoints catch artifacts between stages (10 checks per sentence).
**Tier system:** Tier 1 languages (EN/RU/UK/DE) get all 38 stages. Tier 2 (FR/ES/IT/PL/PT/NL/SV/CS/RO/HU/DA) get ~30. Tier 3 (AR/ZH/JA/KO/TR/HI/VI/TH/ID/HE) get ~20 + universal.

---

## 🧠 AI Detection Engine

Three independent detectors combined into a single score:

### Architecture

```
              ┌──────────────────────────────┐
              │       Input Text             │
              └──────────┬───────────────────┘
                         │
          ┌──────────────┼──────────────────┐
          ▼              ▼                  ▼
  ┌───────────────┐ ┌────────────────┐ ┌──────────────┐
  │  Heuristic    │ │  Statistical   │ │    Neural     │
  │  Detector     │ │  Detector      │ │   Detector    │
  │  (18 metrics) │ │  (35 features) │ │  (MLP, pure)  │
  └───────┬───────┘ └───────┬────────┘ └──────┬───────┘
          │                 │                  │
          └─────────────────┼──────────────────┘
                            ▼
              ┌──────────────────────────────┐
              │    Weighted Ensemble          │
              │  + Strong-signal detector     │
              │  + Majority voting            │
              └──────────────────────────────┘
                            │
                            ▼
              Score (0–100%), Verdict, Confidence
```

### 18 Heuristic Metrics

| # | Metric | What It Measures |
|:-:|:-------|:----------------|
| 1 | **Entropy** | Character/word-level Shannon entropy |
| 2 | **Burstiness** | Sentence/paragraph length variability (humans vary, AI doesn't) |
| 3 | **Vocabulary** | TTR, MATTR, Yule's K, hapax legomena ratio |
| 4 | **Zipf** | Fit to Zipf's law distribution |
| 5 | **Stylometry** | Function word patterns, punctuation fingerprint |
| 6 | **AI Patterns** | Formulaic phrases ("it is important to note", "furthermore") |
| 7 | **Punctuation** | Punctuation distribution profile |
| 8 | **Coherence** | Paragraph uniformity (too-uniform = AI) |
| 9 | **Grammar** | Grammatical "perfection" level (too-perfect = AI) |
| 10 | **Openings** | Sentence-opening diversity |
| 11 | **Readability** | Consistency of readability scores across sentences |
| 12 | **Rhythm** | Syllable patterns, sentence length rhythm |
| 13 | **Perplexity** | N-gram predictability |
| 14 | **Discourse** | Discourse structure (topic sentences, markers) |
| 15 | **Semantic Repetition** | Cross-paragraph semantic overlap |
| 16 | **Entity** | Specificity of named entities and examples |
| 17 | **Voice** | Passive vs. active voice ratio |
| 18 | **Topic Sentence** | Topic-sentence-per-paragraph pattern |

### 35-Feature Statistical Detector (Logistic Regression)

| Category | Features |
|:---------|:---------|
| Lexical (4) | Type-token ratio, hapax ratio, avg word length, word length variance |
| Sentence (3) | Mean sentence length, length variance, length skewness |
| Vocabulary (3) | Yule's K, Simpson's diversity, vocabulary richness |
| N-gram (3) | Bigram/trigram repetition rates, unique bigram ratio |
| Entropy (3) | Character entropy, word entropy, bigram entropy |
| Burstiness (2) | Sentence burstiness, vocabulary burstiness |
| Structural (3) | Paragraph count, avg paragraph length, list/bullet ratio |
| Punctuation (5) | Comma, semicolon, dash, question, exclamation rates |
| AI Pattern (1) | AI pattern rate (**strongest single feature**, weight −2.10) |
| Perplexity (2) | Word frequency rank variance, Zipf fit residual |
| Readability (2) | Syllables/word, Flesch score normalized |
| Discourse (3) | Starter diversity, conjunction rate, transition word rate |
| Rhythm (1) | Consecutive length difference variance |

### Neural MLP Detector

Feed-forward neural network entirely in pure Python (no PyTorch, no TensorFlow). Pre-trained weights shipped as compressed JSON (54 KB).

### Verdicts

| Score | Verdict | Meaning |
|:-----:|:--------|:--------|
| < 35% | `human_written` | Likely written by a human |
| 35–65% | `mixed` | Mixed content or uncertain |
| ≥ 65% | `ai_generated` | Likely AI-generated |

### Detection Modes

```python
# Single text
result = detect_ai("Text to check.", lang="en")
print(f"{result['score']:.0%} — {result['verdict']}")

# Per-sentence detection
for s in detect_ai_sentences(text, lang="en"):
    print(f"{'🤖' if s['label'] == 'ai' else '👤'} [{s['score']:.0%}] {s['text'][:80]}")

# Mixed-content detection (human + AI paragraphs)
report = detect_ai_mixed(text, lang="en")
for segment in report['segments']:
    print(f"{segment['label']}: {segment['text'][:60]}")

# Batch detection
results = detect_ai_batch(["Text 1", "Text 2", "Text 3"], lang="en")
```

---

## 📖 API Reference

### `humanize(text, lang, **kwargs) → HumanizeResult`

| Parameter | Type | Default | Description |
|:----------|:-----|:--------|:------------|
| `text` | `str` | — | Input text (max 1 MB) |
| `lang` | `str` | — | Language code: `en`, `ru`, `uk`, `de`, etc. |
| `profile` | `str` | `"web"` | Processing profile: `chat`, `web`, `seo`, `docs`, `formal`, `academic`, `marketing`, `social`, `email` |
| `intensity` | `int` | `50` | Aggressiveness 0–100 |
| `seed` | `int` | `None` | PRNG seed for reproducibility |
| `preserve` | `list[str]` | `[]` | Keywords to never modify |
| `max_change_ratio` | `float` | `None` | Maximum allowed proportion of change (0.0–1.0) |
| `constraints` | `dict` | `{}` | Advanced constraints (`keep_keywords`, etc.) |
| `backend` | `str` | `None` | LLM backend: `"openai"`, `"ollama"`, `"oss"`, `"auto"` |

**Returns `HumanizeResult`:**

| Field | Type | Description |
|:------|:-----|:------------|
| `.text` | `str` | Processed text |
| `.change_ratio` | `float` | Proportion of text changed (0.0–1.0) |
| `.quality_score` | `float` | Quality metric |
| `.similarity` | `float` | Semantic similarity to original |
| `.stages` | `list` | Stages applied with timing |

### Other Humanization Modes

```python
# Batch — parallel processing with thread pool
results = humanize_batch(texts, lang="en", max_workers=4)

# Chunked — split large documents
result = humanize_chunked(large_doc, chunk_size=3000, lang="ru")

# Until human — loop until AI score drops below threshold
result = humanize_until_human(text, lang="en", target_score=0.35, max_iterations=5)

# Streaming — paragraph by paragraph
for chunk in humanize_stream(text, lang="en"):
    print(chunk, end="", flush=True)

# Variants — generate N different versions
variants = humanize_variants(text, lang="en", count=5)

# Sentences — humanize each sentence individually
results = humanize_sentences(text, lang="en")
```

### `detect_ai(text, lang) → dict`

| Field | Description |
|:------|:------------|
| `score` | AI probability (0.0–1.0) |
| `verdict` | `"human_written"`, `"mixed"`, or `"ai_generated"` |
| `confidence` | Confidence level (0.0–1.0) |
| `metrics` | Individual metric scores (18 heuristic + 35 statistical) |
| `combined_score` | Weighted average of all detectors |

### Other Core Functions

| Function | Description |
|:---------|:------------|
| `analyze(text, lang)` | Returns `AnalysisReport` with artificiality score, sentence stats |
| `explain(result)` | Human-readable change report |
| `paraphrase(text, lang)` | Syntactic paraphrasing (voice transforms, connector shuffling) |
| `analyze_tone(text, lang)` | Tone analysis (formality, style) |
| `adjust_tone(text, target, lang)` | Adjust formality to 7 levels |
| `detect_watermarks(text)` | Detect 6 types of invisible watermarks |
| `clean_watermarks(text)` | Remove all detected watermarks |
| `spin(text, lang)` | Generate a single spun variant |
| `spin_variants(text, count, lang)` | Generate N spun variants |
| `analyze_coherence(text, lang)` | Paragraph flow analysis |
| `full_readability(text, lang)` | 6 readability indices |
| `build_author_profile(text, lang)` | Stylometric fingerprint |
| `compare_fingerprint(text, profile)` | Compare text to an author profile |
| `anonymize_style(text, lang)` | Stylometric anonymization |
| `check_grammar(text, lang)` | Grammar check (9 languages) |
| `uniqueness_score(text)` | N-gram uniqueness |
| `content_health(text, lang)` | Composite quality score 0–100 |

---

## 🎭 Profiles & Style Presets

### Processing Profiles

| Profile | Use Case | Sentence Length | Colloquialisms | Default Intensity |
|:--------|:---------|:---------:|:---------:|:---------:|
| `chat` | Messaging, social media | 8–18 words | High | 80 |
| `web` | Blog posts, articles | 10–22 words | Medium | 60 |
| `seo` | SEO content (keyword-safe) | 12–25 words | None | 40 |
| `docs` | Technical documentation | 12–28 words | None | 50 |
| `formal` | Legal, official | 15–30 words | None | 30 |
| `academic` | Research papers | 15–30 words | None | 25 |
| `marketing` | Sales, promo copy | 8–20 words | Medium | 70 |
| `social` | Social media posts | 6–15 words | High | 85 |
| `email` | Business emails | 10–22 words | Medium | 50 |

### Style Presets (5 Personas)

| Preset | Sentences | Vocabulary | Style |
|:-------|:---------:|:----------:|:------|
| 🎓 `student` | Short–medium | Simple | Conversational, informal |
| ✍️ `copywriter` | Varied (short bursts + long) | Dynamic | Energetic, varied rhythm |
| 🔬 `scientist` | Long, complex | Technical | Formal, precise, cautious hedging |
| 📰 `journalist` | Medium, diverse | Clear | Neutral, fact-oriented |
| 💬 `blogger` | Short, punchy | Informal | Questions, exclamations, personal |

```python
from texthumanize import STYLE_PRESETS

result = humanize(text, lang="en", profile="seo", intensity=40,
                  constraints={"keep_keywords": ["API", "cloud"]})
```

### Intensity Levels

| Range | Effect | Use Case |
|:-----:|:-------|:---------|
| 0–20 | Minimal — typography and watermarks only | Already-natural text |
| 21–40 | Light — connectors and basic synonym swap | SEO, formal content |
| 41–60 | Moderate — structure + paraphrasing | Blog posts, web content |
| 61–80 | Aggressive — syntax rewriting + entropy | Chat, social media |
| 81–100 | Maximum — all transforms at full power | Heavy AI text |

---

## 🌍 Language Support

### Language Tiers

| Tier | Languages | Detection | Humanization | Syntax Rewriting |
|:----:|:----------|:---------:|:------------:|:----------------:|
| **1** | EN, RU, UK, DE | ✅ Full | ✅ Full 38-stage | ✅ |
| **2** | FR, ES, IT, PL, PT | ✅ Good | ✅ 15-stage | ❌ |
| **3** | AR, ZH, JA, KO, TR | ✅ Basic | ✅ 10-stage + universal | ❌ |
| **0** | Any other language | ✅ Statistical | ✅ Universal processor | ❌ |

### Dictionary Coverage

| Language | Code | Synonyms | Bureaucratic | AI Connectors | Sentence Starters | Colloquial | Collocations |
|:---------|:----:|:--------:|:------------:|:-------------:|:-----------------:|:----------:|:------------:|
| English | `en` | 431 | 645 | 152 | 75 | 127 | 1,578 |
| Russian | `ru` | 269 | 486 | 100 | 73 | 102 | 408 |
| Ukrainian | `uk` | 243 | 338 | 75 | 46 | 86 | 38 |
| German | `de` | 138 | 361 | 65 | 54 | 88 | 125 |
| French | `fr` | 141 | 224 | 61 | 49 | 86 | 128 |
| Spanish | `es` | 166 | 230 | 60 | 49 | 78 | 126 |
| Polish | `pl` | 159 | 247 | 60 | 46 | 78 | 34 |
| Portuguese | `pt` | 163 | 204 | 60 | 51 | 79 | 36 |
| Italian | `it` | 168 | 231 | 63 | 49 | 79 | 38 |
| Arabic | `ar` | 126 | 139 | 65 | 40 | 59 | — |
| Chinese | `zh` | 127 | 137 | 51 | 38 | 59 | — |
| Japanese | `ja` | 120 | 123 | 66 | 41 | 59 | — |
| Korean | `ko` | 118 | 120 | 67 | 39 | 59 | — |
| Turkish | `tr` | 119 | 122 | 67 | 43 | 59 | — |

**Universal processor** works for any language using statistical methods — burstiness injection, perplexity normalization, sentence length variation, punctuation diversification.

---

## 🧬 NLP Infrastructure

TextHumanize includes a full NLP stack — all implemented in pure Python with **zero external dependencies:**

| Module | Component | Description |
|:-------|:----------|:------------|
| `pos_tagger.py` | **POS Tagger** (1,917 lines) | Rule-based part-of-speech tagger with suffix/prefix rules for EN/RU/UK/DE |
| `hmm_tagger.py` | **HMM Tagger** (642 lines) | Viterbi-decoding Hidden Markov Model for POS tagging |
| `cjk_segmenter.py` | **CJK Segmenter** (1,277 lines) | Forward/backward max-match Chinese, particle-stripping Korean, character-type Japanese |
| `morphology.py` | **Morphology Engine** (811 lines) | Suffix-based stemming and inflection for RU/UK/EN/DE |
| `collocation_engine.py` | **Collocation Engine** (224 lines) | PMI-based collocation scoring for context-aware synonym selection |
| `word_lm.py` | **Word Language Model** (435 lines) | Bigram/trigram with compressed frequency data for 25 languages |
| `neural_lm.py` | **Neural Char-Level LM** (391 lines) | LSTM-based character language model for perplexity scoring |
| `neural_engine.py` | **Neural Primitives** (610 lines) | Feed-forward net, LSTM cell, embeddings, HMM, layer norm, GELU — all in stdlib |
| `neural_paraphraser.py` | **Seq2Seq Paraphraser** (752 lines) | Encoder-decoder with Bahdanau attention for neural paraphrasing |
| `word_embeddings.py` | **Word Vectors** (399 lines) | Hash-based + cluster embeddings, cosine similarity, nearest neighbors |
| `sentence_split.py` | **Smart Splitter** (338 lines) | Abbreviation-aware sentence splitting (Mr./Dr./URLs/decimals) |
| `lang_detect.py` | **Language Detector** (328 lines) | Character trigram profiling for 25 languages |
| `context.py` | **Contextual Synonyms** (320 lines) | Word sense disambiguation via context windows and topic detection |
| `grammar.py` | **Grammar Checker** (360 lines) | Rule-based grammar for 9 languages (agreement, articles, punctuation) |

> **Total NLP infrastructure:** ~8,800 lines of code, zero pip dependencies.

---

## 🔍 SEO Mode

TextHumanize includes a dedicated SEO workflow to humanize content without harming search rankings:

```python
result = humanize(text, lang="en", profile="seo", intensity=40,
                  constraints={"keep_keywords": ["cloud computing", "API", "microservices"]})
```

| Feature | How It Works |
|:--------|:-------------|
| **Keyword preservation** | `preserve` and `keep_keywords` lists are never modified |
| **Low intensity** | SEO profile defaults to 40% — gentle transformations |
| **No keyword stuffing** | Does not add or repeat keywords |
| **Structure preservation** | Heading hierarchy (H1–H6) preserved |
| **Meta-safe** | Avoids changing first-paragraph introductions (critical for SEO) |
| **Max change control** | `max_change_ratio=0.3` ensures minimal disruption |

---

## 📊 Readability Metrics

`full_readability()` returns 6 reading metrics:

| Index | Range | What It Measures |
|:------|:-----:|:----------------|
| **Flesch Reading Ease** | 0–100 | Higher = easier (60–70 is ideal for web) |
| **Flesch-Kincaid Grade** | 0–18 | US school grade level |
| **Coleman-Liau Index** | 0–18 | Based on characters (not syllables) |
| **Automated Readability Index** | 0–14 | Character and word counts |
| **SMOG Grade** | 0–18 | Polysyllabic word density |
| **Gunning Fog** | 0–20 | Complex words + sentence length |

**Grade interpretation:**

| Grade | Audience |
|:-----:|:---------|
| 5–6 | General public, social media |
| 7–8 | Web content, blog posts |
| 9–10 | Magazine articles |
| 11–12 | Academic papers |
| 13+ | Technical/legal documents |

```python
from texthumanize import full_readability

report = full_readability("Your text here.", lang="en")
print(f"Flesch: {report['flesch_reading_ease']:.1f}")
print(f"Grade: {report['flesch_kincaid_grade']:.1f}")
```

---

## ✍️ Paraphrasing Engine

Rule-based syntactic paraphrasing — no LLM, no API, deterministic:

| Transform | Example |
|:----------|:--------|
| Active → Passive | "The team built the app" → "The app was built by the team" |
| Passive → Active | "The report was written by John" → "John wrote the report" |
| Clause reordering | "After analyzing data, we decided…" → "We decided… after analyzing data" |
| Nominalization reversal | "The implementation of X" → "Implementing X" |
| Connector shuffling | "Furthermore, X. Additionally, Y." → "What's more, X. Also, Y." |
| MWE decomposition | "take into account" → "consider" |
| Hedging injection | "X is true" → "X appears to be true" |
| Perspective rotation | "Users need X" → "X is needed by users" |

```python
from texthumanize import paraphrase

result = paraphrase("The implementation of the new system facilitates optimization.", lang="en")
print(result)  # "Implementing the new system helps optimize."
```

---

## 🎭 Tone Analysis & Adjustment

7-level formality scale with marker-based detection:

| Level | Name | Example Markers |
|:-----:|:-----|:----------------|
| 1 | `slang` | "ya", "gonna", "lol", contractions |
| 2 | `casual` | "pretty much", "kind of", first person |
| 3 | `neutral` | Balanced register |
| 4 | `professional` | "regarding", "in accordance with" |
| 5 | `formal` | "henceforth", "notwithstanding" |
| 6 | `academic` | "thus", "consequently", passive voice |
| 7 | `legal` | "hereinafter", "whereas", "pursuant to" |

```python
from texthumanize import analyze_tone, adjust_tone

tone = analyze_tone("Please submit the documentation.", lang="en")
print(f"Formality: {tone['formality']}")  # "professional"

casual = adjust_tone("It is imperative to proceed immediately.", target="casual", lang="en")
print(casual)  # "We should probably get going on this."
```

---

## 🛡️ Watermark Detection & Cleaning

Detects and removes 6 types of invisible text watermarks:

| Type | How It Hides | Detection Method |
|:-----|:-------------|:-----------------|
| **Zero-width characters** | U+200B, U+200C, U+200D, U+FEFF | Unicode category scanning |
| **Homoglyph substitution** | Latin 'a' → Cyrillic 'а' | Confusable character mapping |
| **Invisible Unicode** | U+2060, U+2061–U+2064 | Codepoint range check |
| **Directional markers** | RTL/LTR overrides | Bidirectional control detection |
| **Soft hyphens** | U+00AD | Pattern matching |
| **Tag characters** | U+E0001–U+E007F | Unicode block scanning |

```python
from texthumanize import detect_watermarks, clean_watermarks

report = detect_watermarks("Te\u200bxt with hid\u200bden marks")
print(f"Found: {report.total_watermarks} watermarks of {len(report.types)} types")

clean = clean_watermarks("Te\u200bxt with hid\u200bden marks")
print(clean)  # "Text with hidden marks"
```

---

## 🔄 Content Spinning

Generate multiple unique variants with spintax support:

```python
from texthumanize import spin, spin_variants

# Single variant
variant = spin("The system provides efficient processing.", lang="en")

# Multiple variants
variants = spin_variants("Original text here.", count=5, lang="en")
for i, v in enumerate(variants):
    print(f"Variant {i+1}: {v}")
```

The spinner uses language-pack synonyms, contextual substitution, and sentence restructuring to produce each variant.

---

## 🔗 Coherence Analysis

Measure paragraph-level text flow:

```python
from texthumanize import analyze_coherence

report = analyze_coherence(text, lang="en")
print(f"Overall coherence: {report['score']:.2f}")
for issue in report.get('issues', []):
    print(f"  ⚠️ {issue['type']}: {issue['description']}")
```

| Metric | What It Measures |
|:-------|:-----------------|
| Paragraph similarity | TF-IDF cosine between adjacent paragraphs |
| Transition quality | Presence and appropriateness of connective phrases |
| Topic continuity | Keyword overlap between sections |
| Reference chains | Pronoun and entity co-reference tracking |

---

## 🔠 Morphological Engine

Rule-based morphology for 4 languages — lemmatization, inflection, declension:

```python
from texthumanize import MorphologyEngine, get_morphology

morph = get_morphology("ru")

# Lemmatize
lemma = morph.lemmatize("процессов")     # → "процесс"

# Get forms
forms = morph.get_forms("оптимизация")   # → ["оптимизации", "оптимизацию", ...]
```

| Language | Operations | Suffix Rules |
|:---------|:----------|:------------|
| Russian | Lemmatization, declension, conjugation | 200+ suffix patterns |
| Ukrainian | Lemmatization, declension | 180+ suffix patterns |
| English | Lemmatization, pluralization | 150+ rules |
| German | Lemmatization, compound splitting | 120+ rules |

---

## 🎨 Stylistic Fingerprinting

Extract and compare author stylometric profiles:

```python
from texthumanize import build_author_profile, compare_fingerprint, anonymize_style

# Build a profile from samples
profile = build_author_profile("Author's writing sample...", lang="en")
print(f"Avg sentence: {profile.avg_sentence_length:.1f} words")
print(f"Vocabulary richness: {profile.vocabulary_richness:.2f}")

# Compare new text to a known author
similarity = compare_fingerprint("New text to attribute", profile)
print(f"Match: {similarity:.0%}")

# Anonymize style — normalize distinctive patterns
anon = anonymize_style("Text with distinctive style markers", lang="en")
```

**Fingerprint dimensions:** Mean sentence length, length variance, vocabulary richness, function word distribution, punctuation profile, discourse marker usage, passive voice ratio, average word length.

---

## 🎛️ Auto-Tuner (Feedback Loop)

Automatically optimize intensity and profile based on feedback:

```python
from texthumanize import AutoTuner

tuner = AutoTuner()

# Process and get feedback
result = tuner.suggest(text, lang="en")

# Provide feedback — was the result good?
tuner.feedback(result, score=0.8)  # 0.0 = bad, 1.0 = perfect

# Next suggestion will adapt
result2 = tuner.suggest(another_text, lang="en")
```

The tuner uses Bayesian-like optimization to find ideal `(intensity, profile)` combinations for your content type.

---

## 🔌 Plugin System

Register custom hooks at any of 20 pipeline stages:

```python
from texthumanize import Pipeline, humanize

# Function hook
def add_disclaimer(text: str, lang: str) -> str:
    return text + "\n\n---\nProcessed by TextHumanize."

Pipeline.register_hook(add_disclaimer, after="naturalization")
result = humanize("Your text here.", lang="en")
Pipeline.clear_plugins()
```

**Available hook points:** `watermark` → `segmentation` → `typography` → `debureaucratization` → `structure` → `repetitions` → `liveliness` → `paraphrasing` → `syntax_rewriting` → `tone` → `universal` → `naturalization` → `paraphrase_engine` → `sentence_restructuring` → `entropy_injection` → `readability` → `grammar` → `coherence` → `validation` → `restore`

---

## 🧪 Using Individual Modules

Every module is independently importable:

```python
# POS Tagging
from texthumanize.pos_tagger import POSTagger
tagger = POSTagger("en")
tags = tagger.tag("The cat sat on the mat".split())

# CJK Segmentation
from texthumanize.cjk_segmenter import CJKSegmenter
seg = CJKSegmenter()
words = seg.segment("自然言語処理は面白い", lang="ja")

# Collocation scoring
from texthumanize.collocation_engine import CollocEngine
engine = CollocEngine("en")
score = engine.collocation_score("make", "decision")
best = engine.best_synonym_in_context("big", "a ___ mistake", ["large", "huge", "great"])

# Perplexity
from texthumanize.word_lm import WordLanguageModel
lm = WordLanguageModel("en")
ppl = lm.word_perplexity("The cat sat on the mat")

# Grammar checking
from texthumanize.grammar import check_grammar
issues = check_grammar("He go to the store yesterday.", lang="en")

# Uniqueness / plagiarism
from texthumanize.uniqueness import uniqueness_score, compare_texts
score = uniqueness_score("Text to check")
sim = compare_texts("Original", "Modified version")

# Content health score
from texthumanize.health_score import content_health
report = content_health("Your article text...", lang="en")
print(f"Health: {report.score}/100")

# Custom dictionary overlay
from texthumanize.dictionaries import load_dict, update_dict
update_dict("en", {"bureaucratic": {"utilize": "use", "facilitate": "help"}})
```

---

## 💻 CLI Reference

```bash
# Basic humanization
texthumanize input.txt -l en -p web -i 70 -o output.txt

# AI detection
texthumanize detect input.txt -l en
texthumanize detect input.txt -l en --json

# With all analysis
texthumanize input.txt -l en --analyze --explain --detect-ai

# Paraphrasing
texthumanize input.txt -l en --paraphrase -o out.txt

# Tone adjustment
texthumanize input.txt -l en --tone casual
texthumanize input.txt -l en --tone-analyze

# Watermark detection
texthumanize input.txt --watermarks

# Content spinning
texthumanize input.txt -l en --spin --variants 5

# Coherence & readability
texthumanize input.txt -l en --coherence --readability

# Start REST API server
texthumanize dummy --api --port 8080

# Train neural detector
texthumanize train --samples 1000 --epochs 50 --output weights/

# Run benchmarks
texthumanize benchmark --json

# Pipe mode
echo "Text to humanize" | texthumanize - -l en

# Keyword preservation
texthumanize input.txt -l en --keep "API,cloud" --brand "TextHumanize"

# Verbose mode with report
texthumanize input.txt -l en --verbose --report report.json
```

### CLI Flags

| Flag | Description |
|:-----|:------------|
| `-l`, `--lang` | Language code (required) |
| `-p`, `--profile` | Processing profile |
| `-i`, `--intensity` | Intensity 0–100 |
| `-o`, `--output` | Output file path |
| `--seed` | PRNG seed for reproducibility |
| `--keep` | Comma-separated keywords to preserve |
| `--brand` | Brand terms to never modify |
| `--max-change` | Maximum change ratio (0.0–1.0) |
| `--analyze` | Print analysis report |
| `--explain` | Print change explanation |
| `--detect-ai` | Run AI detection |
| `--paraphrase` | Paraphrase mode |
| `--tone` | Adjust tone to target level |
| `--tone-analyze` | Analyze current tone |
| `--watermarks` | Detect watermarks |
| `--spin` | Spin mode |
| `--variants N` | Number of spin variants |
| `--coherence` | Coherence analysis |
| `--readability` | Readability metrics |
| `--api` | Start REST API server |
| `--port` | API server port (default: 8080) |
| `--verbose` | Detailed output |
| `--report` | Save JSON report |
| `--json` | JSON output format |

---

## 🌐 REST API Server

Zero-dependency HTTP server with rate limiting and CORS:

```bash
python -m texthumanize.api --port 8080
```

### Endpoints

| Method | Endpoint | Description |
|:-------|:---------|:------------|
| `POST` | `/humanize` | Full humanization |
| `POST` | `/detect-ai` | AI detection (single or batch) |
| `POST` | `/analyze` | Text metrics |
| `POST` | `/paraphrase` | Paraphrase text |
| `POST` | `/tone/analyze` | Tone analysis |
| `POST` | `/tone/adjust` | Tone adjustment |
| `POST` | `/watermarks/detect` | Detect watermarks |
| `POST` | `/watermarks/clean` | Remove watermarks |
| `POST` | `/spin` | Content spinning |
| `POST` | `/spin/variants` | Spin N variants |
| `POST` | `/coherence` | Coherence analysis |
| `POST` | `/readability` | Readability metrics |
| `POST` | `/sse/humanize` | SSE streaming humanization |
| `GET` | `/health` | Health check |
| `GET` | `/` | API documentation index |
| `OPTIONS` | `*` | CORS preflight |

**Rate limit:** 10 req/s per IP, burst 20 · **Max body:** 5 MB

### Example

```bash
# Humanize
curl -X POST http://localhost:8080/humanize \
  -H "Content-Type: application/json" \
  -d '{"text": "Your text here.", "lang": "en", "profile": "web", "intensity": 70}'

# AI detection
curl -X POST http://localhost:8080/detect-ai \
  -H "Content-Type: application/json" \
  -d '{"text": "Text to check.", "lang": "en"}'

# SSE streaming
curl -N http://localhost:8080/sse/humanize \
  -H "Content-Type: application/json" \
  -d '{"text": "Long text...", "lang": "en"}'
```

### Python Client

```python
import requests

resp = requests.post("http://localhost:8080/humanize", json={
    "text": "Your text",
    "lang": "en",
    "profile": "web"
})
print(resp.json()["text"])
```

---

## ⚡ Async API

Native `asyncio` support for all public functions:

```python
import asyncio
from texthumanize import async_humanize, async_detect_ai, async_analyze
from texthumanize import async_paraphrase, async_humanize_batch, async_detect_ai_batch

async def main():
    result = await async_humanize("Text to process", lang="en", seed=42)
    print(result.text)

    ai = await async_detect_ai("Text to check", lang="en")
    print(f"AI: {ai['score']:.0%}")

    # Parallel batch
    results = await async_humanize_batch(["Text 1", "Text 2"], lang="en")

asyncio.run(main())
```

---

## 📈 Performance & Benchmarks

All benchmarks on Apple Silicon (M-series), Python 3.12, single thread, after warm-up.

### Speed

| Function | Text Size | Avg Latency |
|:---------|:----------|:-----------:|
| `humanize()` | ~30 words | **~5 s** |
| `humanize()` | ~80 words | **~10 s** |
| `humanize(phantom=True)` | ~80 words | **~12 s** |
| `detect_ai()` | ~30 words | **~1 s** |
| `detect_ai()` | ~80 words | **~3 s** |
| `paraphrase()` | ~80 words | **< 1 ms** |
| `analyze_tone()` | ~80 words | **< 1 ms** |
| `analyze()` | ~80 words | **~80 ms** |

### AI Score Reduction

```
┌──────────────────────────────────────────────────────────┐
│  TextHumanize v0.28.0 — AI Score Benchmark              │
├──────────────────────────────────────────────────────────┤
│  EN (web/50):    94% → 27%    (reduction: -67pp)        │
│  EN (web/60):    94% → 23%    (reduction: -71pp)        │
│  EN (web/70):    94% →  2%    (reduction: -92pp)        │
├──────────────────────────────────────────────────────────┤
│  RU (web/50):    80% →  5%    (reduction: -75pp)        │
│  UK (web/50):    75% → 17%    (reduction: -58pp)        │
├──────────────────────────────────────────────────────────┤
│  Best result:    EN web/70 — 94% → 2%  (-92pp)          │
└──────────────────────────────────────────────────────────┘
```

### Properties

| Property | Value |
|:---------|:-----:|
| Cold start | **< 100 ms** |
| LRU cache hit | **11× faster** than cold |
| External network calls | **0** (offline-first) |
| Deterministic (same seed) | ✅ Always |
| Pipeline timeout | 30 s (configurable) |
| API rate limiting | 10 req/s per IP, burst 20 |
| Max input size | 1 MB |
| Memory per call | 4–200 KB |

> **Run benchmarks yourself:**
> ```bash
> python benchmarks/run_benchmark.py
> texthumanize benchmark --json
> ```

---

## 🏗️ Architecture

```
texthumanize/                        # 122 Python modules, 235,000+ lines
├── core.py                          # Facade: 28+ public functions (2,391 lines)
├── pipeline.py                      # 38-stage pipeline + adaptive intensity (1,553 lines)
├── sentence_validator.py            # SentenceValidator™: interstage quality gate (350 lines)
├── phantom.py                       # PHANTOM™: gradient-guided adversarial engine (2,943 lines)
├── api.py                           # REST API server, 16 endpoints (396 lines)
├── async_api.py                     # Async wrappers for all functions (200 lines)
├── cli.py                           # CLI (15+ commands) (1,492 lines)
├── exceptions.py                    # Exception hierarchy (77 lines)
│
├── ── Detection & Analysis ──
├── detectors.py                     # AI detector: 18 heuristic metrics (2,441 lines)
├── statistical_detector.py          # 35-feature logistic regression (1,149 lines)
├── neural_detector.py               # MLP neural detector, pure Python (1,094 lines)
├── analyzer.py                      # Artificiality scoring + readability (506 lines)
│
├── ── NLP Infrastructure ──
├── neural_engine.py                 # NN primitives: MLP, LSTM, HMM (610 lines)
├── neural_lm.py                     # LSTM character-level LM (391 lines)
├── neural_paraphraser.py            # Seq2Seq with Bahdanau attention (752 lines)
├── pos_tagger.py                    # Rule-based POS tagger, 4 langs (1,917 lines)
├── hmm_tagger.py                    # Viterbi HMM POS tagger (642 lines)
├── cjk_segmenter.py                 # Chinese/Japanese/Korean segmenter (1,277 lines)
├── morphology.py                    # Morphological engine, 4 langs (1,015 lines)
├── word_lm.py                       # Word-level language model (435 lines)
├── word_embeddings.py               # Lightweight word vectors (399 lines)
├── collocation_engine.py            # PMI collocation scoring (224 lines)
├── sentence_split.py                # Smart sentence splitter (338 lines)
├── lang_detect.py                   # Trigram-based language detection (328 lines)
├── context.py                       # WSD — contextual synonyms (320 lines)
│
├── ── Pipeline Stages ──
├── watermark.py                     # Watermark detection & cleaning (524 lines)
├── segmenter.py                     # URL/code/brand protection (308 lines)
├── normalizer.py                    # Typography normalization (199 lines)
├── decancel.py                      # Debureaucratization (332 lines)
├── structure.py                     # Sentence diversification (319 lines)
├── repetitions.py                   # Repetition reduction (229 lines)
├── liveliness.py                    # Colloquialism injection (171 lines)
├── paraphraser_ext.py               # Semantic paraphrasing (887 lines)
├── syntax_rewriter.py               # Syntax rewriting: 8+ transforms (2,516 lines)
├── tone_harmonizer.py               # Tone alignment (98 lines)
├── universal.py                     # Language-agnostic processor (384 lines)
├── naturalizer.py                   # Core naturalization engine (3,444 lines)
├── paraphrase_engine.py             # MWE, hedging, perspective (1,152 lines)
├── sentence_restructurer.py         # Deep sentence transforms (1,385 lines)
├── entropy_injector.py              # Burstiness + entropy injection (1,187 lines)
├── readability_opt.py               # Readability optimization (274 lines)
├── grammar_fix.py                   # Grammar correction (72 lines)
├── coherence_repair.py              # Coherence repair (446 lines)
├── fingerprint_randomizer.py        # Anti-fingerprint diversification (408 lines)
├── validator.py                     # Quality validation (170 lines)
│
├── ── Extended Features ──
├── tone.py                          # Tone analysis & adjustment (547 lines)
├── paraphrase.py                    # Standalone paraphrasing API (406 lines)
├── spinner.py                       # Content spinning + spintax (370 lines)
├── coherence.py                     # Coherence analysis (357 lines)
├── grammar_guard.py                 # Grammar Guard with safety gates (616 lines)
├── grammar.py                       # Grammar checker, 25 langs (360 lines)
├── uniqueness.py                    # Plagiarism detection (226 lines)
├── health_score.py                  # Composite content health (188 lines)
├── semantic.py                      # Semantic similarity (145 lines)
├── fingerprint.py                   # Author fingerprinting (371 lines)
├── stylistic.py                     # Stylistic analysis + presets (721 lines)
├── plagiarism.py                    # Plagiarism N-gram check (271 lines)
├── diff_report.py                   # HTML/JSON diff reports (277 lines)
│
├── ── Infrastructure ──
├── autotune.py                      # Auto-tuner feedback loop (259 lines)
├── benchmark_suite.py               # Quality benchmarks (401 lines)
├── training.py                      # Neural training loop (1,264 lines)
├── dict_trainer.py                  # Corpus-based dictionary trainer (293 lines)
├── quality_gate.py                  # CI/CD content quality gate (280 lines)
├── dashboard.py                     # HTML dashboard reports (229 lines)
├── dictionaries.py                  # Custom dictionary overlays (174 lines)
├── ai_backend.py                    # LLM backend: OpenAI/Ollama/OSS (931 lines)
├── ai_markers.py                    # AI marker management (528 lines)
├── gptzero.py                       # GPTZero API integration (372 lines)
├── cache.py                         # Thread-safe LRU cache (93 lines)
│
├── ── Data ──
├── _colloc_data.py                  # PMI collocations (455 lines)
├── _replacement_data.py             # AI-word replacements (957 lines)
├── _word_freq_data.py               # Word frequency data (1,532 lines)
├── weights/                         # Pre-trained model weights (472 KB)
│   ├── detector_weights.json.zb85   # MLP detector (54 KB)
│   └── lm_weights.json.zb85        # LSTM LM (418 KB)
│
└── lang/                            # 25 language packs
    ├── en.py · ru.py · uk.py · de.py (Tier 1 — full pipeline)
    ├── fr.py · es.py · pl.py · pt.py · it.py · nl.py · sv.py · cs.py · ro.py · hu.py · da.py (Tier 2)
    └── ar.py · zh.py · ja.py · ko.py · tr.py · hi.py · vi.py · th.py · id_.py · he.py (Tier 3)
```

**Design principles:**

| Principle | Implementation |
|:----------|:--------------|
| **Modular** | Each stage is a standalone class; every module is independently importable |
| **Zero dependencies** | Pure Python stdlib — no pip packages at all |
| **Declarative rules** | Language packs are data-only (dicts), no logic in lang files |
| **Idempotent** | Running the pipeline twice won't double-transform text |
| **Safe defaults** | Works out-of-the-box with sensible profiles |
| **Lazy imports** | PEP 562 lazy loading — only imports what you use |
| **Deterministic** | Seed-based PRNG for reproducible output |
| **Extensible** | Plugin hooks at 38 stages, custom dictionaries, AI backend |

---

## 🟦 TypeScript / JavaScript Port

Core TextHumanize functionality in TypeScript for Node.js and browsers:

```typescript
import { humanize, detectAi, analyze } from 'texthumanize';

const result = humanize("Text to process", { lang: "en", profile: "web" });
console.log(result.text);
console.log(result.changeRatio);

const ai = detectAi("Text to check", { lang: "en" });
console.log(`AI: ${(ai.score * 100).toFixed(0)}%`);
```

| Feature | Status |
|:--------|:------:|
| `humanize()` | ✅ |
| `detectAi()` | ✅ |
| `analyze()` | ✅ |
| Language packs: EN, RU | ✅ |
| Universal processor | ✅ |

```bash
cd js/ && npm install && npm test
```

---

## 🐘 PHP Library

Full-featured PHP port with Composer support:

```php
<?php
use TextHumanize\TextHumanize;

$th = new TextHumanize();

$result = $th->humanize("Text to process", "en", [
    "profile" => "web",
    "intensity" => 70,
]);
echo $result->text;
echo $result->changeRatio;

$ai = $th->detectAi("Check this text", "en");
echo $ai["score"] . " — " . $ai["verdict"];
```

| Feature | Status |
|:--------|:------:|
| All 25 language packs | ✅ |
| `humanize()`, `humanize_batch()`, `humanize_chunked()` | ✅ |
| `detect_ai()`, `analyze()`, `explain()` | ✅ |
| `paraphrase()`, `analyze_tone()`, `adjust_tone()` | ✅ |
| `detect_watermarks()`, `clean_watermarks()` | ✅ |
| `spin()`, `spin_variants()` | ✅ |
| `analyze_coherence()`, `full_readability()` | ✅ |
| Plugin system | ✅ |
| **223 PHPUnit tests** | ✅ |

```bash
cd php/ && composer install && vendor/bin/phpunit
```

---

## ✅ Testing & Quality

| Platform | Tests | Status |
|:---------|------:|:------:|
| **Python** (pytest, 3.9–3.13) | 2,073 | ✅ All passing |
| **PHP** (PHPUnit, 8.1–8.3) | 223 | ✅ All passing |
| **TypeScript** (Jest) | 28 | ✅ All passing |
| **Total** | **2,207** | ✅ |

```bash
# Python
pytest -q                          # 2,073 passed
pytest --cov=texthumanize          # Coverage report
ruff check texthumanize/           # Lint
mypy texthumanize/                 # Type check

# PHP
cd php && vendor/bin/phpunit       # 223 tests

# TypeScript
cd js && npm test                  # 28 tests
```

**CI/CD:** Every push triggers Python 3.9–3.13 + PHP 8.1–8.3 matrix, ruff lint, mypy type check, pytest with coverage ≥ 70%.

---

## 🛡️ Security & Limits

| Aspect | Implementation |
|:-------|:--------------|
| **Input limits** | 1 MB text, 5 MB API body |
| **Network calls** | **Zero.** No telemetry, no analytics, no phone-home |
| **Dependencies** | **Zero.** Pure stdlib only |
| **Regex safety** | All patterns are linear-time; no user input compiled to regex |
| **Reproducibility** | Seed-based PRNG, deterministic output |
| **No eval/exec** | No dynamic code execution |
| **Rate limiting** | Token bucket (API): 10 req/s, burst 20 |
| **Sandboxing** | Resource limits documented for production deployment |

### Threat Model

| Threat | Mitigation |
|:-------|:-----------|
| Data exfiltration | Zero network calls — impossible |
| ReDoS | All regex patterns audited for linear-time complexity |
| Memory exhaustion | 1 MB input limit, streaming for large texts |
| Model poisoning | Weights are read-only compressed JSON; no runtime training by default |
| Dependency supply chain | Zero pip dependencies — nothing to compromise |

---

## 🏢 For Business & Enterprise

| Requirement | How TextHumanize Delivers |
|:------------|:-------------------------|
| **Predictability** | Seed-based PRNG — same input + seed = identical output |
| **Privacy** | 100% local. Zero network calls. No data leaves your server |
| **Auditability** | Every call returns `change_ratio`, `quality_score`, `similarity`, `explain()` report |
| **Integration** | Python SDK · JS SDK · PHP SDK · CLI · REST API · Docker · SSE streaming |
| **Reliability** | 2,207 tests across 3 platforms, CI/CD with ruff + mypy |
| **No vendor lock-in** | Zero dependencies. No cloud APIs, no API keys, no rate limits |
| **Language coverage** | 14 full language packs + universal processor for any language |
| **Self-hosted** | Docker image, pip install, on-premise deployment |
| **Content quality gate** | `quality_gate.py` for CI/CD pipeline integration |
| **Custom training** | Train from your own corpus with `dict_trainer` and `training.py` |
| **Brand safety** | Keyword preservation, brand term protection, max change control |

### Processing Modes

| Mode | Description | Use Case |
|:-----|:------------|:---------|
| `humanize()` | Full 38-stage pipeline | General-purpose normalization |
| `humanize_batch()` | Parallel processing (N workers) | Bulk content processing |
| `humanize_chunked()` | Split + process + rejoin | Documents > 10K chars |
| `humanize_until_human()` | Iterative (loop until target score) | High-quality output |
| `humanize_stream()` | SSE paragraph streaming | Real-time UI |
| `humanize_ai()` | Rules + LLM backend (OpenAI/Ollama) | Maximum quality |

### Docker Deployment

```bash
docker build -t texthumanize .
docker run -p 8080:8080 texthumanize --api --port 8080

# Process a file
docker run -v $(pwd):/data texthumanize /data/input.txt -o /data/output.txt -l en
```

---

## ❓ FAQ & Troubleshooting

**Q: Does TextHumanize guarantee passing GPTZero / Originality.ai / Turnitin?**
No. TextHumanize is a style normalization tool. It reduces AI-like patterns but does not guarantee bypassing external AI detectors. See [Limitations](#-limitations).

**Q: What's the best profile for reducing AI detection scores?**
`chat` with intensity 60–80 gives the largest reduction (up to -53 percentage points in our benchmarks). For professional content, try `web` at 70.

**Q: How do I preserve keywords (e.g., for SEO)?**
Use `preserve=["keyword1", "keyword2"]` or the SEO profile: `profile="seo"`.

**Q: Can I use this for commercial projects?**
Yes, with a commercial license. See [License & Pricing](#-license--pricing).

**Q: Does it work offline? Does it send data to the internet?**
100% offline. Zero network calls. Not even a health check ping. All processing is local.

**Q: Why is the first call slower?**
The first call loads language packs and initializes caches. Subsequent calls are 11× faster via LRU cache.

**Q: Can I train it on my own data?**
Yes — `dict_trainer.py` trains custom dictionaries from your corpus, and `training.py` can retrain the neural detector/LM.

**Q: How do I add support for a new language?**
Create a language pack in `texthumanize/lang/your_lang.py` following the existing pattern (15 required sections). Or use the universal processor which works with any language automatically.

**Q: Can I use individual modules (e.g., just POS tagger) without the full pipeline?**
Yes. Every module is independently importable. See [Using Individual Modules](#-using-individual-modules).

**Q: Is there a GUI?**
Try the [Live Demo](https://humanizekit.tester-buyreadysite.website/). For local use, the REST API + SSE streaming integrates easily with any frontend.

**Q: How deterministic is it?**
100% deterministic when using the same `seed`. Same input + same seed + same version = byte-identical output.

**Q: What Python versions are supported?**
3.9, 3.10, 3.11, 3.12, and 3.13 — all tested in CI.

---

## 🆕 What's New in v0.28.0

### Web Platform — Auth, Payments & Freemium (NEW)
- **User registration** with email/password + Google OAuth 2.0
- **Multi-tier pricing** — Free / Starter $9 / Pro $19 / Business $49/month with monthly/annual toggle
- **API key management** — create, revoke, and group keys per plan (1 / 5 / 20 keys)
- **Monobank Acquiring** payment integration with webhook activation
- **Admin panel** — user management, plan overrides, payment history, usage stats
- **Freemium gates** — guests limited to 3 requests/day; text results blurred after 500 chars
- **API authentication** — Bearer token support with session-based guest quota tracking
- **Expanded API docs** — authentication guide, per-plan rate limits, PAYG billing docs, error codes (401/429)
- **Competitor comparison table** added to Pricing page (vs Quillbot, Undetectable.ai, StealthGPT)

### SentenceValidator™ — Interstage Quality Gate (v0.27.0)
- **`sentence_validator.py` (350 lines)** — sentence-level artifact detection running at 7 checkpoints between pipeline stages
- **10 artifact checks per sentence:** duplicate words, broken contractions, orphaned punctuation, double conjunctions, dangling conjunctions, unterminated parens, triple+ repeats, fragment chains, conjunction chains, empty sentences
- **Final sanitization** in `run()` method catches post-loop residual artifacts

### Stats
- **2,073 tests** · **122 modules** · **235,000+ lines** · **25 languages** · **38-stage pipeline**

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, testing, and PR guidelines.

**Areas for contribution:** New language packs · Improved synonym dictionaries · Better grammar rules · Performance optimizations · Additional integrations

```bash
git clone https://github.com/ksanyok/TextHumanize.git
cd TextHumanize
pip install -e ".[dev]"
pytest -q                    # Run tests
ruff check texthumanize/     # Lint
```

---

## ⚠️ Limitations

TextHumanize is a **style normalization** tool. Please be aware of realistic expectations:

| Aspect | Current State | Notes |
|:-------|:-------------|:------|
| **EN humanization** | Reduces AI markers by 71–92% | Built-in detector; 94% → 2–23% |
| **RU humanization** | Reduces AI markers by 75% | Built-in detector; 80% → 5% |
| **UK humanization** | Reduces AI markers by 58% | Built-in detector; 75% → 17% |
| **External AI detectors** | **Not a reliable bypass** | GPTZero, Originality.ai use different models |
| **Short texts (< 50 words)** | Limited effect | Not enough context for meaningful transformation |
| **Performance** | 300–500 ms per paragraph | Fast enough for batch; not sub-millisecond |
| **Built-in AI detector** | Heuristic + statistical + neural | Useful for internal scoring; not equivalent to commercial detectors |
| **Higher intensity** | ≠ always lower AI score | Some transforms at high intensity may create new patterns |

**What TextHumanize does well:**
- ✅ Removes formulaic connectors ("furthermore", "it is important to note")
- ✅ Varies sentence length to add human-like burstiness
- ✅ Replaces bureaucratic vocabulary with simpler alternatives
- ✅ Deterministic, reproducible results with seed control
- ✅ 100% offline, no data leaks, zero dependencies
- ✅ Full audit trail with every call

**What TextHumanize does NOT do:**
- ❌ Guarantee passing external AI detectors (GPTZero, Originality.ai, Turnitin)
- ❌ Rewrite text at the semantic level (it's rule-based, not LLM-based)
- ❌ Handle domain-specific jargon (medical, legal, etc.) without custom dictionaries

---

## 💛 Support the Project

If TextHumanize saves you time or money, consider supporting development:

[![PayPal](https://img.shields.io/badge/PayPal-Donate-blue.svg?logo=paypal)](https://www.paypal.com/cgi-bin/webscr?cmd=_donations&business=ksanyok%40me.com&item_name=TextHumanize&currency_code=USD)

---

## 📄 License & Pricing

TextHumanize uses a **dual license model**:

| Use Case | License | Cost |
|:---------|:--------|:----:|
| Personal / Academic / Open-source | Free License | **Free** |
| Commercial — 1 dev, 1 project | Indie | **$199/year** |
| Commercial — up to 5 devs | Startup | **$499/year** |
| Commercial — up to 20 devs | Business | **$1,499/year** |
| Enterprise / On-prem / SLA / White-label | Enterprise | [Contact us](mailto:ksanyok@me.com) |

All commercial licenses include full source code, all updates, priority email support, and access to PHANTOM™ + ASH™ proprietary technologies. **Annual billing — well below market alternatives** ($10–50/mo per cloud API at comparable scale).

**[Full licensing details →](COMMERCIAL.md)** · See [LICENSE](LICENSE) for legal text · **Contact:** [ksanyok@me.com](mailto:ksanyok@me.com)

---

<p align="center">
  <a href="https://ksanyok.github.io/TextHumanize/">Documentation</a> ·
  <a href="https://humanizekit.tester-buyreadysite.website/">Live Demo</a> ·
  <a href="https://pypi.org/project/texthumanize/">PyPI</a> ·
  <a href="https://github.com/ksanyok/TextHumanize">GitHub</a> ·
  <a href="https://github.com/ksanyok/TextHumanize/issues">Issues</a> ·
  <a href="https://github.com/ksanyok/TextHumanize/discussions">Discussions</a> ·
  <a href="COMMERCIAL.md">Commercial License</a>
</p>
