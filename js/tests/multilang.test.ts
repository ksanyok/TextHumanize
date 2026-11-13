/**
 * Publication-safety tests on real-world SEO articles in the six PromoPilot
 * languages (fixtures: benchmarks/seo_html/*.html).
 */

import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { humanize, humanizeHtml, detectAi, detectLanguage } from '../src/index';

const LANGS = ['ru', 'uk', 'en', 'pl', 'es', 'pt'] as const;
const fixture = (l: string) => readFileSync(resolve(__dirname, `../../benchmarks/seo_html/${l}.html`), 'utf8');
const links = (h: string) => [...h.matchAll(/<a\b[^>]*>[\s\S]*?<\/a>/g)].map(m => m[0]);
const tags = (h: string) => [...h.matchAll(/<\/?[a-z0-9]+/gi)].map(m => m[0]).join(',');
const visible = (h: string) => h.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ');
const ARTIFACTS = /,\s*[,.;:]|\s[,.;:](?!\d)|\.\.(?!\.)|[.!?]\s+,|\p{L}\s{2,}\p{L}/u;

describe.each(LANGS)('humanizeHtml on %s SEO article', lang => {
  const html = fixture(lang);
  const r = humanizeHtml(html, { lang, profile: 'seo', intensity: 55 });

  it('changes the text', () => {
    expect(r.html).not.toBe(html);
    expect(r.changes.filter(c => c.type !== 'typography').length).toBeGreaterThanOrEqual(5);
    expect(r.stats.changed).toBeGreaterThan(0);
    expect(r.stats.reverted).toBe(0);
  });

  it('keeps every link and anchor byte-identical', () => {
    expect(links(r.html)).toEqual(links(html));
  });

  it('keeps the tag structure', () => {
    expect(tags(r.html)).toBe(tags(html));
  });

  it('leaves no punctuation or spacing artefacts', () => {
    const text = visible(r.html).replace(/\s+([.!?])/g, '$1'); // tag gaps before final dots
    expect(text).not.toMatch(ARTIFACTS);
  });

  it('lowers the AI-style score', () => {
    expect(r.aiScoreBefore).toBeGreaterThanOrEqual(40);
    expect(r.aiScoreAfter).toBeLessThan(r.aiScoreBefore);
  });

  it('changes a bounded share of words', () => {
    const a = visible(html).toLowerCase().match(/\p{L}+/gu)!;
    const b = visible(r.html).toLowerCase().match(/\p{L}+/gu)!;
    const pool = new Map<string, number>();
    a.forEach(w => pool.set(w, (pool.get(w) ?? 0) + 1));
    let common = 0;
    b.forEach(w => { if ((pool.get(w) ?? 0) > 0) { common++; pool.set(w, pool.get(w)! - 1); } });
    expect(1 - (2 * common) / (a.length + b.length)).toBeLessThan(0.3);
  });

  it('is deterministic for the same input', () => {
    expect(humanizeHtml(html, { lang, profile: 'seo', intensity: 55 }).html).toBe(r.html);
  });

  it('detects the language', () => {
    expect(detectLanguage(visible(html))).toBe(lang);
  });
});

