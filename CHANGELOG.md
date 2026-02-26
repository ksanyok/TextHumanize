# Changelog

All notable changes to this project are documented in this file.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.12.0] - 2025-06-27

### Added
- **5 new languages** — Arabic (ar), Chinese Simplified (zh), Japanese (ja), Korean (ko), Turkish (tr). Total: **14 languages** with full deep processing support.
  - **Arabic** — 81 bureaucratic, 80 synonyms, 49 AI connectors, 40 colloquial markers, 47 abbreviations, 40 perplexity boosters, 30 sentence starters, 40 bureaucratic phrases, 39 split conjunctions
  - **Chinese** — 80 bureaucratic, 80 synonyms, 36 AI connectors, 40 colloquial markers, 32 abbreviations, 40 perplexity boosters, 30 sentence starters, 40 bureaucratic phrases, 41 split conjunctions
  - **Japanese** — 60+ entries per category, keigo→casual register replacements
  - **Korean** — 60+ entries per category, honorific→casual register replacements
  - **Turkish** — 60+ entries per category, Ottoman→modern Turkish replacements
- **Placeholder guard system** — all 6 text processing modules (structure, naturalizer, universal, decancel, repetitions, liveliness) now skip words and sentences containing placeholder tokens. Prevents `\x00THZ_*\x00` artifacts from leaking into output.
- **HTML block protection** — entire `<ul>`, `<ol>`, `<table>`, `<pre>`, `<code>`, `<script>`, `<style>`, `<blockquote>` blocks are now protected as single segments. Individual `<li>` items also protected.
- **Bare domain protection** — domains like `site.com.ua`, `portal.kh.ua`, `example.co.uk` are now protected without requiring `http://` prefix. Covers 24 TLDs and 18 country sub-TLDs.
- **Watermark cleaning in pipeline** — `WatermarkDetector.clean()` now runs automatically as the first pipeline stage (before segmentation), removing zero-width characters, homoglyphs, invisible Unicode, and spacing anomalies. Supports plugin hooks (`before`/`after` the `watermark` stage).
- **Language detection for new scripts** — Arabic (Unicode \u0600–\u06FF), CJK (Chinese \u4E00–\u9FFF, Japanese hiragana/katakana, Korean hangul), Turkish (marker-based with ş, ğ, ı).
- **54 new tests** for all v0.12.0 features — HTML protection, domain safety, placeholder safety, new languages, watermark pipeline, language detection, restore robustness.

### Fixed
- **Placeholder token leaks** — processing stages no longer corrupt `\x00THZ_*\x00` tokens through word-boundary regex, `.lower()` operations, or sentence splitting. 3-pass `restore()` recovery: exact match → case-insensitive → orphan cleanup.
- **Homoglyph detector corrupting Cyrillic** — removed Cyrillic `е` (U+0435), `а` (U+0430), `і` (U+0456) from `_SPECIAL_HOMOGLYPHS` table. These are normal Cyrillic/Ukrainian characters, not watermark homoglyphs. Contextual detection via `_CYRILLIC_TO_LATIN` / `_LATIN_TO_CYRILLIC` remains intact.
- **Duplicate dictionary keys** — removed F601 duplicates in ar.py (1), ja.py (1), tr.py (4).
- **Test for unknown language** — updated test to use truly unknown language codes instead of now-supported zh/ja.

### Changed
- **Pipeline stages** — now 12 stages (was 11): watermark → segmentation → typography → debureaucratization → structure → repetitions → liveliness → paraphrasing → universal → naturalization → validation → restore.
- **1,509 Python tests** — up from 1,455 (100% pass rate).

## [0.11.0] - 2025-06-26

