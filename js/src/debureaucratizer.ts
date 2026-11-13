/**
 * Debureaucratizer — replaces officialese words and phrases (and AI
 * cliches) with plainer equivalents. Thin wrapper over ./engine.ts.
 */

import type { ChangeEntry } from './types';
import { getLangPack } from './lang';
import { Rng, rewrite } from './engine';

export class Debureaucratizer {
  readonly changes: ChangeEntry[] = [];
  private lang: string;
  private intensity: number;
  private rng: Rng;

  constructor(lang: string = 'en', profile: string = 'web', intensity: number = 60, seed: number = 0) {
    this.lang = lang;
    this.intensity = intensity;
    this.rng = new Rng(seed);
    void profile;
  }

  process(text: string, keep: string[] = []): string {
    const pack = getLangPack(this.lang);
    if (!pack) return text;
    const r = rewrite(text, pack, {
      intensity: this.intensity, rng: this.rng, connectors: false, phrases: true, words: true, keep, lang: this.lang,
    });
    this.changes.push(...r.changes);
    return r.text;
  }
}
