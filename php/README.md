# TextHumanize PHP

> Zero-dependency PHP library for algorithmic text humanization. Transforms machine-generated text into natural, human-sounding prose using a 10-stage processing pipeline.

PHP port of the [TextHumanize](https://github.com/ksanyok/TextHumanize) Python library.

## Requirements

- PHP 8.1+
- ext-mbstring
- ext-json

## Installation

```bash
composer require ksanyok/text-humanize
```

Если пакет ещё не опубликован на Packagist, добавьте VCS-репозиторий:

```bash
composer config repositories.texthumanize vcs https://github.com/ksanyok/TextHumanize
composer require ksanyok/text-humanize:^0.11
```

## Quick Start

```php
use TextHumanize\TextHumanize;

// Humanize text
$result = TextHumanize::humanize("Your text here");
echo $result->processed;

// Analyze text for artificiality markers
$report = TextHumanize::analyze("Text to check");
echo "Artificiality score: {$report->artificialityScore}%";

// Get detailed explanation
$explanation = TextHumanize::explain("Text to explain");
print_r($explanation['recommendations']);
```

## API Reference

### `TextHumanize::humanize()`

Main text processing entry point.

```php
$result = TextHumanize::humanize(
    text: "Your text here",
    lang: null,           // Auto-detect language (or 'en', 'ru', 'de', etc.)
    profile: 'web',       // chat | web | seo | docs | formal
    intensity: 50,        // 0–100, processing strength
    preserve: [
        'keywords' => ['Brand'],
        'brands' => ['CompanyName'],
    ],
    constraints: [
        'max_length' => 5000,
    ],
    seed: 42,             // Reproducible results
);

echo $result->processed;        // Processed text
echo $result->lang;             // Detected language
echo $result->profile;          // Applied profile
echo $result->getChangeRatio(); // 0.0 – 1.0
print_r($result->changes);     // List of applied stages
```

### `TextHumanize::humanizeChunked()`

Process large texts in chunks split at paragraph boundaries.

```php
$result = TextHumanize::humanizeChunked(
    text: $longText,
    chunkSize: 5000,      // Max characters per chunk
    lang: 'en',
    profile: 'web',
    intensity: 50,
);
```

### `TextHumanize::humanizeBatch()`

Process multiple texts at once with index-based seeding for reproducibility.

```php
$texts = [
    "First text to humanize.",
    "Second text to humanize.",
    "Third text to humanize.",
];

$results = TextHumanize::humanizeBatch(
    texts: $texts,
    lang: 'en',
    profile: 'web',
    intensity: 50,
    seed: 42,
);

foreach ($results as $i => $result) {
    echo "Text {$i}: {$result->processed}\n";
}
```

### `TextHumanize::analyze()`

Analyze text for artificiality markers.

```php
$report = TextHumanize::analyze("Text to analyze", lang: 'en');

echo $report->artificialityScore;    // 0–100
echo $report->bureaucraticRatio;     // Formal language ratio
echo $report->connectorRatio;        // AI connector frequency
echo $report->repetitionScore;       // Word repetition level
echo $report->burstinessScore;       // Sentence length variation
echo $report->totalWords;
echo $report->totalSentences;
echo $report->avgSentenceLength;

$array = $report->toArray();
```

### `TextHumanize::explain()`

Get a detailed explanation of what would be changed.

```php
$explanation = TextHumanize::explain("Text", profile: 'chat', intensity: 70);

// Returns:
// [
//     'before' => [...],
//     'after' => [...],
//     'recommendations' => [...],
//     'changes' => [...],
//     'change_ratio' => 0.15,
//     'summary' => '...',
// ]
```

### `HumanizeResult` Properties

| Method | Returns | Description |
|---|---|---|
| `$result->processed` | `string` | Processed text |
| `$result->lang` | `string` | Detected language |
| `$result->profile` | `string` | Applied profile |
| `$result->getChangeRatio()` | `float` | Change ratio 0.0–1.0 |
| `$result->getSimilarity()` | `float` | Jaccard similarity to original 0.0–1.0 |
| `$result->getQualityScore()` | `float` | Composite quality score 0.0–1.0 |
| `$result->changes` | `array` | List of applied pipeline stages |

### Tone Analysis

Analyze and adjust text tone across 7 levels: formal, academic, professional, neutral, friendly, casual, marketing.

```php
use TextHumanize\ToneAnalyzer;

$analyzer = new ToneAnalyzer('en');
$report = $analyzer->analyze("This is a formal document regarding the implementation.");

echo $report->primaryTone;    // "formal"
echo $report->formality;      // 0.8
echo $report->subjectivity;   // 0.2

// Adjust tone
$adjusted = $analyzer->adjust("Obtain the data", 'informal');
echo $adjusted; // "Get the data"
```

**Supported tone replacement languages:** `en`, `ru`, `uk`, `de`, `fr`, `es`

## Plugin System

Register custom plugins to run before or after any pipeline stage.

```php
use TextHumanize\Pipeline\Pipeline;

// Add a plugin that runs after the typography stage
Pipeline::registerPlugin(
    plugin: function (string $text, string $lang, string $profile, int $intensity): string {
        return str_replace('...', '…', $text);
    },
    after: 'typography',
);

// Available stages: segmentation, typography, debureaucratize,
// structure, repetitions, liveliness, universal, naturalize, validation, restore

Pipeline::clearPlugins(); // Remove all plugins
```

## Profiles

| Profile  | Use Case                 | Intensity |
|----------|--------------------------|-----------|
| `chat`   | Messengers, social media | High — informal, contractions |
| `web`    | Blog posts, articles     | Balanced — natural web content |
| `seo`    | SEO content              | Conservative — preserves keywords |
| `docs`   | Documentation            | Minimal — formal style |
| `formal` | Official documents       | Very minimal — no colloquialisms |

## Supported Languages

| Language   | Code | Support Level |
|------------|------|---------------|
| English    | `en` | Deep (full pipeline) |
| Russian    | `ru` | Deep (full pipeline) |
| Ukrainian  | `uk` | Deep (full pipeline) |
| German     | `de` | Standard |
| French     | `fr` | Standard |
| Spanish    | `es` | Standard |
| Polish     | `pl` | Standard |
| Portuguese | `pt` | Standard |
| Italian    | `it` | Standard |

All other languages receive universal processing (typography, sentence variation, burstiness).

## Processing Pipeline

The 10-stage pipeline:

1. **Segmentation** — Protects code blocks, URLs, emails, markdown, keywords
2. **Typography** — Normalizes dashes, quotes, ellipsis, special spaces
3. **Debureaucratization** — Replaces formal/bureaucratic language (deep langs)
4. **Structure** — Diversifies sentence structure, replaces AI connectors (deep langs)
5. **Repetitions** — Reduces word repetition via synonyms (deep langs)
6. **Liveliness** — Injects colloquial markers, varies punctuation (deep langs)
7. **Universal** — Unicode cleanup, sentence length variation (all langs)
8. **Naturalization** — Style naturalization, burstiness, perplexity (all langs)
9. **Validation** — Quality assurance, can rollback on failure
10. **Restoration** — Restores protected segments

## Architecture

```
php/src/
├── TextHumanize.php              # Main facade
├── TextAnalyzer.php              # Text analysis engine
├── HumanizeOptions.php           # Options / config
├── HumanizeResult.php            # Processing result DTO
├── AnalysisReport.php            # Analysis report DTO
├── Profiles.php                  # 5 processing profiles
├── RandomHelper.php              # Seeded RNG
├── LangDetector.php              # Language detection
├── Lang/
│   ├── Registry.php              # Language pack registry
│   ├── En.php                    # English
│   ├── Ru.php                    # Russian
│   ├── Uk.php                    # Ukrainian
│   ├── De.php                    # German
│   ├── Fr.php                    # French
│   ├── Es.php                    # Spanish
│   ├── Pl.php                    # Polish
│   ├── Pt.php                    # Portuguese
│   └── It.php                    # Italian
└── Pipeline/
    ├── Pipeline.php              # Pipeline orchestrator + plugin system
    ├── Segmenter.php             # Stage 1
    ├── TypographyNormalizer.php  # Stage 2
    ├── Debureaucratizer.php      # Stage 3
    ├── StructureDiversifier.php  # Stage 4
    ├── RepetitionReducer.php     # Stage 5
    ├── LivelinessInjector.php    # Stage 6
    ├── UniversalProcessor.php    # Stage 7
    ├── TextNaturalizer.php       # Stage 8
    └── Validator.php             # Stage 9
```

## Testing

```bash
composer install
vendor/bin/phpunit
```

**223 tests, 825 assertions** covering all pipeline stages, profiles, language packs, batch processing, and quality metrics.

## Support the Project

[![PayPal](https://img.shields.io/badge/PayPal-Donate-blue.svg?logo=paypal)](https://www.paypal.com/cgi-bin/webscr?cmd=_donations&business=ksanyok%40me.com&item_name=TextHumanize&currency_code=USD)

## License

TextHumanize Personal Use License — see [LICENSE](../LICENSE) for details.
Commercial use prohibited without separate agreement.

## See Also

- [TextHumanize Python](https://github.com/ksanyok/TextHumanize) — Original Python library with CLI