### Added
- **Massive dictionary expansion (3× total)** — all 9 language dictionaries expanded from 2,281 to 6,881 entries:
  - **EN**: 257 → 1,391 (5.4×) — synonyms, bureaucratic pairs, AI connectors, sentence starters, colloquial markers, perplexity boosters, split conjunctions, abbreviations, bureaucratic phrases
  - **RU**: 291 → 956 (3.3×) — full expansion across all 9 categories with inflected forms
  - **UK**: 252 → 780 (3.1×) — synonyms with m/f forms, bureaucratic pairs, colloquial markers, perplexity boosters
  - **DE**: 235 → 724 (3.1×) — bureaucratic words with Latin-origin forms, compound words, formal/informal markers
  - **FR**: 263 → 599 (2.3×) — literary vocabulary, academic connectors, bureaucratic phrases
  - **ES**: 255 → 613 (2.4×) — formal/informal synonyms, regional markers
  - **IT**: 244 → 616 (2.5×) — bureaucratic and literary vocabulary
  - **PL**: 244 → 617 (2.5×) — inflected forms, formal registers
  - **PT**: 240 → 585 (2.4×) — Brazilian/European Portuguese markers
- **1,455 Python tests** — up from 1,333 (100% pass rate).

### Fixed
- **Composer package name** — root `composer.json` had incorrect name `ksanyok/texthumanize` (no hyphen); fixed to `ksanyok/text-humanize` matching the actual package name on Packagist. Also changed `type` from `project` to `library` and added proper metadata (authors, extensions, autoload-dev, minimum-stability).
- **TOC dots preservation** — table-of-contents leader dots (`..........`) no longer get collapsed into `…` (ellipsis) by the typography normalizer. Added `leader_dots` pattern to segmenter protection and fixed punctuation spacing logic.

## [0.10.0] - 2025-06-25

### Added
- **Grammar Checker** — `check_grammar(text, lang)` / `fix_grammar(text, lang)` — rule-based grammar checking for all 9 languages. Detects double words, capitalization errors, spacing issues, double punctuation, unclosed brackets, and common typos. Returns `GrammarReport` with per-issue detail, score 0-100. No ML or external API required.
- **Uniqueness Score** — `uniqueness_score(text)` — n-gram fingerprinting uniqueness analysis. Returns `UniquenessReport` with 2/3/4-gram ratios, vocabulary richness, repetition score. `compare_texts(a, b)` computes Jaccard similarity. `text_fingerprint(text)` returns stable SHA-256 hash.
- **Content Health Score** — `content_health(text, lang)` — composite quality metric combining readability, grammar, uniqueness, AI detection, and coherence. Returns `ContentHealthReport` with overall score (0-100), letter grade (A+/A/B/C/D/F), and per-component breakdown. Configurable component toggles.
- **Semantic Similarity** — `semantic_similarity(original, processed)` — measures semantic preservation between original and humanized text via keyword, entity, content-word, and n-gram overlap. Returns `SemanticReport` with preservation score (0-1) and missing/added keyword lists.
- **Sentence-level Readability** — `sentence_readability(text)` — per-sentence difficulty scoring (0-100) with grade assignment (easy/medium/hard/very_hard). Identifies hardest sentences in a document. Returns `SentenceReadabilityReport`.
- **Custom Dictionary API** — `humanize(text, custom_dict={"word": "replacement"})` — user-supplied word/phrase replacement dictionary. Supports single replacement or list of variants (random selection). Applied during pipeline processing.
- **82 new tests** across 6 test files for all v0.10.0 features.

### Changed
- **Language dictionaries massively expanded** — FR (281→397), ES (275→388), IT (272→379), PL (257→368), PT (256→367) entries. Added perplexity_boosters to EN, RU, UK. All 9 languages now balanced (367-439 entries).
- **`humanize()` signature** — new `custom_dict` parameter for user-supplied replacements.
- **17 new exports** in `__init__.py`: `check_grammar`, `fix_grammar`, `GrammarIssue`, `GrammarReport`, `uniqueness_score`, `compare_texts`, `text_fingerprint`, `UniquenessReport`, `SimilarityReport`, `content_health`, `ContentHealthReport`, `HealthComponent`, `semantic_similarity`, `SemanticReport`, `sentence_readability`, `SentenceReadabilityReport`, `SentenceScore`.

