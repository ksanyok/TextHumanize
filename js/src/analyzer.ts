/**
 * Text analyzer — artificiality metrics computation.
 */

import type { AnalysisReport } from './types';
import { aiScore, features, splitSentences } from './detector';

export class TextAnalyzer {
  private lang: string;

  constructor(lang: string = 'en') {
    this.lang = lang;
  }

  /**
   * Analyze text and compute artificiality metrics.
   */
  analyze(text: string): AnalysisReport {
    const report: AnalysisReport = {
      lang: this.lang,
      totalChars: 0,
      totalWords: 0,
      totalSentences: 0,
      avgSentenceLength: 0,
      sentenceLengthVariance: 0,
      bureaucraticRatio: 0,
      connectorRatio: 0,
      repetitionScore: 0,
      typographyScore: 0,
      burstinessScore: 0.5,
      artificialityScore: 0,
      fleschKincaidGrade: 0,
      colemanLiauIndex: 0,
      avgWordLength: 0,
      avgSyllablesPerWord: 0,
      predictabilityScore: 0,
      charPerplexity: 0,
      vocabularyRichness: 0,
    };

    if (!text || text.trim().length < 10) return report;

    report.totalChars = text.length;
    const words = text.split(/\s+/).filter(Boolean);
    report.totalWords = words.length;

    const sentences = this.splitSentences(text);
    report.totalSentences = sentences.length;

    if (sentences.length === 0) return report;

    // Sentence lengths
    const sentLens = sentences.map(s => s.split(/\s+/).filter(Boolean).length);
    const avg = sentLens.reduce((a, b) => a + b, 0) / sentLens.length;
    report.avgSentenceLength = avg;

    // Variance
    const variance = sentLens.reduce((sum, l) => sum + (l - avg) ** 2, 0) / sentLens.length;
    report.sentenceLengthVariance = variance;

    // Word length
    const cleanWords = words.map(w => w.replace(/[.,;:!?"'()[\]{}«»""]/g, '')).filter(w => w.length > 0);
    if (cleanWords.length > 0) {
      report.avgWordLength = cleanWords.reduce((s, w) => s + w.length, 0) / cleanWords.length;
    }

    // Typography score (perfect = AI)
    const hasDoubleSpaces = /  /.test(text);
    const hasTypos = /[.][A-ZА-Я]/.test(text); // missing space after period
    report.typographyScore = hasDoubleSpaces || hasTypos ? 0.3 : 0.8;

    // Artificiality score — dictionary + rhythm based (see ./detector.ts)
    const f = features(text, this.lang);
    report.burstinessScore = f.sentenceLengthCV;
    report.connectorRatio = f.connectorStartShare;
    report.bureaucraticRatio = f.officialesePer100 / 100;
    report.artificialityScore = aiScore(text, this.lang);

    return report;
  }

  private splitSentences(text: string): string[] {
    return splitSentences(text);
  }
}
