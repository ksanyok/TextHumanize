# TextHumanize — Strategic Roadmap

**Version**: 0.20+ | **Last updated**: 2026-02-28 | **Status**: Active

---

## Executive Summary

TextHumanize is the **only open-source, offline, zero-dependency** text humanization
and AI detection library. This document defines the phased plan to make it the
world's #1 solution in this space, with a focus on commercial viability.

### Core Competitive Advantages (to preserve)
- 100% offline — GDPR/HIPAA-ready, no data leaks
- Zero external dependencies — pure Python stdlib
- Deterministic output (seed-based reproducibility)
- Full audit trail via `explain()`
- Multi-SDK: Python + JS/TS + PHP
- Self-hostable (Docker, on-prem)

### Critical Problems (identified via audit, 2026-02-28)
1. **AI detection returns score=0.0 for non-English** — only EN works reliably
2. **Russian humanization produces broken grammar** — artifacts, stray punctuation
3. **syntax_rewriting crashes for 5 languages** — FR/ES/IT/PL/PT
4. **All 14 languages marked as "deep"** — no distinction between real and shallow
5. **Humanization doesn't fool external detectors** — rule-based word swaps don't break statistical patterns
6. **Circular self-evaluation** — humanizer and detector target same features

---

## Phase 0 — Critical Bug Fixes (v0.20.0)

**Goal**: Library stops producing broken output. Detection works for all supported languages.

| # | Task | Status |
|---|------|--------|
| 0.1 | Fix non-EN detection: add AI markers for DE/FR/ES/IT/PL/PT/TR, extend hedging patterns, add per-language passive voice regex | Done |
| 0.2 | Fix `score` field to use `combined_score` (ensemble) instead of heuristic-only | Done |
| 0.3 | Implement language tiers: TIER1 (en/ru/uk/de), TIER2 (fr/es/it/pl/pt), TIER3 (ar/zh/ja/ko/tr) | Done |
| 0.4 | Fix syntax_rewriting to gracefully skip unsupported languages | Done |
| 0.5 | Improve RU humanization grammar: validate sentence integrity post-stage | Done |
| 0.6 | Modular architecture: `texthumanize[detect]`, `texthumanize[full]`, per-language extras | Done |

---

## Phase 1 — Effective Humanization (v0.21.0)

**Goal**: AI text after humanization drops below 0.50 on internal detector in ≥70% of cases.

| # | Task | Description |
|---|------|-------------|
| 1.1 | **Entropy injection** | Inject low-frequency synonym variants to break predictable word choice |
| 1.2 | **Burstiness injection** | Deliberately vary sentence lengths (split long, merge short) to break uniformity |
| 1.3 | **Sentence mixing** | Reorder sentences within paragraphs, swap clauses |
| 1.4 | **Cadence variation** | Randomize punctuation patterns (semicolons → periods, dashes → commas) |
| 1.5 | **External benchmark suite** | Script to validate against GPTZero API (optional, with API key) |
| 1.6 | **Per-language calibration** | Tune sigmoid center/steepness per language family |

---

## Phase 2 — Neural Detection (v0.22.0)

**Goal**: Transformer-quality detection, still offline. Optional ONNX dependency.

| # | Task | Description | Weight Impact |
|---|------|-------------|---------------|
| 2.1 | ONNX Runtime optional dep | `texthumanize[onnx]` extra | +15 MB |
| 2.2 | Distilled RoBERTa detector (EN) | 6-layer, INT8 quantized → ONNX | +25 MB |
| 2.3 | Perplexity from real LM | GPT-2 distilled (117M → INT8 ONNX) | +30 MB |
| 2.4 | Multi-language detection model | mBERT-tiny or per-language models | +15–50 MB |
| 2.5 | Training data pipeline | 50K+ samples per language (ChatGPT/Claude + Wikipedia/News) | — |

---

## Phase 3 — Neural Humanization (v0.23.0)

**Goal**: LLM-quality paraphrasing offline. Optional heavy dependency.