### Fixed
- Duplicate dictionary key in Italian language file (`imprescindibile`).
- Duplicate dictionary key in Polish typo corpus (`wziąść`).
- Short-text edge cases in `compare_texts()` and `text_fingerprint()` — now handle texts shorter than n-gram window correctly.

## [0.9.0] - 2025-06-24

### Added
- **Kirchenbauer Watermark Detector** — green-list z-test based on Kirchenbauer et al. 2023 paper. Uses SHA-256 hash of previous token to partition vocabulary, counts green-list tokens, computes z-score and p-value. Flags AI watermark at z ≥ 4.0. New fields: `kirchenbauer_score`, `kirchenbauer_p_value` in `WatermarkReport`.
- **HTML Diff Report** — `explain(result, fmt="html")` generates self-contained HTML page with inline `<del>`/`<ins>` word-level diff, metrics grid, and change breakdown. Also supports `fmt="json"` (RFC 6902-style JSON Patch) and `fmt="diff"` (unified diff).
- **Quality Gate** — `python -m texthumanize.quality_gate` CLI + GitHub Action (`.github/workflows/quality-gate.yml`) + pre-commit hook. Checks text files for AI score > threshold, low readability, and watermarks. Returns exit code 1 on failure.
- **Selective Humanization** — `humanize(text, only_flagged=True)` processes only sentences detected as AI-generated (`ai_probability > 0.5`). Human-written sentences pass through unchanged.
- **Stylometric Anonymizer** — `StylometricAnonymizer` class and `anonymize_style()` convenience function. Transforms text to disguise authorship by adjusting sentence lengths, punctuation patterns, sentence starters, toward a target stylistic preset. Supports all 5 presets. Returns `AnonymizeResult` with before/after similarity scores.
- **40 new tests** covering all v0.9.0 features in `tests/test_v090_features.py`.

### Changed
- `explain()` now accepts `fmt` parameter: `"text"` (default), `"html"`, `"json"`, `"diff"`.
- `humanize()` accepts new `only_flagged` parameter.
- New exports: `explain_html`, `explain_json_patch`, `explain_side_by_side`, `anonymize_style`, `StylometricAnonymizer`, `AnonymizeResult`.

## [0.8.2] - 2026-02-19

### Added
- **Security & Limits section** in README — input limits, resource consumption, ReDoS safety, sandboxing recommendations, threat model, and testing/QA summary. Addresses enterprise compliance requirements.

### Changed
- **Enterprise-friendly positioning** — replaced "indistinguishable from human writing" and AI-detector-bypass claims with readability/style normalization messaging throughout README. Removed competitor brand names from comparison headers.
- **JS/TS README** — updated status from "Skeleton" to "Production-ready"; corrected ported modules checklist to reflect actually ported Typography Normalizer, Debureaucratizer, and TextNaturalizer.
- **Root package.json** — converted from stub to proper private monorepo config with workspaces, cross-platform test scripts, and `node >= 18` engine requirement.
- **Root composer.json** — fixed PHP requirement (`>=7.4` → `>=8.1`), corrected PSR-4 autoload path (`src/` → `php/src/`), replaced stub post-install echo with proper test script.
- **Commercial license pricing** — Indie $99 → $199/yr, Startup $299 → $499/yr, Business $799 → $1,499/yr. Updated across COMMERCIAL.md, LICENSE, and README.
- **Speed claims** — corrected from 56K to 30K+ chars/sec to match real benchmark data in comparison tables.

## [0.8.1] - 2026-02-19

