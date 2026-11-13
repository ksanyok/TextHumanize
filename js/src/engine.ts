/**
 * Edit engine — publication-safe rewriting shared by every stage.
 *
 * All candidate edits (AI cliches, officialese, sentence-initial connectors)
 * are collected against the *original* string first, de-overlapped, ranked
 * by priority and budgeted, and only then applied in a single pass. This
 * keeps edits from cascading into each other and makes the change log exact
 * (every entry carries `original` and `replacement`).
 *
 * Private-use characters (U+E000–U+F8FF) are treated as opaque boundaries so
 * callers (see ./html.ts) can embed placeholders for tags and links.
 */

import type { ChangeEntry, LangPack } from './types';

/** Seeded PRNG (xoshiro128**). */
export class Rng {
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
    const result = Math.imul(Math.imul(s[1], 5) << 7 | Math.imul(s[1], 5) >>> 25, 9) >>> 0;
    const t = s[1] << 9;
    s[2] ^= s[0]; s[3] ^= s[1]; s[1] ^= s[2]; s[0] ^= s[3];
    s[2] ^= t;
    s[3] = (s[3] << 11 | s[3] >>> 21) >>> 0;
    return result / 0x100000000;
  }

  choice<T>(arr: T[]): T {
    return arr[Math.floor(this.random() * arr.length)];
  }
}