| # | Task | Description | Weight Impact |
|---|------|-------------|---------------|
| 3.1 | T5-small paraphraser (ONNX) | Sentence-level, EN | +100 MB |
| 3.2 | Hybrid mode | `humanize(mode="fast"\|"quality"\|"best")` | — |
| 3.3 | Anti-detector strategies | Target GPTZero/Originality.ai specific patterns | — |
| 3.4 | Quality gate improvement | Perplexity + semantic similarity validation | — |

---

## Phase 4 — Commercial Features (v1.0.0)

**Goal**: Enterprise-ready release.

| # | Task | Description |
|---|------|-------------|
| 4.1 | SaaS-ready API | Rate limiting, API keys, usage metering, WebSocket |
| 4.2 | Admin dashboard | Web UI for monitoring and configuration |
| 4.3 | Pluggable detector registry | `detect_ai(text, detectors=["builtin", "gptzero"])` |
| 4.4 | Compliance pack | GDPR statement, SOC 2 checklist, DPA template, audit log export |
| 4.5 | License server | Hardware fingerprint + license key for Enterprise tier |
| 4.6 | White-label SDK | Custom branding support |
| 4.7 | Browser extension | Chrome/Edge/Firefox — detect AI on any webpage |
| 4.8 | Document upload | PDF/DOCX/TXT parsing for CLI and API |
| 4.9 | LMS integrations | Google Classroom, Moodle, Canvas connectors |

---

## Modular Architecture

The library uses Python's `[extras]` system for modular installation:

```bash
pip install texthumanize                    # 5 MB — core, rule-based, zero deps
pip install texthumanize[detect]            # +50 MB — ONNX transformer detector
pip install texthumanize[paraphrase]        # +100 MB — T5 neural paraphraser
pip install texthumanize[full]              # all features
pip install texthumanize[api]               # OpenAI/Anthropic API clients
pip install texthumanize[lang-cjk]          # CJK language support (zh/ja/ko)
pip install texthumanize[lang-european]     # European languages (fr/es/it/pl/pt)
```

Core package remains **zero-dependency** and **<5 MB**. Neural models are downloaded
on first use and cached in `~/.cache/texthumanize/`.

---

## Language Tier System

| Tier | Languages | Detection | Humanization | Dictionary |
|------|-----------|-----------|-------------|------------|
| **TIER1** (Full) | en, ru, uk, de | 18-metric ensemble + statistical + neural | Full 17-stage pipeline | 700–1700 entries |
| **TIER2** (Good) | fr, es, it, pl, pt | Ensemble + statistical (calibrated) | 15-stage pipeline (no syntax rewriting) | 600–800 entries |
| **TIER3** (Basic) | ar, zh, ja, ko, tr | Statistical-only (limited markers) | Universal pipeline (typography + naturalizer) | 600+ entries |
| **Universal** | any other | Basic heuristics | Typography + universal processing | — |

---

## Version History

| Version | Date | Key Changes |
|---------|------|-------------|
| 0.19.0 | 2025-06-30 | Training infrastructure, trained MLP weights |
| **0.20.0** | 2026-02-28 | **Critical fixes: non-EN detection, language tiers, modular extras** |
| 0.21.0 | TBD | Effective humanization (entropy/burstiness/mixing) |
| 0.22.0 | TBD | Neural detection (ONNX, transformer) |
| 0.23.0 | TBD | Neural humanization (T5 paraphraser) |
| 1.0.0 | TBD | Commercial release (SaaS API, dashboard, compliance) |

---

## Success Metrics

| Metric | Current | v0.20 Target | v1.0 Target |
|--------|---------|-------------|-------------|
| EN AI detection accuracy | 80% | 85% | 95% |
| RU/DE detection accuracy | 0% | 70% | 90% |
| FR/ES detection accuracy | 0% | 60% | 85% |
| Humanization bypass rate (internal) | ~100% (circular) | 70% | 85% |
| Humanization bypass rate (GPTZero) | unknown | benchmark | 70% |
| False positive rate (human→AI) | 50% non-EN | <15% | <5% |
| Tests passing | 1994 | 2100+ | 2500+ |
| Package size (core) | 5.2 MB | 5.5 MB | <6 MB |