### Added
- **Dual License** — replaced "Personal Use Only" with clear dual license: free for personal/academic/non-commercial use, commercial licenses with 4 tiers (Indie, Startup, Business, Enterprise).
- **COMMERCIAL.md** — dedicated commercial licensing page with pricing table, feature comparison, FAQ, and purchase instructions.
- **Full benchmark suite** (`benchmarks/full_benchmark.py`) — reproducible benchmark covering processing speed, AI detection speed, predictability (determinism), memory usage, quality metrics, and change reports.
- **"For Business & Enterprise" section** in README — corporate-focused block addressing predictability, privacy, auditability, processing modes, and integration options.
- **Change Report section** in Performance & Benchmarks — demonstrates `explain()` audit trail with every `humanize()` call.
- **Predictability section** with determinism guarantees and seed-based reproducibility proof.

### Changed
- **LICENSE** rewritten — now clearly states dual license with pricing tiers table, commercial use definitions, and contact information.
- **README Performance section** — replaced estimated numbers with real benchmark data from `full_benchmark.py`.
- **License references** updated in `pyproject.toml` to reflect dual license model.

## [0.8.0] - 2026-02-19

### Added
- **Style Presets** (`STYLE_PRESETS`) — 5 predefined `StylisticFingerprint` targets: `student`, `copywriter`, `scientist`, `journalist`, `blogger`. Pass `target_style="student"` to `humanize()`.
- **Auto-Tuner** (`AutoTuner`) — feedback loop that records processing results and suggests optimal `intensity` / `max_change_ratio` based on accumulated history. Persistent JSON storage.
- **Semantic preservation guards** — expanded `_CONTEXT_GUARDS` with 20+ patterns across EN/RU/UK/DE. Echo check prevents introducing duplicate words within sentence boundaries. Negative collocations expanded for DE.
- **Typography-only fast path** — text with AI score ≤ 5% skips all semantic stages, applying only typography normalization. Prevents over-processing of genuine human text.
- **JS/TS full processing stages** — ported `TypographyNormalizer`, `Debureaucratizer`, `TextNaturalizer` with burstiness injection, AI word replacement, and connector variation. Full pipeline with adaptive intensity and graduated retry. 28 JS tests passing.
- **API Reference** (`docs/API_REFERENCE.md`) — complete reference for all public APIs.
- **Cookbook** (`docs/COOKBOOK.md`) — 14 practical recipes covering common use cases.
- **1333 Python tests** — up from 1255 (100% benchmark pass rate).
- **28 JS/TS tests** — covering normalizer, debureaucratizer, naturalizer, and pipeline.

### Changed
- **`change_ratio` calculation** — switched from positional word comparison to `SequenceMatcher`. Fixes critical bug where inserting one word inflated ratio from ~0.15 to 0.65+.
- **Graduated retry** — pipeline retries at lower intensity (factors: 0.4, 0.15) when change_ratio exceeds limit, instead of rolling back entirely.
- **Decancel budget** — debureaucratizer limited to max 15% of words per pass, preventing over-replacement.
- **Adaptive intensity** — refined thresholds: AI ≤ 5% → typography only, AI ≤ 10% → ×0.2, AI ≤ 15% → ×0.35, AI ≤ 25% → ×0.5.
- **German (DE) dictionaries** — bureaucratic entries 22→64, phrases 14→25, ai_connectors 12→20, synonyms 26→45, AI word replacements 20→38. All include inflected noun/verb/adjective forms.
- **`quality_score` formula** — improved handling of natural texts (AI < 15 with no changes → 0.7); widened optimal change range.
- **Benchmark speed** — improved from 42K to 56K chars/sec (33% faster) due to fast path optimization.

### Fixed
- **DE zero-change bug** — German text processed with 0% changes because dictionary contained only verb infinitives while text used noun forms (e.g., "implementieren" vs "Implementierung"). Fixed by adding inflected forms.
- **Natural text over-processing** — human-written text (AI ≤ 5%) no longer gets unnecessarily modified.
- **Validator change_ratio** — also migrated to SequenceMatcher for consistency.

## [0.7.0] - 2026-02-19

