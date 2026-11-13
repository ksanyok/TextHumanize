/**
 * Pipeline — orchestrates the processing stages for plain text.
 *
 * 1. Typography normalization
 * 2. Edit engine (AI cliches → officialese → stock connectors → one long-sentence split)
 * 3. Change-ratio guard with a graduated retry at lower intensity
 *
 * Text that contains HTML is routed to ./html.ts by `humanize()`.
 */

import type { AnalysisReport, ChangeEntry, HumanizeOptions, HumanizeResult } from './types';
import { TextAnalyzer } from './analyzer';
import { TypographyNormalizer } from './normalizer';
import { getLangPack } from './lang';
import { Rng, hashSeed, rewrite } from './engine';

const DEFAULT_OPTIONS: Required<HumanizeOptions> = {
  lang: 'auto',
  profile: 'web',
  intensity: 60,
  preserve: {
    codeBlocks: true,
    urls: true,
    emails: true,
    hashtags: true,
    mentions: true,
    markdown: true,
    html: true,
    numbers: false,
    brandTerms: [],
  },
  constraints: {
    maxChangeRatio: 0.4,
    minSentenceLength: 3,
    keepKeywords: [],
  },
  seed: 0,
};

/** Profiles where sentences must not be restructured. */
const NO_SPLIT = new Set(['formal', 'academic', 'docs']);

/** URLs, e-mails, @mentions and #hashtags survive verbatim. */
const PROTECT_RE = /\b(?:https?:\/\/|www\.)[^\s<>"']+|[\w.+-]+@[\w-]+\.[\w.-]+|(?<![\p{L}\p{N}])[@#][\p{L}\p{N}_]+/gu;

export class Pipeline {
  private options: Required<HumanizeOptions>;

  constructor(options?: HumanizeOptions) {
    this.options = { ...DEFAULT_OPTIONS, ...options } as Required<HumanizeOptions>;
    this.options.preserve = { ...DEFAULT_OPTIONS.preserve, ...(options?.preserve ?? {}) };
    this.options.constraints = { ...DEFAULT_OPTIONS.constraints, ...(options?.constraints ?? {}) };
  }

  /** Terms the engine must not touch. */
  keepTerms(text: string): string[] {
    const keep = [
      ...(this.options.preserve.brandTerms ?? []),
      ...(this.options.constraints.keepKeywords ?? []),
    ];
    for (const m of text.matchAll(PROTECT_RE)) keep.push(m[0]);
    return keep;
  }

  /** Effective intensity for a text with the given AI score (0–100). */
  static adaptIntensity(intensity: number, aiScore: number): number {
    if (aiScore <= 5) return 0;
    if (aiScore <= 15) return Math.max(8, Math.floor(intensity * 0.35));
    if (aiScore <= 25) return Math.max(10, Math.floor(intensity * 0.5));
    if (aiScore >= 70) return Math.min(100, Math.floor(intensity * 1.2));
    return intensity;
  }

  /** Run the humanization pipeline. */
  run(text: string, lang: string): HumanizeResult {
    const analyzer = new TextAnalyzer(lang);
    const metricsBefore = analyzer.analyze(text);
    const original = text;
    const changes: ChangeEntry[] = [];
    const intensity = this.options.intensity;
    const seed = this.options.seed || hashSeed(text);

    const normalizer = new TypographyNormalizer(this.options.profile, lang);
    let processed = normalizer.normalize(text);
    changes.push(...normalizer.changes);

    const effective = Pipeline.adaptIntensity(intensity, metricsBefore.artificialityScore);
    if (effective === 0) {
      changes.push({
        type: 'skip_natural',
        description: `Text already natural (AI=${metricsBefore.artificialityScore}%). Typography only.`,
      });
      return this.buildResult(original, processed, lang, changes, metricsBefore, analyzer.analyze(processed));
    }
    if (effective !== intensity) {
      changes.push({
        type: 'adaptive_intensity',
        description: `Adapted intensity: AI=${metricsBefore.artificialityScore}%, ${intensity}→${effective}`,
      });
    }

    const pack = getLangPack(lang);
    if (pack) {
      const keep = this.keepTerms(processed);
      const run = (level: number) => {
        const rng = new Rng(seed);
        // Paragraph by paragraph so splits and budgets stay local.
        const parts = processed.split(/(\n\s*\n)/);
        const out: string[] = [];
        const ch: ChangeEntry[] = [];
        for (const part of parts) {
          if (/^\n\s*\n$/.test(part) || !part.trim()) { out.push(part); continue; }
          const r = rewrite(part, pack, {
            intensity: level, rng, keep, lang, split: !NO_SPLIT.has(this.options.profile),
          });
          out.push(r.text);
          ch.push(...r.changes);
        }
        return { text: out.join(''), changes: ch };
      };

      let r = run(effective);
      const maxChange = this.options.constraints.maxChangeRatio ?? 0.4;
      if (this.calcChangeRatio(original, r.text) > maxChange) {
        const retryLevel = Math.max(5, Math.floor(effective * 0.4));
        const retry = run(retryLevel);
        if (this.calcChangeRatio(original, retry.text) <= maxChange) {
          r = retry;
          r.changes.push({ type: 'graduated_retry', description: `Retry at lower intensity: ${retryLevel}` });
        }
      }
      processed = r.text;
      changes.push(...r.changes);
    }

    return this.buildResult(original, processed, lang, changes, metricsBefore, analyzer.analyze(processed));
  }

  private calcChangeRatio(original: string, current: string): number {
    const origWords = original.split(/\s+/);
    const currWords = current.split(/\s+/);
    if (origWords.length === 0) return 0;
    const origCounts = new Map<string, number>();
    for (const w of origWords) origCounts.set(w, (origCounts.get(w) || 0) + 1);
    let common = 0;
    for (const w of currWords) {
      const c = origCounts.get(w) || 0;
      if (c > 0) { common++; origCounts.set(w, c - 1); }
    }
    const similarity = (2 * common) / (origWords.length + currWords.length);
    return Math.min(1 - similarity, 1.0);
  }

  private buildResult(
    original: string, text: string, lang: string, changes: ChangeEntry[],
    metricsBefore: AnalysisReport, metricsAfter: AnalysisReport,
  ): HumanizeResult {
    return {
      original,
      text,
      lang,
      profile: this.options.profile,
      intensity: this.options.intensity,
      changes,
      metricsBefore: metricsBefore as unknown as Record<string, number>,
      metricsAfter: metricsAfter as unknown as Record<string, number>,
    };
  }
}
