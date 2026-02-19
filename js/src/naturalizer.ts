/**
 * Text naturalizer — makes AI-generated text stylistically closer to human writing.
 *
 * Key transformations:
 * 1. Burstiness — vary sentence lengths for natural rhythm
 * 2. AI word replacement — swap characteristic AI words
 * 3. Connector variation — reduce repetitive connectors
 */

import type { ChangeEntry, LangPack } from './types';
import { getLangPack } from './lang';

/**
 * Seeded PRNG (xoshiro128**)
 */
class Rng {
  private s: Uint32Array;

  constructor(seed: number = 0) {
    this.s = new Uint32Array(4);
    let z = (seed | 0) + 0x9e3779b9;
    for (let i = 0; i < 4; i++) {
      z ^= z >>> 16; z = Math.imul(z, 0x45d9f3b);
      z ^= z >>> 16; z = Math.imul(z, 0x45d9f3b);
      z ^= z >>> 16;
      this.s[i] = z >>> 0;
      z += 0x9e3779b9;
    }
  }

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

// AI-characteristic words → human replacements (by language)
const AI_WORD_REPLACEMENTS: Record<string, Record<string, string[]>> = {
  en: {
    'comprehensive': ['thorough', 'full', 'complete', 'detailed'],
    'significant': ['major', 'notable', 'important', 'big'],
    'utilize': ['use', 'work with', 'apply'],
    'facilitate': ['help', 'make easier', 'enable'],
    'demonstrate': ['show', 'prove', 'illustrate'],
    'implement': ['set up', 'put in place', 'apply'],
    'leverage': ['use', 'take advantage of'],
    'optimize': ['improve', 'tune', 'refine'],
    'streamline': ['simplify', 'speed up', 'smooth out'],
    'enhance': ['improve', 'boost', 'strengthen'],
    'robust': ['strong', 'reliable', 'solid'],
    'innovative': ['new', 'fresh', 'creative'],
    'crucial': ['vital', 'key', 'essential'],
    'fundamental': ['basic', 'core', 'key'],
    'paradigm': ['model', 'framework', 'approach'],
    'methodology': ['method', 'approach', 'way'],
    'furthermore': ['also', 'plus', 'what\'s more'],
    'additionally': ['also', 'on top of that'],
    'consequently': ['so', 'as a result'],
    'nevertheless': ['still', 'yet', 'even so'],
    'moreover': ['also', 'besides', 'on top of that'],
    'subsequently': ['then', 'later', 'after that'],
    'notwithstanding': ['despite', 'even though'],
    'aforementioned': ['this', 'that', 'the one mentioned'],
  },
  ru: {
    'осуществлять': ['делать', 'проводить', 'выполнять'],
    'являться': ['быть', 'выступать'],
    'обеспечивать': ['давать', 'создавать', 'помогать'],
    'данный': ['этот', 'текущий'],
    'соответствующий': ['нужный', 'подходящий'],
    'комплексный': ['сложный', 'многосторонний', 'полный'],
    'оптимизировать': ['улучшать', 'настраивать'],
    'имплементировать': ['внедрять', 'применять'],
    'функционировать': ['работать', 'действовать'],
    'представлять собой': ['быть'],
    'в рамках': ['в', 'при', 'внутри'],
    'на основании': ['по', 'из-за'],
    'вышеуказанный': ['этот', 'упомянутый'],
    'надлежащий': ['нужный', 'правильный'],
    'парадигма': ['подход', 'модель'],
    'методология': ['метод', 'подход'],
    'концепция': ['идея', 'замысел'],
    'систематизировать': ['упорядочивать', 'структурировать'],
    'детерминировать': ['определять'],
    'адаптировать': ['приспосабливать', 'подстраивать'],
  },
};

// AI connectors that should be varied or reduced
const AI_CONNECTORS: Record<string, string[]> = {
  en: [
    'However', 'Moreover', 'Furthermore', 'Additionally',
    'Consequently', 'Therefore', 'Nevertheless', 'In addition',
    'As a result', 'On the other hand', 'In conclusion',
    'Specifically', 'Notably', 'Importantly',
  ],
  ru: [
    'Однако', 'Кроме того', 'Более того', 'Тем не менее',
    'Следовательно', 'Поэтому', 'Таким образом', 'При этом',
    'Вместе с тем', 'Впрочем', 'В частности', 'Например',
  ],
};

export class TextNaturalizer {
  readonly changes: ChangeEntry[] = [];
  private lang: string;
  private intensity: number;
  private rng: Rng;
  private langPack: LangPack | undefined;

  constructor(
    lang: string = 'en',
    profile: string = 'web',
    intensity: number = 60,
    seed: number = 0,
  ) {
    this.lang = lang;
    this.intensity = intensity;
    this.rng = new Rng(seed);
    this.langPack = getLangPack(lang);
  }

  process(text: string): string {
    const prob = this.intensity / 100;
    if (prob < 0.05) return text;

    // 1. Replace AI-characteristic words
    text = this.replaceAiWords(text, prob);

    // 2. Inject burstiness (sentence length variation)
    text = this.injectBurstiness(text, prob);

    // 3. Vary connectors
    text = this.varyConnectors(text, prob);

    return text;
  }

