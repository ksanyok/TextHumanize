/**
 * Core API functions — main entry points for TextHumanize.
 */

import type { AnalysisReport, HumanizeOptions, HumanizeResult } from './types';
import { Pipeline } from './pipeline';
import { TextAnalyzer } from './analyzer';
import { humanizeHtml } from './html';
import { detectLanguage } from './langdetect';
import { normalizeLang } from './lang';

export { detectLanguage };

const HTML_RE = /<(?:[a-zA-Z][a-zA-Z0-9-]*)(?:\s[^<>]*)?>|<\/[a-zA-Z][a-zA-Z0-9-]*>/;

/**
 * Humanize text — make it more natural-sounding.
 *
 * Input containing HTML tags is processed with `humanizeHtml()` so markup,
 * links and anchors are preserved (disable with `preserve.html = false`).
 */
export function humanize(text: string, options?: HumanizeOptions): HumanizeResult {
  const opts = { ...options };
  if (!text || !text.trim()) {
    return {
      original: text || '',
      text: text || '',
      lang: opts.lang === 'auto' || !opts.lang ? 'en' : normalizeLang(opts.lang),
      profile: opts.profile || 'web',
      intensity: opts.intensity ?? 60,
      changes: [],
      metricsBefore: {},
      metricsAfter: {},
    };
  }

  const lang = opts.lang === 'auto' || !opts.lang ? detectLanguage(text.replace(/<[^<>]*>/g, ' ')) : normalizeLang(opts.lang);

  if (opts.preserve?.html !== false && HTML_RE.test(text)) {
    const r = humanizeHtml(text, { ...opts, lang });
    const analyzer = new TextAnalyzer(lang);
    const plain = (s: string) => s.replace(/<[^<>]*>/g, ' ').replace(/\s+/g, ' ').trim();
    return {
      original: text,
      text: r.html,
      lang,
      profile: opts.profile || 'web',
      intensity: opts.intensity ?? 60,
      changes: r.changes,
      metricsBefore: analyzer.analyze(plain(text)) as unknown as Record<string, number>,
      metricsAfter: analyzer.analyze(plain(r.html)) as unknown as Record<string, number>,
    };
  }

  const pipeline = new Pipeline({ ...opts, lang });
  return pipeline.run(text, lang);
}

/** Analyze text — get artificiality metrics. */
export function analyze(text: string, lang: string = 'auto'): AnalysisReport {
  const effectiveLang = lang === 'auto' ? detectLanguage(text) : normalizeLang(lang);
  const analyzer = new TextAnalyzer(effectiveLang);
  return analyzer.analyze(text);
}

/** Detect AI-generated text probability (0–100 score + verdict). */
export function detectAi(
  text: string,
  lang: string = 'auto',
): { verdict: string; score: number; details: Record<string, number> } {
  const report = analyze(text, lang);
  const score = report.artificialityScore;
  const verdict = score >= 60 ? 'ai_generated' : score >= 35 ? 'mixed' : 'human_written';
  return {
    verdict,
    score,
    details: {
      artificialityScore: report.artificialityScore,
      avgSentenceLength: report.avgSentenceLength,
      sentenceLengthVariance: report.sentenceLengthVariance,
      burstiness: report.burstinessScore,
      connectorRatio: report.connectorRatio,
      bureaucraticRatio: report.bureaucraticRatio,
      typographyScore: report.typographyScore,
    },
  };
}
