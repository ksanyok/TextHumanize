# TextHumanize — JavaScript/TypeScript Port

Zero-dependency TypeScript port of TextHumanize.

## Status

**Production-ready** — publication-safe engine for 9 languages (en, ru, uk, de, fr, es, pl, pt, it), HTML-aware mode, detector; 90+ tests including six-language SEO fixtures.

## Installation

```bash
npm install texthumanize
```

## Usage

```typescript
import { humanize, analyze, detectAi } from 'texthumanize';

// Humanize text
const result = humanize('This text utilizes advanced methodologies.', {
  lang: 'en',
  profile: 'web',
  intensity: 60,
});
console.log(result.text);

// Analyze text
const report = analyze('Some text to check.', 'en');
console.log(report.artificialityScore);

// Detect AI
const ai = detectAi('AI-generated text here.', 'en');
console.log(ai.verdict, ai.score);
```

### HTML articles

```typescript
import { humanizeHtml } from 'texthumanize';

const r = humanizeHtml(articleHtml, {
  lang: 'uk',          // or 'auto'
  profile: 'seo',
  intensity: 55,
  constraints: { keepKeywords: ['купити ноутбук'] },
});
r.html;            // same tags, links and anchors — only visible prose rewritten
r.changes;         // [{ type, description, original, replacement, block }]
r.stats;           // { blocks, changed, reverted, skipped }
r.aiScoreBefore;   // 0–100
r.aiScoreAfter;
```

What is never touched: `<a>…</a>` (anchor text included), `<code>`, `<pre>`,
`<script>`, `<style>`, attributes, entities, and any element with
`data-humanize="off"`, `translate="no"` or class `notranslate`. Inline tags
(`<strong>`, `<em>`, `<br>` …) are kept in place; if a block's markup would not
survive, the block is left as it was (`stats.reverted`). Headings are not
touched by default (`headingFactor: 0`, they carry SEO keywords; pass e.g. 0.45
to opt in); list items/table cells get `listFactor` (0.75) of the intensity.

### What the engine does

Edits are publication-safe by design — no slang, no filler, no foreign asides:

1. **AI cliches** — "In today's rapidly evolving digital landscape", "Следует отметить, что", "Cabe destacar que" … replaced or dropped.
2. **Stock connectors** at sentence start — "Moreover,", "Кроме того,", "Ponadto" … varied (same meaning class) or dropped.
3. **Officialese** — "utilize", "осуществлять", "здійснювати" … replaced only where inflection/gender agreement and collocations survive.
4. **One over-long sentence** per paragraph may be split at a clause joint (", but", ", а", ";").

Dictionaries are generated from the Python packs: `python3 scripts/export_js_langs.py`.

## Ported Modules

- [x] Core API (`humanize`, `analyze`, `detectAi`)
- [x] Text Analyzer (artificiality metrics)
- [x] Pipeline (full stage orchestration)
- [x] Typography Normalizer
- [x] Debureaucratizer
- [x] Text Naturalizer
- [x] Language packs: EN, RU, UK, DE, FR, ES, PL, PT, IT (generated)
- [x] HTML-aware mode (`humanizeHtml`)
- [x] Type definitions
- [ ] Structure diversifier
- [ ] Repetition reducer
- [ ] Liveliness injector
- [ ] Semantic paraphraser
- [ ] Sentence splitter

## Development

```bash
npm install
npm run build
npm test
```
