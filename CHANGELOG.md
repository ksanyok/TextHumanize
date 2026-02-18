# Changelog

All notable changes to this project are documented in this file.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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

## [0.4.0] - 2025-02-19

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
