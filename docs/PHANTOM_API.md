# PHANTOM™ API Reference

> **PHANTOM™** (PHysical Adversarial Network for Text Optimization and Manipulation)
> — gradient-guided bypass engine for AI detection evasion.

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Architecture](#architecture)
4. [API Reference](#api-reference)
   - [humanize() — PHANTOM mode](#humanize--phantom-mode)
   - [phantom_optimize()](#phantom_optimize)
   - [get_phantom()](#get_phantom)
   - [PhantomEngine](#phantomengine)
   - [ForgeResult](#forgeresult)
   - [ForgeStep](#forgestep)
   - [FeatureGapReport](#featuregapreport)
   - [FeatureGap](#featuregap)
5. [Examples](#examples)
6. [Supported Languages](#supported-languages)
7. [Performance](#performance)

---

## Overview

PHANTOM™ is a three-stage optimization engine that reduces AI detection scores
by analyzing neural feature gradients and applying targeted text transformations:

1. **ORACLE** — Computes numerical gradients of the neural detector to identify
   which text features contribute most to AI classification.
2. **SURGEON** — Applies 32 targeted text operations (synonym swap, sentence
   restructuring, filler injection, etc.) guided by the gradient analysis.
3. **FORGE** — Iterates ORACLE → SURGEON in a loop until the target detection
   score is reached or no further improvement is possible.

**Key metrics (v0.26.0):**
- 93% bypass rate (14/15 texts classified as "human")
- EN 100%, RU 100%, UK 80%
- DE, FR, ES support with full dictionaries

---

## Quick Start

### Via `humanize()` (recommended)

```python
import texthumanize as th

result = th.humanize(
    "AI-generated text here...",
    lang="en",
    phantom=True,           # Enable PHANTOM™
    phantom_budget=1.0,     # Edit budget (0.0–1.0)
    phantom_target=0.30,    # Target AI score
    seed=42,                # Reproducibility
)
print(result.text)
print(f"AI score: {result.ai_probability:.3f}")
print(f"Verdict: {result.detection_verdict}")
```

### Direct API

```python
from texthumanize import phantom_optimize, ForgeResult

result: ForgeResult = phantom_optimize(
    "AI-generated text here...",
    lang="en",
    max_iterations=8,
    target_score=0.30,
    budget=1.0,
    seed=42,
)
print(result.optimized_text)
print(result.summary())
```

---

## Architecture

```
Input Text
    │
    ▼
┌─────────┐     ┌──────────┐     ┌─────────┐
│  ORACLE  │────▶│  SURGEON  │────▶│  FORGE   │
│          │     │           │     │          │
│ Gradient │     │ 32 text   │     │ Iterate  │
│ analysis │     │ operations│     │ until    │
│ (35 feat)│     │ per gap   │     │ target   │
└─────────┘     └──────────┘     └─────────┘
    │                                  │
    ▼                                  ▼
FeatureGapReport              ForgeResult
(per-feature gradients)       (optimized text)
```

### 35 Neural Features

The detector uses these features for AI classification:

| Category | Features |
|---|---|
| **Lexical** | TTR, avg word length, rare word ratio, content word ratio |
| **Syntactic** | Avg sentence length, sentence length std, max/min sentence ratio |
| **Entropy** | Shannon entropy, conditional entropy, entropy rate |
| **Burstiness** | Sentence length burstiness, word repetition patterns |
| **Punctuation** | Comma/semicolon/dash/question/exclamation rates |
| **Readability** | Flesch-Kincaid, fog index analogue |
| **Perplexity** | Mean perplexity, CV, autocorrelation, peak ratio |
| **Structural** | Paragraph count, list/header ratio, transition density |

### 32 Surgeon Operations

The Surgeon applies targeted edits based on gradient priorities:

- Synonym insertion/replacement (via SynonymDB + language-specific dictionaries)
- Sentence splitting/merging
- Filler sentence injection
- Question sentence injection
- Discourse marker insertion
- Comma/dash/semicolon manipulation
- Word repetition injection
- Sentence length variance adjustment
- Rare word injection
- AI pattern replacement (language-specific)
- And more...

---

## API Reference

### `humanize()` — PHANTOM mode

The simplest way to use PHANTOM™ is through the main `humanize()` function:

```python
import texthumanize as th

result = th.humanize(
    text: str,
    lang: str = "en",
    *,
    phantom: bool = False,          # Enable PHANTOM™ engine
    phantom_budget: float = 1.0,    # Edit budget (0.0 = minimal, 1.0 = full)
    phantom_target: float = 0.30,   # Target AI detection score
    seed: int | None = None,
    # ... other humanize params
) -> HumanizeResult
```

When `phantom=True`, the pipeline runs:
1. Normal rule-based humanization (naturalizer, spinner, ASH, etc.)
2. PHANTOM™ optimization on the result
3. Grammar post-processing (RU/UK)

The best of the two results (lower AI score) is returned.

---

### `phantom_optimize()`

Module-level convenience function for direct PHANTOM™ optimization.

```python
from texthumanize import phantom_optimize

def phantom_optimize(
    text: str,
    lang: str = "en",
    *,
    max_iterations: int = 8,
    target_score: float = 0.30,
    budget: float = 1.0,
    seed: int | None = None,
) -> ForgeResult
```

**Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `text` | `str` | — | Input text to optimize |
| `lang` | `str` | `"en"` | Language code (`en`, `ru`, `uk`, `de`, `fr`, `es`) |
| `max_iterations` | `int` | `8` | Maximum FORGE iterations |
| `target_score` | `float` | `0.30` | Stop when AI score ≤ this value |
| `budget` | `float` | `1.0` | Edit budget (0.0–1.0). Lower = fewer edits |
| `seed` | `int \| None` | `None` | Random seed for reproducibility |

**Returns:** `ForgeResult`

---

### `get_phantom()`

Returns a singleton `PhantomEngine` instance.

```python
from texthumanize import get_phantom

engine = get_phantom()  # PhantomEngine (cached singleton)
```

---

### `PhantomEngine`

Main PHANTOM™ engine combining ORACLE + SURGEON + FORGE.

```python
from texthumanize import PhantomEngine

class PhantomEngine:
    def __init__(self) -> None: ...
    
    def optimize(
        self,
        text: str,
        lang: str = "en",
        *,
        max_iterations: int = 8,
        target_score: float = 0.30,
        budget: float = 1.0,
        seed: int | None = None,
    ) -> ForgeResult: ...
    
    def analyze(
        self,
        text: str,
        lang: str = "en",
    ) -> FeatureGapReport: ...
    
    def gradient_report(
        self,
        text: str,
        lang: str = "en",
    ) -> str: ...
```

**Methods:**

| Method | Returns | Description |
|---|---|---|
| `optimize(text, lang, ...)` | `ForgeResult` | Full PHANTOM™ optimization loop |
| `analyze(text, lang)` | `FeatureGapReport` | Feature analysis without modifications |
| `gradient_report(text, lang)` | `str` | Human-readable gradient table for debugging |

---

### `ForgeResult`

Result of PHANTOM™ optimization.

```python
from texthumanize import ForgeResult
```

**Fields:**

| Field | Type | Description |
|---|---|---|
| `original_text` | `str` | Input text before optimization |
| `optimized_text` | `str` | Output text after optimization |
| `original_score` | `float` | AI detection score before (0.0–1.0) |
| `final_score` | `float` | AI detection score after (0.0–1.0) |
| `iterations` | `int` | Number of FORGE iterations executed |
| `trace` | `list[ForgeStep]` | Per-iteration trace data |
| `final_report` | `FeatureGapReport` | Feature analysis of the final text |

**Properties:**

| Property | Type | Description |
|---|---|---|
| `improvement` | `float` | Score improvement (`original_score - final_score`) |
| `bypassed` | `bool` | `True` if `final_score ≤ 0.34` (verdict: "human") |

**Methods:**

| Method | Returns | Description |
|---|---|---|
| `summary()` | `str` | Multi-line human-readable optimization summary |

**Example:**

```python
result = phantom_optimize("AI text...", lang="en")

print(f"Score: {result.original_score:.3f} → {result.final_score:.3f}")
print(f"Improvement: {result.improvement:.3f}")
print(f"Bypassed: {result.bypassed}")
print(f"Iterations: {result.iterations}")
print(result.summary())
```

---

### `ForgeStep`

One step of the FORGE optimization loop.

| Field | Type | Description |
|---|---|---|
| `iteration` | `int` | Zero-based iteration index |
| `score` | `float` | Detection score at this step |
| `top_features` | `list[str]` | Names of top contributing features |
| `top_contributions` | `list[float]` | Contribution values of those features |

**Example:**

```python
result = phantom_optimize("AI text...", lang="en")
for step in result.trace:
    print(f"Iter {step.iteration}: score={step.score:.3f}")
    for feat, contrib in zip(step.top_features, step.top_contributions):
        print(f"  {feat}: {contrib:+.4f}")
```

---

### `FeatureGapReport`

Complete analysis of a text's AI detection features.

| Field | Type | Description |
|---|---|---|
| `score` | `float` | Current AI detection score |
| `raw_features` | `list[float]` | Raw (unnormalized) 35-dim feature vector |
| `normed_features` | `list[float]` | Z-score normalized feature vector |
| `gradients` | `list[float]` | Per-feature gradient (impact on score) |
| `gaps` | `list[FeatureGap]` | Per-feature gap analysis |
| `lang` | `str` | Language code |

**Methods:**

| Method | Returns | Description |
|---|---|---|
| `top_gaps(n=10)` | `list[FeatureGap]` | Top N features with highest contribution |
| `actionable_gaps()` | `list[FeatureGap]` | Features that can be improved by Surgeon |

---

### `FeatureGap`

One feature's gap from human-like values.

| Field | Type | Description |
|---|---|---|
| `index` | `int` | Feature index (0–34) |
| `name` | `str` | Feature name (e.g. `"burstiness"`) |
| `raw_value` | `float` | Raw feature value |
| `normed_value` | `float` | Z-score normalized value |
| `gradient` | `float` | Gradient (how much this feature affects the score) |
| `raw_gradient` | `float` | Raw (unnormalized) gradient |
| `contribution` | `float` | Feature's contribution to the total AI score |
| `mean` | `float` | Human-profile mean for this feature |
| `std` | `float` | Human-profile standard deviation |

**Properties:**

| Property | Type | Description |
|---|---|---|
| `target_direction` | `str` | `"decrease"` if gradient > 0, else `"increase"` |

---

## Examples

### Diagnostic Analysis

```python
from texthumanize import get_phantom

engine = get_phantom()
report = engine.analyze("AI-generated text here...", lang="en")

print(f"AI score: {report.score:.3f}")
for gap in report.top_gaps(5):
    print(f"  {gap.name}: value={gap.raw_value:.4f}, "
          f"gradient={gap.gradient:+.4f}, "
          f"direction={gap.target_direction}")
```

### Gradient Debugging

```python
engine = get_phantom()
print(engine.gradient_report("AI-generated text here..."))
```

Output:
```
Feature                  Raw Value  Normed  Gradient  Contribution  Direction
─────────────────────────────────────────────────────────────────────────────
burstiness                  0.0321   -1.42    +0.082       +0.116  decrease
sentence_length_std         2.1340   -0.98    +0.064       +0.063  decrease
entropy_rate                4.2100   +0.34    -0.051       -0.017  increase
...
```

### Iterative Optimization with Trace

```python
from texthumanize import phantom_optimize

result = phantom_optimize(
    text="Long AI-generated essay...",
    lang="en",
    max_iterations=15,
    target_score=0.25,
    budget=1.0,
    seed=42,
)

if result.bypassed:
    print("✅ Text classified as human!")
else:
    print(f"⚠️ Score reduced to {result.final_score:.3f} but not bypassed")

# Print optimization trace
for step in result.trace:
    print(f"Iteration {step.iteration}: {step.score:.3f}")
```

### Budget Control

```python
# Minimal edits (preserve more of the original)
result = phantom_optimize(text, lang="en", budget=0.3)

# Aggressive optimization (more edits allowed)
result = phantom_optimize(text, lang="en", budget=1.0)
```

### Multi-Language Support

```python
# German
result = phantom_optimize(german_text, lang="de")

# French
result = phantom_optimize(french_text, lang="fr")

# Spanish
result = phantom_optimize(spanish_text, lang="es")

# Russian
result = phantom_optimize(russian_text, lang="ru")

# Ukrainian
result = phantom_optimize(ukrainian_text, lang="uk")
```

---

## Supported Languages

| Language | Code | PHANTOM™ Dict Entries | Bypass Rate |
|---|---|---|---|
| English | `en` | Full pipeline | 100% (5/5) |
| Russian | `ru` | 100+ AI replacements | 100% (5/5) |
| Ukrainian | `uk` | 80+ AI replacements | 80% (4/5) |
| German | `de` | 90 entries | Supported |
| French | `fr` | 80 entries | Supported |
| Spanish | `es` | 80 entries | Supported |

---

## Performance

| Metric | Value |
|---|---|
| **Bypass rate** | 93% (14/15 texts) |
| **Avg score reduction** | 0.67 → 0.14 (Δ 0.53) |
| **Avg iterations** | 3–8 |
| **Processing time** | 5–20s per text (depends on length) |
| **No external dependencies** | ✅ |
| **Deterministic** | ✅ (with seed) |

### Comparison

| Method | Avg Δ Score | Bypass Rate |
|---|---|---|
| Naturalizer only | ~0.10–0.15 | ~30% |
| ASH™ balanced | ~0.32 | ~70% |
| **PHANTOM™** | **~0.53** | **93%** |
| PHANTOM™ + rules | **~0.55** | **93%** |

---

## Imports

```python
# All available imports
from texthumanize import (
    PhantomEngine,
    phantom_optimize,
    get_phantom,
    ForgeResult,
)

# Or use via humanize()
from texthumanize import humanize
result = humanize(text, phantom=True)
```
