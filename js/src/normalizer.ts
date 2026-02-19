/**
 * Typography normalizer — fixes common AI-generated formatting patterns.
 */

import type { ChangeEntry } from './types';

export class TypographyNormalizer {
  readonly changes: ChangeEntry[] = [];
  private profile: string;
  private lang: string;

  constructor(profile: string = 'web', lang: string = 'en') {
    this.profile = profile;
    this.lang = lang;
  }

  normalize(text: string): string {
    let result = text;

    // Multiple spaces → single
    result = this.applyRule(result, / {2,}/g, ' ', 'double_spaces');

    // Space before punctuation
    result = this.applyRule(result, / ([.,;:!?])/g, '$1', 'space_before_punct');

    // Missing space after punctuation (avoid URLs and numbers like 3.14)
    result = this.applyRule(
      result,
      /([.!?])([A-ZА-ЯЁЇІЄҐÄÖÜß])/g,
      '$1 $2',
      'missing_space_after_punct',
    );

    // Smart quotes for Cyrillic
    if (this.lang === 'ru' || this.lang === 'uk') {
      result = this.normalizeRuQuotes(result);
    }

    // Normalize dashes
    result = this.applyRule(result, / -- /g, ' — ', 'dashes');
    result = this.applyRule(result, / - /g, ' — ', 'dashes');

    // Ellipsis normalization
    result = this.applyRule(result, /\.{3,}/g, '…', 'ellipsis');

    // Trim trailing spaces per line
    result = result.replace(/ +\n/g, '\n');

    return result;
  }

  private applyRule(
    text: string,
    pattern: RegExp,
    replacement: string,
    ruleType: string,
  ): string {
    const matches = text.match(pattern);
    if (!matches || matches.length === 0) return text;

    const result = text.replace(pattern, replacement);
    if (result !== text) {
      this.changes.push({
        type: 'typography',
        description: `${ruleType}: ${matches.length} fix(es)`,
      });
    }
    return result;
  }

  private normalizeRuQuotes(text: string): string {
    // Replace straight quotes with «» for Cyrillic
    let result = text;
    let inQuote = false;
    const chars: string[] = [];

    for (let i = 0; i < result.length; i++) {
      if (result[i] === '"') {
        if (!inQuote) {
          chars.push('«');
          inQuote = true;
        } else {
          chars.push('»');
          inQuote = false;
        }
      } else {
        chars.push(result[i]);
      }
    }

    const newResult = chars.join('');
    if (newResult !== result) {
      this.changes.push({
        type: 'typography',
        description: 'Normalized quotes to «»',
      });
    }
    return newResult;
  }
}
