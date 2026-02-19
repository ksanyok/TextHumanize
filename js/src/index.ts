/**
 * TextHumanize — Algorithmic text humanization (TypeScript port)
 *
 * Zero-dependency, rule-based text transformation for making
 * AI-generated text appear more natural and human-written.
 *
 * @packageDocumentation
 */

export { humanize, analyze, detectAi } from './core';
export { Pipeline } from './pipeline';
export { TextAnalyzer } from './analyzer';
export { TypographyNormalizer } from './normalizer';
export { Debureaucratizer } from './debureaucratizer';
export { TextNaturalizer } from './naturalizer';
export { getLangPack, hasDeepSupport, supportedLanguages } from './lang';
export type {
  HumanizeOptions,
  HumanizeResult,
  AnalysisReport,
  LangPack,
  ChangeEntry,
} from './types';
export { VERSION } from './version';
