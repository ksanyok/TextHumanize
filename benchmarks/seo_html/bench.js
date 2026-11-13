// Six-language SEO benchmark for the JS port. Usage: node benchmarks/seo_html/bench.js
const fs = require('fs');
const path = require('path');
const th = require(path.join(__dirname, '../../js/dist/index.js'));

const plain = h => h.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim();
const links = h => [...h.matchAll(/<a\b[^>]*>[\s\S]*?<\/a>/g)].map(m => m[0]).join('\n');
const tags = h => [...h.matchAll(/<\/?[a-z0-9]+/gi)].map(m => m[0]).join(',');
const words = t => t.toLowerCase().match(/[\p{L}\p{N}]+/gu) || [];
function changed(a, b) {
  const A = words(a), B = words(b), pool = new Map();
  A.forEach(w => pool.set(w, (pool.get(w) || 0) + 1));
  let common = 0;
  B.forEach(w => { if (pool.get(w) > 0) { common++; pool.set(w, pool.get(w) - 1); } });
  return 1 - (2 * common) / (A.length + B.length);
}

const rows = [];
for (const lang of ['ru', 'uk', 'en', 'pl', 'es', 'pt']) {
  const html = fs.readFileSync(path.join(__dirname, `${lang}.html`), 'utf8');
  const runs = 20;
  const t0 = process.hrtime.bigint();
  let r;
  for (let i = 0; i < runs; i++) r = th.humanizeHtml(html, { lang, profile: 'seo', intensity: 55 });
  const ms = Number(process.hrtime.bigint() - t0) / 1e6 / runs;
  rows.push({
    lang,
    'AI before': r.aiScoreBefore,
    'AI after': r.aiScoreAfter,
    edits: r.changes.filter(c => c.type !== 'typography').length,
    'changed words': `${(changed(plain(html), plain(r.html)) * 100).toFixed(1)}%`,
    'links kept': links(html) === links(r.html),
    'tags kept': tags(html) === tags(r.html),
    ms: +ms.toFixed(2),
  });
}
console.table(rows);
