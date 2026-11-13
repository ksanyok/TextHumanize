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
// Visible text without regex tag stripping (CodeQL: incomplete multi-character
// sanitization): a single pass that drops everything between '<' and '>'.
const textOf = (h: string, gap = '') => {
  let out = '';
  let inTag = false;
  for (const ch of h) {
    if (ch === '<') { inTag = true; out += gap; continue; }
    if (ch === '>' && inTag) { inTag = false; continue; }
    if (!inTag) out += ch;
  }
  return out;
};
const visible = (h: string) => textOf(h, ' ').replace(/\s+/g, ' ');
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

describe('0.36.1: headings and connector punctuation', () => {
  const headings = (h: string) => [...h.matchAll(/<h[1-6][^>]*>[\s\S]*?<\/h[1-6]>/g)].map(m => m[0]);

  it.each(LANGS)('leaves headings untouched by default (%s)', lang => {
    const html = fixture(lang);
    for (let seed = 1; seed <= 10; seed++) {
      expect(headings(humanizeHtml(html, { lang, intensity: 100, seed }).html)).toEqual(headings(html));
    }
  });

  it('still rewrites headings when headingFactor is set', () => {
    const html = '<h2>Furthermore, it is important to note that SEO matters a lot today</h2>';
    const outs = Array.from({ length: 10 }, (_, i) => humanizeHtml(html, { lang: 'en', intensity: 100, seed: i + 1, headingFactor: 1 }).html);
    expect(outs.some(o => o !== html)).toBe(true);
  });

  it.each(LANGS)('no comma after bare adverbs and no colon openers (%s)', lang => {
    const html = fixture(lang);
    for (let seed = 1; seed <= 15; seed++) {
      const text = visible(humanizeHtml(html, { lang, intensity: 100, seed }).html);
      expect(text).not.toMatch(/(?:^|[.!?]\s+)(Также|Ещё|Плюс|Також|Ще|Także|Również|También|Também),/u);
      expect(text).not.toMatch(/(?:^|[.!?]\s+)(Заметим|Отмечу|Zauważmy|Звернімо увагу|Warto dodać):/u);
    }
  });
});

describe('0.36.1: mixed-script warnings', () => {
  it('reports words mixing Cyrillic and Latin letters', () => {
    const html = '<p>Платформа объединяет предложения судовладельцев, менеджеров и манning агентств по всему миру сегодня.</p>';
    const r = humanizeHtml(html, { lang: 'ru' });
    expect(r.warnings).toEqual([{ type: 'mixed_script', token: 'манning' }]);
  });

  it.each(LANGS)('has no warnings on clean fixtures (%s)', lang => {
    expect(humanizeHtml(fixture(lang), { lang }).warnings).toEqual([]);
  });
});

describe('0.37: contrast connectors are never dropped', () => {
  const cases: Array<[string, string, RegExp]> = [
    ['en', '<p>The tool is fast and cheap for small teams. However, it lacks reporting features for large agencies today.</p>', /\. (However|But|Still|Yet|Even so|That said|Though|Nevertheless|Nonetheless|On the other hand)\b/],
    ['ru', '<p>Инструмент быстрый и недорогой для небольших команд. Однако ему не хватает отчётов для крупных агентств сегодня.</p>', /\. (Однако|Но|Впрочем|При этом|Правда|Тем не менее|Всё же|Зато|Хотя)(?=[\s,])/u],
    ['pt', '<p>A ferramenta é rápida e barata para equipes pequenas. No entanto, faltam relatórios para grandes agências hoje em dia.</p>', /\. (No entanto|Mas|Contudo|Porém|Todavia|Ainda assim|Entretanto|Mesmo assim)(?=[\s,])/u],
  ];
  it.each(cases)('%s', (lang, html, re) => {
    for (let seed = 1; seed <= 25; seed++) {
      expect(textOf(humanizeHtml(html, { lang, intensity: 100, seed }).html)).toMatch(re);
    }
  });
});