  private replaceAiWords(text: string, prob: number): string {
    const replacements = AI_WORD_REPLACEMENTS[this.lang];
    if (!replacements) return text;

    let replaced = 0;
    const maxReplacements = Math.max(5, Math.floor(text.split(/\s+/).length / 20));

    for (const [word, candidates] of Object.entries(replacements)) {
      if (replaced >= maxReplacements) break;
      if (this.rng.random() > prob * 0.8) continue;

      const pattern = new RegExp(`\\b${escapeRegex(word)}\\b`, 'i');
      const match = text.match(pattern);

      if (!match || match.index === undefined) continue;

      const original = match[0];
      let replacement = this.rng.choice(candidates);

      // Preserve case
      if (original === original.toUpperCase()) {
        replacement = replacement.toUpperCase();
      } else if (original[0] === original[0].toUpperCase()) {
        replacement = replacement[0].toUpperCase() + replacement.slice(1);
      }

      text = text.slice(0, match.index) + replacement + text.slice(match.index + original.length);
      replaced++;

      this.changes.push({
        type: 'naturalize_word',
        description: `${original} → ${replacement}`,
      });
    }

    return text;
  }

  private injectBurstiness(text: string, prob: number): string {
    const sentences = splitSentences(text);
    if (sentences.length < 5) return text;

    const lengths = sentences.map(s => s.split(/\s+/).length);
    const avg = lengths.reduce((a, b) => a + b, 0) / lengths.length;

    // Check variance — if already varied, skip
    const variance = lengths.reduce((sum, l) => sum + (l - avg) ** 2, 0) / lengths.length;
    if (variance > 25) return text; // Already bursty

    const modified = [...sentences];
    let changed = false;

    for (let i = 0; i < sentences.length; i++) {
      if (this.rng.random() > prob * 0.5) continue;

      const words = sentences[i].split(/\s+/);

      // Split long sentences (> avg * 1.3)
      if (words.length > avg * 1.3 && words.length > 15) {
        const splitPoint = this.findSplitPoint(words);
        if (splitPoint > 3 && splitPoint < words.length - 3) {
          const first = words.slice(0, splitPoint).join(' ');
          const second = words.slice(splitPoint).join(' ');
          // Capitalize second part
          const secondCapitalized = second[0].toUpperCase() + second.slice(1);
          modified[i] = first + '. ' + secondCapitalized;
          changed = true;
          this.changes.push({
            type: 'burstiness',
            description: `Split long sentence at position ${i}`,
          });
        }
      }
    }

    return changed ? modified.join(' ') : text;
  }

  private findSplitPoint(words: string[]): number {
    // Look for natural split points: after conjunctions, commas
    const splitMarkers = [',', 'and', 'but', 'or', 'which', 'that', 'while', 'although',
      'и', 'но', 'или', 'который', 'которая', 'которое', 'хотя', 'пока'];

    const mid = Math.floor(words.length / 2);
    let bestIdx = -1;
    let bestDist = Infinity;

    for (let i = 3; i < words.length - 3; i++) {
      const w = words[i].replace(/[.,;:]/g, '').toLowerCase();
      const endsWithComma = words[i].endsWith(',');

      if (splitMarkers.includes(w) || endsWithComma) {
        const dist = Math.abs(i - mid);
        if (dist < bestDist) {
          bestDist = dist;
          bestIdx = endsWithComma ? i + 1 : i;
        }
      }
    }

    return bestIdx > 0 ? bestIdx : mid;
  }

  private varyConnectors(text: string, prob: number): string {
    const connectors = AI_CONNECTORS[this.lang];
    if (!connectors) return text;

    // Count connector usage
    const counts: Map<string, number> = new Map();
    for (const conn of connectors) {
      const pattern = new RegExp(`\\b${escapeRegex(conn)}\\b`, 'gi');
      const matches = text.match(pattern);
      if (matches) counts.set(conn, matches.length);
    }

    // If any connector appears 3+ times, replace some occurrences
    for (const [conn, count] of counts) {
      if (count < 3) continue;
      if (this.rng.random() > prob) continue;

      const alternatives = this.langPack?.fillers || [];
      if (alternatives.length === 0) continue;

      // Replace second occurrence onwards
      let seen = 0;
      const pattern = new RegExp(`\\b${escapeRegex(conn)}\\b`, 'gi');
      text = text.replace(pattern, (match) => {
        seen++;
        if (seen > 1 && this.rng.random() > 0.5) {
          this.changes.push({
            type: 'connector_variation',
            description: `Varied connector: ${match}`,
          });
          return '';  // Remove extra connector
        }
        return match;
      });
    }

    return text;
  }
}

function splitSentences(text: string): string[] {
  return text
    .split(/(?<=[.!?…])\s+/)
    .map(s => s.trim())
    .filter(s => s.length > 0 && s.split(/\s+/).length > 1);
}

function escapeRegex(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}
