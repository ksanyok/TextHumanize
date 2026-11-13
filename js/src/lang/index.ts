/**
 * Language pack registry.
 *
 * Dictionaries live in ./generated (exported from the Python packs by
 * scripts/export_js_langs.py); the hand-written en/ru packs only add the
 * legacy `synonyms`/`fillers` fields.
 */

import type { LangData, LangPack } from '../types';
import { en as enLegacy } from './en';
import { ru as ruLegacy } from './ru';
import { en } from './generated/en';
import { ru } from './generated/ru';
import { uk } from './generated/uk';
import { de } from './generated/de';
import { fr } from './generated/fr';
import { es } from './generated/es';
import { pl } from './generated/pl';
import { pt } from './generated/pt';
import { it } from './generated/it';

/**
 * Joints where splitting a long sentence keeps both halves grammatical.
 * Only coordinating joints after a comma (clause boundaries) and semicolons;
 * English ", and" is excluded because of serial commas ("A, B, and C").
 */
const SPLIT_JOINTS: Record<string, string[]> = {
  en: ['; ', ', but '],
  ru: ['; ', ', но ', ', а ', ', и '],
  uk: ['; ', ', але ', ', а ', ', і '],
  de: ['; ', ', aber '],
  fr: ['; ', ', mais '],
  es: ['; ', ', pero '],
  pl: ['; ', ', ale ', ', a '],
  pt: ['; ', ', mas '],
  it: ['; ', ', ma '],
};

function build(data: LangData, legacy?: { synonyms: Record<string, string[]>; fillers: string[] }): LangPack {
  return {
    code: data.code,
    name: data.name,
    bureaucratic: data.bureaucratic,
    phrases: data.phrases,
    connectorMap: data.connectors,
    connectors: Object.keys(data.connectors),
    synonyms: legacy?.synonyms ?? {},
    fillers: legacy?.fillers ?? [],
    contrast: new Set((data.contrast ?? []).map(k => k.toLowerCase())),
    splitJoints: SPLIT_JOINTS[data.code] ?? ['; '],
  };
}

const registry: Record<string, LangPack> = {
  en: build(en, enLegacy),
  ru: build(ru, ruLegacy),
  uk: build(uk),
  de: build(de),
  fr: build(fr),
  es: build(es),
  pl: build(pl),
  pt: build(pt),
  it: build(it),
};

const ALIASES: Record<string, string> = { ua: 'uk', br: 'pt', 'pt-br': 'pt', 'pt-pt': 'pt' };

/** Normalise a language code ("UA" → "uk", "pt-BR" → "pt"). */
export function normalizeLang(code: string | undefined): string {
  const c = String(code || '').trim().toLowerCase();
  return ALIASES[c] ?? c.split(/[-_]/)[0];
}

/** Get language pack by code. */
export function getLangPack(code: string): LangPack | undefined {
  return registry[normalizeLang(code)];
}

/** Check if language has deep support (full dictionary). */
export function hasDeepSupport(code: string): boolean {
  return normalizeLang(code) in registry;
}

/** List all supported languages. */
export function supportedLanguages(): string[] {
  return Object.keys(registry);
}