### Added
- **13 AI-detection metrics** — new `perplexity_score` metric (character-level trigram model with Laplace smoothing) complements the existing 12 statistical indicators.
- **Ensemble boosting** — replaces simple weighted sum with 3-classifier aggregation: base weighted sum (50%), strong-signal detector (30%), majority voting (20%). AI/Human separation improved from ~60% to 86%/10%.
- **Benchmark suite** (`benchmarks/detector_benchmark.py`) — 11 labeled samples (5 AI, 5 Human, 1 Mixed), per-label accuracy breakdown, detailed metric visualisation. Currently 90.9% accuracy.
- **CLI `detect` subcommand** — `texthumanize detect [file] [--verbose] [--json]` for piped/interactive AI detection with emoji verdicts and bar-chart metrics.
- **Streaming progress callback** — `humanize_batch(texts, on_progress=callback)` calls `callback(index, total, result)` after each text is processed.
- **C2PA / IPTC watermark detection** — new `_detect_metadata_markers()` method in WatermarkDetector (Python + PHP) detects content provenance patterns: C2PA manifests, IPTC/XMP namespace prefixes, Content Credentials strings, base64 blobs, UUID provenance identifiers.
- **Tone replacements for UK/DE/FR/ES** — informal ↔ formal replacement pairs (12 per direction per language) and formal/informal/subjective markers for German, French, Spanish (Python + PHP).
- **PHP examples/** — `basic_usage.php` and `advanced.php` with batch, tone, multilingual, plugin, chunked, and profiles comparison demos.
- **Full PHP README** — `humanizeBatch()` docs, `HumanizeResult` properties table, Tone Analysis section.

### Changed
- **Zipf metric rewritten** — log-log linear regression with R² goodness-of-fit replaces naive deviation; minimum threshold raised from 50 to 150 clean words for reliability.
- **Confidence formula** — 4-component formula: text length (35%), metric agreement (20%), extreme bonus (abs(p−0.5)×0.6), agreement ratio (25%). Short-text detection now yields meaningful confidence.
- **Grammar detection expanded** — 5 → 9 indicators: +Oxford comma, +sentence fragments, +informal punctuation (!! …), +structured list formatting.

## [0.6.0] - 2026-02-19

### Added
- **`humanize_batch()` / `humanizeBatch()`** — batch processing of multiple texts in a single call (Python + PHP). Each text gets a unique seed (base_seed + index) for reproducibility.
- **`HumanizeResult.similarity`** — Jaccard similarity metric (0..1) comparing original and processed text.
- **`HumanizeResult.quality_score`** — overall quality score (0..1) balancing sufficient change with meaning preservation.
- **1255 Python tests** — up from 500, with **99% code coverage**.
- **223 PHP tests** (825 assertions) — up from 30 tests, covering all modules including new batch/similarity/quality features.
- **10 PHP test files**: `AIDetectorTest`, `CoherenceAnalyzerTest`, `ContentSpinnerTest`, `ToneAnalyzerTest`, `ParaphraserTest`, `WatermarkDetectorTest`, `SentenceSplitterTest`, `PipelineStagesTest`, `TextHumanizeExtraTest`.

### Changed
- **Python test coverage 85% → 99%** — 28 of 38 modules at 100%; dead code cleaned up.
- **mypy clean** — 0 type errors across all 38 source files (fixed 37 type issues).
- **Dead code removed** — 11 unreachable code blocks cleaned up across 7 Python modules (detectors, decancel, tone, tokenizer, universal, analyzer, sentence_split).
- **PHP autoloading** — added `classmap` to `composer.json` for proper autoloading of multi-class files.

### Fixed
- **ToneAnalyzer MARKETING direction** — `MARKETING` tone level now properly included in formal levels set, enabling tone adjustment to/from marketing (Python + PHP).
- **PHP SentenceSplitter Cyrillic** — replaced ASCII-only `ctype_alpha()` with Unicode-aware `preg_match('/\\pL/u')` for proper Cyrillic letter detection in abbreviation/initial checks.
- **Python `decancel.py` case logic** — reordered `isupper()` / `[0].isupper()` checks to make the all-caps branch reachable.
- **37 mypy type errors** fixed: proper type annotations, explicit casts, Union typing.
- **PHP Version constant** updated from `0.1.0` to `0.6.0`.

## [0.5.0] - 2026-02-19

### Added
- **500 tests** — up from 382 tests, comprehensive coverage of all modules.
- **conftest.py** — 12 reusable pytest fixtures (en/ru/uk AI/human text samples, profiles, seed).
- **test_morphology_ext.py** — 71 tests covering RU/UK/EN/DE morphology: lemmatization, POS detection, form generation, match forms, singleton cache.
- **test_coverage_boost.py** — 47 tests for coherence analyzer, paraphraser, and watermark detector.
- **PEP 561 compliance** — `py.typed` marker file for downstream type checkers.
- **Pre-commit hooks** — `.pre-commit-config.yaml` with ruff lint/format, trailing whitespace, YAML/TOML checks.
- **mypy configuration** — type checking config in `pyproject.toml` (python 3.9, check_untyped_defs).
- **CI/CD enhancements** — ruff lint step, mypy type check (Python 3.12), XML coverage output.

### Changed
- **Test coverage 80% → 85%** — morphology (55→93%), coherence (68→96%), paraphrase (71→87%), watermark (74→87%).
- **0 lint errors** — fixed all 67 ruff errors (E741 variable names, F841 unused variables, E501 line length, F601 duplicate dict keys, I001 import sorting, W291 trailing whitespace, F401 unused imports).

### Fixed
- **PHP SentenceSplitter** — `PREG_OFFSET_CAPTURE` offset now properly cast to `int` (was implicit string).
- **PHP ToneAnalyzer** — `preg_match` offset cast to `int` for `mb_substr()` compatibility.
- **Python E741** — renamed ambiguous variable `l` → `sl`/`slen`/`wlen`/`pl`/`long_cnt` in 6 modules.
- **Duplicate dict keys** — removed duplicates in `en.py`, `uk.py`, `morphology.py`.
- **Unused variables** — cleaned up `commas`, `periods`, `quest_rate`, `paren_rate`, `modified`, `original` in detectors and naturalizer.

## [0.4.0] - 2026-02-19

### Added
- **AI Detection Engine** (`detect_ai()`) — 12 independent statistical metrics (entropy, burstiness, vocabulary richness, Zipf law, stylometry, AI patterns, punctuation diversity, coherence, grammar perfection, opening diversity, readability consistency, rhythm analysis). Designed to rival GPTZero.
- **Morphological Engine** (`morphology.py`) — rule-based lemmatization and form generation for RU, UK, EN, DE without external dependencies; used for smarter synonym matching.
- **Smart Sentence Splitter** (`sentence_split.py`) — handles abbreviations, decimals, initials, direct speech; replaces naive regex splitting.
- **Context-Aware Synonyms** (`context.py`) — word-sense disambiguation via collocations and topic detection (technology, business, casual).
- **Coherence Analyzer** (`coherence.py`) — paragraph-level analysis: lexical cohesion, transition quality, topic consistency, opening diversity.
- **Syntactic Paraphraser** (`paraphrase.py`) — clause swaps, passive-to-active, sentence splitting, adverb fronting, nominalization.
- **Tone Analyzer & Adjuster** (`tone.py`) — 7 tone levels (formal ↔ casual), formality/subjectivity scoring, marker-based tone adjustment for EN/RU/UK.
- **Watermark Detector & Cleaner** (`watermark.py`) — detects/removes zero-width chars, homoglyphs, invisible Unicode, spacing steganography, statistical watermarks.
- **Content Spinner** (`spinner.py`) — synonym-based spinning, spintax generation, variant production for EN/RU/UK.
- **REST API** (`api.py`) — zero-dependency HTTP server with 12 POST endpoints and health check; CORS support.
- **4 new profiles**: `academic`, `marketing`, `social`, `email`.
- **5 new readability metrics**: ARI, SMOG Index, Gunning Fog, Dale-Chall, `full_readability()`.
- New CLI commands: `--detect-ai`, `--paraphrase`, `--tone`, `--tone-analyze`, `--watermarks`, `--spin`, `--variants`, `--coherence`, `--readability`, `--api`.
- `texthumanize-api` entry point for running API server.

### Changed
- All 6 secondary language dictionaries (DE, FR, ES, PL, PT, IT) expanded with `sentence_starters`, `colloquial_markers`, `abbreviations`, `perplexity_boosters`.
- `_vary_sentence_structure()` in naturalizer.py fully reimplemented (was a no-op — both branches ended with `pass`).
- Morphology integrated into `repetitions.py` — synonyms resolved by lemma with form agreement.
- Version bumped to 0.4.0.

### Fixed
- `_vary_sentence_structure()` no longer silently skips all transformations.

## [0.3.0] - 2026-02-18

### Added
- **Plugin system** for Python и PHP пайплайнов — регистрация кастомных плагинов `before`/`after` любого из 10 этапов обработки
- **Readability-метрики** в `AnalysisReport`: Flesch-Kincaid Grade Level, Coleman-Liau Index, средняя длина слова, среднее кол-во слогов
- **Chunk-обработка**: `humanize_chunked()` (Python) / `humanizeChunked()` (PHP) — разбиение больших текстов по абзацам с независимой обработкой каждого чанка
- **7 новых языковых пакетов для PHP**: украинский (uk), немецкий (de), французский (fr), испанский (es), польский (pl), португальский (pt), итальянский (it)
- PHP-библиотека теперь поддерживает все 9 языков наравне с Python
- **GitHub Actions CI** — матрица тестов: Python 3.9–3.12, PHP 8.1–8.3

### Changed
- Переименование `AntiDetector` → `TextNaturalizer` (Python + PHP)
- Переименование `antidetect.py` → `naturalizer.py`, `AntiDetector.php` → `TextNaturalizer.php`
- Лицензия изменена с MIT на **Personal Use Only** (коммерческое использование запрещено)
- Полная переработка README.md — профессиональная документация на английском без упоминаний антидетекции
- Полная переработка php/README.md — документация API, плагины, все 9 языков
- Очистка метаданных: composer.json (оба), package.json, pyproject.toml — убраны все упоминания anti-detection, обновлены описания
- CHANGELOG.md переведён на английский с подробным описанием всех версий
- Версия обновлена до 0.3.0

### Fixed
- PHP Pipeline теперь корректно вызывает `runPlugins()` до и после каждого из 10 этапов

## [0.2.0] - 2026-02-17

### Added
- **PHP-порт библиотеки** — полный порт на PHP 8.1+ (20 файлов)
- 44 теста, 303 assertion'а для PHP-версии
- README.md переведён на английский язык
- 10-этапный пайплайн обработки текста
- 5 профилей: `chat`, `web`, `seo`, `docs`, `formal`
- CLI-интерфейс (`python -m texthumanize`)
- API анализа текста (`analyze`) и объяснения изменений (`explain`)
- 9 языковых пакетов для Python: RU, UK, EN, DE, FR, ES, PL, PT, IT

## [0.1.0] - 2026-02-16

### Added
- Первый публичный релиз
- Пайплайн гуманизации текста с 6 этапами обработки
- Поддержка русского, украинского и английского языков
- Автоматическое определение языка
- Нормализация типографики (кавычки, тире, многоточия, пробелы)
- Деканцеляризация текста (замена бюрократизмов)
- Разнообразие структуры предложений (разбиение/объединение, замена AI-коннекторов)
- Уменьшение повторов и тавтологий (синонимы)
- Инъекция «живости» для разговорных профилей
- Валидация качества с автоматическим rollback при ухудшении
- Защита сегментов: код, URL, email, markdown, HTML, хештеги, бренды
- CLI-интерфейс
- Метрики анализа «искусственности» текста (artificialityScore)
- 158 тестов для Python
