/**
 * Debureaucratizer — replaces heavy bureaucratic words and phrases
 * with simpler, more natural alternatives.
 */

import type { ChangeEntry, LangPack } from './types';
import { getLangPack } from './lang';

/**
 * Seeded pseudo-random number generator (xoshiro128**).
 */
class Rng {
  private s: Uint32Array;

  constructor(seed: number = 0) {
    this.s = new Uint32Array(4);
    // Splitmix32 to seed state
    let z = (seed | 0) + 0x9e3779b9;
    for (let i = 0; i < 4; i++) {
      z ^= z >>> 16; z = Math.imul(z, 0x45d9f3b);
      z ^= z >>> 16; z = Math.imul(z, 0x45d9f3b);
      z ^= z >>> 16;
      this.s[i] = z >>> 0;
      z += 0x9e3779b9;
    }
  }

  /** Returns [0, 1) */
  random(): number {
    const s = this.s;
    const result = Math.imul(s[1] * 5, 7) >>> 0;
    const t = s[1] << 9;
    s[2] ^= s[0]; s[3] ^= s[1]; s[1] ^= s[2]; s[0] ^= s[3];
    s[2] ^= t;
    s[3] = (s[3] << 11 | s[3] >>> 21) >>> 0;
    return (result >>> 0) / 0x100000000;
  }

  choice<T>(arr: T[]): T {
    return arr[Math.floor(this.random() * arr.length)];
  }
}

export class Debureaucratizer {
  readonly changes: ChangeEntry[] = [];
  private langPack: LangPack | undefined;
  private intensity: number;
  private rng: Rng;
  private maxChanges: number = 100;
  private changesMade: number = 0;

  constructor(
    lang: string = 'en',
    profile: string = 'web',
    intensity: number = 60,
    seed: number = 0,
  ) {
    this.langPack = getLangPack(lang);
    this.intensity = intensity;
    this.rng = new Rng(seed);
  }

  process(text: string): string {
    if (!this.langPack) return text;

    const prob = this.intensity / 100;
    if (prob < 0.05) return text;

    // Change budget: max 15% of words
    const wordCount = text.split(/\s+/).length;
    this.maxChanges = Math.max(2, Math.floor(wordCount * 0.15));
    this.changesMade = 0;

    text = this.replaceWords(text, prob);
    return text;
  }

  private replaceWords(text: string, prob: number): string {
    const dict = this.langPack?.bureaucratic;
    if (!dict) return text;

    for (const [word, replacements] of Object.entries(dict)) {
      if (this.changesMade >= this.maxChanges) break;
      if (this.rng.random() > prob) continue;

      const pattern = new RegExp(`(?<=\\s|^)${escapeRegex(word)}(?=\\s|$|[.,;:!?])`, 'gi');
      const matches = [...text.matchAll(pattern)];

      for (const match of matches.reverse()) {
        if (this.changesMade >= this.maxChanges) break;
        if (this.rng.random() > prob) continue;

        const original = match[0];
        let replacement = this.rng.choice(replacements);

        // Preserve case
        if (original[0] === original[0].toUpperCase() && original[0] !== original[0].toLowerCase()) {
          replacement = replacement[0].toUpperCase() + replacement.slice(1);
        }

        const idx = match.index!;
        text = text.slice(0, idx) + replacement + text.slice(idx + original.length);
        this.changesMade++;

        this.changes.push({
          type: 'decancel_word',
          description: `${original} → ${replacement}`,
        });
      }
    }

    return text;
  }
}

function escapeRegex(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}
