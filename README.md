# TextHumanize

**Algorithmic text naturalization library — transforms machine-generated text into natural, human-like prose**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![PHP 8.1+](https://img.shields.io/badge/php-8.1+-purple.svg)](https://www.php.net/)
[![Tests](https://img.shields.io/badge/tests-158%20passed-green.svg)]()
[![License](https://img.shields.io/badge/license-Personal%20Use-orange.svg)](LICENSE)

---

TextHumanize is a text processing library that normalizes typography, simplifies bureaucratic language, diversifies sentence structure, increases burstiness and perplexity, and replaces formulaic phrases with natural alternatives. Available for **Python** and **PHP**.

**Full language support:** Russian · Ukrainian · English · German · French · Spanish · Polish · Portuguese · Italian

**Universal processor:** works with any language using statistical methods (no dictionaries required).

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [API Reference](#api-reference)
- [Profiles](#profiles)
- [Parameters](#parameters)
- [Plugin System](#plugin-system)
- [Chunk Processing](#chunk-processing)
- [CLI](#cli)
- [Processing Pipeline](#processing-pipeline)
- [Language Support](#language-support)
- [SEO Mode](#seo-mode)
- [Readability Metrics](#readability-metrics)
- [Examples](#examples)
- [Testing](#testing)
- [Architecture](#architecture)
- [PHP Library](#php-library)
- [Contributing](#contributing)
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
| **Uniform sentences** | All 15-20 words | Varied lengths |
| **Word repetition** | `important... important...` | Synonym substitution |
| **Overly perfect punctuation** | Frequent `;` and `:` | Simplified punctuation |
| **Low perplexity** | Predictable word choice | Natural variation |
| **Boilerplate phrases** | `it is important to note` | `notably`, `by the way` |

### Key Advantages

- **Fast** — pure algorithmic processing, zero network requests
- **Private** — all processing happens locally, data never leaves your system
- **Controllable** — fine-tuned via intensity, profiles, and keyword preservation
- **9 languages + universal** — RU, UK, EN, DE, FR, ES, PL, PT, IT + any other
- **Zero dependencies** — Python standard library only
- **Extensible** — plugin system for custom pipeline stages
- **Large text support** — chunk processing for texts of any size
- **Readability metrics** — Flesch-Kincaid, Coleman-Liau built-in

---

## Installation

### pip

```bash
pip install texthumanize
```

### From source

```bash
git clone https://github.com/ksanyok/TextHumanize.git
cd TextHumanize
pip install -e .
```

---

## Quick Start

```python
from texthumanize import humanize, analyze, explain

# Basic usage
result = humanize("This text utilizes a comprehensive methodology for implementation.")
print(result.text)
# → "This text uses a complete method for setup."

# With options
result = humanize(
    "Furthermore, it is important to note that the implementation facilitates optimization.",
    lang="en",
    profile="web",
    intensity=70,
)
print(result.text)

# Analyze text metrics
report = analyze("Text to analyze for naturalness.", lang="en")
print(f"Artificiality score: {report.artificiality_score:.1f}/100")
print(f"Flesch-Kincaid grade: {report.flesch_kincaid_grade:.1f}")

# Get detailed explanation
report = explain(result)
print(report)
```

---

## API Reference

### `humanize(text, **options)`

Main function — transforms text to sound more natural.

```python
from texthumanize import humanize

result = humanize(
    text="Your text here",
    lang="auto",        # auto-detect or specify: en, ru, de, fr, es, etc.
    profile="web",      # chat, web, seo, docs, formal
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

print(result.text)           # processed text
print(result.change_ratio)   # fraction of text changed (0.0-1.0)
print(result.changes)        # list of individual changes
print(result.metrics_before) # metrics before processing
print(result.metrics_after)  # metrics after processing
```

### `humanize_chunked(text, chunk_size=5000, **options)`

Process large texts by splitting into chunks at paragraph boundaries.

```python
from texthumanize import humanize_chunked

# Process a 50,000-character document
with open("large_document.txt") as f:
    text = f.read()

result = humanize_chunked(
    text,
    chunk_size=5000,     # characters per chunk
    lang="en",
    profile="docs",
    intensity=50,
)
print(result.text)
```

### `analyze(text, lang)`

Analyze text and return naturalness metrics.

```python
from texthumanize import analyze

report = analyze("Text to analyze.", lang="en")
print(f"Artificiality: {report.artificiality_score:.1f}/100")
print(f"Avg sentence length: {report.avg_sentence_length:.1f}")
print(f"Bureaucratic ratio: {report.bureaucratic_ratio:.3f}")
print(f"Connector ratio: {report.connector_ratio:.3f}")
print(f"Repetition score: {report.repetition_score:.3f}")
print(f"Burstiness: {report.burstiness_score:.3f}")
print(f"Flesch-Kincaid grade: {report.flesch_kincaid_grade:.1f}")
print(f"Coleman-Liau index: {report.coleman_liau_index:.1f}")
```

### `explain(result)`

Generate a human-readable report of changes.

```python
from texthumanize import humanize, explain

result = humanize("Text to process.")
print(explain(result))
```

---

## Profiles

Five built-in profiles control the processing style:

| Profile | Use Case | Sentence Length | Colloquialisms | Punctuation |
|---------|----------|-----------------|----------------|-------------|
| `chat` | Messaging, social media | 8-18 words | High | Simplified |
| `web` | Blog posts, articles | 10-22 words | Medium | Standard |
| `seo` | SEO content | 12-25 words | None | Preserved |
| `docs` | Documentation | 12-28 words | None | Formal |
| `formal` | Academic, legal | 15-30 words | None | Strict |

```python
# Conversational style
result = humanize(text, profile="chat", intensity=80)

# SEO-safe mode (preserves keywords)
result = humanize(text, profile="seo", intensity=40,
                  constraints={"keep_keywords": ["API", "cloud"]})

# Formal documentation
result = humanize(text, profile="formal", intensity=30)
```

---

## Parameters

### Intensity (0-100)

Controls how aggressively text is modified:

| Range | Effect |
|-------|--------|
| 0-20 | Typography only |
| 20-40 | + light debureaucratization |
| 40-60 | + structure diversification |
| 60-80 | + synonym replacement, natural phrasing |
| 80-100 | + maximum variation, colloquial insertions |

### Preserve Options

```python
preserve = {
    "code_blocks": True,   # protect ```code``` blocks
    "urls": True,           # protect URLs
    "emails": True,         # protect email addresses
    "hashtags": True,       # protect #hashtags
    "mentions": True,       # protect @mentions
    "markdown": True,       # protect markdown formatting
    "html": True,           # protect HTML tags
    "numbers": False,       # protect numbers
    "brand_terms": ["TextHumanize", "MyBrand"],  # exact terms to protect
}
```

### Constraints

```python
constraints = {
    "max_change_ratio": 0.4,           # max 40% of text changed
    "min_sentence_length": 3,          # minimum sentence length (words)
    "keep_keywords": ["SEO", "API"],   # keywords to preserve
}
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
        return text.replace(self.brand.lower(), self.canonical)

Pipeline.register_plugin(
    BrandEnforcer("texthumanize", "TextHumanize"),
    after="typography",
)

# Process text — plugins will be applied automatically
result = humanize("texthumanize is great.")

# Clean up
Pipeline.clear_plugins()
```

Available stage names: `segmentation`, `typography`, `debureaucratization`,
`structure`, `repetitions`, `liveliness`, `universal`, `naturalization`,
`validation`, `restore`.

---

## Chunk Processing

For large documents (articles, books, reports), use `humanize_chunked` to process text in manageable pieces:

```python
from texthumanize import humanize_chunked

# Automatically splits at paragraph boundaries
result = humanize_chunked(
    very_long_text,
    chunk_size=5000,    # characters per chunk
    lang="en",
    profile="docs",
    intensity=50,
    seed=42,            # consistent results across chunks
)
```

Each chunk is processed independently with its own seed for variation, then reassembled into the final text. The chunk boundary detection preserves paragraph integrity.

---

## CLI

```bash
# Process a file
texthumanize input.txt -o output.txt

# With options
texthumanize input.txt --lang en --profile web --intensity 70

# Analyze without processing
texthumanize input.txt --analyze

# Process from stdin
echo "Text to process" | texthumanize --lang en
```

---

## Processing Pipeline

TextHumanize uses a 10-stage pipeline:

```
Input Text
  ↓
1. Segmentation       — protect code blocks, URLs, emails, brands
  ↓
2. Typography          — normalize dashes, quotes, ellipses, punctuation
  ↓
3. Debureaucratization — replace bureaucratic/formal words (deep languages)
  ↓
4. Structure           — diversify sentence openings and structure (deep)
  ↓
5. Repetitions         — reduce word/phrase repetitions with synonyms (deep)
  ↓
6. Liveliness          — inject natural phrasing, colloquialisms (deep)
  ↓
7. Universal           — statistical processing for ALL languages
  ↓
8. Naturalization      — style naturalization: burstiness, perplexity (KEY STAGE)
  ↓
9. Validation          — quality check, rollback if needed
  ↓
10. Restore            — restore protected segments
  ↓
Output Text
```

Stages 3-6 require full dictionary support (9 languages). Stages 7-8 work for any language.

---

## Language Support

### Full Dictionary Support (9 languages)

Each language pack includes:
- Bureaucratic word → natural replacements
- Formulaic connector alternatives
- Synonym dictionaries
- Sentence starter variations
- Colloquial markers
- Abbreviation lists
- Language-specific trigrams for detection
- Stop words
- Profile-specific sentence length targets

| Language | Code | Bureaucratic | Connectors | Synonyms |
|----------|------|-------------|------------|----------|
| Russian | `ru` | 70+ | 25+ | 50+ |
| Ukrainian | `uk` | 50+ | 24 | 48 |
| English | `en` | 40+ | 25 | 35+ |
| German | `de` | 22 | 12 | 26 |
| French | `fr` | 20 | 12 | 20 |
| Spanish | `es` | 18 | 12 | 18 |
| Polish | `pl` | 18 | 12 | 18 |
| Portuguese | `pt` | 16 | 12 | 17 |
| Italian | `it` | 16 | 12 | 17 |

### Universal Processor

For any language not in the dictionary list, TextHumanize uses statistical methods:
- Sentence length variation (burstiness)
- Punctuation normalization
- Whitespace regularization
- Perplexity boosting
- Fragment insertion

```python
# Works with any language
result = humanize("日本語のテキスト", lang="ja")
result = humanize("Текст на казахском", lang="kk")
```

---

## SEO Mode

The `seo` profile is designed for content that must preserve search ranking:

```python
result = humanize(
    text,
    profile="seo",
    intensity=40,
    constraints={
        "max_change_ratio": 0.3,
        "keep_keywords": ["cloud computing", "API", "microservices"],
    },
)
```

SEO mode features:
- Lower intensity defaults
- Keyword preservation
- No colloquial insertions
- Minimal structure changes
- Sentence length stays within optimal range (12-25 words)

---

## Readability Metrics

TextHumanize includes built-in readability scoring:

```python
from texthumanize import analyze

report = analyze("Your text here.", lang="en")

# Readability indices
print(f"Flesch-Kincaid Grade Level: {report.flesch_kincaid_grade:.1f}")
print(f"Coleman-Liau Index: {report.coleman_liau_index:.1f}")
print(f"Avg word length: {report.avg_word_length:.1f}")
print(f"Avg syllables/word: {report.avg_syllables_per_word:.1f}")

# Naturalness metrics
print(f"Artificiality: {report.artificiality_score:.1f}/100")
print(f"Burstiness: {report.burstiness_score:.2f}")
print(f"Bureaucratic ratio: {report.bureaucratic_ratio:.3f}")
```

---

## Examples

### Blog Post Processing

```python
from texthumanize import humanize

text = """
Furthermore, it is important to note that the implementation of cloud computing
facilitates the optimization of business processes. Additionally, the utilization
of microservices constitutes a significant advancement. Nevertheless, considerable
challenges remain in the area of security.
"""

result = humanize(text, profile="web", intensity=70, lang="en")
print(result.text)
print(f"Changed: {result.change_ratio:.0%}")
```

### Russian Document

```python
result = humanize(
    "Данный документ является примером осуществления обработки текста.",
    lang="ru",
    profile="docs",
    intensity=60,
)
```

### Full Configuration

```python
result = humanize(
    text="Your text here",
    lang="auto",
    profile="web",
    intensity=70,
    preserve={
        "code_blocks": True,
        "urls": True,
        "brand_terms": ["MyBrand"],
    },
    constraints={
        "max_change_ratio": 0.3,
        "keep_keywords": ["SEO"],
    },
    seed=42,
)
```

### Using Individual Modules

```python
# Typography only
from texthumanize.normalizer import TypographyNormalizer
norm = TypographyNormalizer(profile="web")
result = norm.normalize("Text — with dashes and «quotes»...")

# Debureaucratization only
from texthumanize.decancel import Debureaucratizer
db = Debureaucratizer(lang="en", profile="chat", intensity=80)
result = db.process("This text utilizes a comprehensive methodology.")

# Analysis only
from texthumanize.analyzer import TextAnalyzer
analyzer = TextAnalyzer(lang="en")
report = analyzer.analyze("Text to analyze.")
```

---

## Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=texthumanize

# Specific test suites
pytest tests/test_core.py
pytest tests/test_golden.py
pytest tests/test_segmenter.py
pytest tests/test_normalizer.py
pytest tests/test_decancel.py
pytest tests/test_structure.py
pytest tests/test_multilang.py
pytest tests/test_naturalizer.py
```

---

## Architecture

```
texthumanize/
├── __init__.py          # Public API exports
├── core.py              # humanize(), analyze(), explain(), humanize_chunked()
├── pipeline.py          # 10-stage pipeline + plugin system
├── analyzer.py          # Artificiality + readability metrics
├── tokenizer.py         # Paragraph/sentence/word splitting
├── segmenter.py         # Code/URL/email protection
├── normalizer.py        # Typography normalization
├── decancel.py          # Debureaucratization
├── structure.py         # Sentence structure diversification
├── repetitions.py       # Repetition reduction
├── liveliness.py        # Natural phrasing injection
├── universal.py         # Universal processor (all languages)
├── naturalizer.py       # Style naturalization (key stage)
├── validator.py         # Quality validation + rollback
├── lang_detect.py       # Language detection (9 languages)
├── utils.py             # Options, profiles, utilities
├── cli.py               # CLI interface
└── lang/                # Language packs
    ├── __init__.py      # Registry + fallback
    ├── ru.py            # Russian
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

- **Modularity** — each stage in a separate module
- **Declarative rules** — language packs contain only data, not logic
- **Idempotent** — repeated processing does not degrade quality
- **Safe** — validator rolls back changes that exceed thresholds
- **Extensible** — add languages, profiles, or pipeline stages easily
- **Portable** — declarative architecture enables easy porting

---

## PHP Library

A full PHP port is available in the `php/` directory with identical functionality:

```php
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

See [php/README.md](php/README.md) for full PHP documentation.

---

## Contributing

Contributions are welcome:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit changes: `git commit -m 'Add my feature'`
4. Push: `git push origin feature/my-feature`
5. Open a Pull Request

### Areas for Improvement

- **Dictionaries** — expand bureaucratic and synonym dictionaries for all languages
- **Languages** — add support for new languages
- **Tests** — more edge cases and golden tests
- **Documentation** — tutorials and examples
- **Ports** — Node.js, Go implementations

---

## Support the Project

If you find TextHumanize useful, consider supporting the development:

[![PayPal](https://img.shields.io/badge/PayPal-Donate-blue.svg?logo=paypal)](https://www.paypal.com/paypalme/ksanyok)

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
