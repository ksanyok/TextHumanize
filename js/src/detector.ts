/**
 * Lightweight AI-style detector for the TS port.
 *
 * Scores the stylistic fingerprints that LLM copy leaves and that editors
 * remove: AI cliches and officialese density, sentences opened by stock
 * connectors ("Moreover,", "Кроме того,"), uniform sentence length (low
 * burstiness) and long average sentences. Dictionaries come from the same
 * language packs the humanizer uses, so it works for every supported
 * language. It is a heuristic — use the Python detector for forensic work.
 */

import { getLangPack } from './lang';
import { dictMatcher, isSentenceStart } from './engine';

export interface DetectorFeatures {
  words: number;
  sentences: number;
  avgSentenceLength: number;
  sentenceLengthCV: number;
  clichePer100: number;
  officialesePer100: number;
  connectorStartShare: number;
}

export function splitSentences(text: string): string[] {
  return text
    .split(/(?<=[.!?…])\s+|\n+/u)
    .map(s => s.trim())
    .filter(s => (s.match(/[\p{L}\p{N}]+/gu) || []).length > 1);
}

function count(re: RegExp | null, text: string): number {
  if (!re) return 0;
  re.lastIndex = 0;
  return (text.match(re) || []).length;
}

export function features(text: string, lang: string): DetectorFeatures {
  const words = (text.match(/[\p{L}\p{N}]+/gu) || []).length;
  const sentences = splitSentences(text);
  const lens = sentences.map(s => (s.match(/[\p{L}\p{N}]+/gu) || []).length);
  const avg = lens.length ? lens.reduce((a, b) => a + b, 0) / lens.length : 0;
  const sd = lens.length ? Math.sqrt(lens.reduce((s, l) => s + (l - avg) ** 2, 0) / lens.length) : 0;
  const pack = getLangPack(lang);
  let cliches = 0, officialese = 0, connStarts = 0;
  if (pack) {
    cliches = count(dictMatcher(pack.phrases), text);
    officialese = count(dictMatcher(pack.bureaucratic), text);
    const re = dictMatcher(pack.connectorMap);
    if (re) {
      re.lastIndex = 0;
      for (const m of text.matchAll(re)) if (isSentenceStart(text, m.index!)) connStarts++;
    }
  }
  return {
    words,
    sentences: sentences.length,
    avgSentenceLength: avg,
    sentenceLengthCV: avg > 0 ? sd / avg : 0,
    clichePer100: words ? (cliches / words) * 100 : 0,
    officialesePer100: words ? (officialese / words) * 100 : 0,
    connectorStartShare: sentences.length ? connStarts / sentences.length : 0,
  };
}

/** 0–100 AI-style score. */
export function aiScore(text: string, lang: string): number {
  const f = features(text, lang);
  if (f.words < 8) return 0;
  let s = 0;
  s += Math.min(40, (f.clichePer100 + 0.5 * f.officialesePer100) * 9);
  s += Math.min(25, f.connectorStartShare * 70);
  if (f.sentences >= 3) {
    s += f.sentenceLengthCV < 0.25 ? 20 : f.sentenceLengthCV < 0.35 ? 14 : f.sentenceLengthCV < 0.45 ? 7 : 0;
  }
  s += f.avgSentenceLength > 22 ? 15 : f.avgSentenceLength > 17 ? 8 : 0;
  // Short snippets carry little evidence.
  const conf = Math.min(1, f.words / 40);
  return Math.max(0, Math.min(100, Math.round(s * conf)));
}
