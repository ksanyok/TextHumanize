/**
 * Language detection — script + diacritics + stop-word voting.
 * Covers every language with a pack (en, ru, uk, de, fr, es, pl, pt, it).
 */

const STOP: Record<string, string[]> = {
  en: ['the', 'and', 'is', 'of', 'to', 'in', 'that', 'it', 'for', 'with', 'this', 'are', 'you'],
  de: ['der', 'die', 'und', 'das', 'ist', 'nicht', 'mit', 'ein', 'eine', 'für', 'auf', 'sich', 'auch'],
  fr: ['le', 'la', 'les', 'et', 'est', 'des', 'une', 'pour', 'dans', 'que', 'pas', 'sur', 'avec'],
  es: ['el', 'los', 'las', 'y', 'es', 'del', 'una', 'para', 'por', 'con', 'que', 'se', 'su'],
  pt: ['o', 'os', 'as', 'e', 'é', 'do', 'da', 'uma', 'para', 'com', 'não', 'que', 'em', 'seu'],
  it: ['il', 'gli', 'e', 'è', 'della', 'una', 'per', 'con', 'che', 'non', 'nel', 'sono', 'anche'],
  pl: ['i', 'w', 'jest', 'się', 'na', 'nie', 'z', 'do', 'że', 'to', 'oraz', 'jak', 'dla'],
};

export function detectLanguage(text: string): string {
  const sample = text.slice(0, 2000).toLowerCase();
  const cyr = (sample.match(/[а-яёіїєґ]/g) || []).length;
  const lat = (sample.match(/[a-zà-ÿąćęłńóśźż]/g) || []).length;
  if (cyr > lat) {
    const uk = (sample.match(/[іїєґ]/g) || []).length;
    const ru = (sample.match(/[ыэъё]/g) || []).length;
    return uk > ru ? 'uk' : 'ru';
  }
  const words = sample.match(/\p{L}+/gu) || [];
  const scores: Record<string, number> = {};
  for (const [lang, list] of Object.entries(STOP)) {
    const set = new Set(list);
    scores[lang] = words.reduce((s, w) => s + (set.has(w) ? 1 : 0), 0);
  }
  // Diacritics are strong signals.
  scores.pl += 3 * (sample.match(/[ąćęłńśźż]/g) || []).length;
  scores.pt += 3 * (sample.match(/[ãõ]/g) || []).length + 2 * (sample.match(/ção|ções/g) || []).length;
  scores.es += 3 * (sample.match(/[ñ¿¡]/g) || []).length + 2 * (sample.match(/ción/g) || []).length;
  scores.de += 3 * (sample.match(/[äöüß]/g) || []).length;
  scores.fr += 2 * (sample.match(/[èêëçœ]/g) || []).length;
  scores.it += 2 * (sample.match(/zione|zioni/g) || []).length;
  let best = 'en';
  for (const [lang, sc] of Object.entries(scores)) if (sc > scores[best]) best = lang;
  return best;
}
