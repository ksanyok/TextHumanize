/**
 * Text naturalizer — varies stock sentence-initial connectors and breaks up
 * one over-long sentence where a clean clause boundary exists. Thin wrapper
 * over ./engine.ts.
 */

import type { ChangeEntry } from './types';
import { getLangPack } from './lang';
import { Rng, rewrite } from './engine';

export class TextNaturalizer {
  readonly changes: ChangeEntry[] = [];
  private lang: string;
  private intensity: number;
  private rng: Rng;
  private allowSplit: boolean;

  constructor(lang: string = 'en', profile: string = 'web', intensity: number = 60, seed: number = 0, allowSplit = true) {
    this.lang = lang;
    this.intensity = intensity;
    this.rng = new Rng(seed);
    this.allowSplit = allowSplit && profile !== 'formal' && profile !== 'academic' && profile !== 'docs';
  }

  process(text: string, keep: string[] = []): string {
    const pack = getLangPack(this.lang);
    if (!pack) return text;
    const r = rewrite(text, pack, {
      intensity: this.intensity, rng: this.rng, connectors: true, phrases: true, words: false,
      split: this.allowSplit, keep, lang: this.lang,
    });
    this.changes.push(...r.changes);
    return r.text;
  }
}
