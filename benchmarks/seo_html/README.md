# SEO HTML benchmark (ru / uk / en / pl / es / pt)

Six typical machine-written SEO articles with headings, lists and links.
`bench.js` runs the JS port's `humanizeHtml()` on each and reports the AI-style
score before/after, share of changed words, whether links and the tag sequence
survived, and the time per article.

```bash
cd js && npm run build && node ../benchmarks/seo_html/bench.js
```