/** FNV-1a hash → default seed, so equal texts get equal output but different texts vary. */
export function hashSeed(text: string): number {
  let h = 0x811c9dc5;
  for (let i = 0; i < text.length; i++) {
    h ^= text.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return h >>> 0;
}

// Word characters for boundary checks. Hyphen/apostrophe count as word-internal
// so "e-commerce" never matches "commerce".
const WORD = "\\p{L}\\p{N}\\p{M}_'’\\-";
const LEAD_WORD = new RegExp(`[${WORD}]`, 'u');

export function escapeRegex(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

const matcherCache = new WeakMap<object, RegExp | null>();

/** One alternation regex per dictionary (longest key first), cached. */
export function dictMatcher(dict: Record<string, unknown>): RegExp | null {
  if (matcherCache.has(dict)) return matcherCache.get(dict)!;
  const keys = Object.keys(dict).filter(k => k.trim().length > 0);
  if (keys.length === 0) {
    matcherCache.set(dict, null);
    return null;
  }
  keys.sort((a, b) => b.length - a.length);
  const body = keys.map(k => escapeRegex(k.trim()).replace(/\s+/g, '\\s+')).join('|');
  const re = new RegExp(`(?<![${WORD}])(?:${body})(?![${WORD}])`, 'giu');
  matcherCache.set(dict, re);
  return re;
}

const lowerCache = new WeakMap<object, Map<string, string[]>>();

/** Case-insensitive lookup table for a dictionary. */
export function lowerIndex(dict: Record<string, string[]>): Map<string, string[]> {
  let m = lowerCache.get(dict);
  if (!m) {
    m = new Map();
    for (const [k, v] of Object.entries(dict)) m.set(normKey(k), v);
    lowerCache.set(dict, m);
  }
  return m;
}

export function normKey(s: string): string {
  return s.toLowerCase().replace(/\s+/g, ' ').trim();
}

const PLACEHOLDER = /[-]/u;
const OPENERS = /["'«“„‘(\[¿¡]/u;

/** True when `idx` begins a sentence (start, after .!?… / newline; tags and opening quotes ignored). */
export function isSentenceStart(text: string, idx: number): boolean {
  let i = idx - 1;
  while (i >= 0) {
    const ch = text[i];
    if (ch === '\n') return true;
    if (/\s/.test(ch) || PLACEHOLDER.test(ch) || OPENERS.test(ch)) { i--; continue; }
    return /[.!?…]/.test(ch);
  }
  return true;
}

function capitalizeFirst(s: string): string {
  const m = s.match(/\p{L}/u);
  if (!m || m.index === undefined) return s;
  return s.slice(0, m.index) + m[0].toUpperCase() + s.slice(m.index + 1);
}

function isUpperInitial(s: string): boolean {
  const m = s.match(/\p{L}/u);
  return !!m && m[0] !== m[0].toLowerCase();
}

function isAllCaps(s: string): boolean {
  const letters = s.replace(/[^\p{L}]/gu, '');
  return letters.length > 1 && letters === letters.toUpperCase() && letters !== letters.toLowerCase();
}

/** Coordinating conjunctions that never take a comma when opening a sentence. */
const BARE_CONJ = new Set([
  'and', 'but', 'yet', 'и', 'но', 'а', 'да', 'і', 'але', 'та', 'ale', 'i', 'a', 'y', 'pero',
  'e', 'mas', 'und', 'aber', 'et', 'mais', 'ma', 'і ще', 'и ещё', 'and also',
  // adverbs that take no comma at sentence start ("Также X", not "Также, X")
  'также', 'ещё', 'еще', 'плюс', 'тоже', 'також', 'ще', 'теж', 'także', 'również', 'też',
  'también', 'também', 'auch', 'aussi', 'anche',
]);

export interface EngineOptions {
  intensity: number;
  rng: Rng;
  /** Enable sentence-initial connector edits. */
  connectors?: boolean;
  /** Enable officialese single-word edits. */
  words?: boolean;
  /** Enable AI-cliche / officialese phrase edits. */
  phrases?: boolean;
  /** Allow splitting one over-long sentence at a safe joint. */
  split?: boolean;
  /** Terms that must survive verbatim (brand names, keywords). */
  keep?: string[];
  /** Language code (typography differences, e.g. French spacing). */
  lang?: string;
}

interface Candidate {
  start: number;
  end: number;
  original: string;
  options: string[];
  type: 'phrase' | 'connector' | 'word';
  priority: number;
  prob: number;
}

/** Run the edit engine on plain text (may contain private-use placeholders). */
export function rewrite(text: string, pack: LangPack, opts: EngineOptions): { text: string; changes: ChangeEntry[] } {
  const changes: ChangeEntry[] = [];
  const intensity = Math.max(0, Math.min(100, opts.intensity));
  if (!text.trim() || intensity < 5) return { text, changes };
  const rng = opts.rng;
  const p = intensity / 100;

  const protectedRanges = findProtected(text, opts.keep ?? []);
  const candidates: Candidate[] = [];

  if (opts.phrases !== false) {
    collect(text, pack.phrases, 'phrase', 3, Math.min(1, 0.35 + p), candidates);
  }
  if (opts.connectors !== false) {
    const re = dictMatcher(pack.connectorMap);
    const idx = lowerIndex(pack.connectorMap);
    if (re) {
      re.lastIndex = 0;
      for (const m of text.matchAll(re)) {
        const start = m.index!;
        if (!isSentenceStart(text, start)) continue;
        const opts2 = idx.get(normKey(m[0]));
        if (!opts2) continue;
        candidates.push({ start, end: start + m[0].length, original: m[0], options: opts2, type: 'connector', priority: 2, prob: Math.min(1, 0.3 + p) });
      }
    }
  }
  if (opts.words !== false) {
    collect(text, pack.bureaucratic, 'word', 1, p * 0.9, candidates);
  }

  // Budget: ~3 + 15×intensity edits per 100 words.
  const wordCount = (text.match(/[\p{L}\p{N}]+/gu) || []).length;
  const budget = Math.max(1, Math.round(wordCount * (0.03 + p * 0.15)));

  candidates.sort((a, b) => b.priority - a.priority || (b.end - b.start) - (a.end - a.start) || a.start - b.start);
  const accepted: Candidate[] = [];
  for (const c of candidates) {
    if (accepted.length >= budget) break;
    if (overlaps(c, protectedRanges) || overlaps(c, accepted)) continue;
    if (rng.random() > c.prob) continue;
    accepted.push(c);
  }
  if (accepted.length === 0 && !opts.split) return { text, changes };

  // "Moreover, it is worth noting that X": rewriting both reads worse than
  // simply dropping the connector, so force a drop in that case.
  const forceDrop = new Set<Candidate>();
  for (const c of accepted) {
    if (c.type !== 'connector') continue;
    if (accepted.some(o => o !== c && o.start >= c.end && /^[\s,:]*$/u.test(text.slice(c.end, o.start)))) forceDrop.add(c);
  }

  // Apply right-to-left so offsets stay valid.
  accepted.sort((a, b) => b.start - a.start);
  const used = new Map<string, number>();
  let out = text;
  for (const c of accepted) {
    const atStart = isSentenceStart(out, c.start);
    // Never empty an inline element: no drops right next to a placeholder.
    const nextToTag = PLACEHOLDER.test(out[c.start - 1] ?? '') || PLACEHOLDER.test(out.slice(c.end).replace(/^[\s,:]*/u, '')[0] ?? '');
    // Contrast ("However", "Однако", "No entanto") carries meaning: replace, never drop.
    const keepMeaning = pack.contrast.has(normKey(c.original));
    const noDrop = nextToTag || keepMeaning;
    let repl = forceDrop.has(c) && !noDrop ? '' : pickReplacement(c, atStart, used, rng, noDrop);
    if (repl === null) continue;
    let start = c.start;
    let end = c.end;

    if (repl === '') {
      // Drop the fragment together with a trailing comma/colon and whitespace.
      const tail = out.slice(end).match(/^\s*[,:]?\s*/u)![0];
      end += tail.length;
      if (!atStart) {
        // keep exactly one separating space mid-sentence
        const prevSpace = /\s$/u.test(out.slice(0, start));
        if (!prevSpace) repl = ' ';
      }
      const after = out.slice(end);
      const nextIsLetter = /^\p{L}/u.test(after);
      out = out.slice(0, start) + repl + (atStart && nextIsLetter ? capitalizeFirst(after) : after);
    } else {
      if (isAllCaps(c.original)) repl = repl.toUpperCase();
      else if (atStart || isUpperInitial(c.original)) repl = capitalizeFirst(repl);
      // Avoid ",," / ":," when the replacement already ends with punctuation.
      if (/[,:]$/.test(repl) && /^\s*[,:]/.test(out.slice(end))) {
        end += out.slice(end).match(/^\s*[,:]/)![0].length;
      }
      // "Moreover, X" → "But X", not "But, X": bare conjunctions take no comma.
      if (atStart && BARE_CONJ.has(normKey(repl)) && /^,/.test(out.slice(end))) {
        end += 1;
      }
      out = out.slice(0, start) + repl + out.slice(end);
    }
    used.set(normKey(repl), (used.get(normKey(repl)) ?? 0) + 1);
    changes.push({
      type: c.type === 'connector' ? 'connector' : c.type === 'phrase' ? 'phrase' : 'decancel_word',
      // Drops are not written as "a → b" so legacy consumers that replay
      // descriptions never paste an empty string into the text.
      description: repl.trim() ? `${c.original} → ${repl.trim()}` : `Dropped "${c.original}"`,
      original: c.original,
      replacement: repl.trim(),
    });
  }
  changes.reverse();

  if (opts.split && rng.random() < p * 0.6) {
    const split = splitLongSentence(out, pack);
    if (split) {
      out = split.text;
      changes.push({ type: 'split', description: split.description });
    }
  }

  out = tidy(out, opts.lang ?? pack.code);
  return { text: out, changes };
}

function collect(text: string, dict: Record<string, string[]>, type: Candidate['type'], priority: number, prob: number, out: Candidate[]): void {
  const re = dictMatcher(dict);
  if (!re) return;
  const idx = lowerIndex(dict);
  re.lastIndex = 0;
  for (const m of text.matchAll(re)) {
    const options = idx.get(normKey(m[0]));
    if (!options || options.length === 0) continue;
    out.push({ start: m.index!, end: m.index! + m[0].length, original: m[0], options, type, priority, prob });
  }
}

function findProtected(text: string, keep: string[]): Array<{ start: number; end: number }> {
  const ranges: Array<{ start: number; end: number }> = [];
  for (const term of keep) {
    if (!term || !term.trim()) continue;
    const re = new RegExp(escapeRegex(term.trim()), 'giu');
    for (const m of text.matchAll(re)) ranges.push({ start: m.index!, end: m.index! + m[0].length });
  }
  return ranges;
}

function overlaps(c: { start: number; end: number }, list: Array<{ start: number; end: number }>): boolean {
  for (const r of list) if (c.start < r.end && r.start < c.end) return true;
  return false;
}

function pickReplacement(c: Candidate, atStart: boolean, used: Map<string, number>, rng: Rng, noDrop = false): string | null {
  let opts = c.options.slice();
  if (noDrop) opts = opts.filter(o => o !== '');
  if (atStart) {
    // A sentence cannot start with a dash or punctuation-led fragment.
    opts = opts.filter(o => o === '' || LEAD_WORD.test(o[0]));
  }
  if (c.type === 'connector') {
    // Drop "Moreover," entirely ~1/3 of the time when a comma follows.
    if (!noDrop && rng.random() < 0.33) return '';
  }
  if (opts.length === 0) return null;
  // Mid-sentence, "— это" beats bare "это" (ru/uk copula needs the dash).
  if (!atStart) {
    const dashed = opts.filter(o => /^[—–]\s/.test(o));
    if (dashed.length && opts.some(o => dashed.includes('— ' + o) || dashed.includes('– ' + o))) opts = dashed;
  }
  // Prefer replacements not used yet in this text (avoid "use … use … use").
  const fresh = opts.filter(o => !used.has(normKey(o)));
  const pool = fresh.length > 0 ? fresh : opts;
  return rng.choice(pool);
}

/**
 * Split the longest over-long sentence at a coordinating joint near its
 * middle: "X, and Y" → "X. And Y". Both halves must keep ≥ 8 words.
 */
function splitLongSentence(text: string, pack: LangPack): { text: string; description: string } | null {
  // Anchored to sentence starts so a long text without terminators stays linear.
  const sentRe = /(?:^|(?<=[.!?…]))[^.!?…]+[.!?…]+/gu;
  let best: { start: number; end: number; words: number } | null = null;
  for (const m of text.matchAll(sentRe)) {
    const words = (m[0].match(/[\p{L}\p{N}]+/gu) || []).length;
    if (words >= 28 && (!best || words > best.words)) best = { start: m.index!, end: m.index! + m[0].length, words };
  }
  if (!best) return null;
  const sentence = text.slice(best.start, best.end);
  const mid = sentence.length / 2;
  let pick: { at: number; joint: string } | null = null;
  for (const joint of pack.splitJoints) {
    let from = 0;
    for (;;) {
      const at = sentence.indexOf(joint, from);
      if (at < 0) break;
      from = at + 1;
      const left = (sentence.slice(0, at).match(/[\p{L}\p{N}]+/gu) || []).length;
      const right = (sentence.slice(at + joint.length).match(/[\p{L}\p{N}]+/gu) || []).length;
      if (left < 8 || right < 8) continue;
      if (!pick || Math.abs(at - mid) < Math.abs(pick.at - mid)) pick = { at, joint };
    }
  }
  if (!pick) return null;
  const conj = pick.joint.replace(/^[,;]\s*/, '').trim();
  const rest = sentence.slice(pick.at + pick.joint.length);
  const glued = conj ? `${capitalizeFirst(conj)} ${rest}` : capitalizeFirst(rest);
  const newSentence = sentence.slice(0, pick.at).replace(/\s+$/, '') + '. ' + glued;
  return {
    text: text.slice(0, best.start) + newSentence + text.slice(best.end),
    description: `Split long sentence at "${pick.joint.trim()}"`,
  };
}

/** Repair spacing/punctuation artefacts that edits can leave behind. */
export function tidy(text: string, lang: string): string {
  let t = text;
  t = t.replace(/[ \t]{2,}/g, ' ');
  if (lang !== 'fr') t = t.replace(/(?<! ) +(?=[,.;:!?…])/g, '');
  else t = t.replace(/(?<! ) +(?=[,.…])/g, '');
  t = t.replace(/,\s*([,.;:!?])/g, '$1');
  t = t.replace(/([.!?])\s+,/g, '$1');
  return t;
}
