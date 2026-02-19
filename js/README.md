# TextHumanize — JavaScript/TypeScript Port

Zero-dependency TypeScript port of TextHumanize.

## Status

**Skeleton** — core types, analyzer, and pipeline structure are in place.
Full processing stages (debureaucratization, naturalization, etc.) will be
ported incrementally.

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

## Currently Ported

- [x] Core API (`humanize`, `analyze`, `detectAi`)
- [x] Text Analyzer (artificiality metrics)
- [x] Pipeline skeleton
- [x] Language packs: EN, RU
- [x] Type definitions
- [ ] Typography normalizer
- [ ] Debureaucratizer
- [ ] Structure diversifier
- [ ] Repetition reducer
- [ ] Liveliness injector
- [ ] Text naturalizer
- [ ] Semantic paraphraser
- [ ] Sentence splitter
- [ ] Full language packs (UK, DE, FR, ES, PL, PT, IT)

## Development

```bash
npm install
npm run build
npm test
```
