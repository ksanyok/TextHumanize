# Architecture

## Module Structure

```
texthumanize/                    # 75 Python modules, 42,500+ lines
├── core.py                      # Facade: humanize(), analyze(), detect_ai()
├── async_api.py                 # Async wrappers: async_humanize(), async_detect_ai()
├── pipeline.py                  # 17-stage pipeline + adaptive intensity
├── api.py                       # REST API server (12+ endpoints + SSE)
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
│
└── lang/                        # 14 language packs + registry
    ├── en.py, ru.py, de.py ...  # Data only, no logic
    └── ar.py, zh.py, ja.py ...  # Including CJK + RTL
```

## Processing Pipeline

```
Input → Watermark Cleaning → Segmentation → CJK Segmentation → Typography
      → Debureaucratization → Structure → Repetitions → Liveliness
      → Paraphrasing → Syntax Rewriting → Tone Harmonization → Universal
      → Naturalization → Word LM Quality Gate → Readability → Grammar
      → Coherence Repair → Fingerprint Diversification → Validation → Output
```

17 stages with:

- **Adaptive intensity** — auto-reduces processing for already-natural text
- **Graduated retry** — retries at lower intensity if change ratio exceeds limit
- **Plugin hooks** — register before/after any stage

## Design Principles

- **Modular** — each stage is an independent module
- **Declarative rules** — dictionaries and patterns, not neural networks
- **Idempotent** — processing twice ≈ processing once
- **Safe defaults** — won't break meaning at default settings
- **Extensible** — plugin system for custom stages
- **Zero dependencies** — pure Python stdlib
- **Lazy imports** — modules loaded on first use