describe('HTML protection', () => {
  it('never touches link text, code or opted-out blocks', () => {
    const html = '<p>Furthermore, it is important to note that <a href="/x">it is important to note that</a> matters. Moreover, <code>utilize()</code> is robust.</p>'
      + '<p data-humanize="off">Furthermore, it is important to note that this stays.</p>';
    const r = humanizeHtml(html, { lang: 'en', intensity: 100, seed: 3 });
    expect(r.html).toContain('<a href="/x">it is important to note that</a>');
    expect(r.html).toContain('<code>utilize()</code>');
    expect(r.html).toContain('<p data-humanize="off">Furthermore, it is important to note that this stays.</p>');
  });

  it('keeps inline formatting and entities', () => {
    const html = '<p>Moreover, our <strong>comprehensive</strong> guide&nbsp;helps you navigate the complexities of SEO &amp; content.</p>';
    const r = humanizeHtml(html, { lang: 'en', intensity: 100, seed: 1 });
    expect(r.html).toContain('<strong>');
    expect(r.html).toContain('</strong>');
    expect(r.html).toContain('&nbsp;');
    expect(r.html).toContain('&amp;');
  });

  it('respects keepKeywords', () => {
    const html = '<p>In today\'s rapidly evolving digital landscape, it is important to note that link building matters. Furthermore, it is crucial.</p>';
    const r = humanizeHtml(html, { lang: 'en', intensity: 100, seed: 1, constraints: { keepKeywords: ['it is important to note that'] } });
    expect(r.html).toContain('it is important to note that');
  });

  it('humanize() routes HTML input through the HTML engine', () => {
    const html = fixture('ru');
    const r = humanize(html, { lang: 'ru', profile: 'seo', intensity: 55 });
    expect(links(r.text)).toEqual(links(html));
  });
});

describe('grammar guards', () => {
  const runMany = (html: string, lang: string) =>
    Array.from({ length: 25 }, (_, seed) => humanizeHtml(html, { lang, intensity: 100, seed: seed + 1 }).html);

  it('ru: light verbs keep their collocations', () => {
    for (const out of runMany('<p>Компания должна осуществлять контроль над позициями и осуществлять мониторинг результатов каждый день без исключений.</p>', 'ru')) {
      expect(out).not.toMatch(/делать (контроль|мониторинг)|контролировать над/);
    }
  });

  it('uk: no broken government after "здійснювати контроль над"', () => {
    for (const out of runMany('<p>Компанія повинна здійснювати контроль над позиціями та здійснювати моніторинг результатів щодня без винятків.</p>', 'uk')) {
      expect(out).not.toMatch(/контролювати над|робити (контроль|моніторинг)/);
    }
  });

  it('ru: bare copula is never replaced by a dash', () => {
    for (const out of runMany('<p>Продвижение является ключевым фактором успеха для любого бизнеса в нашей стране сегодня.</p>', 'ru')) {
      expect(out).not.toMatch(/—\s*ключевым/);
    }
  });

  it('pt: additive connectors stay additive', () => {
    for (const out of runMany('<p>O SEO ajuda muito. Além disso, este método garante o aumento da visibilidade orgânica nos buscadores.</p>', 'pt')) {
      expect(out).not.toMatch(/Por outro lado|No entanto|Contudo/);
    }
  });

  it('drops are never reported in the "a → b" form', () => {
    const r = humanizeHtml(fixture('en'), { lang: 'en', intensity: 100, seed: 7 });
    for (const c of r.changes) {
      if (c.replacement === '') expect(c.description).not.toContain(' → ');
    }
  });
});

describe('detector', () => {
  it('scores natural human prose low', () => {
    const human = 'I tried three tools last week. Two broke on the first import, honestly. The third one? Slow, but it worked, and my client was happy enough to pay on Friday.';
    expect(detectAi(human, 'en').score).toBeLessThan(35);
  });

  it('scores stock AI copy high in every language', () => {
    for (const lang of LANGS) {
      expect(detectAi(visible(fixture(lang)), lang).score).toBeGreaterThanOrEqual(40);
    }
  });
});

describe('pathological input (ReDoS guard)', () => {
  const cases: Record<string, string> = {
    spaces: ' '.repeat(50000) + 'x',
    unclosedTags: '<a'.repeat(30000),
    unclosedComments: '<!--'.repeat(20000),
    noTerminators: 'word '.repeat(40000),
    longToken: 'a'.repeat(50000),
  };
  for (const [name, input] of Object.entries(cases)) {
    it(`stays fast on ${name}`, () => {
      const t0 = Date.now();
      humanize(input, { lang: 'en' });
      humanizeHtml(input, { lang: 'en' });
      expect(Date.now() - t0).toBeLessThan(2000);
    });
  }
});
