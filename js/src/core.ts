/**
 * Core API functions — main entry points for TextHumanize.
 */

import type { AnalysisReport, HumanizeOptions, HumanizeResult } from './types';
import { Pipeline } from './pipeline';
import { TextAnalyzer } from './analyzer';

/**
 * Detect language from text (simplified heuristic).
 */
function detectLanguage(text: string): string {
  const sample = text.slice(0, 500).toLowerCase();

  // Cyrillic check
  const cyrillic = (sample.match(/[а-яёіїєґ]/g) || []).length;
  const latin = (sample.match(/[a-z]/g) || []).length;

  if (cyrillic > latin) {
    // Distinguish RU/UK
    const ukChars = (sample.match(/[іїєґ]/g) || []).length;
    return ukChars > 2 ? 'uk' : 'ru';
  }

  // German: ö, ü, ä, ß
  const deChars = (sample.match(/[öüäß]/g) || []).length;
  if (deChars > 2) return 'de';

  // French: é, è, ê, ç, à
  const frChars = (sample.match(/[éèêçàù]/g) || []).length;
  if (frChars > 2) return 'fr';

  // Spanish: ñ, ¿, ¡
  const esChars = (sample.match(/[ñ¿¡]/g) || []).length;
  if (esChars > 0) return 'es';

  return 'en';
}

/**
 * Humanize text — make it more natural-sounding.
 */
export function humanize(
  text: string,
  options?: HumanizeOptions,
): HumanizeResult {
  const opts = { ...options };

  if (!text || !text.trim()) {
    return {
      original: text || '',
      text: text || '',
      lang: opts.lang === 'auto' || !opts.lang ? 'en' : opts.lang,
      profile: opts.profile || 'web',
      intensity: opts.intensity ?? 60,
      changes: [],
      metricsBefore: {},
      metricsAfter: {},
    };
  }

  const lang = opts.lang === 'auto' || !opts.lang
    ? detectLanguage(text)
    : opts.lang;

  const pipeline = new Pipeline({ ...opts, lang });
  return pipeline.run(text, lang);
}

/**
 * Analyze text — get artificiality metrics.
 */
export function analyze(
  text: string,
  lang: string = 'auto',
): AnalysisReport {
  const effectiveLang = lang === 'auto' ? detectLanguage(text) : lang;
  const analyzer = new TextAnalyzer(effectiveLang);
  return analyzer.analyze(text);
}

/**
 * Detect AI-generated text probability.
 */
export function detectAi(
  text: string,
  lang: string = 'auto',
): { verdict: string; score: number; details: Record<string, number> } {
  const report = analyze(text, lang);
  const score = report.artificialityScore;

  let verdict: string;
  if (score >= 70) verdict = 'ai_generated';
  else if (score >= 40) verdict = 'mixed';
  else verdict = 'human_written';

  return {
    verdict,
    score,
    details: {
      artificialityScore: report.artificialityScore,
      avgSentenceLength: report.avgSentenceLength,
      sentenceLengthVariance: report.sentenceLengthVariance,
      typographyScore: report.typographyScore,
    },
  };
}
