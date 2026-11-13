/**
 * TextHumanize — Algorithmic text humanization (TypeScript port)
 *
 * Zero-dependency, rule-based text transformation for making
 * AI-generated text appear more natural and human-written.
 *
 * @packageDocumentation
 */

export { humanize, analyze, detectAi, detectLanguage } from './core';
export { humanizeHtml } from './html';
export { aiScore, features as detectorFeatures } from './detector';
export { Pipeline } from './pipeline';
export { TextAnalyzer } from './analyzer';
export { TypographyNormalizer } from './normalizer';
export { Debureaucratizer } from './debureaucratizer';
export { TextNaturalizer } from './naturalizer';
export { getLangPack, hasDeepSupport, supportedLanguages, normalizeLang } from './lang';
export type {
  HumanizeOptions,
  HumanizeResult,
  AnalysisReport,
  LangPack,
  ChangeEntry,
  HumanizeHtmlOptions,
  HumanizeHtmlResult,
  LangData,
} from './types';
export { VERSION } from './version';
