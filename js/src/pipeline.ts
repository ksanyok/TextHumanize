/**
 * Pipeline — orchestrates all processing stages.
 *
 * Stages:
 * 1. Typography normalization
 * 2. Debureaucratization (for supported languages)
 * 3. Naturalizer (burstiness, AI word replacement, connector variation)
 */

import type { AnalysisReport, ChangeEntry, HumanizeOptions, HumanizeResult } from './types';
import { TextAnalyzer } from './analyzer';
import { TypographyNormalizer } from './normalizer';
import { Debureaucratizer } from './debureaucratizer';
import { TextNaturalizer } from './naturalizer';
import { hasDeepSupport } from './lang';

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

export class Pipeline {
  private options: Required<HumanizeOptions>;

  constructor(options?: HumanizeOptions) {
    this.options = { ...DEFAULT_OPTIONS, ...options } as Required<HumanizeOptions>;
  }

  /**
   * Run the humanization pipeline.
   */
  run(text: string, lang: string): HumanizeResult {
    const analyzer = new TextAnalyzer(lang);
    const metricsBefore = analyzer.analyze(text);

    const original = text;
    const changes: ChangeEntry[] = [];
    let processed = text;
    const intensity = this.options.intensity;
    const seed = this.options.seed;

    // Adaptive intensity based on AI score
    const aiScore = metricsBefore.artificialityScore;
    let effectiveIntensity = intensity;

    if (aiScore <= 5) {
      // Already natural — only typography
      const normalizer = new TypographyNormalizer(this.options.profile, lang);
      processed = normalizer.normalize(processed);
      changes.push(...normalizer.changes);
      changes.push({
        type: 'skip_natural',
        description: `Text already natural (AI=${aiScore}%). Typography only.`,
      });

      const metricsAfter = analyzer.analyze(processed);
      return this.buildResult(original, processed, lang, changes, metricsBefore, metricsAfter);
    } else if (aiScore <= 15) {
      effectiveIntensity = Math.max(8, Math.floor(intensity * 0.35));
    } else if (aiScore <= 25) {
      effectiveIntensity = Math.max(10, Math.floor(intensity * 0.5));
    } else if (aiScore >= 70) {
      effectiveIntensity = Math.min(100, Math.floor(intensity * 1.3));
    }

    if (effectiveIntensity !== intensity) {
      changes.push({
        type: 'adaptive_intensity',
        description: `Adapted intensity: AI=${aiScore}%, ${intensity}→${effectiveIntensity}`,
      });
    }

    // 1. Typography normalization
    const normalizer = new TypographyNormalizer(this.options.profile, lang);
    processed = normalizer.normalize(processed);
    changes.push(...normalizer.changes);

    // 2. Debureaucratization (for languages with dictionaries)
    if (hasDeepSupport(lang)) {
      const decancel = new Debureaucratizer(lang, this.options.profile, effectiveIntensity, seed);
      processed = decancel.process(processed);
      changes.push(...decancel.changes);
    }

    // 3. Naturalizer (for all languages)
    const naturalizer = new TextNaturalizer(lang, this.options.profile, effectiveIntensity, seed);
    processed = naturalizer.process(processed);
    changes.push(...naturalizer.changes);

    // 4. Validate change ratio
    const maxChange = this.options.constraints.maxChangeRatio ?? 0.4;
    const changeRatio = this.calcChangeRatio(original, processed);

    if (changeRatio > maxChange) {
      // Graduated retry at lower intensity
      const retryIntensity = Math.max(5, Math.floor(effectiveIntensity * 0.4));
      let retryText = text;
      const retryChanges: ChangeEntry[] = [];

      const retryNorm = new TypographyNormalizer(this.options.profile, lang);
      retryText = retryNorm.normalize(retryText);
      retryChanges.push(...retryNorm.changes);

      if (hasDeepSupport(lang)) {
        const retryDecancel = new Debureaucratizer(lang, this.options.profile, retryIntensity, seed);
        retryText = retryDecancel.process(retryText);
        retryChanges.push(...retryDecancel.changes);
      }

      const retryNat = new TextNaturalizer(lang, this.options.profile, retryIntensity, seed);
      retryText = retryNat.process(retryText);
      retryChanges.push(...retryNat.changes);

      const retryRatio = this.calcChangeRatio(original, retryText);
      if (retryRatio <= maxChange) {
        processed = retryText;
        changes.length = 0;
        changes.push(...retryChanges);
        changes.push({
          type: 'graduated_retry',
          description: `Retry at lower intensity: ${retryIntensity}`,
        });
      }
    }

    const metricsAfter = analyzer.analyze(processed);
    return this.buildResult(original, processed, lang, changes, metricsBefore, metricsAfter);
  }

  private calcChangeRatio(original: string, current: string): number {
    const origWords = original.split(/\s+/);
    const currWords = current.split(/\s+/);
    if (origWords.length === 0) return 0;

    const m = origWords.length;
    const n = currWords.length;

    const origCounts = new Map<string, number>();
    for (const w of origWords) {
      origCounts.set(w, (origCounts.get(w) || 0) + 1);
    }
    const currCounts = new Map<string, number>();
    for (const w of currWords) {
      currCounts.set(w, (currCounts.get(w) || 0) + 1);
    }

    let common = 0;
    for (const [word, origCount] of origCounts) {
      const currCount = currCounts.get(word) || 0;
      common += Math.min(origCount, currCount);
    }

    const similarity = (2 * common) / (m + n);
    return Math.min(1 - similarity, 1.0);
  }

  private buildResult(
    original: string,
    text: string,
    lang: string,
    changes: ChangeEntry[],
    metricsBefore: AnalysisReport,
    metricsAfter: AnalysisReport,
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
