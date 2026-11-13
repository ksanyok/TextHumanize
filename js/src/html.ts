/**
 * HTML-aware humanization.
 *
 * The document is tokenised into tags and text. Text is grouped into blocks
 * (p, li, h1–h6, td, blockquote, …); inside a block every inline tag, HTML
 * entity and protected element (<a>…</a>, <code>, <pre>, <script>, …) is
 * replaced by a single private-use placeholder character, so sentences can
 * span <strong>/<em> while links, anchors and attributes stay byte-identical.
 * After rewriting, a block is accepted only if all its placeholders come back
 * in the same order — otherwise the block is reverted untouched.
 */

import type { ChangeEntry, HumanizeHtmlOptions, HumanizeHtmlResult } from './types';
import { getLangPack, normalizeLang } from './lang';
import { Rng, hashSeed, rewrite } from './engine';
import { TypographyNormalizer } from './normalizer';
import { aiScore } from './detector';
import { Pipeline } from './pipeline';
import { detectLanguage } from './langdetect';

const BLOCK = new Set([
  'p', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'td', 'th', 'blockquote', 'div', 'section',
  'article', 'header', 'footer', 'main', 'aside', 'nav', 'dd', 'dt', 'dl', 'figcaption', 'caption',
  'summary', 'details', 'ul', 'ol', 'table', 'thead', 'tbody', 'tfoot', 'tr', 'figure', 'form',
  'fieldset', 'address', 'body', 'html', 'hr',
]);
/** Elements whose whole content is copied verbatim. */
const PROTECTED = new Set([
  'a', 'code', 'pre', 'script', 'style', 'kbd', 'samp', 'var', 'textarea', 'svg', 'math', 'button',
  'select', 'option', 'noscript', 'template', 'iframe', 'object', 'title', 'head', 'tt',
]);
const VOID = new Set(['br', 'img', 'hr', 'input', 'meta', 'link', 'source', 'wbr', 'area', 'col', 'embed', 'param', 'track']);
const HEADINGS = new Set(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']);
const LISTISH = new Set(['li', 'td', 'th', 'dt', 'dd', 'caption', 'figcaption', 'summary']);
const SPLITTABLE = new Set(['p', 'div', 'blockquote', 'section', 'article', 'main', 'body', '']);

const TOKEN_RE = /<!--[\s\S]*?-->|<![^>]*>|<\/?[a-zA-Z][^>]*>/g;
const ENTITY_RE = /&(?:[a-zA-Z][a-zA-Z0-9]{1,31}|#\d{1,7}|#[xX][0-9a-fA-F]{1,6});/g;
const PH_BASE = 0xE000;
const PH_MAX = 0xF8FF - PH_BASE;
const PH_RE = /[-]/gu;
const PROTECT_RE = /\b(?:https?:\/\/|www\.)[^\s<>"']+|[\w.+-]+@[\w-]+\.[\w.-]+|(?<![\p{L}\p{N}])[@#][\p{L}\p{N}_]+/gu;

interface Part { kind: 'text' | 'atom'; raw: string; visible: string }

function tagName(tag: string): string {
  const m = tag.match(/^<\/?\s*([a-zA-Z][a-zA-Z0-9-]*)/);
  return m ? m[1].toLowerCase() : '';
}
function isClosing(tag: string): boolean { return /^<\//.test(tag); }
function isSelfClosing(tag: string): boolean { return /\/>$/.test(tag); }
function optedOut(tag: string): boolean {
  return /\sdata-humanize\s*=\s*["']?(?:off|false|0)/i.test(tag)
    || /\stranslate\s*=\s*["']?no/i.test(tag)
    || /\sclass\s*=\s*["'][^"']*\bnotranslate\b/i.test(tag);
}
function stripTags(s: string): string {
  return s.replace(/<[^>]*>/g, ' ').replace(ENTITY_RE, ' ');
}

/** Humanize an HTML fragment or document while keeping markup intact. */
export function humanizeHtml(html: string, options: HumanizeHtmlOptions = {}): HumanizeHtmlResult {
  const lang = normalizeLang(options.lang && options.lang !== 'auto' ? options.lang : detectFromHtml(html));
  const stats = { blocks: 0, changed: 0, reverted: 0, skipped: 0 };
  const changes: ChangeEntry[] = [];
  const pack = getLangPack(lang);
  const wantScore = options.score !== false;

  // ---- tokenise into a flat list of segments -------------------------------
  const segments: Array<{ tag?: string; text?: string }> = [];
  let last = 0;
  for (const m of html.matchAll(TOKEN_RE)) {
    if (m.index! > last) segments.push({ text: html.slice(last, m.index!) });
    segments.push({ tag: m[0] });
    last = m.index! + m[0].length;
  }
  if (last < html.length) segments.push({ text: html.slice(last) });

  // ---- group into blocks ----------------------------------------------------
  type Block = { tag: string; parts: Part[] };
  const units: Array<string | Block> = [];
  const blockStack: string[] = [];
  let cur: Block = { tag: '', parts: [] };
  const flush = () => {
    if (cur.parts.length) units.push(cur);
    cur = { tag: blockStack[blockStack.length - 1] ?? '', parts: [] };
  };

  for (let i = 0; i < segments.length; i++) {
    const seg = segments[i];
    if (seg.text !== undefined) {
      pushText(cur.parts, seg.text);
      continue;
    }
    const tag = seg.tag!;
    const name = tagName(tag);
    if (!name) { cur.parts.push({ kind: 'atom', raw: tag, visible: '' }); continue; }

    const closing = isClosing(tag);
    const opensProtected = !closing && !VOID.has(name) && !isSelfClosing(tag) && (PROTECTED.has(name) || optedOut(tag));
    if (opensProtected) {
      // Swallow everything up to the matching close tag as one atom.
      let depth = 1;
      let raw = tag;
      let j = i + 1;
      for (; j < segments.length && depth > 0; j++) {
        const s = segments[j];
        if (s.tag !== undefined) {
          const n = tagName(s.tag);
          if (n === name && !VOID.has(n) && !isSelfClosing(s.tag)) depth += isClosing(s.tag) ? -1 : 1;
          raw += s.tag;
        } else {
          raw += s.text;
        }
      }
      i = j - 1;
      if (BLOCK.has(name)) {
        flush();
        units.push(raw);
      } else {
        cur.parts.push({ kind: 'atom', raw, visible: stripTags(raw) });
      }
      continue;
    }

    if (BLOCK.has(name)) {
      flush();
      units.push(tag);
      if (!VOID.has(name) && !isSelfClosing(tag)) {
        if (closing) {
          const at = blockStack.lastIndexOf(name);
          if (at >= 0) blockStack.length = at;
        } else {
          blockStack.push(name);
        }
      }
      cur.tag = blockStack[blockStack.length - 1] ?? '';
      continue;
    }
    cur.parts.push({ kind: 'atom', raw: tag, visible: name === 'br' ? ' ' : '' });
  }
  flush();

  // ---- score & intensity ----------------------------------------------------
  const blocks = units.filter((u): u is Block => typeof u !== 'string');
  const visibleOf = (b: Block) => b.parts.map(p => p.visible).join('');
  const docBefore = blocks.map(visibleOf).join('\n');
  const aiScoreBefore = wantScore || options.intensity === undefined ? aiScore(docBefore, lang) : -1;
  const baseIntensity = options.intensity ?? 60;
  const effective = aiScoreBefore >= 0 ? Pipeline.adaptIntensity(baseIntensity, aiScoreBefore) : baseIntensity;
  if (effective !== baseIntensity) {
    changes.push({ type: 'adaptive_intensity', description: `Adapted intensity: AI=${aiScoreBefore}%, ${baseIntensity}→${effective}` });
  }

  const rng = new Rng(options.seed || hashSeed(html));
  const keepBase = [...(options.preserve?.brandTerms ?? []), ...(options.constraints?.keepKeywords ?? [])];
  const headingFactor = options.headingFactor ?? 0.45;
  const listFactor = options.listFactor ?? 0.75;
  const maxLinkShare = options.maxLinkShare ?? 0.6;
  const noSplitProfile = options.profile === 'formal' || options.profile === 'academic' || options.profile === 'docs';

  // ---- rewrite block by block -----------------------------------------------
  const out: string[] = [];
  const afterVisible: string[] = [];
  for (const u of units) {
    if (typeof u === 'string') { out.push(u); continue; }
    const original = u.parts.map(p => p.raw).join('');
    const visible = visibleOf(u);
    const words = (visible.match(/[\p{L}\p{N}]+/gu) || []).length;
    if (words === 0) { out.push(original); afterVisible.push(visible); continue; }
    stats.blocks++;

    const linkChars = u.parts.filter(p => p.kind === 'atom' && /^<a\b/i.test(p.raw)).reduce((s, p) => s + p.visible.trim().length, 0);
    const visChars = visible.trim().length || 1;
    const atoms = u.parts.filter(p => p.kind === 'atom').length;
    if (!pack || effective === 0 || words < 4 || linkChars / visChars > maxLinkShare || atoms > PH_MAX) {
      stats.skipped++;
      out.push(original);
      afterVisible.push(visible);
      continue;
    }

    // Encode atoms as placeholders.
    const atomList: Part[] = [];
    let encoded = '';
    for (const p of u.parts) {
      if (p.kind === 'text') encoded += p.raw;
      else { encoded += String.fromCharCode(PH_BASE + atomList.length); atomList.push(p); }
    }

    const factor = HEADINGS.has(u.tag) ? headingFactor : LISTISH.has(u.tag) ? listFactor : 1;
    const keep = [...keepBase];
    for (const m of encoded.matchAll(PROTECT_RE)) keep.push(m[0]);

    const norm = new TypographyNormalizer(options.profile ?? 'web', lang);
    let text = norm.normalize(encoded);
    const r = rewrite(text, pack, {
      intensity: Math.round(effective * factor),
      rng,
      keep,
      lang,
      split: !noSplitProfile && SPLITTABLE.has(u.tag),
    });
    text = r.text;

    const phBefore = encoded.match(PH_RE)?.join('') ?? '';
    const phAfter = text.match(PH_RE)?.join('') ?? '';
    if (phBefore !== phAfter || !text.trim()) {
      stats.reverted++;
      out.push(original);
      afterVisible.push(visible);
      continue;
    }
    if (text === encoded) { out.push(original); afterVisible.push(visible); continue; }

    stats.changed++;
    const restored = text.replace(PH_RE, ch => atomList[ch.charCodeAt(0) - PH_BASE].raw);
    out.push(restored);
    afterVisible.push(text.replace(PH_RE, ch => atomList[ch.charCodeAt(0) - PH_BASE].visible));
    for (const c of [...norm.changes, ...r.changes]) changes.push({ ...c, block: u.tag || 'text' });
  }

  const result = out.join('');
  const aiScoreAfter = wantScore ? aiScore(afterVisible.join('\n'), lang) : -1;
  return { html: result, lang, changes, stats, aiScoreBefore: wantScore ? aiScoreBefore : -1, aiScoreAfter };
}

function pushText(parts: Part[], text: string): void {
  let last = 0;
  for (const m of text.matchAll(ENTITY_RE)) {
    if (m.index! > last) parts.push({ kind: 'text', raw: text.slice(last, m.index!), visible: text.slice(last, m.index!) });
    const ent = m[0];
    const vis = /^&nbsp;$|^&#160;$|^&#xa0;$/i.test(ent) ? ' ' : ent === '&amp;' ? '&' : '';
    parts.push({ kind: 'atom', raw: ent, visible: vis });
    last = m.index! + ent.length;
  }
  if (last < text.length) parts.push({ kind: 'text', raw: text.slice(last), visible: text.slice(last) });
}

function detectFromHtml(html: string): string {
  return detectLanguage(stripTags(html));
}
